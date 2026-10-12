# contentdigest

Build and verify the HTTP `Content-Digest` and `Repr-Digest` fields of
[RFC 9530](https://www.rfc-editor.org/rfc/rfc9530), and read and answer the
`Want-Content-Digest` / `Want-Repr-Digest` preference fields. Typed, streaming, zero
dependencies.

## Install

```
pip install contentdigest
```

## Build and check a field

```python
from contentdigest import make_digest, parse, verify

body = b'{"hello": "world"}'

field = make_digest(body)
print(field)
# sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:

print(make_digest(body, algos=["sha-512", "sha-256"]).split(", ")[1] == field)
# True

print(parse(field)["sha-256"].hex()[:16])
# 5f8f04f6a3a892aa

print(verify(field, body), verify(field, b"tampered"))
# True False
```

The value is the same for both fields, so the string works as `Content-Digest` or as
`Repr-Digest`. What changes is which bytes you hash: `Content-Digest` covers the message
content as sent (after content coding, only the range you send), `Repr-Digest` covers the
whole selected representation (RFC 9530 sections 2 and 3).

## Stream a large body

`Digester` builds a value from chunks. `Verifier` takes the received field first, as headers
arrive before the body, then the chunks.

```python
from contentdigest import Digester, Verifier

digester = Digester(["sha-256", "sha-512"])
for chunk in (b'{"hello": ', b'"world"}'):
    digester.update(chunk)
field = digester.value()
print(field.split(", ")[0])
# sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:

verifier = Verifier(field)
print(verifier.algorithms)
# ('sha-256', 'sha-512')
for chunk in (b'{"hello": ', b'"world"}'):
    verifier.update(chunk)
print(verifier.verify())
# True
```

## Which algorithms count

```python
from contentdigest import ACTIVE_ALGORITHMS, DigestError, make_digest, verify

print(sorted(ACTIVE_ALGORITHMS))
# ['sha-256', 'sha-512']

body = b'{"hello": "world"}'
legacy = make_digest(body, algos=["md5"])
print(legacy)
# md5=:Sd/dVLAcvNLSq16eXua5uQ==:

try:
    verify(legacy, body)
except DigestError as error:
    print(type(error).__name__)
# DigestError

print(verify(legacy, body, accept=["md5"]))
# True
```

All eight algorithms of the IANA registry are built in: `sha-256` and `sha-512`
(`ACTIVE_ALGORITHMS`), and `md5`, `sha`, `unixsum`, `unixcksum`, `adler` and `crc32c`
(`DEPRECATED_ALGORITHMS`); `SUPPORTED_ALGORITHMS` is both. `make_digest` builds any of them
when asked. `verify` and `Verifier` check only the algorithms in `accept`, which defaults to
the Active ones, because RFC 9530 says the Deprecated ones MUST NOT be relied on where an
attacker could change the content. Widen `accept` only to catch accidental corruption.

## Preference fields

```python
from contentdigest import choose_algorithm, make_want, parse_want

print(parse_want("sha-512=3, sha-256=10, unixsum=0"))
# {'sha-512': 3, 'sha-256': 10, 'unixsum': 0}

print(choose_algorithm("sha-512=3, sha-256=10, unixsum=0"))
# sha-256

print(choose_algorithm("sha=10"))
# None

print(make_want({"sha-512": 10, "sha-256": 5}))
# sha-512=10, sha-256=5
```

`choose_algorithm(field, supported=ACTIVE_ALGORITHMS)` returns the supported algorithm with
the highest weight above 0, the first one in the field on a tie, and `None` when the field
is absent or names none of them. Preferences are only a hint: on `None` you may still send
any digest, or none. `parse_want` reads a field and `make_want` writes one.

## Command line

```
$ contentdigest body.json
sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
$ contentdigest -a sha-512 -a sha-256 body.json
$ contentdigest --verify "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:" body.json
match
```

The file is read in chunks; `-` or no file reads standard input. With `--verify`, the exit
status is 0 on a match, 1 on a mismatch and 2 on bad input; `-a` then sets the accepted
algorithms. `python -m contentdigest` does the same.

## The exact rules

- Fields are parsed with a complete RFC 9651 structured-field parser that passes every
  parsing test of the httpwg test suite. A field may be a `str`, ASCII `bytes` (as ASGI
  servers hand headers over) or an iterable of field lines, which are joined with commas.
- Every member of a digest field must be a byte sequence, and every weight of a preference
  field an integer from 0 to 10. Anything else makes the whole field invalid and raises
  `DigestError` (a `ValueError`), as RFC 9651 requires. Parameters are ignored. A repeated
  key keeps its last value. An empty field is an empty dict, the same as an absent field.
- Byte sequences decode as RFC 9651 section 4.2.7 asks: missing `=` padding, one `=` too
  many (as some RFC 9530 examples print) and non-zero pad bits are accepted; characters
  outside the base64 alphabet are not.
- `verify` and `Verifier` require every accepted member present to match, compare in
  constant time and run every comparison, and raise `DigestError` when no member is
  accepted, since then there is nothing to check.
- Bodies are any bytes-like object. Wrong argument types raise `TypeError`, including a
  bare string where a collection of algorithm names is expected.
- The checksums `unixsum` (BSD `sum`), `unixcksum` (POSIX `cksum`), `adler` and `crc32c` are
  big-endian, which is what reproduces the RFC 9530 Appendix D sample values. They are pure
  Python, so they are much slower than the hashes.

## Why

RFC 9530 replaced the `Digest` field of RFC 3230 with `Content-Digest` and `Repr-Digest`,
which carry their digests as RFC 9651 structured-field dictionaries. Getting them right
means parsing structured fields properly, knowing which registered algorithms are safe to
rely on, and hashing while the body streams. This package does that one job, ships type
information and has no dependencies. (The unrelated `python-digest` on PyPI is an HTTP
Digest authentication helper.)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/contentdigest/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
