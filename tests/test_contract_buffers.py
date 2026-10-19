"""Bodies whose buffer cannot be read: which error each one raises, through every entry point."""

from __future__ import annotations

import ctypes
import mmap
import sys
from collections.abc import Callable
from typing import Any

import pytest

from contentdigest import SUPPORTED_ALGORITHMS, Digester, Verifier, make_digest, verify
from contentdigest._types import Buffer


def _entry_points(body: Buffer) -> list[Callable[[], Any]]:
    return [
        lambda: make_digest(body),
        lambda: Digester().update(body),
        lambda: verify("sha-256=:AAAA:", body),
        lambda: Verifier("sha-256=:AAAA:").update(body),
    ]


def test_a_released_memoryview_is_a_type_error() -> None:
    released = memoryview(b"abc")
    released.release()
    for call in _entry_points(released):
        with pytest.raises(TypeError, match="released memoryview"):
            call()


def test_a_closed_mmap_keeps_the_exporters_value_error() -> None:
    # An anonymous map needs no file; once closed, it refuses to export its buffer.
    closed = mmap.mmap(-1, 3)
    closed.close()
    for call in _entry_points(closed):
        with pytest.raises(ValueError, match="closed") as caught:
            call()
        assert type(caught.value) is ValueError


@pytest.mark.skipif(sys.version_info < (3, 12), reason="__buffer__ is honoured from Python 3.12")
def test_an_exporters_own_value_error_reaches_the_caller_unchanged() -> None:
    class Refusing:
        def __buffer__(self, flags: int, /) -> memoryview:
            raise ValueError("I/O operation on closed file")

    for call in _entry_points(Refusing()):
        with pytest.raises(ValueError) as caught:
            call()
        assert type(caught.value) is ValueError
        assert str(caught.value) == "I/O operation on closed file"


@pytest.mark.parametrize("algo", sorted(SUPPORTED_ALGORITHMS))
def test_an_empty_buffer_of_any_shape_is_the_empty_body(algo: str) -> None:
    # A zero-length dimension: memoryview.cast refuses such a shape, but the body is empty.
    # Every algorithm is checked: the checksums cannot read such a view, unlike hashlib.
    algos = [algo]
    empty = make_digest(b"", algos=algos)
    shapes: list[Any] = [
        (ctypes.c_ubyte * 4 * 0)(),
        (ctypes.c_ubyte * 0 * 3)(),
        (ctypes.c_uint32 * 0)(),
    ]
    for body in shapes:
        assert make_digest(body, algos=algos) == empty
        digester = Digester(algos)
        digester.update(body)
        assert digester.value() == empty
        assert verify(empty, body, accept=algos)
        verifier = Verifier(empty, accept=algos)
        verifier.update(body)
        assert verifier.verify()
