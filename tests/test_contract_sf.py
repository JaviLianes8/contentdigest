"""The structured-field rules every member value goes through, pinned without fetched files.

Hand-written from the RFC 9651 parsing algorithms (sections 4.2.2 and 4.2.3 to 4.2.10), so they
run without the httpwg corpus or any oracle: a bare key is Boolean true, integers have at most
15 digits, decimals at most 12 integer and 3 fractional digits, strings escape only DQUOTE and
backslash, display strings take only lower-case percent escapes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from contentdigest import DigestError
from contentdigest._sf import parse_dictionary


def _values(field: str) -> dict[str, object]:
    return {key: member[0] for key, member in parse_dictionary(field).items()}


def test_a_bare_key_is_true_with_its_parameters() -> None:
    parsed = parse_dictionary("a, b;x, c=?0")
    assert parsed == {"a": (True, {}), "b": (True, {"x": True}), "c": (False, {})}
    assert all(type(value) is bool for value, _ in parsed.values())


@pytest.mark.parametrize("digits", ["1", "123456789012345", "-123456789012345", "000"])
def test_integers_have_at_most_15_digits(digits: str) -> None:
    assert _values(f"a={digits}") == {"a": int(digits)}


@pytest.mark.parametrize("digits", ["1234567890123456", "-1234567890123456"])
def test_a_16_digit_integer_is_refused(digits: str) -> None:
    with pytest.raises(DigestError, match="integer too long"):
        parse_dictionary(f"a={digits}")


@pytest.mark.parametrize("text", ["123456789012.123", "-0.5", "1.0"])
def test_decimals_within_the_limits(text: str) -> None:
    assert _values(f"a={text}") == {"a": Decimal(text)}


@pytest.mark.parametrize("text", ["1234567890123.1", "1.1234", "1.", "-"])
def test_decimals_beyond_the_limits_are_refused(text: str) -> None:
    with pytest.raises(DigestError):
        parse_dictionary(f"a={text}")


def test_strings_unescape_dquote_and_backslash() -> None:
    assert _values(r'a="x\"y\\z"') == {"a": 'x"y\\z'}


@pytest.mark.parametrize("escape", ["n", "t", "x", "'", "u"])
def test_any_other_string_escape_is_refused(escape: str) -> None:
    with pytest.raises(DigestError, match="bad escape"):
        parse_dictionary(f'a="x\\{escape}y"')


def test_display_strings_decode_lower_case_percent_escapes() -> None:
    assert _values('a=%"caf%c3%a9 50%25"') == {"a": "café 50%"}


@pytest.mark.parametrize("escape", ["%C3%A9", "%c3%A9", "%Ab", "%g0", "%2"])
def test_other_percent_escapes_are_refused(escape: str) -> None:
    with pytest.raises(DigestError, match="bad percent escape"):
        parse_dictionary(f'a=%"{escape}"')


def test_tokens_dates_and_inner_lists() -> None:
    values = _values("a=*tok/x:y, b=@-62, c=(1 ?1);p=2")
    assert values["a"] == "*tok/x:y" and type(values["a"]).__name__ == "Token"
    assert values["b"] == -62 and type(values["b"]).__name__ == "Date"
    assert parse_dictionary("c=(1 ?1);p=2")["c"] == ([(1, {}), (True, {})], {"p": 2})
