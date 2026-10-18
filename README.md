# contentdigest

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Build and verify the HTTP `Content-Digest` and `Repr-Digest` fields of
[RFC 9530](https://www.rfc-editor.org/rfc/rfc9530), and read and answer the
`Want-Content-Digest` and `Want-Repr-Digest` preference fields. Typed, streaming, zero
dependencies.

## The problem

RFC 9530 replaced the `Digest` field of RFC 3230 in February 2024. Its fields are
[RFC 9651](https://www.rfc-editor.org/rfc/rfc9651) structured-field dictionaries of byte
sequences, keyed by the names of an IANA registry in which only `sha-256` and `sha-512` are
safe where an attacker may change the content. Getting a field right takes a real
structured-field parser (padding, parameters, several field lines), knowing which algorithms
to trust, hashing while the body streams and comparing in constant time.

## Install

```
pip install contentdigest
```

## Quick start

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
content as sent (after content coding, only the range you send), `Repr-Digest` the whole
selected representation (RFC 9530 sections 2 and 3).

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
    print(error)
# no accepted algorithm in the field (it has 'md5'; accepted are 'sha-256', 'sha-512')

print(verify(legacy, body, accept=["md5"]))
# True
```

All eight algorithms of the IANA registry are built in: `sha-256` and `sha-512`
(`ACTIVE_ALGORITHMS`), and `md5`, `sha`, `unixsum`, `unixcksum`, `adler` and `crc32c`
(`DEPRECATED_ALGORITHMS`); `SUPPORTED_ALGORITHMS` is both. `make_digest` builds any of them.
`verify` and `Verifier` check only the algorithms in `accept`, by default the Active ones,
because RFC 9530 says the Deprecated ones MUST NOT be used where the setting may be
adversarial. Every accepted member present must match.

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

## Command line

```
$ contentdigest body.json
sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
$ contentdigest -a sha-512 -a sha-256 body.json
$ contentdigest --verify "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:" body.json
match
```

The file is read in chunks; `-` or no file reads standard input. The exit status is 0 when a
value was printed or matched, 1 on a mismatch and 2 on bad input or an I/O error. `-a` sets
the algorithms to print, or with `--verify` the ones accepted. `python -m contentdigest`
does the same.

## API

| Name | What it does |
| --- | --- |
| `make_digest(body, algos=("sha-256",))` | field value for a body |
| `parse(field)` | raw digests by algorithm |
| `verify(field, body, *, accept=ACTIVE_ALGORITHMS)` | whether every accepted digest matches |
| `Digester(algos=("sha-256",))` | `update`, `digests`, `value` over a streamed body |
| `Verifier(field, *, accept=ACTIVE_ALGORITHMS)` | `algorithms`, `update`, `verify` over a streamed body |
| `parse_want(field)` | preference weights by algorithm |
| `make_want(preferences)` | preference field value |
| `choose_algorithm(field, supported=ACTIVE_ALGORITHMS)` | the algorithm to answer with, or `None` |
| `ACTIVE_ALGORITHMS`, `DEPRECATED_ALGORITHMS`, `SUPPORTED_ALGORITHMS` | registry keys by status |
| `DigestError` | a `ValueError` for a malformed field or an unsupported algorithm |

A field may be a `str`, ASCII `bytes` or an iterable of field lines; a body any bytes-like
object. Wrong argument types raise `TypeError`. The
[GUIDE](https://github.com/JaviLianes8/contentdigest/blob/main/GUIDE.md) gives the exact
rules, the errors and how the results were checked; the
[CHANGELOG](https://github.com/JaviLianes8/contentdigest/blob/main/CHANGELOG.md) lists what
changed from 0.2.0.

## Why this package

In Python, these fields otherwise turn up inside HTTP signing libraries (checked in October
2026):

- `requests-http-signature` 0.7.1 (its latest release, April 2022) sets `Content-Digest` with
  `sha-256` or `sha-512` while signing a Requests request, and its verifier rejects a field
  that carries any other algorithm as well.
- `http-message-signatures` 2.0.1 leaves checking the content digest to the caller, as its
  README says.
- `http_sf` and `http-sfv` parse structured fields in general; the hashing, the registry and
  the preference fields stay with you.

contentdigest does that one job: both fields and both preference fields, the eight registered
algorithms with their statuses, streaming in both directions, a structured-field parser that
passes the httpwg test suite, type information and no dependencies. (The unrelated
`python-digest` on PyPI implements HTTP Digest authentication.)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/contentdigest/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
