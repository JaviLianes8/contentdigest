# contentdigest

Build and verify RFC 9530 Content-Digest and Repr-Digest headers, zero dependencies

## Install

```
pip install contentdigest
```

## Usage

```python
from contentdigest import make_digest, parse, verify

body = b'{"hello": "world"}'

# Build a header value for Content-Digest or Repr-Digest.
header = make_digest(body)
# "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"

# Cover more than one algorithm in a single value.
make_digest(body, algos=("sha-256", "sha-512"))

# Read the raw digest bytes back out, keyed by algorithm.
parse(header)  # {"sha-256": b"..."}

# Check a received header against the body you have.
verify(header, body)       # True
verify(header, b"other")   # False
```

The header value is identical for both headers RFC 9530 defines, so the same
string works whether you send it as `Content-Digest` or `Repr-Digest`. Both
`sha-256` and `sha-512` are supported. `verify` compares in constant time and
raises `DigestError` on a malformed header or one that carries no supported
algorithm.

## Why

[RFC 9530](https://www.rfc-editor.org/rfc/rfc9530) replaced the deprecated
`Digest` header (RFC 3230) with `Content-Digest` and `Repr-Digest`, which carry
their digests as RFC 8941 structured-field dictionaries. No maintained, typed,
zero-dependency Python package builds and verifies them: the digest logic sits
copied inside larger frameworks, and the unrelated `python-digest` on PyPI is an
HTTP Digest authentication helper. This is a small primitive that does the one
job and ships type information.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
