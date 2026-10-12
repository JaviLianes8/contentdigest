"""The non-cryptographic checksums of the RFC 9530 registry, computed incrementally.

Each one is big-endian, which is what reproduces the RFC 9530 Appendix D sample values.
"""

from __future__ import annotations

import zlib


def _crc_table(poly: int, reflected: bool) -> tuple[int, ...]:
    table = []
    for byte in range(256):
        if reflected:
            crc = byte
            for _ in range(8):
                crc = (crc >> 1) ^ poly if crc & 1 else crc >> 1
        else:
            crc = byte << 24
            for _ in range(8):
                crc = ((crc << 1) ^ poly if crc & 0x80000000 else crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return tuple(table)


_CRC32C = _crc_table(0x82F63B78, reflected=True)
_CKSUM = _crc_table(0x04C11DB7, reflected=False)


class UnixSum:
    """The BSD 16-bit rotating checksum printed by UNIX ``sum``."""

    def __init__(self) -> None:
        self._sum = 0

    def update(self, data: memoryview) -> None:
        total = self._sum
        for byte in data:
            total = (((total >> 1) | ((total & 1) << 15)) + byte) & 0xFFFF
        self._sum = total

    def digest(self) -> bytes:
        return self._sum.to_bytes(2, "big")


class UnixCksum:
    """The POSIX CRC printed by UNIX ``cksum``: CRC-32 over the data, then its length."""

    def __init__(self) -> None:
        self._crc = 0
        self._length = 0

    @staticmethod
    def _feed(crc: int, data: bytes | memoryview) -> int:
        for byte in data:
            crc = ((crc << 8) & 0xFFFFFFFF) ^ _CKSUM[(crc >> 24) ^ byte]
        return crc

    def update(self, data: memoryview) -> None:
        self._crc = self._feed(self._crc, data)
        self._length += len(data)

    def digest(self) -> bytes:
        length = self._length.to_bytes((self._length.bit_length() + 7) // 8, "little")
        return (~self._feed(self._crc, length) & 0xFFFFFFFF).to_bytes(4, "big")


class Crc32c:
    """CRC-32C (Castagnoli), as in RFC 9260 Appendix A."""

    def __init__(self) -> None:
        self._crc = 0xFFFFFFFF

    def update(self, data: memoryview) -> None:
        crc = self._crc
        for byte in data:
            crc = (crc >> 8) ^ _CRC32C[(crc ^ byte) & 0xFF]
        self._crc = crc

    def digest(self) -> bytes:
        return (self._crc ^ 0xFFFFFFFF).to_bytes(4, "big")


class Adler32:
    """Adler-32 from RFC 1950, through ``zlib``."""

    def __init__(self) -> None:
        self._value = 1

    def update(self, data: memoryview) -> None:
        self._value = zlib.adler32(data, self._value)

    def digest(self) -> bytes:
        return self._value.to_bytes(4, "big")
