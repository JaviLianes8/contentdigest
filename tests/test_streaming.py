"""Digester and Verifier: the same results as the one-shot API, fed in chunks."""

from __future__ import annotations

import random

import pytest

from contentdigest import (
    SUPPORTED_ALGORITHMS,
    Digester,
    DigestError,
    Verifier,
    make_digest,
)

ALL = sorted(SUPPORTED_ALGORITHMS)


def _chunks(data: bytes, rng: random.Random) -> list[bytes]:
    cuts = sorted(rng.sample(range(len(data) + 1), k=min(len(data) + 1, 6)))
    return [data[a:b] for a, b in zip([0, *cuts], [*cuts, len(data)], strict=True)]


@pytest.mark.parametrize("seed", range(20))
def test_chunked_digest_equals_one_shot(seed: int) -> None:
    rng = random.Random(seed)
    data = rng.randbytes(rng.randrange(0, 3000))
    digester = Digester(ALL)
    for chunk in _chunks(data, rng):
        digester.update(chunk)
    assert digester.value() == make_digest(data, algos=ALL)


def test_digests_can_be_read_midway_and_feeding_continues() -> None:
    digester = Digester(ALL)
    digester.update(b"abc")
    assert digester.value() == make_digest(b"abc", algos=ALL)
    assert digester.value() == make_digest(b"abc", algos=ALL)
    digester.update(b"def")
    assert digester.value() == make_digest(b"abcdef", algos=ALL)


def test_a_fresh_digester_digests_the_empty_body() -> None:
    assert Digester().value() == make_digest(b"")


def test_digester_needs_an_algorithm() -> None:
    with pytest.raises(DigestError):
        Digester([])


def test_digester_refuses_text_chunks() -> None:
    with pytest.raises(TypeError):
        Digester().update("text")  # type: ignore[arg-type]


def test_verifier_reads_the_field_then_the_chunks() -> None:
    field = make_digest(b"hello world", algos=["sha-256", "sha-512"])
    verifier = Verifier(field)
    assert verifier.algorithms == ("sha-256", "sha-512")
    verifier.update(b"hello ")
    assert verifier.verify() is False
    verifier.update(b"world")
    assert verifier.verify() is True
    verifier.update(b"!")
    assert verifier.verify() is False


def test_verifier_hashes_only_the_accepted_algorithms_present() -> None:
    field = make_digest(b"x", algos=["md5", "sha-512", "crc32c"])
    assert Verifier(field).algorithms == ("sha-512",)
    assert Verifier(field, accept=ALL).algorithms == ("md5", "sha-512", "crc32c")


def test_verifier_raises_on_a_field_without_accepted_members() -> None:
    with pytest.raises(DigestError):
        Verifier(make_digest(b"x", algos=["crc32c"]))


def test_verifier_raises_on_a_malformed_field() -> None:
    with pytest.raises(DigestError):
        Verifier("sha-256=:AAAA:,")
