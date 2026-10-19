# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The public API is now stable: the twelve names in `contentdigest.__all__`, their
signatures, defaults and error types follow Semantic Versioning from this release on.

### Changed

- `DigestError`, `Digester` and `Verifier` show and pickle as `contentdigest.<Name>`
  instead of the private module that defines them; `DigestError` pickles made by 0.2.0
  still load.
- `md5` and `sha` digests are computed with `usedforsecurity=False`, since RFC 9530 allows
  them only against accidental corruption.
- The command exits with status 2 when it cannot read standard input or write its result,
  and its help text says so.
- A released `memoryview` passed as a body raises `TypeError`, like any other body that is
  not bytes-like, instead of the plain `ValueError` of `memoryview()`. Any other buffer its
  exporter refuses, such as a closed `mmap`, still raises the exporter's own error.
- Any bytes-like value (any object with the buffer protocol, such as `bytearray`,
  `memoryview`, `array.array` or `mmap`) given as `algos`, `accept` or `supported` raises
  `TypeError`, as `bytes` already did. An empty one used to pass as no names at all, so
  `choose_algorithm` returned `None` and the others raised `DigestError`; a non-empty one
  failed on its first item instead.
- A collection of algorithm names (`algos`, `accept`, `supported`) counts each name once,
  so passing a name many times no longer makes checking a field slower with every repeat.
- Fields are typed `str | bytes | bytearray | Iterable[str | bytes | bytearray]`, which is
  what 0.2.0 already accepted at run time.
- The sdist no longer ships the repository's process notes or `.github`; the project URL
  `Repository` is now `Source`. It ships `.gitignore`, which the build backend always adds.
- The signatures are those of 0.2.0 and are now stable: `algos` and `supported` may be
  passed by position, `accept` only by keyword (see the GUIDE).

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
- `scripts/release.ps1` refused to upload any version once the name was on PyPI; it now
  refuses only a version that is already there, and only from a clean tree.

### Added

- Runnable examples in every public docstring, run as doctests, and a GUIDE.
- Tests that read RFC 9530 (every digest value it prints), its erratum 8890, RFC 9651, the
  IANA registry, RFC 9260, RFC 7143, RFC 1950, the POSIX `cksum` page and the CRC catalogue
  from fetched copies; that compare every algorithm with output captured from GNU coreutils,
  Windows certutil and the Java runtime, with Node.js decoding the Brotli example of
  erratum 8890; that compare the parser with `http_sf` and
  the built values with `requests-http-signature`; seeded fuzz, linear-time and installed
  wheel tests; and the PyPI release 0.2.0 as an oracle for the upgrade.

## [0.2.0] - 2026-10-18

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

## [0.1.0] - 2026-10-11

Never published to PyPI; 0.2.0 is the first release there.

- First version: `make_digest`, `parse` and `verify` for RFC 9530 Content-Digest
  and Repr-Digest header values, with `sha-256` and `sha-512` support and
  constant-time verification.
