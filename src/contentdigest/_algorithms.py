"""The "Hash Algorithms for HTTP Digest Fields" registry (RFC 9530 section 7.2)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from typing import Protocol

from ._checksums import Adler32, Crc32c, UnixCksum, UnixSum
from ._errors import DigestError, excerpt, type_name
from ._types import Buffer


class Hasher(Protocol):
    def update(self, data: memoryview, /) -> None: ...
    def digest(self) -> bytes: ...


def _legacy(name: str) -> Callable[[], Hasher]:
    # RFC 9530 allows MD5 and SHA-1 only against accidental corruption, so they are not used
    # for security; saying so keeps them working where OpenSSL runs in FIPS mode.
    return lambda: hashlib.new(name, usedforsecurity=False)


_ACTIVE: dict[str, Callable[[], Hasher]] = {
    "sha-256": hashlib.sha256,
    "sha-512": hashlib.sha512,
}
_DEPRECATED: dict[str, Callable[[], Hasher]] = {
    "md5": _legacy("md5"),
    "sha": _legacy("sha1"),
    "unixsum": UnixSum,
    "unixcksum": UnixCksum,
    "adler": Adler32,
    "crc32c": Crc32c,
}
_FACTORIES = {**_ACTIVE, **_DEPRECATED}

#: Registry status "Active": suitable where an attacker may tamper with content.
ACTIVE_ALGORITHMS = frozenset(_ACTIVE)
#: Registry status "Deprecated": only against accidental corruption (RFC 9530 section 5).
DEPRECATED_ALGORITHMS = frozenset(_DEPRECATED)
#: Every algorithm this library can produce and verify.
SUPPORTED_ALGORITHMS = ACTIVE_ALGORITHMS | DEPRECATED_ALGORITHMS


def algorithm_names(names: Iterable[str], what: str) -> list[str]:
    """Lower-case and check a collection of algorithm names, keeping each one once."""
    # A bytes-like value iterates as ints, and an empty one would pass as no names at all.
    if isinstance(names, (str, bytes, bytearray, memoryview)):
        raise TypeError(
            f"{what} must be a collection of algorithm names, not a single string or bytes value"
        )
    result: list[str] = []
    for name in names:
        if not isinstance(name, str):
            raise TypeError(f"an algorithm name must be str, not {type_name(name)}")
        # Only ASCII is lower-cased: str.lower() maps some other letters to ASCII ones.
        key = name.lower() if name.isascii() else name
        if key not in _FACTORIES:
            raise DigestError(f"unsupported algorithm: {excerpt(name)}")
        result.append(key)
    # Callers test membership against the result, so repeats would multiply that work.
    return list(dict.fromkeys(result))


def new_hasher(name: str) -> Hasher:
    return _FACTORIES[name]()


def as_view(data: Buffer) -> memoryview:
    """Return the bytes of any buffer as a flat byte view, refusing ``str``."""
    if isinstance(data, str):
        raise TypeError("the body must be bytes-like, not str; encode it first")
    try:
        view = memoryview(data)
    except TypeError:
        raise TypeError(f"the body must be bytes-like, not {type_name(data)}") from None
    except ValueError:
        # Only a released memoryview has no bytes at all; any other exporter that refuses (a
        # closed mmap, a numpy dtype with no buffer format) keeps its own error and reason.
        if isinstance(data, memoryview):
            raise TypeError("the body must be bytes-like, not a released memoryview") from None
        raise
    if view.c_contiguous:
        return view.cast("B") if view.format != "B" or view.ndim != 1 else view
    return memoryview(view.tobytes())
