"""The structured-field rules every member value goes through, pinned without fetched files.

Hand-written from the RFC 9651 parsing algorithms (sections 4.2.2 and 4.2.3 to 4.2.10), so they
run without the httpwg corpus or any oracle: a bare key is Boolean true, integers have at most
15 digits, decimals at most 12 integer and 3 fractional digits, strings escape only DQUOTE and
backslash, display strings take only lower-case percent escapes. The section of each further rule is
named next to its test.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from contentdigest import DigestError, parse, parse_want
from contentdigest._sf import parse_dictionary, parse_item, parse_list


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


def test_booleans_are_only_question_mark_zero_or_one() -> None:
    assert _values("a=?0, b=?1") == {"a": False, "b": True}
    assert parse_dictionary("a=1;x=?0;y=?1")["a"] == (1, {"x": False, "y": True})


@pytest.mark.parametrize("bad", ["?2", "?", "?a", "?01"])
def test_any_other_boolean_is_refused_as_a_value_or_a_parameter(bad: str) -> None:
    for field in (f"a={bad}", f"a=1;x={bad}", f"a=({bad})"):
        with pytest.raises(DigestError):
            parse_dictionary(field)
    with pytest.raises(DigestError):
        parse(f"sha-256=:AAAA:;x={bad}")
    with pytest.raises(DigestError):
        parse_want(f"a=1;x={bad}")


# Section 4.2 discards only SP before and after the whole value; sections 4.2.1 and 4.2.2
# discard OWS (SP or HTAB) after each list or dictionary member, so a tab may end those.
@pytest.mark.parametrize("field", ["\ta=1", "\ta=1, b=2", " \ta=1"])
def test_a_leading_tab_is_refused(field: str) -> None:
    with pytest.raises(DigestError):
        parse_dictionary(field)
    with pytest.raises(DigestError):
        parse_item("\t1")


def test_spaces_at_either_end_and_ows_around_commas_are_accepted() -> None:
    assert _values("  a=1 \t,\t b=2 \t ") == {"a": 1, "b": 2}
    with pytest.raises(DigestError):
        parse_item("1\t")
    assert parse_item(" 1  ") == (1, {}) and parse_list(" 1 \t, 2  ") == [(1, {}), (2, {})]


def test_spaces_are_allowed_after_a_parameter_semicolon() -> None:
    # Section 4.2.3.2 discards SP after ";" before the parameter key.
    assert parse_dictionary("a=1;  x=2; y")["a"] == (1, {"x": 2, "y": True})


@pytest.mark.parametrize("gap", ["\t", " \t", "\t "])
def test_a_tab_after_a_parameter_semicolon_is_refused(gap: str) -> None:
    # Section 4.2.3.2 discards only SP there, never HTAB.
    with pytest.raises(DigestError):
        parse_dictionary(f"a=1;{gap}x=2")
    with pytest.raises(DigestError):
        parse(f"sha-256=:AAAA:;{gap}x=1")
    with pytest.raises(DigestError):
        parse_want(f"sha-256=1;{gap}x")


@pytest.mark.parametrize("field", ["1a=1", "_a=1", "-a=1", ".a=1", "Aa=1", "aB=1", "a-B=1"])
def test_keys_are_lower_case_and_start_with_a_letter_or_star(field: str) -> None:
    # Section 4.2.3.3: key = ( lcalpha / "*" ) *( lcalpha / DIGIT / "_" / "-" / "." / "*" ).
    with pytest.raises(DigestError):
        parse_dictionary(field)
    with pytest.raises(DigestError):
        parse(field.replace("=1", "=:AAAA:"))


def test_valid_keys_with_every_allowed_character() -> None:
    assert list(parse_dictionary("*a=1, a0_-.*=2")) == ["*a", "a0_-.*"]


def test_a_repeated_key_keeps_its_first_position_and_its_last_value() -> None:
    # Section 4.2.2: a repeated key overwrites the value in place.
    assert list(parse_dictionary("a=1, b=2, a=3").items()) == [("a", (3, {})), ("b", (2, {}))]
    assert list(parse("a=:AQ==:, b=:Ag==:, a=:Aw==:").items()) == [("a", b"\x03"), ("b", b"\x02")]


@pytest.mark.parametrize("field", ['a=(abc"def")', "a=(1?1)", "a=(1(2))", "a=(x:AA==:)"])
def test_inner_list_items_must_be_separated_by_spaces(field: str) -> None:
    # Section 4.2.1.2: after each item comes SP or ")".
    with pytest.raises(DigestError):
        parse_dictionary(field)


@pytest.mark.parametrize("inner", ["(\t1)", "(1 \t2)", "( \t1)", "(1\t)"])
def test_a_tab_inside_an_inner_list_is_refused(inner: str) -> None:
    # Section 4.2.1.2 discards only SP inside an inner list. A later repeat of the key must not
    # hide the error by overwriting the refused value.
    for field in (f"a={inner}", f"a={inner}, a=1"):
        with pytest.raises(DigestError):
            parse_dictionary(field)
        with pytest.raises(DigestError):
            parse_want(field)
    with pytest.raises(DigestError):
        parse(f"sha-256={inner}, sha-256=:AAAA:")


def test_strings_accept_every_printable_ascii_character() -> None:
    # Section 4.2.5: unescaped %x20-21 / %x23-5B / %x5D-7E, plus the two escapes.
    text = "".join(map(chr, range(0x20, 0x7F)))
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    assert _values(f'a="{escaped}"') == {"a": text}
    assert parse(f'sha-256=:AAAA:;x="{escaped}"') == {"sha-256": b"\x00\x00\x00"}
    assert parse_want('a=1;x="a~b"') == {"a": 1}
    assert _values('a=%"a~b"') == {"a": "a~b"}


def test_a_decimal_date_is_refused() -> None:
    # Section 4.2.9: a date is an integer.
    with pytest.raises(DigestError):
        parse_dictionary("a=@1.5")
    assert _values("a=@0") == {"a": 0}


@pytest.mark.parametrize("char", ["\t", "\x7f", "\x00", "\x1f", "\n"])
def test_control_characters_are_refused_in_strings_and_display_strings(char: str) -> None:
    # Sections 4.2.5 and 4.2.10: only %x20-7E may appear unescaped.
    with pytest.raises(DigestError, match="control character in string"):
        parse_dictionary(f'a="x{char}y"')
    with pytest.raises(DigestError, match="control character in display string"):
        parse_dictionary(f'a=%"x{char}y"')
