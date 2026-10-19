# contentdigest 1.0.0 certification report

The 1.0.0 certification bar applied to contentdigest. PyPI has 0.2.0 (uploaded 2026-10-18),
whose wheel holds byte for byte the modules of `main` at 24f06de, so every change listed here
is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (24f06de, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: specifications and registries fetched live, reference implementations and real program output (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15), final run
- [x] PR #3 and trace guard CLEAN
- [ ] Five QA lenses (item 19): round 1 fixed, awaiting re-verification
- [ ] Independent reviewer (item 16)
- [ ] Merge and publish (item 17), left to the maintainer

## Scorecard (author's run)

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: the twelve names of 0.2.0 kept, signatures, defaults and parameter names pinned by `tests/test_contract_api.py`; every behaviour change in the CHANGELOG |
| 2 | `__all__` exact, no private imports in docs | PASS: `tests/test_contract.py`, and the installed wheel checks `dir()` against `__all__` |
| 3 | Docstrings with runnable examples, doctests | PASS: 16 doctests run with the suite; README and GUIDE examples run by `tests/test_docs.py` |
| 4 | Typed end to end | PASS: `mypy --strict src tests scripts`, `py.typed` shipped, hints resolve at run time, consumer typing checked by `tests/test_typing.py` |
| 5 | Typed, documented, bounded errors | PASS: `DigestError` (a `ValueError`) and `TypeError`; inputs quoted to 40 characters, lists to five names, command messages to 300 characters |
| 6 | Contract tests of every public name | PASS: `tests/test_contract*.py` plus a behaviour file per area |
| 7 | Real ground truth | PASS: 30 fetched sources re-fetched 2026-10-19, hashes unchanged; captured and live program output; three independent implementations |
| 8 | Real e2e from the wheel | PASS: wheel and sdist built, wheel driven from an empty folder with `-I` and the command by subprocess, PyPI 0.2.0 upgraded in place |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: three seeds, also at ten times the default scale; linear-time checks |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, the interpreters of this PC; 3.13t is not installed here |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge, problem, honest comparison checked 2026-10-19 |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS: 3.10 to 3.14 classifiers, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` |
| 14 | sdist and wheel contents | PASS: see Packaging |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #3 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 34 author mutants, all killed; the 4 first caught only by optional checks now also killed by contracts that always run |
| 19 | Five independent QA lenses | pending |

## Baseline on 0.2.0 (before any change)

At 24f06de: `ruff format --check .`, `ruff check .` and `mypy --strict src tests` exit 0 (this
PC, 2026-10-19); `pytest` 1822 passed on the laptop, CPython 3.14.6 (2026-10-18). There were no
doctests and no GUIDE. Defects found in 0.2.0 by reading and then reproducing are the Fixed
entries of the 1.0.0 CHANGELOG section: unbounded error messages, a plain `ValueError` and an
`AttributeError` from `make_want`, `typing.get_type_hints` failing on four callables, a stray
`annotations` attribute, the command exiting 120 or 0 or with a traceback on closed streams,
importing `contentdigest.__main__` running the command, and the release script.

## API review (item 1)

Kept: the twelve public names of 0.2.0 with their signatures, parameter names and defaults.
Changed (all in the CHANGELOG): the public classes show and pickle as `contentdigest.<Name>`
(0.2.0 pickles of `DigestError` still load), `md5` and `sha` use `usedforsecurity=False`, the
command's exit status 2 for I/O errors, the field annotation names what 0.2.0 already
accepted, bounded messages, `TypeError` from `make_want` for a non-mapping.

## Ground truth (item 7)

- Specifications and registry: `scripts/fetch_upstream.py` fetches 30 files into the ignored
  `tests/upstream` folder; `tests/upstream/MANIFEST.json` records URL, revision, size, sha256
  and licence, and the tests check the hash before reading. First fetched 2026-10-18, fetched
  again in this run on 2026-10-19 with every size and sha256 unchanged: RFC 9530 and erratum
  8890, RFC 9651, the IANA "Hash Algorithms for HTTP Digest Fields" registry, RFC 9260, RFC
  7143, RFC 1950, the POSIX `cksum` page, the CRC catalogue and the httpwg structured-field
  tests at commit 781ba38 (1,598 cases). Every digest value RFC 9530 prints is cut from the text
  and reproduced (`tests/test_rfc_text.py`); the registry table is read from the XML
  (`tests/test_registry.py`); the CRC tables, polynomials and check values are read from the
  RFCs, the POSIX page and the catalogue (`tests/test_checksum_specs.py`).
- Real program output: `tests/program_output.json`, captured 2026-10-18 by
  `scripts/capture_program_output.py` from GNU coreutils 8.32, Windows certutil, OpenJDK 21
  (`Adler32`, `CRC32C`) and Node.js 24 (Brotli for erratum 8890), 27 inputs up to just over
  1 MiB. The live test ran GNU coreutils 8.32 on this PC on 2026-10-19 on fresh seeded inputs
  for `unixsum`, `unixcksum`, `md5`, `sha`, `sha-256` and `sha-512`: all equal.
- Independent implementations (`tests/test_oracles.py`), installed from PyPI on 2026-10-19:
  `http_sf` 1.4.0 (also 1.3.1) agrees on 30,000 seeded valid and broken dictionaries with the
  strict base64 decoder swapped in; `requests-http-signature` 1.0.0 builds the same
  `Content-Digest` for 400 random bodies. `http_sf` 1.4.0 now returns an empty dictionary for an
  empty field as RFC 9651 says (1.3.1 refused it); the test follows the installed version.
  Before Python 3.12, strict base64 accepts excess padding, so `http_sf` does too while this
  parser refuses it everywhere; that comparison runs from 3.12.
- PyPI 0.2.0 as an oracle (`tests/test_upgrade.py`): same results and error families, except
  the documented changes.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: seeds 1, 2 and 3, 4,000 hostile fields each through `parse`,
`parse_want`, `choose_algorithm` and `verify` (only `DigestError`; byte values and weights in
range; the same result as text, bytes or one line), made fields and preferences parse back
and verify, and chunked digests equal one-shot for every algorithm; run at the default scale
and at `CONTENTDIGEST_FUZZ_SCALE=10` (40,000 per seed). `tests/test_hostile.py`: 16 input
shapes timed at n and 4n (linear, from members and parameters to display strings, preference
fields and the verifier), a large body through every algorithm, a huge field refused with a
short message.

## Author mutation round (item 18)

34 mutants over every source module, each applied alone to a fresh clone of ddf450b on Elena's
PC, the whole suite run with `-x` and a 300 s per-test limit, with the fetched files,
`http_sf`, `requests-http-signature` and the 0.2.0 oracle present. All 34 killed. The four
first caught only by an optional check (M25, M27 by `http_sf`; M29, M30 by the fetched httpwg
corpus) survived a second run without them, so `tests/test_contract_sf.py` (d660254) pins
those rules from the RFC 9651 grammar; run alone, it kills all four.

| # | Mutation | Module | Result | First test to fail |
| --- | --- | --- | --- | --- |
| M1 | unixsum rotates into bit 14 | `_checksums.py` | killed | doctest `Digester.digests` |
| M2 | unixsum little-endian | `_checksums.py` | killed | doctest `Digester.digests` |
| M3 | cksum length bytes big-endian | `_checksums.py` | killed | `test_algorithms::test_checksums_match_bitwise_models[3]` |
| M4 | cksum final complement dropped | `_checksums.py` | killed | `test_algorithms::test_checksums_match_bitwise_models[0]` |
| M5 | crc32c initial value 0 | `_checksums.py` | killed | doctest `Digester` |
| M6 | crc32c with the CRC-32 polynomial | `_checksums.py` | killed | doctest `Digester` |
| M7 | adler32 initial value 0 | `_checksums.py` | killed | doctest `make_digest` |
| M8 | `sha` computes md5 | `_algorithms.py` | killed | `test_algorithms::test_digest_sizes[sha-20]` |
| M9 | algorithm names case-sensitive | `_algorithms.py` | killed | `test_digest::test_make_digest_lower_cases_and_drops_repeated_algorithms` |
| M10 | bare string accepted as a collection | `_algorithms.py` | killed | `test_contract_errors::test_wrong_argument_types_raise_type_error` |
| M11 | empty algorithm collection accepted | `_digest.py` | killed | `test_contract_errors::test_invalid_values_raise_digest_error` |
| M12 | members joined without the space | `_digest.py` | killed | doctest `Digester` |
| M13 | non-byte-sequence values accepted | `_digest.py` | killed | `test_digest::test_parse_rejects_the_whole_malformed_field` |
| M14 | one matching digest is enough | `_verify.py` | killed | `test_digest::test_verify_needs_every_accepted_member_to_match` |
| M15 | md5 checked although not accepted | `_verify.py` | killed | doctest `Verifier` |
| M16 | only four bytes compared | `_verify.py` | killed | `test_digest::test_verify_runs_every_comparison_in_constant_time` |
| M17 | weight 10 refused | `_want.py` | killed | doctest `choose_algorithm` |
| M18 | `make_want` keeps upper case | `_want.py` | killed | doctest `make_want` |
| M19 | duplicate preference key accepted | `_want.py` | killed | `test_contract_errors::test_invalid_values_raise_digest_error` |
| M20 | tie goes to the last listed | `_want.py` | killed | `test_docs::test_every_example_prints_its_comments[GUIDE]` |
| M21 | weight 0 can be chosen | `_want.py` | killed | `test_docs::test_every_example_prints_its_comments[GUIDE]` |
| M22 | non-ASCII bytes silently dropped | `_sf.py` | killed | `test_fuzz::test_hostile_fields_only_raise_digest_error[1]` |
| M23 | trailing comma accepted | `_sf.py` | killed | `test_cli::test_bad_field_exits_2` |
| M24 | repeated key keeps the first value | `_sf.py` | killed | `test_digest::test_parse_keeps_the_last_of_repeated_keys` |
| M25 | bare key reads as false | `_sf.py` | killed | `test_oracles` (`http_sf`); `test_contract_sf::test_a_bare_key_is_true_with_its_parameters` |
| M26 | upper-case key start accepted | `_sf_items.py` | killed | `test_contract_errors::test_invalid_values_raise_digest_error` |
| M27 | 16-digit integer accepted | `_sf_items.py` | killed | `test_oracles` (`http_sf`); `test_contract_sf::test_a_16_digit_integer_is_refused` |
| M28 | two excess pad characters accepted | `_sf_items.py` | killed | `test_byte_sequences::test_parse_rejects_more_padding_than_that[abcd==]` |
| M29 | `\n` escape accepted in strings | `_sf_items.py` | killed | `test_sf_suite` (httpwg); `test_contract_sf::test_any_other_string_escape_is_refused` |
| M30 | upper-case percent escapes accepted | `_sf_items.py` | killed | `test_sf_suite` (httpwg); `test_contract_sf::test_other_percent_escapes_are_refused` |
| M31 | error excerpts not cut | `_errors.py` | killed | `test_contract_errors::test_messages_stay_short_for_huge_input` |
| M32 | mismatch exits 2 | `_cli.py` | killed | `test_cli::test_verify_exits_1_on_a_mismatch` |
| M33 | last byte of each full chunk dropped | `_cli.py` | killed | `test_cli::test_prints_the_requested_algorithms_of_a_file` |
| M34 | non-contiguous buffers passed through | `_algorithms.py` | killed | `test_digest::test_make_digest_hashes_a_non_contiguous_view` |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Wheel (21,258 bytes): the twelve modules, `py.typed`, `METADATA`, `WHEEL`,
  `entry_points.txt`, `licenses/LICENSE`, `RECORD`; no dependencies, only the `dev` extra.
  Sdist from a clean clone of ddf450b: README, GUIDE, CHANGELOG, CONTRIBUTING, LICENSE,
  pyproject, `src`, `tests` (with `program_output.json` and only the manifest of
  `tests/upstream`), `scripts`; no process notes, `.github`, caches or fetched files.
  `twine check --strict` passes for both.
- At d7bec4f on Elena's PC, CPython 3.14, `CONTENTDIGEST_E2E=1` and
  `CONTENTDIGEST_E2E_PYPI=1`: the wheel installed in a fresh venv is driven from an empty folder
  with `-I` (API, metadata, typing, pickling, errors) and the `contentdigest` command and
  `python -m contentdigest` by subprocess (print, several algorithms, match, mismatch, bad
  field, Deprecated only, missing file, help, reader closing the pipe); PyPI 0.2.0 is installed
  and upgraded in place to the wheel, which then gives the same results.
- Interpreter matrix at ddf450b on the laptop: for each of CPython 3.10.19, 3.11.5, 3.12.12,
  3.13.2, 3.14.2 and 3.14.2t (the builds this PC has), the built wheel in a fresh venv and the
  sdist's own suite run with `src` removed, the fetched files, `http_sf` and the 0.2.0 oracle
  present: exit 0 each, `contentdigest` imported from site-packages. Skipped there: the four
  e2e tests (they need the source tree and ran above), `requests-http-signature` (not installed
  in the matrix), the live coreutils run (ran on this PC), and on 3.10 and 3.11 the `http_sf`
  comparison (see Ground truth). 3.8 and 3.9 are below `requires-python`.

## Gates (item 15)

At ec9b81d on Elena's PC from a fresh clone, CPython 3.14, each command on its own, with the
fetched files, `http_sf` 1.4.0, `requests-http-signature` 1.0.0, the 0.2.0 oracle,
`CONTENTDIGEST_E2E=1` and `CONTENTDIGEST_E2E_PYPI=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests scripts` and `pytest` (2105 passed, 1 skipped:
the live coreutils run, which needs GNU coreutils and ran on this PC) exit 0; the fuzz at ten
times scale then passes. The commit after it changes this report only.

## QA lenses (item 19)

### Round 1

Five lenses ran on bd2818b. Lens b (ground truth) raised no finding. Every other
finding is fixed in 85d9394; none is disputed.

| Lens | Finding | Change |
| --- | --- | --- |
| a F1 | Before 3.12 the run-time body hint is `bytes \| bytearray \| memoryview`, not `Buffer` | GUIDE Typing says so and what it means for run-time checkers; `test_the_body_hint_at_run_time_is_what_the_guide_says` pins it on each Python |
| a F2 | Node.js credited with checksum output | CHANGELOG and CONTRIBUTING: Node.js only decodes the Brotli example of erratum 8890 |
| a F3 | 0.2.0 undated; "usage line" | `## [0.2.0] - 2026-10-18` (PyPI upload date); "its help text says so" |
| a F4 | GUIDE: a field is quoted with its length | Reworded: a field is a window of at most 40 characters with its offset; a name or key is cut to 40 with its length |
| a F5 | `algos` and `supported` positional, `accept` keyword-only | Kept, as in 0.2.0, so callers of 0.2.0 keep working; new GUIDE section "Stable signatures" gives the reason and the CHANGELOG states the shape is stable |
| c F1 | Repeated names in `accept` / `supported` make checking quadratic | `algorithm_names` keeps each name once (`dict.fromkeys`); two new `test_time_grows_linearly` shapes, red before the fix |
| c F2 | A released `memoryview` body raised a plain `ValueError` | `as_view` raises `TypeError`; `test_a_released_buffer_is_a_type_error` covers `make_digest`, `Digester.update`, `verify`, `Verifier.update`, red before the fix; GUIDE error table and CHANGELOG updated |
| d D1 | `.gitignore` excluded in pyproject but always shipped by hatchling | Exclude line removed with a comment; `test_wheel_and_sdist_contents` now pins the sdist to exactly the tracked files minus the excluded ones plus `PKG-INFO` |
| e F1, F2 | M62 and 11 other RFC 9651 parser mutants survive a clean checkout | Hand-written contract cases in `tests/test_contract_sf.py`, each with its RFC 9651 section: booleans, leading tab, SP after `;`, key characters, repeated key position, inner-list separators, decimal date, OWS before a comma, control characters in strings and display strings, trailing SP |

Verification: lens e's own harness applied M49, M52, M61, M62, M63, M77, M78, M79, M86, M88,
M89 and M93 one at a time to a copy of the fixed tree, with no fetched files and no oracle;
`tests/test_contract_sf.py` fails for each of the twelve. While writing the cases, a trailing
tab after the last dictionary member turned out to be valid (section 4.2.2 discards OWS after
each member), so it is pinned as accepted and only a leading tab as refused. On Elena's PC,
CPython 3.14, from a fresh clone of 85d9394 with the fetched files, both oracles, the 0.2.0
oracle and both e2e switches: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests scripts` and `pytest` (2138 passed, 1 skipped: the live coreutils
run) exit 0, then the fuzz at ten times scale passes. The new contract files also pass on
3.10 and 3.11 on this PC. The first try of that run failed the new sdist pin, correctly: the
job script had been copied into the clone's root and was packed into the sdist.
