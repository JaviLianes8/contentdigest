"""Collections of algorithm names: what counts as one, and the order of what comes out."""

from __future__ import annotations

import mmap
from array import array
from collections.abc import Callable, Iterator
from typing import Any

import pytest

import contentdigest
from contentdigest import Digester, Verifier, choose_algorithm, make_digest, verify

SHA256 = "sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:"
SHA512 = (
    "sha-512=:z4PhNX7vuL3xVChQ1m2AB9Yg5AULVxXcg/SpIdNs6c5H0NE8XYXysP+DG"
    "NKHfuwvY7kxvUdBeoGlODJ6+SfaPg==:"
)
# Wrong types on purpose: called through an untyped alias so the checker lets them pass.
api: Any = contentdigest
STR_TYPE = type("Names", (str,), {})
BYTES_TYPE = type("Raw", (bytes,), {})

NAME_COLLECTION_ARGS: list[Callable[[Any], Any]] = [
    lambda names: api.make_digest(b"", algos=names),
    lambda names: api.verify(SHA256, b"", accept=names),
    lambda names: api.choose_algorithm("sha-256=1", supported=names),
    lambda names: api.Digester(names),
    lambda names: api.Verifier(SHA256, accept=names),
]


def _mapped(data: bytes) -> mmap.mmap:
    mapped = mmap.mmap(-1, len(data))
    mapped.write(data)
    return mapped


def _closed_mmap() -> mmap.mmap:
    mapped = _mapped(b"sha-256")
    mapped.close()
    return mapped


def _released_view() -> memoryview:
    view = memoryview(b"sha-256")
    view.release()
    return view


# A string or any bytes-like value (anything that exports the buffer protocol, subclasses
# included) is one value, never a collection of names, empty or not.
SINGLE_VALUES: list[Callable[[], object]] = [
    lambda: STR_TYPE(""),
    lambda: STR_TYPE("sha-256"),
    lambda: b"",
    lambda: b"sha-256",
    lambda: BYTES_TYPE(b""),
    lambda: BYTES_TYPE(b"sha-256"),
    lambda: bytearray(),
    lambda: bytearray(b"sha-256"),
    lambda: memoryview(b""),
    lambda: memoryview(b"sha-256"),
    _released_view,
    lambda: array("B"),
    lambda: array("B", b"sha-256"),
    lambda: array("I", [1, 2]),
    lambda: _mapped(b"sha-256"),
    _closed_mmap,
]


@pytest.mark.parametrize("value", SINGLE_VALUES)
@pytest.mark.parametrize("call", NAME_COLLECTION_ARGS)
def test_a_bytes_like_value_is_not_a_name_collection(
    call: Callable[[Any], Any], value: Callable[[], object]
) -> None:
    with pytest.raises(TypeError, match="must be a collection of algorithm names, not a single"):
        call(value())


ONE_SHOT: list[Callable[[], Iterator[str]]] = [
    lambda: (name for name in ["sha-256"]),
    lambda: iter(["sha-256"]),
    lambda: iter({"sha-256": 1}),
]


@pytest.mark.parametrize("names", ONE_SHOT)
def test_a_one_shot_iterable_is_a_name_collection(names: Callable[[], Iterator[str]]) -> None:
    assert make_digest(b"", algos=names()) == SHA256
    assert verify(SHA256, b"", accept=names()) is True
    assert verify(SHA256, b"x", accept=names()) is False
    assert choose_algorithm("sha-512=9, sha-256=1", supported=names()) == "sha-256"
    digester = Digester(names())
    assert digester.value() == SHA256
    verifier = Verifier(SHA256, accept=names())
    assert verifier.algorithms == ("sha-256",)
    assert verifier.verify() is True


def test_a_repeated_name_keeps_the_place_of_its_first_occurrence() -> None:
    names = ["sha-256", "sha-512", "SHA-256"]
    assert make_digest(b"", algos=names) == f"{SHA256}, {SHA512}"
    assert Digester(names).value() == f"{SHA256}, {SHA512}"
    assert list(Digester(names).digests()) == ["sha-256", "sha-512"]
    assert make_digest(b"", algos=["sha-512", "sha-256", "sha-512"]) == f"{SHA512}, {SHA256}"
