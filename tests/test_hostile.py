"""Hostile shapes: time grows linearly with the input, and huge inputs stay workable."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable

import pytest

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
from contentdigest._sf import parse_dictionary


def _swallow(call: Callable[[], object]) -> None:
    with contextlib.suppress(DigestError):
        call()


# Each shape builds a call for a size n; n is picked so the small run takes milliseconds.
SHAPES: dict[str, tuple[int, Callable[[int], Callable[[], object]]]] = {
    "members": (20_000, lambda n: lambda: parse(", ".join(f"k{i}=:AA==:" for i in range(n)))),
    "repeated key": (20_000, lambda n: lambda: parse(", ".join(["a=:AA==:"] * n))),
    "long byte sequence": (500_000, lambda n: lambda: parse("a=:" + "QUFB" * n + ":")),
    "unterminated byte sequence": (500_000, lambda n: lambda: parse("a=:" + "QUFB" * n)),
    "long key": (500_000, lambda n: lambda: parse("a" * n + "=:AA==:")),
    "parameters": (20_000, lambda n: lambda: parse("a=:AA==:" + ";p=1" * n)),
    "whitespace": (500_000, lambda n: lambda: parse("a=:AA==:" + " \t" * n + ",b=:AA==:")),
    "field lines": (20_000, lambda n: lambda: parse(["a=:AA==:"] * n)),
    "inner list": (20_000, lambda n: lambda: parse_dictionary("a=(" + "1 " * n + ")")),
    "long string": (200_000, lambda n: lambda: parse('a="' + 'x\\"' * n + '"')),
    "display string": (50_000, lambda n: lambda: parse('a=%"' + "%c3%a9" * n + '"')),
    "want members": (20_000, lambda n: lambda: parse_want(", ".join(f"k{i}=5" for i in range(n)))),
    "choose": (20_000, lambda n: lambda: choose_algorithm(",".join(f"k{i}=1" for i in range(n)))),
    "make want": (20_000, lambda n: lambda: make_want({f"k{i}": 1 for i in range(n)})),
    "verifier": (20_000, lambda n: lambda: Verifier(",".join(f"k{i}=:AA==:" for i in range(n)))),
    "broken at the end": (20_000, lambda n: lambda: parse("a=:AA==:," * n + "!")),
    # A caller may pass the same name many times; the field is still the attacker's.
    "repeated accept names": (
        4_000,
        lambda n: (
            lambda: verify(",".join(f"k{i}=:AA==:" for i in range(n)), b"", accept=["sha-256"] * n)
        ),
    ),
    "repeated supported names": (
        4_000,
        lambda n: lambda: choose_algorithm(",".join(f"k{i}=9" for i in range(n)), ["sha-256"] * n),
    ),
}


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        _swallow(call)
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_time_grows_linearly(shape: str) -> None:
    size, build = SHAPES[shape]
    small, large = _seconds(build(size)), _seconds(build(4 * size))
    # Linear growth gives a ratio near 4; quadratic would give 16. Timing noise is allowed for.
    assert large < 10 * max(small, 0.002), (shape, small, large)


def test_a_large_body_streams_through_every_algorithm() -> None:
    digester = Digester(["sha-256", "sha-512", "md5", "sha", "adler"])
    chunk = bytes(range(256)) * 4096
    for _ in range(10):
        digester.update(chunk)
    assert digester.value() == make_digest(
        chunk * 10, ["sha-256", "sha-512", "md5", "sha", "adler"]
    )


def test_a_huge_field_is_refused_with_a_short_message() -> None:
    with pytest.raises(DigestError) as caught:
        parse("a=:AA==:," * 200_000 + "!")
    assert len(str(caught.value)) < 200
