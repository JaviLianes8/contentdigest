"""make_digest, parse and verify: the one-shot API."""

from __future__ import annotations

import base64
from array import array

import pytest

from contentdigest import DigestError, make_digest, parse, verify

# RFC 9530 Appendix D: {"hello": "world"} under sha-256.
BODY = b'{"hello": "world"}'
SHA256 = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
RAW256 = base64.b64decode("X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=")


def test_make_digest_defaults_to_sha_256() -> None:
    assert make_digest(BODY) == SHA256


def test_make_digest_emits_one_member_per_algorithm_in_order() -> None:
    field = make_digest(BODY, algos=("sha-512", "sha-256"))
    assert list(parse(field)) == ["sha-512", "sha-256"]


def test_make_digest_lower_cases_and_drops_repeated_algorithms() -> None:
    assert make_digest(BODY, algos=("SHA-256", "sha-256")) == SHA256


@pytest.mark.parametrize("body", [bytearray(BODY), memoryview(BODY), array("B", BODY)])
def test_make_digest_takes_any_bytes_like_body(body: object) -> None:
    assert make_digest(body) == SHA256  # type: ignore[arg-type]


def test_make_digest_hashes_the_bytes_of_a_wide_buffer() -> None:
    wide = array("I", [1, 2])
    assert make_digest(wide) == make_digest(wide.tobytes())


def test_make_digest_hashes_a_non_contiguous_view() -> None:
    assert make_digest(memoryview(b"abcdef")[::2]) == make_digest(b"ace")


@pytest.mark.parametrize("body", ["text", 5, None])
def test_make_digest_refuses_a_body_that_is_not_bytes_like(body: object) -> None:
    with pytest.raises(TypeError):
        make_digest(body)  # type: ignore[arg-type]


def test_make_digest_rejects_an_unknown_algorithm() -> None:
    with pytest.raises(DigestError, match="unsupported algorithm"):
        make_digest(BODY, algos=("sha3-256",))


def test_make_digest_rejects_an_empty_algorithm_list() -> None:
    with pytest.raises(DigestError):
        make_digest(BODY, algos=())


def test_make_digest_refuses_a_bare_string_of_algorithms() -> None:
    with pytest.raises(TypeError, match="collection"):
        make_digest(BODY, algos="sha-256")


def test_parse_returns_raw_digest_bytes_in_field_order() -> None:
    parsed = parse(make_digest(BODY, algos=("sha-512", "sha-256")))
    assert list(parsed) == ["sha-512", "sha-256"]
    assert parsed["sha-256"] == RAW256


def test_parse_keeps_unknown_algorithms() -> None:
    assert parse("future-hash=:AAAA:") == {"future-hash": b"\x00\x00\x00"}


def test_parse_ignores_parameters_and_tabs() -> None:
    assert parse(f"md5=:AAAA:;x=1,\t{SHA256};y") == {"md5": b"\0\0\0", "sha-256": RAW256}


def test_parse_takes_bytes_and_several_field_lines() -> None:
    assert parse(SHA256.encode()) == {"sha-256": RAW256}
    assert parse(["md5=:AAAA:", SHA256.encode()]) == {"md5": b"\0\0\0", "sha-256": RAW256}


def test_parse_keeps_the_last_of_repeated_keys() -> None:
    assert parse(f"sha-256=:AAAA:, {SHA256}") == {"sha-256": RAW256}


def test_parse_of_an_empty_field_is_empty() -> None:
    assert parse("") == {}
    assert parse([]) == {}


def test_parse_accepts_missing_padding_and_non_zero_pad_bits() -> None:
    assert parse("a=:aGVsbG8:, b=:iZ==:") == {"a": b"hello", "b": b"\x89"}


@pytest.mark.parametrize(
    "field",
    [
        "sha-256",
        "sha-256=",
        "sha-256=1",
        "sha-256=token",
        'sha-256="string"',
        "sha-256=(:AAAA:)",
        "sha-256=:not*base64:",
        "sha-256=:a=GVsbG8=:",
        "sha-256=:aGVsbG8===:",
        "sha-256=:A:",
        SHA256.upper(),
        f"{SHA256},",
        f"{SHA256} junk",
        "sha-256=:AAAA:, md5",
        "sha-256 =:AAAA:",
        "sha-256=:AAéA:",
    ],
)
def test_parse_rejects_the_whole_malformed_field(field: str) -> None:
    with pytest.raises(DigestError):
        parse(field)


def test_parse_rejects_non_ascii_bytes() -> None:
    with pytest.raises(DigestError):
        parse("sha-256=:AAéA:".encode())


@pytest.mark.parametrize("field", [5, None, [5]])
def test_parse_refuses_a_field_of_the_wrong_type(field: object) -> None:
    with pytest.raises(TypeError):
        parse(field)  # type: ignore[arg-type]


def test_verify_accepts_a_matching_body() -> None:
    assert verify(SHA256, BODY) is True


def test_verify_rejects_a_different_body() -> None:
    assert verify(SHA256, BODY + b" ") is False


def test_verify_needs_every_accepted_member_to_match() -> None:
    good512 = make_digest(BODY, algos=["sha-512"])
    assert verify(f"{good512}, {SHA256}", BODY) is True
    assert verify(f"{good512}, sha-256=:AAAA:", BODY) is False
    assert verify(f"sha-256=:AAAA:, {good512}", BODY) is False


def test_verify_ignores_members_outside_accept() -> None:
    assert verify(f"md5=:AAAA:, {SHA256}", BODY) is True
    assert verify(f"md5=:AAAA:, {SHA256}", BODY, accept=["sha-256"]) is True


def test_verify_checks_deprecated_members_only_when_accepted() -> None:
    field = f"md5=:AAAA:, {SHA256}"
    assert verify(field, BODY, accept=["md5", "sha-256"]) is False


def test_verify_raises_when_no_accepted_algorithm_is_present() -> None:
    with pytest.raises(DigestError, match="no accepted algorithm"):
        verify(make_digest(BODY, algos=["md5"]), BODY)
    with pytest.raises(DigestError):
        verify("", BODY)


def test_verify_rejects_unknown_names_in_accept() -> None:
    with pytest.raises(DigestError):
        verify(SHA256, BODY, accept=["sha256"])
    with pytest.raises(TypeError):
        verify(SHA256, BODY, accept="sha-256")


def test_verify_treats_a_truncated_digest_as_a_mismatch() -> None:
    short = base64.b64encode(RAW256[:16]).decode()
    assert verify(f"sha-256=:{short}:", BODY) is False
