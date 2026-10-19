"""Message limits at their exact boundaries, and the messages for a field of the wrong type."""

from __future__ import annotations

import io
from array import array
from collections.abc import Callable
from typing import Any

import pytest

import contentdigest
from contentdigest import make_digest, verify
from contentdigest._cli import run

# Wrong types on purpose: called through an untyped alias so the checker lets them pass.
api: Any = contentdigest
SHA256 = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"


def _unsupported(name: str) -> str:
    with pytest.raises(contentdigest.DigestError) as caught:
        make_digest(b"", algos=[name])
    return str(caught.value)


def test_a_name_of_forty_characters_is_quoted_whole() -> None:
    assert _unsupported("a" * 40) == f"unsupported algorithm: {'a' * 40!r}"


def test_a_name_of_forty_one_characters_is_cut_with_its_length() -> None:
    assert _unsupported("a" * 41) == f"unsupported algorithm: {'a' * 40!r}... (41 characters)"


@pytest.mark.parametrize(("length", "shown"), [(40, "T" * 40), (41, "T" * 40 + "...")])
def test_a_type_name_is_cut_after_forty_characters(length: int, shown: str) -> None:
    instance = type("T" * length, (), {})()
    with pytest.raises(TypeError) as caught:
        api.make_digest(instance)
    assert str(caught.value) == f"the body must be bytes-like, not {shown}"


def _usage_error(argument: str) -> str:
    err = io.StringIO()
    assert run(["f", argument], stdout=io.StringIO(), stderr=err) == 2
    return err.getvalue().splitlines()[-1]


def test_a_command_message_of_three_hundred_characters_is_kept_whole() -> None:
    message = "unrecognized arguments: --x" + "y" * 273
    assert len(message) == 300
    assert _usage_error("--x" + "y" * 273) == f"contentdigest: error: {message}"


def test_a_command_message_of_three_hundred_and_one_characters_is_cut() -> None:
    message = "unrecognized arguments: --x" + "y" * 274
    assert _usage_error("--x" + "y" * 274) == (
        f"contentdigest: error: {message[:300]}... (301 characters)"
    )


def test_the_accepted_names_are_listed_sorted_whatever_order_they_come_in() -> None:
    # Seven names in reverse order: neither the given order nor a set's order is sorted.
    accept = ["unixsum", "unixcksum", "sha-512", "sha-256", "sha", "md5", "adler"]
    with pytest.raises(contentdigest.DigestError) as caught:
        verify("crc32c=:AAAAAA==:", b"", accept=accept)
    assert str(caught.value) == (
        "no accepted algorithm in the field (it has 'crc32c'; "
        "accepted are 'adler', 'md5', 'sha', 'sha-256', 'sha-512' and 2 more)"
    )


FIELD_ENTRY_POINTS: list[Callable[[Any], Any]] = [
    lambda field: api.parse(field),
    lambda field: api.parse_want(field),
    lambda field: api.verify(field, b""),
    lambda field: api.Verifier(field),
    lambda field: api.choose_algorithm(field),
]
NOT_A_FIELD = "a field must be str, bytes, bytearray or an iterable of them, not "


@pytest.mark.parametrize("call", FIELD_ENTRY_POINTS)
@pytest.mark.parametrize(
    ("field", "shown"),
    [
        (memoryview(b"sha-256=:AAAA:"), "memoryview"),
        (memoryview(b""), "memoryview"),
        (array("B", b"sha-256=:AAAA:"), "array"),
        (array("B"), "array"),
        (5, "int"),
        (None, "NoneType"),
    ],
)
def test_a_field_of_the_wrong_type_is_named_in_the_message(
    call: Callable[[Any], Any], field: object, shown: str
) -> None:
    if field is None and call is FIELD_ENTRY_POINTS[-1]:
        # An absent preference field is no preference, not a type error.
        assert call(field) is None
        return
    with pytest.raises(TypeError) as caught:
        call(field)
    assert str(caught.value) == NOT_A_FIELD + shown


@pytest.mark.parametrize("call", FIELD_ENTRY_POINTS)
def test_a_field_line_of_the_wrong_type_is_named_in_the_message(
    call: Callable[[Any], Any],
) -> None:
    for line, shown in [(memoryview(b"a=:AA==:"), "memoryview"), (5, "int"), (None, "NoneType")]:
        with pytest.raises(TypeError) as caught:
            call([SHA256, line])
        assert str(caught.value) == f"a field line must be str, bytes or bytearray, not {shown}"
