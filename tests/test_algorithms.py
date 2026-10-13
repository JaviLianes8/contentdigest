"""The registry and its checksums.

Registry statuses: RFC 9530 section 7.2 (https://www.rfc-editor.org/rfc/rfc9530.txt), still
unchanged at https://www.iana.org/assignments/http-digest-hash-alg/ (fetched 2026-10-12).
CRC check values over "123456789": the CRC catalogue,
https://reveng.sourceforge.io/crc-catalogue/17plus.htm (CRC-32/CKSUM check=0x765e7680,
CRC-32/ISCSI check=0xe3069283), fetched 2026-10-12.
"""

from __future__ import annotations

import random
import zlib

import pytest

from contentdigest import (
    ACTIVE_ALGORITHMS,
    DEPRECATED_ALGORITHMS,
    SUPPORTED_ALGORITHMS,
    make_digest,
    parse,
)
from contentdigest._checksums import Crc32c, UnixCksum, UnixSum


def test_registry_statuses_match_rfc_9530() -> None:
    assert frozenset({"sha-256", "sha-512"}) == ACTIVE_ALGORITHMS
    deprecated = {"md5", "sha", "unixsum", "unixcksum", "adler", "crc32c"}
    assert frozenset(deprecated) == DEPRECATED_ALGORITHMS
    assert SUPPORTED_ALGORITHMS == ACTIVE_ALGORITHMS | DEPRECATED_ALGORITHMS


@pytest.mark.parametrize(
    ("algo", "size"),
    [
        ("sha-256", 32),
        ("sha-512", 64),
        ("md5", 16),
        ("sha", 20),
        ("unixsum", 2),
        ("unixcksum", 4),
        ("adler", 4),
        ("crc32c", 4),
    ],
)
def test_digest_sizes(algo: str, size: int) -> None:
    assert len(parse(make_digest(b"x", algos=[algo]))[algo]) == size


def test_crc32c_check_value() -> None:
    crc = Crc32c()
    crc.update(memoryview(b"123456789"))
    assert crc.digest() == (0xE3069283).to_bytes(4, "big")


def test_cksum_crc_core_check_value() -> None:
    # The catalogue CRC has no length appended; cksum then feeds the length bytes.
    core = UnixCksum._feed(0, b"123456789") ^ 0xFFFFFFFF
    assert core == 0x765E7680


def _cksum_model(data: bytes) -> int:
    """Derived: the POSIX cksum definition written bit by bit, for comparison."""
    crc = 0
    length = len(data)
    tail = b""
    while length:
        tail += bytes([length & 0xFF])
        length >>= 8
    for byte in data + tail:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) if crc & 0x80000000 else crc << 1
            crc &= 0xFFFFFFFF
    return ~crc & 0xFFFFFFFF


def _sum_model(data: bytes) -> int:
    """Derived: BSD sum, rotate right one bit then add, 16 bits."""
    total = 0
    for byte in data:
        total = (total >> 1) + ((total & 1) << 15) + byte
        total &= 0xFFFF
    return total


@pytest.mark.parametrize("seed", range(10))
def test_checksums_match_bitwise_models(seed: int) -> None:
    data = random.Random(seed).randbytes(seed * 97)
    assert parse(make_digest(data, algos=["unixcksum"]))["unixcksum"] == _cksum_model(
        data
    ).to_bytes(4, "big")
    assert parse(make_digest(data, algos=["unixsum"]))["unixsum"] == _sum_model(data).to_bytes(
        2, "big"
    )
    adler = parse(make_digest(data, algos=["adler"]))["adler"]
    assert adler == zlib.adler32(data).to_bytes(4, "big")


def test_cksum_length_crosses_byte_boundaries() -> None:
    data = bytes(300)
    assert parse(make_digest(data, algos=["unixcksum"]))["unixcksum"] == _cksum_model(
        data
    ).to_bytes(4, "big")


def test_unix_sum_digest_does_not_consume_state() -> None:
    total = UnixSum()
    total.update(memoryview(b"ab"))
    assert total.digest() == total.digest()
