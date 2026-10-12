"""Want-Content-Digest and Want-Repr-Digest: parse_want, make_want, choose_algorithm."""

from __future__ import annotations

import pytest

from contentdigest import DigestError, choose_algorithm, make_want, parse_want


def test_parse_want_keeps_field_order_and_unknown_keys() -> None:
    assert parse_want("b=1, future=4, a=10") == {"b": 1, "future": 4, "a": 10}


def test_parse_want_ignores_parameters_and_takes_lines() -> None:
    assert parse_want(["sha-256=10;q=1", b"md5=0"]) == {"sha-256": 10, "md5": 0}


def test_parse_want_of_an_empty_field_is_empty() -> None:
    assert parse_want("") == {}


@pytest.mark.parametrize(
    "field", ["sha-256=11", "sha-256=-1", "sha-256=1.0", "sha-256", "sha-256=?1", "sha-256=@1"]
)
def test_parse_want_rejects_weights_that_are_not_0_to_10(field: str) -> None:
    with pytest.raises(DigestError):
        parse_want(field)


def test_parse_want_accepts_both_ends_of_the_range() -> None:
    assert parse_want("a=0, b=10") == {"a": 0, "b": 10}


def test_make_want_round_trips() -> None:
    value = make_want({"sha-512": 3, "SHA-256": 10, "unixsum": 0})
    assert value == "sha-512=3, sha-256=10, unixsum=0"
    assert parse_want(value) == {"sha-512": 3, "sha-256": 10, "unixsum": 0}


@pytest.mark.parametrize("weight", [11, -1])
def test_make_want_rejects_out_of_range_weights(weight: int) -> None:
    with pytest.raises(DigestError):
        make_want({"sha-256": weight})


@pytest.mark.parametrize("weight", [True, 1.0, "1"])
def test_make_want_refuses_weights_that_are_not_int(weight: object) -> None:
    with pytest.raises(TypeError):
        make_want({"sha-256": weight})  # type: ignore[dict-item]


@pytest.mark.parametrize("key", ["", "1sha", "sha 256", "sha=", "shä"])
def test_make_want_rejects_invalid_keys(key: str) -> None:
    with pytest.raises(DigestError):
        make_want({key: 1})


def test_make_want_needs_a_preference() -> None:
    with pytest.raises(DigestError):
        make_want({})


def test_choose_takes_the_highest_supported_weight() -> None:
    assert choose_algorithm("sha-256=3, sha-512=7") == "sha-512"


def test_choose_breaks_ties_by_field_order() -> None:
    assert choose_algorithm("sha-512=5, sha-256=5") == "sha-512"
    assert choose_algorithm("sha-256=5, sha-512=5") == "sha-256"


def test_choose_never_picks_weight_zero() -> None:
    assert choose_algorithm("sha-256=0, md5=1") is None


def test_choose_respects_the_supported_set() -> None:
    assert choose_algorithm("md5=9, sha-256=1", supported=["md5", "sha-256"]) == "md5"
    assert choose_algorithm("md5=9, sha-256=1") == "sha-256"


def test_choose_returns_none_for_an_absent_or_empty_field() -> None:
    assert choose_algorithm(None) is None
    assert choose_algorithm("") is None


def test_choose_validates_supported_names() -> None:
    with pytest.raises(DigestError):
        choose_algorithm("sha-256=1", supported=["sha256"])
    with pytest.raises(TypeError):
        choose_algorithm("sha-256=1", supported="sha-256")


def test_choose_raises_on_a_malformed_field() -> None:
    with pytest.raises(DigestError):
        choose_algorithm("sha-256=11")
