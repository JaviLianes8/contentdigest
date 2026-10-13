# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `Digester` and `Verifier` to build and check a field while the body streams.
- All eight algorithms of the IANA registry: `md5`, `sha`, `unixsum`, `unixcksum`, `adler`
  and `crc32c` next to `sha-256` and `sha-512`, with `ACTIVE_ALGORITHMS` and
  `DEPRECATED_ALGORITHMS`.
- `parse_want`, `make_want` and `choose_algorithm` for the Want-Content-Digest and
  Want-Repr-Digest preference fields.
- `verify(..., accept=...)` to choose which algorithms are checked.
- Fields may be `bytes` or several field lines; bodies may be any bytes-like object.
- The `contentdigest` command (also `python -m contentdigest`).

### Changed

- Fields are parsed with a complete RFC 9651 structured-field parser, checked against the
  httpwg test suite. Tabs, parameters and repeated keys are handled as the RFC says.
- Byte sequences with missing padding or non-zero pad bits are accepted, as RFC 9651 asks,
  and so is one `=` beyond the padding needed, so the over-padded examples printed in
  RFC 9530 verify.
- An empty field parses to an empty dict instead of raising.
- `verify` checks only Active algorithms unless `accept` says otherwise, and runs every
  comparison.
- A bare string passed as `algos` or `accept`, or a body that is not bytes-like, raises
  `TypeError`.

## [0.1.0]

- First release: `make_digest`, `parse` and `verify` for RFC 9530 Content-Digest
  and Repr-Digest header values, with `sha-256` and `sha-512` support and
  constant-time verification.
