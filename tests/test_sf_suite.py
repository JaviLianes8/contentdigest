"""The structured-field parser passes every parsing test of the pinned httpwg suite.

Source: https://github.com/httpwg/structured-field-tests/tree/781ba38464b2ec4c547e1e14d007d4f5ace7457e
The corpus is third-party and not committed: `python scripts/fetch_vectors.py` downloads it
into tests/vectors/httpwg, checked against MANIFEST.txt. Without it these tests skip.
"""

from __future__ import annotations

import base64
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from contentdigest import DigestError
from contentdigest._sf import parse_dictionary, parse_item, parse_list
from contentdigest._sf_items import Date, DisplayString, Token

VECTORS = Path(__file__).resolve().parent / "vectors" / "httpwg"
PARSERS = {"dictionary": parse_dictionary, "list": parse_list, "item": parse_item}


def _manifest() -> dict[str, tuple[str, int]]:
    lines = (VECTORS / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    rows = [line.split() for line in lines if line and not line.startswith("#")]
    return {name: (digest, int(size)) for digest, size, name in rows}


def _present() -> bool:
    return all((VECTORS / name).is_file() for name in _manifest())


pytestmark = pytest.mark.skipif(
    not _present(), reason="run scripts/fetch_vectors.py to fetch the httpwg corpus"
)


def _cases() -> list[Any]:
    if not _present():
        return []
    cases = []
    for name in sorted(n for n in _manifest() if n.endswith(".json")):
        for case in json.loads((VECTORS / name).read_text(encoding="utf-8")):
            cases.append(pytest.param(case, id=f"{name}:{case['name']}"))
    return cases


def _bare(ours: object, expected: Any) -> bool:
    if isinstance(expected, bool):
        return type(ours) is bool and ours is expected
    if isinstance(expected, int):
        return type(ours) is int and ours == expected
    if isinstance(expected, float):
        return type(ours) is Decimal and float(ours) == expected
    if isinstance(expected, str):
        return type(ours) is str and ours == expected
    kind, value = expected["__type"], expected["value"]
    if kind == "binary":
        return type(ours) is bytes and ours == base64.b32decode(value)
    wanted = {"token": Token, "date": Date, "displaystring": DisplayString}[kind]
    return type(ours) is wanted and ours == value


def _params(ours: dict[str, object], expected: list[Any]) -> bool:
    return list(ours) == [k for k, _ in expected] and all(_bare(ours[k], v) for k, v in expected)


def _member(ours: Any, expected: Any) -> bool:
    value, params = expected
    if isinstance(value, list):
        items, our_params = ours
        return (
            isinstance(items, list)
            and len(items) == len(value)
            and all(_member(i, e) for i, e in zip(items, value, strict=True))
            and _params(our_params, params)
        )
    return not isinstance(ours[0], list) and _bare(ours[0], value) and _params(ours[1], params)


def _matches(kind: str, ours: Any, expected: Any) -> bool:
    if kind == "item":
        return _member(ours, expected)
    if kind == "list":
        return len(ours) == len(expected) and all(map(_member, ours, expected))
    return list(ours) == [k for k, _ in expected] and all(_member(ours[k], v) for k, v in expected)


def test_fetched_files_match_the_manifest() -> None:
    for name, (digest, size) in _manifest().items():
        data = (VECTORS / name).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (size, digest), name


def test_the_suite_is_not_empty() -> None:
    assert len(_cases()) > 1500


@pytest.mark.parametrize("case", _cases())
def test_httpwg_case(case: dict[str, Any]) -> None:
    parser = PARSERS[case["header_type"]]
    raw = case["raw"]
    if case.get("must_fail"):
        with pytest.raises(DigestError):
            parser(raw)
        return
    # Tests marked can_fail are the leniencies RFC 9651 says parsers SHOULD allow; this
    # parser allows all of them, so every one must produce the expected value.
    assert _matches(case["header_type"], parser(raw), case["expected"])
