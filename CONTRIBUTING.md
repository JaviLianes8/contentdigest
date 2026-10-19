# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
python scripts/fetch_upstream.py
```

The second line downloads the third-party files the tests read: RFC 9530 and its erratum,
RFC 9651, the IANA registry, the httpwg structured-field test corpus, and the RFCs, POSIX
page and catalogue that define the checksums. They are not kept in the repository;
`tests/upstream/MANIFEST.json` records each URL, revision, size and sha256. Without them,
the tests that use them are skipped.

The checksum values captured from real programs (GNU coreutils, Windows certutil, the
Java runtime), and Node.js decoding the Brotli example of erratum 8890, are in
`tests/program_output.json`, written by `scripts/capture_program_output.py`.

## Before you open a pull request

- Keep public API in `src/contentdigest/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
