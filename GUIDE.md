# contentdigest guide

The behaviour of every public name in detail. Each Python block below runs as a test: a
comment line after a `print` holds what it prints.

## Fields as they arrive

`parse`, `parse_want`, `verify`, `Verifier` and `choose_algorithm` take a field as a `str`,
as ASCII `bytes` or `bytearray` (ASGI servers hand headers over as bytes), or as an iterable
of field lines, which are joined with commas as RFC 9110 section 5.3 describes. An empty
field, or no lines at all, is an empty dictionary, the same as an absent field.

The text is read by a complete [RFC 9651](https://www.rfc-editor.org/rfc/rfc9651) parser
that passes every parsing test of the httpwg structured-field test suite, including the
leniencies it marks as optional:

- Parameters are allowed and ignored, a repeated key keeps its last value, and spaces and
  tabs around the commas are allowed.
- A byte sequence may lack its `=` padding or have non-zero pad bits (RFC 9651 section 4.2.7
  asks parsers to accept both), and one `=` beyond the padding needed is accepted too,
  because RFC 9530 prints its `{"hello": "world"}` + LF digest that way. More padding, `=`
  inside the data, characters outside the base64 alphabet and line feeds are refused.
- A member of a digest field whose value is not a byte sequence, or a preference weight that
  is not an integer from 0 to 10, makes the whole field invalid: RFC 9651 section 2.2 says
  the entire field is then ignored. The library raises `DigestError` for the whole field, so
  the caller can do that.

```python
from contentdigest import DigestError, parse

field = ["sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:;x=1", b"new-hash=:AQID:"]
print(list(parse(field)), parse(field)["new-hash"])
# ['sha-256', 'new-hash'] b'\x01\x02\x03'
print(parse(""))
# {}
try:
    parse("sha-256=:AAAA:, md5=1")
except DigestError as error:
    print(error)
# the value of 'md5' is not a byte sequence
```

## Building a value

`make_digest(body, algos)` and `Digester(algos)` take registry keys in any case; the value
lists each algorithm once, in the order given (a repeated name keeps the place of its first
occurrence), as `name=:base64:` members separated by `", "`. Any iterable of names works,
a generator or iterator included, for `algos`, `accept` and `supported` alike. A body is any bytes-like object (`bytes`, `bytearray`, `memoryview`, `array.array`,
a ctypes object): its raw bytes are hashed, whatever its item size, shape or strides.
A `str` body raises `TypeError`, since only the caller knows its encoding.

Which bytes to hash is the caller's choice: `Content-Digest` covers the content of this
message (after content coding, only the range sent), `Repr-Digest` the whole selected
representation (RFC 9530 sections 2 and 3; its Appendix A has worked examples). To say that
no representation data was sent, hash the empty body (section 3).

```python
from contentdigest import Digester, make_digest

print(make_digest(b"", algos=["SHA-256", "sha-256"]))
# sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:
print(make_digest(memoryview(b"abcdef")[::2]) == make_digest(b"ace"))
# True
digester = Digester(["unixsum", "crc32c"])
digester.update(b'{"hello": "world"}')
print(digester.digests())
# {'unixsum': b'\x19\x05', 'crc32c': b'CyG '}
```

`Digester.value` and `Digester.digests` can be read at any time; feeding may continue.

## Verifying

`verify(field, body, accept=...)` and `Verifier(field, accept=...)` check only the members
whose algorithm is in `accept`, by default `ACTIVE_ALGORITHMS`. Every accepted member present
must match the body. Each comparison is constant-time and all of them run, so timing does not
tell which one failed. A digest of the wrong length is a mismatch. If no member is accepted,
`DigestError` is raised, because there is nothing to check; a field with only Deprecated
algorithms needs `accept` widened on purpose. Unknown algorithms in the field are ignored.

`Verifier` reads the field when it is created and hashes only the accepted algorithms
present (at most eight, however long the field). `verify()` can be called after any chunk.

```python
from contentdigest import Verifier, make_digest, verify

body = b'{"hello": "world"}'
field = make_digest(body, algos=["md5", "sha-256"]) + ", new-hash=:AAAA:"
print(verify(field, body), Verifier(field).algorithms)
# True ('sha-256',)
print(verify(field, body, accept=["md5", "sha-256"]))
# True
print(verify("sha-256=:AAAA:, " + make_digest(body, algos=["sha-512"]), body))
# False
```

RFC 9530 section 6.6 notes that a receiver depending on a digest for security is as weak as
the weakest algorithm it accepts; widening `accept` to Deprecated algorithms only makes sense
against accidental corruption.

## The algorithms

| Key | Status | Digest | Definition |
| --- | --- | --- | --- |
| `sha-256` | Active | 32 bytes | SHA-256 (`hashlib`) |
| `sha-512` | Active | 64 bytes | SHA-512 (`hashlib`) |
| `md5` | Deprecated | 16 bytes | MD5 (`hashlib`, `usedforsecurity=False`) |
| `sha` | Deprecated | 20 bytes | SHA-1 (`hashlib`, `usedforsecurity=False`) |
| `unixsum` | Deprecated | 2 bytes | the BSD checksum of UNIX `sum` |
| `unixcksum` | Deprecated | 4 bytes | the POSIX `cksum` CRC, length included |
| `adler` | Deprecated | 4 bytes | Adler-32 of RFC 1950 (`zlib`) |
| `crc32c` | Deprecated | 4 bytes | CRC-32C of RFC 9260 Appendix A |

The statuses are those of the IANA registry (unchanged since 2024-05-22 when checked on
2026-10-18). The four checksums are written big-endian, which is how RFC 9530 Appendix D
prints its sample values and how RFC 1950 stores Adler-32. `unixsum`, `unixcksum` and
`crc32c` are pure Python, so they are much slower than the hashes on large bodies.

## Preference fields

`parse_want` returns the weights by algorithm in field order, keeping algorithms it does not
know. `make_want` lower-cases the keys (ASCII only), refuses a key that is not a
structured-field key or appears twice, and weights outside 0 to 10. `choose_algorithm(field,
supported)` returns the supported algorithm with the highest weight above 0, the first one in
the field on a tie, and `None` when the field is absent or names none of them. Preferences
are only a hint (RFC 9530 section 4): on `None` a sender may still use any algorithm, or
none. A malformed field raises `DigestError`; catch it to treat such a field as absent.

```python
from contentdigest import choose_algorithm, make_want

print(choose_algorithm("sha-512=5, sha-256=5"), choose_algorithm("sha-256=0, md5=9"))
# sha-512 None
print(choose_algorithm("md5=9, sha-256=1", supported=["md5", "sha-256"]))
# md5
print(make_want({"SHA-256": 10, "future-hash": 1}))
# sha-256=10, future-hash=1
```

## Errors

| Raised | When |
| --- | --- |
| `DigestError` (a `ValueError`) | malformed field; a member that is not a byte sequence or a weight outside 0 to 10; unsupported algorithm name in `algos`, `accept` or `supported`; no algorithm in `algos`; no accepted member in a verified field; bad key, repeated key, bad weight or no entry in `make_want` |
| `TypeError` | a body that is `str`, not bytes-like, or a released `memoryview`; a field that is not text, bytes or lines of them; a bare string or bytes-like value (anything with the buffer protocol: `bytes`, `bytearray`, `memoryview`, `array.array`, `mmap`, subclasses included) where a collection of names is expected; a name that is not `str`; `make_want` given something other than a mapping, or a weight that is not an `int` (`bool` included) |

A body whose exporter refuses to give its buffer for another reason, such as a closed `mmap`,
raises the exporter's own error unchanged (usually a `ValueError`), as 0.2.0 did.

A malformed field is quoted as a window of at most 40 characters around the error, with its
offset. A name or key is quoted to 40 characters, with its length when it is longer. A list
of names shows at most five, and long type names are cut, so a hostile megabyte field gives a
short message. A `DigestError` pickles as `contentdigest.DigestError`.

## Command line

```
contentdigest [-a NAME]... [--verify VALUE] [FILE]
```

It prints the field value of `FILE` (or standard input when `FILE` is `-` or missing), or with
`--verify` prints `match` or `mismatch`. `-a` repeats; it sets the algorithms to print (default
`sha-256`), or with `--verify` the ones accepted (default the Active ones). Exit status: 0 printed
or matched, 1 mismatch, 2 bad input or an I/O error: a usage error, an unsupported algorithm, a
malformed field, no accepted algorithm, an unreadable file, no standard input, or a result that
cannot be written (a closed pipe exits 2 quietly). Errors go to standard error as one short line.

## Typing

The package ships `py.typed` and passes `mypy --strict`. Bodies are typed as
`collections.abc.Buffer` (`typing_extensions.Buffer` before Python 3.12) and fields as `str |
bytes | bytearray | Iterable[str | bytes | bytearray]`. `typing.get_type_hints` resolves every
public function and method at run time. Before Python 3.12 there is no run-time `Buffer`, so
there the body hint resolves to `bytes | bytearray | memoryview`: static checkers still see
`Buffer`, but a run-time checker (pydantic, typeguard, beartype) then refuses an
`array.array` or ctypes body that the functions themselves accept.

## Stable signatures

The signatures are the ones 0.2.0 had and are kept as they are. The collection of names
that says what to build or answer with, `algos` in `make_digest` and `Digester` and
`supported` in `choose_algorithm`, may be passed by position, so `Digester(["sha-512"])` and
`make_digest(body, ["md5"])` keep working. `accept` in `verify` and `Verifier` is keyword-only,
so that a third argument to `verify(field, body, ...)` cannot be taken for an expected
value. The short name `algos` stays too, since renaming it would break 0.2.0 callers that pass
it by keyword.

## Upgrading from 0.2.0

Every result 0.2.0 gave for valid input is the same; the differences are in errors and edges:

- Error messages are shorter and quote inputs only partly.
- `make_want` raises `TypeError` for a non-mapping (was `AttributeError`) and `DigestError` for
  a weight too large to print (was a plain `ValueError`).
- A released `memoryview` body raises `TypeError` (was a plain `ValueError`). Any other buffer
  its exporter refuses, such as a closed `mmap`, still raises the exporter's own error.
- Any bytes-like value (`bytearray`, `memoryview`, `array.array`, `mmap`, ...) given as `algos`,
  `accept` or `supported` raises `TypeError`, as `bytes` already did. An empty one used to pass
  as no names at all.
- `DigestError`, `Digester` and `Verifier` report `contentdigest` as their module; 0.2.0
  pickles of `DigestError` still load.
- The command exits 2 instead of 120 when its reader closes the pipe, 2 with a message instead
  of a traceback when standard input is closed, and 2 instead of 0 when standard output is
  closed.

## How the results were checked

- RFC 9530, its erratum 8890, RFC 9651 and the IANA registry are fetched by
  `scripts/fetch_upstream.py` (hashes in `tests/upstream/MANIFEST.json`); every digest value and
  preference RFC 9530 prints is read from the text and reproduced, and so is its registry table.
  Erratum 8890 (status Reported) is right: with the corrected Brotli bytes, which Node.js
  decompresses to the example body, the published digests match.
- The httpwg structured-field test suite, all 1,598 parsing cases.
- The CRC-32C table and polynomial of RFC 9260, the CRC examples of RFC 7143, the POSIX `cksum`
  polynomial, length rule and table, the Adler-32 definition of RFC 1950 and the CRC
  catalogue's check values, each read from the fetched text.
- Output captured from GNU coreutils 8.32 (`sum`, `cksum`, `md5sum`, `sha1sum`, `sha256sum`,
  `sha512sum`), Windows `certutil` and the Java 21 runtime (`Adler32`, `CRC32C`) for 27 inputs,
  the largest just over 1 MiB (`tests/program_output.json`).
- `http_sf`, by an author of RFC 9651: with its strict base64 decoding swapped in, this parser
  gives the same results on 30,000 seeded valid and broken dictionaries (on Python 3.12 and
  later, whose strict base64 refuses excess padding as this parser does), apart from limits of
  `http_sf` (before 1.4.0 it refused an empty dictionary; it stops at dates beyond Python's
  `datetime`); without the swap it accepts a superset with the same values.
  `requests-http-signature` builds the same `Content-Digest` values.
- Seeded fuzz and linear-time tests, and the PyPI release 0.2.0 as an oracle for the upgrade.
