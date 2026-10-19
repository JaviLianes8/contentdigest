"""Errors: the type each failure raises, and messages that stay short for any input."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

import contentdigest
from contentdigest import (
    Digester,
    DigestError,
    Verifier,
    choose_algorithm,
    make_digest,
    make_want,
    parse,
    parse_want,
    verify,
)

SHA256 = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
HUGE = "q" * 1_000_000
LONG_KEY = "k" + "e" * 1_000_000
# Wrong types on purpose: called through an untyped alias so the checker lets them pass.
api: Any = contentdigest
WIDE = type("N" * 100_000, (), {})()  # an instance of a type with a 100,000 character name

WRONG_TYPES: list[Callable[[], Any]] = [
    lambda: api.make_digest("text"),
    lambda: api.make_digest(5),
    lambda: api.make_digest(b"", algos="sha-256"),
    lambda: api.make_digest(b"", algos=5),
    lambda: api.make_digest(b"", algos=[b"sha-256"]),
    lambda: api.parse(5),
    lambda: api.parse(None),
    lambda: api.parse([5]),
    lambda: api.parse(memoryview(b"a=:AA==:")),
    lambda: api.verify(SHA256, "text"),
    lambda: api.verify(SHA256, b"", accept="sha-256"),
    lambda: api.verify(SHA256, b"", accept=[None]),
    lambda: api.parse_want(5),
    lambda: api.make_want([("sha-256", 1)]),
    lambda: api.make_want({5: 1}),
    lambda: api.make_want({"sha-256": "1"}),
    lambda: api.make_want({"sha-256": 1.0}),
    lambda: api.make_want({"sha-256": True}),
    lambda: api.choose_algorithm(5),
    lambda: api.choose_algorithm("sha-256=1", supported="sha-256"),
    lambda: api.Digester("sha-256"),
    lambda: api.Digester().update("text"),
    lambda: api.Digester().update(None),
    lambda: api.Verifier(5),
    lambda: api.Verifier(SHA256, accept="sha-256"),
    lambda: api.Verifier(SHA256).update("text"),
]

INVALID_VALUES: list[Callable[[], Any]] = [
    lambda: make_digest(b"", algos=["sha3-256"]),
    lambda: make_digest(b"", algos=[]),
    lambda: parse("sha-256=1"),
    lambda: parse("SHA-256=:AAAA:"),
    lambda: parse(f"{SHA256},"),
    lambda: verify(SHA256, b"", accept=["sha256"]),
    lambda: verify("md5=:AAAA:", b""),
    lambda: verify("", b""),
    lambda: parse_want("sha-256=11"),
    lambda: make_want({}),
    lambda: make_want({"sha 256": 1}),
    lambda: make_want({"a": 1, "A": 2}),
    lambda: make_want({"sha-256": 11}),
    lambda: choose_algorithm("sha-256=:AAAA:"),
    lambda: choose_algorithm(None, supported=["nope"]),
    lambda: Digester([]),
    lambda: Verifier("crc32c=:AAAAAA==:"),
]

HUGE_INPUTS: list[Callable[[], Any]] = [
    lambda: api.make_digest(b"", algos=[HUGE]),
    lambda: api.make_digest(b"", algos=[WIDE]),
    lambda: api.make_digest(WIDE),
    lambda: api.parse(LONG_KEY + "=1"),
    lambda: api.parse([WIDE]),
    lambda: api.parse("a=:" + "A" * 1_000_000),
    lambda: api.parse_want(LONG_KEY + "=:AA==:"),
    lambda: api.verify(", ".join(f"k{i}=:AA==:" for i in range(100_000)), b""),
    lambda: api.verify(LONG_KEY + "=:AA==:", b""),
    lambda: api.verify(SHA256, b"", accept=[HUGE]),
    lambda: api.make_want({HUGE + "!": 1}),
    lambda: api.make_want({LONG_KEY: 11}),
    lambda: api.make_want({LONG_KEY: WIDE}),
    lambda: api.make_want({"sha-256": 10**5000}),
    lambda: api.make_want({"sha-256": -(10**5000)}),
    lambda: api.make_want(WIDE),
    lambda: api.choose_algorithm("sha-256=1", supported=[HUGE]),
    lambda: api.Verifier(SHA256, accept=[WIDE]),
]


@pytest.mark.parametrize("call", WRONG_TYPES)
def test_wrong_argument_types_raise_type_error(call: Callable[[], Any]) -> None:
    with pytest.raises(TypeError):
        call()


@pytest.mark.parametrize("call", INVALID_VALUES)
def test_invalid_values_raise_digest_error(call: Callable[[], Any]) -> None:
    with pytest.raises(DigestError) as caught:
        call()
    assert isinstance(caught.value, ValueError)


@pytest.mark.parametrize("call", HUGE_INPUTS)
def test_messages_stay_short_for_huge_input(call: Callable[[], Any]) -> None:
    with pytest.raises((DigestError, TypeError)) as caught:
        call()
    assert len(str(caught.value)) < 300, str(caught.value)[:400]


def test_a_huge_weight_is_a_digest_error_not_a_formatting_error() -> None:
    with pytest.raises(DigestError, match="out of range"):
        make_want({"sha-256": 10**5000})
    with pytest.raises(DigestError, match=r"not 11$"):
        make_want({"sha-256": 11})


def test_a_long_name_is_quoted_with_its_length() -> None:
    with pytest.raises(DigestError) as caught:
        make_digest(b"", algos=[HUGE])
    assert str(caught.value) == f"unsupported algorithm: {'q' * 40!r}... (1000000 characters)"


def test_the_no_accepted_algorithm_message_lists_a_few_names() -> None:
    field = ", ".join(f"k{i}=:AA==:" for i in range(7))
    with pytest.raises(DigestError) as caught:
        verify(field, b"")
    assert str(caught.value) == (
        "no accepted algorithm in the field (it has 'k0', 'k1', 'k2', 'k3', 'k4' and 2 more; "
        "accepted are 'sha-256', 'sha-512')"
    )


def test_a_type_name_is_cut_in_messages() -> None:
    with pytest.raises(TypeError) as caught:
        make_digest(WIDE)
    assert str(caught.value) == f"the body must be bytes-like, not {'N' * 40}..."


def test_a_released_buffer_is_a_type_error() -> None:
    released = memoryview(b"abc")
    released.release()
    calls: list[Callable[[], Any]] = [
        lambda: make_digest(released),
        lambda: Digester().update(released),
        lambda: verify("sha-256=:AAAA:", released),
        lambda: Verifier("sha-256=:AAAA:").update(released),
    ]
    for call in calls:
        with pytest.raises(TypeError, match="released"):
            call()
