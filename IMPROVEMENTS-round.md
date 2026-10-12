# contentdigest improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Full RFC 9651 structured-field parser, checked against the pinned httpwg suite
- [x] Byte sequences decoded as RFC 9651 says (missing or extra padding, non-zero pad bits)
- [x] Algorithm registry: all eight IANA algorithms, Active versus Deprecated, verify accepts Active only by default
- [x] Streaming `Digester` and `Verifier`, bytes-like bodies, `str` or `bytes` fields, several field lines
- [x] Want-Content-Digest / Want-Repr-Digest: `parse_want`, `make_want`, `choose_algorithm`
- [x] Command line tool (`python -m contentdigest`)
- [x] Contracts: fetched RFC vectors, httpwg suite, typing snippet, README examples, installed wheel e2e
- [x] Mutation run (guards removed one at a time, each must fail the suite)
- [x] Docs: README, CHANGELOG, docstrings, packaging metadata
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` (not on PyPI) ships `make_digest`, `parse`, `verify`, `SUPPORTED_ALGORITHMS` and
`DigestError`, with `sha-256` and `sha-512`. Read as a user who receives these fields from
real peers, it has these gaps:

- `parse` splits on commas and calls `base64.b64decode(validate=True)`. It is not an RFC 9651
  parser: it accepts no tabs around commas, no parameters, and it fails on byte sequences the
  RFC says parsers SHOULD accept. The RFC 9530 examples themselves (B.5, B.6, B.11, C.1) send
  `sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg==:` with one `=` too many; 0.1.0 raises
  on it. An unpadded value raises too.
- An empty field raises, but RFC 9651 says an empty dictionary is the same as an absent field.
- Several field lines (a header plus a trailer merged, or a split header) cannot be passed.
- Only two of the eight registered algorithms. A peer migrating from RFC 3230 that sends
  `md5` or `crc32c` cannot be checked even when the application accepts the risk.
- No streaming: the whole body must be in memory to build or verify a digest, while RFC 9530
  section 6.4 calls out hashing while streaming as the point of trailers.
- No support at all for Want-Content-Digest and Want-Repr-Digest (section 4).
- Wrong types fail deep inside `hashlib`; `algos="sha-256"` iterates characters.
- Packaging: no Python version classifiers, no keywords, README examples never run, no wheel test.

## Sources (fetched 2026-10-12)

- RFC 9530, https://www.rfc-editor.org/rfc/rfc9530.txt: field definitions (sections 2 to 4:
  dictionary of byte sequences, Want-* dictionary of integers 0 to 10), the registry table
  (section 7.2: `sha-512` and `sha-256` Active; `md5`, `sha`, `unixsum`, `unixcksum`, `adler`,
  `crc32c` Deprecated, MUST NOT be used in adversarial settings), Appendix B and C examples and
  Appendix D sample values for all eight algorithms over `{"hello": "world"}`.
- RFC 9530 errata, https://www.rfc-editor.org/errata/rfc9530: erratum 8890 (Reported) says the
  Brotli bytes of B.4 and B.6 are wrong in their first two bytes; with `0B 09` instead of
  `8B 08` the published digests match, and over the published bytes SHA-256 gives
  `MklYnI/SsUF/5X7enJ2TU+DFjodRObdKLFaPPLe/Kcw=`.
- IANA registry, https://www.iana.org/assignments/http-digest-hash-alg/http-digest-hash-alg.xml
  (updated 2024-05-22): still the same eight entries and statuses.
- RFC 9651, https://www.rfc-editor.org/rfc/rfc9651.txt: section 4.2 parsing algorithms
  (dictionary, list, item, every bare item type including Date and Display String), section
  4.2.7 (parsers SHOULD NOT fail on missing padding or non-zero pad bits, MUST fail on other
  characters), section 2.2 (a field-specific constraint violation ignores the whole field).
- httpwg structured-field-tests at commit `781ba38464b2ec4c547e1e14d007d4f5ace7457e`,
  https://github.com/httpwg/structured-field-tests/tree/781ba38464b2ec4c547e1e14d007d4f5ace7457e:
  every parsing test file. Not committed (third-party corpus): `scripts/fetch_vectors.py`
  fetches it into a gitignored folder, checked against a tracked MANIFEST (URL, revision,
  size, SHA-256, licence); the suite tests skip when it is absent.

Derived, not copied: which UNIX `sum` and `cksum` variants RFC 9530 means. The BSD 16-bit
`sum` and the POSIX `cksum` CRC (length appended), both big-endian, reproduce the Appendix D
values `GQU=` and `7zsHAA==`; `adler` and `crc32c` are big-endian for the same reason.

## Ranked improvements

1. **A real RFC 9651 parser.** Private, complete (all item types, inner lists, parameters,
   limits), run against every parsing test in the pinned httpwg suite. Digest fields then
   accept tabs, parameters (ignored, as section 2.3 asks) and several field lines, and reject
   exactly what the RFC rejects. A member whose value is not a byte sequence makes the whole
   field invalid (section 2.2).
2. **Byte sequences per section 4.2.7.** Missing padding, over-padding up to `==` and
   non-zero pad bits decode; any other character, inner `=` or impossible length raises.
   The RFC's own over-padded examples verify.
3. **The full algorithm registry with its statuses.** `ACTIVE_ALGORITHMS`,
   `DEPRECATED_ALGORITHMS`, `SUPPORTED_ALGORITHMS`. `make_digest` builds any of them on
   request; `verify` checks only Active ones unless the caller widens `accept`. Every
   accepted member present must match, compared in constant time with no early exit, so the
   field is as strong as its weakest accepted algorithm and no weaker.
4. **Streaming.** `Digester` builds a value from chunks; `Verifier` reads the field first,
   then takes chunks, matching how headers arrive before a body. Bodies are any C buffer;
   fields are `str`, `bytes` (ASGI) or an iterable of field lines.
5. **Integrity preference fields.** `parse_want` (integers 0 to 10, anything else raises),
   `make_want`, and `choose_algorithm` (highest weight above 0 among what the server
   supports, first listed on a tie, `None` when nothing fits).
6. **Honest types and errors.** `DigestError` (a `ValueError`) for bad field content and
   unknown algorithms, `TypeError` for wrong argument types, including a bare `str` where a
   collection of names is expected.
7. **A small command line tool.** `contentdigest FILE` prints a field value to paste into a
   request; `--verify VALUE` exits 0 on a match, 1 on a mismatch, 2 on bad input. It streams.
8. **Contracts that bite.** RFC vectors copied from the fetched text with their URLs, the
   pinned httpwg suite with a hash manifest, a mypy snippet for the public types, executed
   README examples, an installed-wheel e2e, and a mutation run.
9. **Docs and packaging.** README with runnable examples and exact rules, CHANGELOG 0.2.0,
   classifiers and keywords, sdist without this file.

Left out on purpose: a structured-field serializer for arbitrary values (only the two shapes
these fields use are emitted), framework middleware (one line of glue per framework, and it
would add dependencies), content-coding helpers (which bytes to hash is the caller's
decision; the README explains Content-Digest versus Repr-Digest), and the obsolete RFC 3230
`Digest` field.

## Verification

- Gates: `ruff format --check .`, `ruff check .`, `mypy --strict src` (also `src tests`) and
  `pytest` exit 0 on Windows with Python 3.13 and 3.14; the wheel e2e passes with
  `CONTENTDIGEST_E2E=1` (it builds the wheel, installs it in a fresh venv, drives the API
  from an empty folder, and runs the installed `contentdigest` script and `python -m`).
- The httpwg suite: 1598 parsing cases, all passing, including every `can_fail` leniency.
- Mutations: 62 guards were removed or altered one at a time (every base64 rule, key and
  token characters, number limits, string and display string rules, booleans, dates, the
  trailing input and trailing comma checks, repeated keys, inner list separators, tabs,
  parameter spacing, field line joining, ASCII decoding of bytes, the byte sequence member
  rule, all versus any, the Active-only default and filter, the empty and unknown algorithm
  errors, name lower-casing, the bare string refusal, buffer flattening, each checksum's
  rotation, length, reflection, final XOR, byte order and seed, the Want weight range and
  type, `make_want` validation, the tie, zero and supported rules of `choose_algorithm`, and
  the command's accept default, exit codes and file errors). Every one made the suite fail.
  Two earlier survivors were equivalent mutants (a decimal length limit the digit checks
  already imply, and an ASCII check on `str` that the grammar already implies); that code was
  removed.
- The review fixes added 9 more mutations (padding cap, all-padding content, a
  short-circuiting comparison, `==` instead of `hmac.compare_digest`, the error excerpt,
  ASCII-only lower-casing in both places, repeated `make_want` keys, CLI stream redirection);
  every one is killed.

## Review findings fixed

- The httpwg corpus was committed verbatim. It now lives in a gitignored folder fetched by
  `scripts/fetch_vectors.py` and checked against a tracked MANIFEST (URL, revision, size,
  SHA-256, licence); the suite tests skip without it, and the corpus was removed from the
  branch history.
- Up to two `=` were accepted whatever the length (`abcd==`, and `==` decoded to an empty
  digest), and the docs attributed over-padding to RFC 9651. Now at most one `=` beyond the
  padding needed is accepted, all-padding content is rejected, and the docs say which
  leniency comes from where. Tests pin both sides.
- "Runs every comparison" had no test: a spy on `hmac.compare_digest` now proves both the
  count and that the constant-time function is the one used.
- Error messages embedded the whole field (2 MB in, 2 MB message out); they quote a short
  excerpt now.
- `choose_algorithm` raising on a malformed field is documented (docstring and README).
- `str.lower()` folded non-ASCII letters (Kelvin sign) into registry names; names are
  lower-cased only when ASCII.
- argparse help and usage errors bypassed the injected CLI streams; they are redirected.
- `make_want` silently merged keys that differ only in case; it raises now.
- A redundant `bytearray` conversion was removed; the contract test file got its docstring.

## Left uncovered

- Python 3.10 is in the classifiers but was not available on any machine here; the suite
  ran on 3.11, 3.13 and 3.14.
- The CLI and typing tests use pytest's `tmp_path` for a real file and a mypy snippet.
