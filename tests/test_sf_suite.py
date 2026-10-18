"""The structured-field parser passes every parsing test of the pinned httpwg suite.

Source: https://github.com/httpwg/structured-field-tests/tree/781ba38464b2ec4c547e1e14d007d4f5ace7457e
(fetched 2026-10-18). The corpus is third-party and not committed: `python
scripts/fetch_upstream.py` downloads it into tests/upstream, checked against MANIFEST.json.
Without it these tests skip.
"""

from __future__ import annotations

import base64
import json
from decimal import Decimal
from typing import Any

import pytest
from conftest import UPSTREAM, manifest, upstream_bytes

from contentdigest import DigestError
from contentdigest._sf import parse_dictionary, parse_item, parse_list
from contentdigest._sf_items import Date, DisplayString, Token

PARSERS = {"dictionary": parse_dictionary, "list": parse_list, "item": parse_item}
FILES = sorted(
    name for name, entry in manifest().items() if entry.get("group") == "httpwg" and ".json" in name
)


def _cases() -> list[Any]:
    if not all((UPSTREAM / name).is_file() for name in FILES):
        return [pytest.param(None, marks=pytest.mark.skip(reason="run scripts/fetch_upstream.py"))]
    cases = []
    for name in FILES:
        for case in json.loads(upstream_bytes(name).decode("utf-8")):
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


def test_the_suite_has_every_parsing_file_and_is_not_empty() -> None:
    assert len(FILES) == 20
    cases = _cases()
    if cases[0].values[0] is None:
        pytest.skip("run scripts/fetch_upstream.py")
    assert len(cases) > 1500


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
