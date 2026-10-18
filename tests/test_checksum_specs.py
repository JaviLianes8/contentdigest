"""The four checksums against their specifications, read from the fetched text.

Sources (fetched 2026-10-18 into tests/upstream, see MANIFEST.json): RFC 9260 Appendix A
(CRC32c polynomial and table), RFC 7143 Appendix A.4 (CRC examples), the POSIX.1-2024 cksum
page (polynomial, length rule, model table), RFC 1950 (Adler-32) and the CRC catalogue
(check values). Each test skips while its file is not fetched.
"""

from __future__ import annotations

import random
import re

from conftest import upstream_bytes, upstream_prose, upstream_text

from contentdigest import make_digest, parse
from contentdigest._checksums import _CKSUM, _CRC32C

CHECK = b"123456789"


def _digest(data: bytes, algo: str) -> bytes:
    return parse(make_digest(data, [algo]))[algo]


def _poly(exponents: list[int]) -> int:
    return sum(1 << exponent for exponent in exponents)


def test_crc32c_table_and_polynomial_are_rfc_9260s() -> None:
    text = upstream_text("rfc9260.txt")
    terms = re.search(r"code 0x11EDC6F41 \(Castagnoli93\) or (x\^32[^.]*?x\^0)\.", text)
    assert terms is not None
    exponents = [int(e) for e in re.findall(r"x\^(\d+)", terms.group(1).replace("\n", ""))]
    assert _poly(exponents) == 0x11EDC6F41
    table = text[text.index("uint32_t crc_c[256] = {") : text.index("};", text.index("crc_c[256]"))]
    assert tuple(int(word, 16) for word in re.findall(r"0x([0-9A-F]{8})UL", table)) == _CRC32C


def test_crc32c_reproduces_the_rfc_7143_examples() -> None:
    text = upstream_text("rfc7143.txt")
    start = text.index("A.4.  CRC Examples")
    section = text[start : text.index("Appendix B.", start)]
    crcs = [
        bytes.fromhex(c) for c in re.findall(r"CRC:\s+((?:[0-9a-f]{2} +){3}[0-9a-f]{2})", section)
    ]
    pdu_text = section[section.index("SCSI Read (10) Command PDU") :]
    pdu_rows = re.findall(r"^\s+\d+:\s+((?:[0-9a-f]{2}\s+){3}[0-9a-f]{2})$", pdu_text, re.M)
    pdu = bytes.fromhex(" ".join(pdu_rows))
    labels = ["32 bytes of zeroes", "32 bytes of ones", "32 bytes of incrementing 00..1f"]
    assert all(label in section for label in [*labels, "32 bytes of decrementing 1f..00"])
    inputs = [bytes(32), b"\xff" * 32, bytes(range(32)), bytes(range(31, -1, -1)), pdu]
    assert len(pdu) == 48 and len(crcs) == 5
    # The examples print the CRC word least significant byte first; RFC 9530 serializes the
    # same value big-endian (its Appendix D crc32c sample is reproduced in test_rfc_text).
    assert [_digest(data, "crc32c")[::-1] for data in inputs] == crcs


def test_cksum_polynomial_length_rule_and_table_are_posixs() -> None:
    raw = upstream_bytes("posix-cksum.html").decode("utf-8")
    formula = raw[raw.index("defined by the generating polynomial") : raw.index("Mathematically")]
    exponents = [int(e) for e in re.findall(r"<sup><small>(\d+)</small></sup>", formula)]
    assert formula.rstrip().endswith("+</tt><i>x</i><tt>+1\n</tt></pre>\n<p>")
    assert _poly([*exponents, 1, 0]) & 0xFFFFFFFF == 0x04C11DB7
    prose = upstream_prose("posix-cksum.html")
    assert (
        "representing the length of the file as a binary value, least significant octet first"
        in prose
    )
    assert (
        "The smallest number of octets capable of representing this integer shall be used" in prose
    )
    table = raw[raw.index("crctab[] = {") : raw.index("};", raw.index("crctab[] = {"))]
    assert tuple(int(word, 16) for word in re.findall(r"0x([0-9a-f]{8})", table)) == _CKSUM


def _memcrc(data: bytes) -> int:
    """Derived: the POSIX model program memcrc(), written in Python from the fetched page."""
    s = 0
    for c in data:
        s = ((s << 8) & 0xFFFFFFFF) ^ _CKSUM[(s >> 24) ^ c]
    n = len(data)
    while n != 0:
        c, n = n & 0o377, n >> 8
        s = ((s << 8) & 0xFFFFFFFF) ^ _CKSUM[(s >> 24) ^ c]
    return ~s & 0xFFFFFFFF


def _adler(data: bytes, base: int) -> int:
    """Derived: update_adler32() of RFC 1950 section 9, written in Python from the text."""
    s1, s2 = 1, 0
    for byte in data:
        s1 = (s1 + byte) % base
        s2 = (s2 + s1) % base
    return (s2 << 16) + s1


def test_cksum_matches_the_posix_model_program() -> None:
    upstream_bytes("posix-cksum.html")
    rng = random.Random(1950)
    for size in [0, 1, 255, 256, 257, 65535, 65536, 70000]:
        data = rng.randbytes(size)
        assert _digest(data, "unixcksum") == _memcrc(data).to_bytes(4, "big"), size


def test_adler_follows_rfc_1950() -> None:
    text = re.sub(r"\s+", " ", upstream_text("rfc1950.txt"))
    found = re.search(r"#define BASE (\d+) /\* largest prime smaller than 65536 \*/", text)
    assert found is not None
    base = int(found.group(1))
    assert "stored as s2*65536 + s1 in most- significant-byte first (network) order" in text
    rng = random.Random(1951)
    for size in [0, 1, 2, 5552, 5553, 100_000]:
        data = rng.randbytes(size) if size != 100_000 else b"\xff" * size
        assert _digest(data, "adler") == _adler(data, base).to_bytes(4, "big"), size


def test_catalogue_check_values() -> None:
    prose = upstream_prose("crc-catalogue-17plus.htm")

    def check(name: str) -> int:
        found = re.search(
            rf"check=0x([0-9a-f]{{8}}) residue=0x[0-9a-f]{{8}} name=\"{name}\"", prose
        )
        assert found is not None, name
        return int(found.group(1), 16)

    assert _digest(CHECK, "crc32c") == check("CRC-32/ISCSI").to_bytes(4, "big")
    # The catalogue's CKSUM check value is the CRC alone, before the length is appended.
    core = 0
    for byte in CHECK:
        core = ((core << 8) & 0xFFFFFFFF) ^ _CKSUM[(core >> 24) ^ byte]
    assert core ^ 0xFFFFFFFF == check("CRC-32/CKSUM")
    returned = re.search(r"It returns (\d+) \( 0x([0-9A-F]{8}) \) on the", prose)
    assert returned is not None and int(returned.group(1)) == int(returned.group(2), 16)
    assert _digest(CHECK, "unixcksum") == int(returned.group(1)).to_bytes(4, "big")
