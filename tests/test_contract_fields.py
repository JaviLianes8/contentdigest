"""Fields as callers hand them over: a whole bytearray, and iterables that fail on their own."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from contentdigest import Verifier, choose_algorithm, parse, parse_want, verify

SHA256 = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
BODY = b'{"hello": "world"}'

# Each field entry point, called so that its result can be compared across equal fields.
ENTRY_POINTS: dict[str, Callable[[Any], object]] = {
    "parse": parse,
    "parse_want": parse_want,
    "verify": lambda field: verify(field, BODY),
    "Verifier": lambda field: Verifier(field).algorithms,
    "choose_algorithm": choose_algorithm,
}
FIELDS = {
    "parse": SHA256,
    "parse_want": "sha-512=3, sha-256=10",
    "verify": SHA256,
    "Verifier": SHA256,
    "choose_algorithm": "sha-512=3, sha-256=10",
}


@pytest.mark.parametrize("name", sorted(ENTRY_POINTS))
def test_a_whole_field_as_bytearray_reads_like_the_equal_bytes(name: str) -> None:
    call, text = ENTRY_POINTS[name], FIELDS[name]
    expected = call(text.encode("ascii"))
    assert call(bytearray(text, "ascii")) == expected
    assert call(text) == expected


class _CallerError(Exception):
    """An error of the caller's own, which the library has no reason to know."""


def _failing_lines(error: Exception) -> Iterator[str]:
    yield SHA256
    raise error


@pytest.mark.parametrize("name", sorted(ENTRY_POINTS))
@pytest.mark.parametrize(
    "error", [TypeError("caller iterable broke"), _CallerError("caller iterable broke")]
)
def test_an_iterables_own_error_reaches_the_caller_unchanged(name: str, error: Exception) -> None:
    with pytest.raises(type(error)) as caught:
        ENTRY_POINTS[name](_failing_lines(error))
    assert caught.value is error
    assert str(caught.value) == "caller iterable broke"
