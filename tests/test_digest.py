import base64

import pytest

from contentdigest import DigestError, make_digest, parse, verify

# RFC 9530 worked example: the body {"hello": "world"} under sha-256.
BODY = b'{"hello": "world"}'
SHA256_VALUE = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"


def test_make_digest_matches_the_rfc_example() -> None:
    assert make_digest(BODY) == SHA256_VALUE


def test_make_digest_emits_one_member_per_algorithm_in_order() -> None:
    header = make_digest(BODY, algos=("sha-512", "sha-256"))
    keys = [member.split("=", 1)[0] for member in header.split(", ")]
    assert keys == ["sha-512", "sha-256"]


def test_make_digest_accepts_algorithm_names_case_insensitively() -> None:
    assert make_digest(BODY, algos=("SHA-256",)) == SHA256_VALUE


def test_make_digest_rejects_an_unsupported_algorithm() -> None:
    with pytest.raises(DigestError):
        make_digest(BODY, algos=("md5",))


def test_make_digest_rejects_an_empty_algorithm_list() -> None:
    with pytest.raises(DigestError):
        make_digest(BODY, algos=())


def test_parse_round_trips_the_raw_digest_bytes() -> None:
    parsed = parse(make_digest(BODY, algos=("sha-256", "sha-512")))
    assert set(parsed) == {"sha-256", "sha-512"}
    expected = base64.b64decode("X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=")
    assert parsed["sha-256"] == expected


def test_parse_keeps_unsupported_algorithms() -> None:
    parsed = parse("md5=:1B2M2Y8AsgTpgAmY7PhCfg==:")
    assert set(parsed) == {"md5"}


def test_parse_tolerates_surrounding_whitespace() -> None:
    assert parse(f"  {SHA256_VALUE}  ") == parse(SHA256_VALUE)


@pytest.mark.parametrize(
    "header",
    [
        "",
        "sha-256",
        "sha-256=",
        "sha-256=notabytesequence",
        "sha-256=:not*base64:",
        "SHA-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:",
        "sha-256=:abc:,",
    ],
)
def test_parse_rejects_malformed_input(header: str) -> None:
    with pytest.raises(DigestError):
        parse(header)


def test_verify_accepts_a_matching_digest() -> None:
    assert verify(make_digest(BODY), BODY) is True


def test_verify_rejects_a_mismatching_body() -> None:
    assert verify(make_digest(BODY), b"tampered") is False


def test_verify_checks_every_supported_member() -> None:
    header = make_digest(BODY, algos=("sha-256", "sha-512"))
    assert verify(header, BODY) is True
    assert verify(header, b"tampered") is False


def test_verify_raises_when_no_supported_algorithm_is_present() -> None:
    with pytest.raises(DigestError):
        verify("md5=:1B2M2Y8AsgTpgAmY7PhCfg==:", BODY)
