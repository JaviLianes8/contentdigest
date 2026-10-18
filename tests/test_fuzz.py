"""Seeded property tests: hostile input only ever raises DigestError, and round trips hold.

CONTENTDIGEST_FUZZ_SCALE multiplies every case count for a longer run (default 1).
"""

from __future__ import annotations

import hashlib
import os
import random
from typing import Any

import generators
import pytest

from contentdigest import (
    ACTIVE_ALGORITHMS,
    SUPPORTED_ALGORITHMS,
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

SEEDS = [1, 2, 3]
SCALE = int(os.environ.get("CONTENTDIGEST_FUZZ_SCALE", "1"))
ALGOS = sorted(SUPPORTED_ALGORITHMS)


def _hostile(rng: random.Random) -> str:
    pick = rng.randrange(3)
    if pick == 0:
        return generators.mutate(rng, generators.dictionary(rng))
    if pick == 1:
        return generators.dictionary(rng)
    return "".join(rng.choice(generators.HOSTILE) for _ in range(rng.randrange(30)))


def _outcome(call: Any, *args: Any, **kwargs: Any) -> object:
    try:
        return call(*args, **kwargs)
    except DigestError as error:
        assert len(str(error)) < 300
        return DigestError


@pytest.mark.parametrize("seed", SEEDS)
def test_hostile_fields_only_raise_digest_error(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000 * SCALE):
        text = _hostile(rng)
        digests = _outcome(parse, text)
        weights = _outcome(parse_want, text)
        _outcome(choose_algorithm, text, supported=ALGOS)
        _outcome(verify, text, b"body", accept=ALGOS)
        if digests is not DigestError:
            assert all(type(value) is bytes for value in digests.values())  # type: ignore[attr-defined]
        if weights is not DigestError:
            assert all(0 <= w <= 10 for w in weights.values())  # type: ignore[attr-defined]
        # A field is the same whether it arrives as text, bytes or split over lines.
        assert _outcome(parse, text.encode("latin-1")) == digests
        assert _outcome(parse, [text]) == digests


@pytest.mark.parametrize("seed", SEEDS)
def test_made_fields_parse_back_and_verify(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(300 * SCALE):
        body = rng.randbytes(rng.randrange(0, 2000))
        algos = rng.sample(ALGOS, rng.randrange(1, len(ALGOS) + 1))
        field = make_digest(body, algos=algos)
        digests = parse(field)
        assert list(digests) == algos
        for name in ("sha-256", "sha-512", "md5"):
            if name in digests:
                standard = {"sha-256": "sha256", "sha-512": "sha512", "md5": "md5"}[name]
                assert digests[name] == hashlib.new(standard, body).digest()
        assert verify(field, body, accept=algos)
        assert not verify(field, body + b"\0", accept=algos)
        cut = rng.randrange(len(body) + 1)
        verifier = Verifier(field.split(", "), accept=algos)
        verifier.update(body[:cut])
        verifier.update(memoryview(body)[cut:])
        assert verifier.verify() and verifier.algorithms == tuple(algos)


@pytest.mark.parametrize("seed", SEEDS)
def test_made_preferences_parse_back_and_choose_like_the_model(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(1000 * SCALE):
        keys = list(dict.fromkeys(generators.key(rng) for _ in range(rng.randrange(1, 6))))
        keys += rng.sample(ALGOS, rng.randrange(0, 4))
        preferences = {key: rng.randrange(11) for key in dict.fromkeys(keys)}
        field = make_want(preferences)
        assert parse_want(field) == preferences
        supported = rng.sample(ALGOS, rng.randrange(0, len(ALGOS) + 1))
        weights = [(w, -i, k) for i, (k, w) in enumerate(preferences.items()) if k in supported]
        best = max(weights, default=(0, 0, None))
        assert choose_algorithm(field, supported=supported) == (best[2] if best[0] else None)


@pytest.mark.parametrize("seed", SEEDS)
def test_chunked_digests_equal_one_shot_for_every_algorithm(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(40 * SCALE):
        body = rng.randbytes(rng.randrange(0, 5000))
        digester = Digester(ALGOS)
        position = 0
        while position < len(body):
            step = rng.randrange(1, 700)
            digester.update(body[position : position + step])
            position += step
        assert digester.value() == make_digest(body, algos=ALGOS)


def test_a_field_with_many_members_checks_only_the_accepted_ones() -> None:
    body = b"payload"
    members = [f"k{i}=:AAAA:" for i in range(5000)] + [make_digest(body)]
    verifier = Verifier(", ".join(members))
    assert verifier.algorithms == ("sha-256",)
    verifier.update(body)
    assert verifier.verify()
    assert set(Verifier(", ".join(members), accept=ACTIVE_ALGORITHMS).algorithms) == {"sha-256"}
