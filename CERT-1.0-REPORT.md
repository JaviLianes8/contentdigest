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
- [ ] Five QA lenses (item 19): rounds 1 to 6 fixed, awaiting re-verification
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

Final run after the QA rounds, at 46df396 (the code of ff402c6), each from a fresh clone of the
pushed commit:

- Elena's PC, CPython 3.14, with the fetched files, `http_sf` 1.4.0, `requests-http-signature`
  1.0.0, the 0.2.0 oracle, `CONTENTDIGEST_E2E=1` and `CONTENTDIGEST_E2E_PYPI=1`:
  `ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests scripts`
  and `pytest` (2240 passed, 1 skipped: the live coreutils run) exit 0, then the fuzz at ten
  times scale passes. The e2e tests build the wheel and sdist, drive the wheel and the command
  from an empty folder and upgrade PyPI 0.2.0 in place.
- Elena's PC, interpreter matrix as above (built wheel in a fresh venv, sdist's own suite with
  `src` removed, fetched files, `http_sf` and the 0.2.0 oracle present): CPython 3.10.19,
  3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t each exit 0, `contentdigest` imported from
  site-packages; the only skip is the live coreutils run.

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

### Round 2

Lenses a, d and e re-ran on 03659c2 (lenses b and c had passed). Each confirmed its round 1
findings fixed and lens a accepted the argument for F5. Every new finding is fixed in dd917fe;
none is disputed. Lens e also reported an operational incident outside the repository, which
went back to the orchestrator; it needs no change here.

| Lens | Finding | Change |
| --- | --- | --- |
| a G1, d D3 | `as_view` turned every `ValueError` from `memoryview()` into "not a released buffer", so a closed `mmap`, a numpy `datetime64` array or any refusing `__buffer__` lost its own error and type | Only a released `memoryview` becomes `TypeError` ("not a released memoryview"); any other exporter's `ValueError` is raised unchanged, as in 0.2.0. New `tests/test_contract_buffers.py` pins the released view, a closed anonymous `mmap` and (3.12+) a `__buffer__` raising `ValueError` through `make_digest`, `Digester.update`, `verify` and `Verifier.update`; red before the fix. GUIDE error section, Upgrading and CHANGELOG say so |
| a G2 | `## [0.1.0]` undated | `## [0.1.0] - 2026-10-11` (commit 7023bd4), with a line that it was never published to PyPI |
| a G3 | "`algos` stays for the same reason" gave it the keyword-only reason | It stays because renaming it would break 0.2.0 callers that pass it by keyword |
| d D2 | `test_wheel_and_sdist_contents` called `git ls-files` with `check=True`, so it failed from an unpacked sdist | The content checks run first everywhere; the exact listing comparison runs only when the root has `.git` and is skipped with a reason otherwise; the module docstring says so |
| e F3 (N13) | Nothing pinned that `bytes` as a name collection raises `TypeError` | `WRONG_TYPES` gains `b""` and `b"sha-256"` as `algos`, `accept` and `supported`, in the functions and both classes |
| e F4 (N18) | Nothing pinned that HTAB after a parameter `;` is refused | `test_a_tab_after_a_parameter_semicolon_is_refused` (RFC 9651 section 4.2.3.2), through `parse_dictionary`, `parse` and `parse_want` |
| e F5 (N19) | Nothing pinned that HTAB inside an inner list is refused | `test_a_tab_inside_an_inner_list_is_refused` (section 4.2.1.2): `(\t1)`, `(1 \t2)`, `( \t1)`, `(1\t)`, alone and with the key repeated later |
| e F6 (N28) | Nothing pinned that `~` is accepted in an sf-string | `test_strings_accept_every_printable_ascii_character` (section 4.2.5): SP to `~` round-trips, also as a parameter of `parse` and `parse_want`, and `~` in a display string |

Verification: a harness applied N13, N18, N19, N28, the same `~` cut in display strings, and
the old broad conversion in `as_view`, one at a time to a copy of the fixed tree without the
fetched files or the oracles; the contract files fail for each of the six. On Elena's PC,
CPython 3.14, from a fresh clone of dd917fe with the fetched files, `http_sf` 1.4.0,
`requests-http-signature` 1.0.0, the 0.2.0 oracle and both e2e switches: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests scripts` and `pytest` (2156 passed,
1 skipped: the live coreutils run) exit 0, then the fuzz at ten times scale passes. From the sdist
built there and unpacked outside any checkout, `CONTENTDIGEST_E2E=1 pytest tests/test_e2e_wheel.py`
gives 2 passed and 1 skipped (the listing comparison). The changed contract files also pass on
3.11 and 3.13 on this PC.

### Round 3

Lens e re-ran on 70c2a1d (lenses a and d had passed round 2). It confirmed F3 to F6 fixed and
showed its surviving mutant S08 (HTAB taken as an inner-list separator) to be equivalent: over
66,429 generated fields the original and the mutant agree on success, failure and error type.
Its one new finding is fixed in 331d3db; none is disputed.

| Lens | Finding | Change |
| --- | --- | --- |
| e F7 (B03, B04) | A `bytearray` or `memoryview` passed as `algos`, `accept` or `supported` was not refused like `bytes`: an empty one passed as no names (`choose_algorithm` returned `None`, the others raised `DigestError`), a non-empty one failed on its first `int` | `algorithm_names` refuses `str`, `bytes`, `bytearray` and `memoryview` with `TypeError`. New `test_a_bytes_like_value_is_not_a_name_collection` sends `b""`, `b"sha-256"`, `bytearray()`, `bytearray(b"sha-256")`, `memoryview(b"")` and `memoryview(b"sha-256")` through `make_digest`, `verify`, `choose_algorithm`, `Digester` and `Verifier`; 20 of its 30 cases were red before the fix. GUIDE error table, Upgrading and CHANGELOG say so |

Verification: on this PC the check was cut back one at a time to `(str, bytes, bytearray)`,
`(str, bytes, memoryview)` and `(str, bytes)`; `tests/test_contract_errors.py` fails for each.
`ruff format --check .`, `ruff check .`, `mypy --strict src` and `mypy --strict src tests scripts`
exit 0 here. On Elena's PC, CPython 3.14, from a fresh clone of 331d3db (without the fetched
files or the oracles): `ruff format --check .`, `ruff check .`, `mypy --strict src` and `pytest`
exit 0.

### Round 4

Lens e re-ran on d70e546. It confirmed F7 fixed and judged its surviving mutants N08, N09 and
N20 (message wording only) equivalent. Its four new findings are fixed in ff402c6; none is
disputed. The name-collection contract moved to `tests/test_contract_names.py`.

| Lens | Finding | Change |
| --- | --- | --- |
| e G1 (N10) | Nothing pinned that subclasses of `str` and `bytes` are refused as a name collection | The contract now sends a `str` subclass and a `bytes` subclass, empty and not, through `make_digest`, `verify`, `choose_algorithm`, `Digester` and `Verifier`, expecting `TypeError` |
| e G2 (N18) | Other bytes-like values (`array.array`, `mmap`) still passed as a name collection; an empty one counted as no names | `algorithm_names` refuses `str` and any object that exports the buffer protocol (also when the exporter refuses its bytes, as a closed `mmap` or a released `memoryview` does). New cases `array("B")`, `array("B", b"sha-256")`, `array("I", [1, 2])`, an open and a closed `mmap`, and a released `memoryview`; 25 cases were red before the fix. GUIDE error table, Upgrading and CHANGELOG say so |
| e G3 (N29) | Nothing pinned which occurrence of a repeated name sets the member order | New `test_a_repeated_name_keeps_the_place_of_its_first_occurrence` asserts the exact `make_digest` and `Digester` output for `["sha-256", "sha-512", "SHA-256"]` and `["sha-512", "sha-256", "sha-512"]`; the GUIDE says the first occurrence keeps its place |
| e G4 (N32) | Nothing pinned that one-shot iterables work as `algos`, `accept` and `supported` | New `test_a_one_shot_iterable_is_a_name_collection` passes a generator and two iterators to all five entry points and asserts the normal result; the GUIDE says any iterable works |

Verification: on this PC each mutant was applied to the fixed source one at a time (exact
`type(names) is str`, keep-last deduplication, `iter(names) is names` refused, the round 3 check
`(str, bytes, bytearray, memoryview)`, and a closed exporter taken as not bytes-like);
`tests/test_contract_names.py` fails for each. `ruff format --check .`, `ruff check .`,
`mypy --strict src` and `mypy --strict src tests scripts` exit 0 here. On Elena's PC, CPython
3.14, from a fresh clone of ff402c6: `ruff format --check .`, `ruff check .`,
`mypy --strict src` and `pytest --timeout 300` exit 0.

### Round 5

Lenses a, c and e ran on 2b41964. Every finding is fixed in 6169c8c; none is disputed. Each
behaviour fix has a contract that was red on 2b41964 and is green on 6169c8c.

| Lens | Finding | Change |
| --- | --- | --- |
| a A1 | The six public functions reported and pickled under their private modules | `__init__.py` sets `__module__` to `contentdigest` on `choose_algorithm`, `make_digest`, `make_want`, `parse`, `parse_want` and `verify`, as it did for the classes; their doctests are now collected once at the package top. New `test_every_public_callable_reports_and_pickles_as_the_package` checks every callable of `__all__`: module `contentdigest`, no private module in its pickle, and the pickle loads to the same object (6 cases red before the fix). CHANGELOG and GUIDE Upgrading say so; 0.2.0 pickles still load because the private modules still define the functions |
| a A2 | The GUIDE "Fields as they arrive" example failed `mypy --strict` when copied (a mixed list inferred as `list[Sequence[object]]`) | The variable is annotated `list[str \| bytes]`. New `test_every_example_passes_strict_type_checking` wraps each README and GUIDE block in a function and runs `mypy --strict` over them; it fails on the old GUIDE with exactly the reported error |
| a A3 | "Errors go to standard error as one short line", but a usage error prints the usage line too | GUIDE Command line: "a usage error prints the usage line before it" |
| a A4 | A field of the wrong type got a misleading or generic message (`memoryview` reported as `int`, `bytearray` not named, `'int' object is not iterable`) | `_sf.combine` refuses up front any bytes-like value other than `bytes` and `bytearray` and anything not iterable, with "a field must be str, bytes, bytearray or an iterable of them, not <type>"; a bad line says "str, bytes or bytearray". `is_bytes_like` moved to `_types.py` so both checks share it. New `tests/test_contract_limits.py` pins both messages through `parse`, `parse_want`, `verify`, `Verifier` and `choose_algorithm` (where `None` stays an absent field). Behaviour change: an empty `memoryview` or `array` field used to pass as an empty field and now raises `TypeError`; CHANGELOG, GUIDE error table and Upgrading say so |
| c F1 | An empty body with a zero in its shape (`ctypes` `c_ubyte * 4 * 0`, numpy `zeros((0, 4))`) raised `TypeError` from `memoryview.cast` | `as_view` returns an empty view when the buffer has no bytes. New `test_an_empty_buffer_of_any_shape_is_the_empty_body` sends three zero-shaped `ctypes` buffers through `make_digest`, `Digester.update`, `verify` and `Verifier.update` and expects the empty-body digest; CHANGELOG Fixed and GUIDE Upgrading say so |
| e F1 (N14) | The 40-character name cut had no boundary test | 40 characters quoted whole, 41 cut with "(41 characters)" |
| e F2 (N16) | The 40-character type name cut had no boundary test | A type name of 40 shown whole, 41 cut to 40 plus "..." |
| e F3 (N21) | The 300-character command message cut had no boundary test | A usage error of exactly 300 characters kept whole, 301 cut with "(301 characters)" |
| e F4 (N08) | The sorted "accepted are" list was pinned only under some hash seeds | `accept` of seven names in reverse order; the message must list `'adler', 'md5', 'sha', 'sha-256', 'sha-512' and 2 more`. Neither the given order nor the set order of those names is sorted (checked for `PYTHONHASHSEED` 0 to 40) |

Verification: on this PC, N14, N16, N21, N08 (`sorted(set(...))` replaced by `list(set(...))`)
and the order-keeping variant `list(accepted)` were applied one at a time; `tests/test_contract_limits.py`
fails for each under `PYTHONHASHSEED` 0 to 5 (N14, N16 and N21 under 0, 2 and 3). The other new
contracts were run against 2b41964 and fail there. `ruff format --check .`, `ruff check .`,
`mypy --strict src` and `mypy --strict src tests scripts` exit 0 here. On Elena's PC, CPython
3.14, from a fresh clone of 6169c8c: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests scripts` and `pytest --timeout 300` (666 passed, 31 skipped: the fetched
files, the oracles and the e2e switches were absent) exit 0.

### Round 6

Lenses a and e ran on b785f5e. Lens a confirmed A1 to A4 fixed and lens e confirmed F1 to F4
fixed (N14, N16, N21, N08 and N08b killed, the last two under `PYTHONHASHSEED` 0 to 99). Every
new finding is fixed in the commit that adds this section; none is disputed. Each one has a
contract that is red on b785f5e (or, for a surviving mutant, red with that mutant applied) and
green after it.

| Lens | Finding | Change |
| --- | --- | --- |
| a B1 | A 0.2.0 pickle of `verify` did not load: 0.2.0 defined it in `_digest`, 1.0.0 in `_verify`. The round 5 note that the private modules still define the functions was wrong for it | The same holds for `Verifier`, which 0.2.0 also defined in `_digest`. `_digest` now resolves `Verifier` and `verify` on first access (a module `__getattr__`, so there is no import cycle). New `tests/test_contract_pickles.py` holds the pickles of all nine public callables written by the real 0.2.0 wheel under CPython 3.13, protocols 0 and 4, and asserts each loads as the live object; 4 cases (`Verifier` and `verify`) were red on b785f5e. The GUIDE and CHANGELOG now say every public class and function loads |
| e G1 (S08) | The empty-shape contract used only `sha-256`, which reads the raw empty view; the checksums do not | `test_an_empty_buffer_of_any_shape_is_the_empty_body` runs once per supported algorithm through `make_digest`, `Digester`, `verify` and `Verifier`; S08 fails it for `crc32c`, `unixcksum` and `unixsum` |
| e G2 (S18) | No test passed a whole field as `bytearray` | New `test_a_whole_field_as_bytearray_reads_like_the_equal_bytes` in `tests/test_contract_fields.py`: `parse`, `parse_want`, `verify`, `Verifier` and `choose_algorithm` give the same result for a `bytearray`, the equal `bytes` and the `str`; S18 fails all five |
| e G3 (S19) | Nothing pinned that an error raised by the caller's own iterable of lines reaches the caller unchanged | New `test_an_iterables_own_error_reaches_the_caller_unchanged`: a generator that raises a `TypeError`, or an exception class of its own, after its first line; the same exception object reaches the caller through all five entry points; S19 fails the five `TypeError` cases. The GUIDE Errors section says so |
| e G4 (S20) | The "a field must be ..." message had no long type name case | Two rows added to `test_a_field_of_the_wrong_type_is_named_in_the_message`: a type name of 40 characters shown whole and one of 41 cut to 40 plus "...", through all five entry points; S20 fails the 41 case |

Verification: on this PC, S08, S18, S19 and S20, and two variants of the B1 fix that resolve
only one of the two names, were applied one at a time to the fixed source; the new contracts fail
for each. The hex pickles in the new contract were checked again against the 0.2.0 wheel.
`ruff format --check .`, `ruff check .`, `mypy --strict src` and `mypy --strict src tests
scripts` exit 0 here. On Elena's PC, CPython 3.14, from a fresh clone of b785f5e with this
change applied and the fetched files present: `ruff format --check .`, `ruff check .`, `mypy --strict src` and `pytest --timeout 300` (2332 passed, 12
skipped) exit 0.
