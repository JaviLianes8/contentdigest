"""Byte sequences: the base64 leniencies RFC 9651 section 4.2.7 asks for, and their limits."""

from __future__ import annotations

import pytest

from contentdigest import DigestError, parse


def test_parse_accepts_missing_padding_and_non_zero_pad_bits() -> None:
    assert parse("a=:aGVsbG8:, b=:iZ==:") == {"a": b"hello", "b": b"\x89"}


def test_parse_accepts_one_pad_beyond_what_is_needed() -> None:
    assert parse("a=:aGVsbG8==:, b=:abcd=:") == {"a": b"hello", "b": b"i\xb7\x1d"}


@pytest.mark.parametrize("content", ["abcd==", "aG===", "=", "==", "aGVsbG8==="])
def test_parse_rejects_more_padding_than_that(content: str) -> None:
    with pytest.raises(DigestError, match="malformed base64"):
        parse(f"a=:{content}:")


def test_errors_quote_only_a_short_excerpt_of_a_huge_field() -> None:
    with pytest.raises(DigestError) as error:
        parse("a=:" + "A" * 2_000_000)
    assert len(str(error.value)) < 200
