# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-18

The public API is now stable: the twelve names in `contentdigest.__all__`, their
signatures, defaults and error types follow Semantic Versioning from this release on.

### Changed

- `DigestError`, `Digester` and `Verifier` show and pickle as `contentdigest.<Name>`
  instead of the private module that defines them; `DigestError` pickles made by 0.2.0
  still load.
- `md5` and `sha` digests are computed with `usedforsecurity=False`, since RFC 9530 allows
  them only against accidental corruption.
- The command exits with status 2 when it cannot read standard input or write its result,
  and its usage line says so.

### Fixed

- Error messages stay short for any input: a name or key is quoted to 40 characters with
  its length, a list of names to five, and type names are cut. 0.2.0 quoted inputs whole,
  so a 1 MB algorithm name gave a 1 MB message and a field of 100,000 members was listed
  in full by the "no accepted algorithm" message.
- `make_want` raised a plain `ValueError` while describing a weight too large to print;
  it raises `DigestError`. Given something other than a mapping it raised
  `AttributeError`; it raises `TypeError`.
- `typing.get_type_hints` failed with `NameError` on `make_digest`, `verify` and the
  `update` methods.
- The package no longer exposes a stray `annotations` attribute.
- The command no longer exits 120 with "Exception ignored" on standard error when its
  reader closes the pipe, no longer exits 0 having printed nothing when standard output is
  closed, no longer shows a traceback when standard input is closed, and no longer echoes
  a whole argument in a usage error.
- Importing `contentdigest.__main__` no longer runs the command.

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
