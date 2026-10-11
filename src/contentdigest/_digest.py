"""Encode and decode RFC 9530 digest header values."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from collections.abc import Callable, Iterable

_Hasher = Callable[[bytes], "hashlib._Hash"]

_HASHERS: dict[str, _Hasher] = {
    "sha-256": hashlib.sha256,
    "sha-512": hashlib.sha512,
}

#: Algorithm names this library can produce and verify.
SUPPORTED_ALGORITHMS = frozenset(_HASHERS)

# A structured-field dictionary key: lowercase, as required by RFC 8941.
_KEY = re.compile(r"[a-z*][a-z0-9_.*-]*")


class DigestError(ValueError):
    """Raised when a digest header is malformed or names an unsupported algorithm."""


def make_digest(body: bytes, algos: Iterable[str] = ("sha-256",)) -> str:
    """Return a Content-Digest / Repr-Digest value for ``body`` over ``algos``.

    The value is an RFC 8941 dictionary, one member per algorithm, each digest
    carried as a byte sequence (``algo=:base64:``). Order follows ``algos``.
    """
    members: list[str] = []
    for name in algos:
        key = name.lower()
        hasher = _HASHERS.get(key)
        if hasher is None:
            raise DigestError(f"unsupported algorithm: {name!r}")
        encoded = base64.b64encode(hasher(body).digest()).decode("ascii")
        members.append(f"{key}=:{encoded}:")
    if not members:
        raise DigestError("at least one algorithm is required")
    return ", ".join(members)


def parse(header: str) -> dict[str, bytes]:
    """Parse a digest header value into a mapping of algorithm to raw digest bytes.

    Every member is returned, including algorithms this library cannot verify.
    """
    result: dict[str, bytes] = {}
    for raw in header.split(","):
        member = raw.strip()
        if not member:
            raise DigestError("empty dictionary member")
        key, sep, value = member.partition("=")
        key = key.strip()
        value = value.strip()
        if not sep or not _KEY.fullmatch(key):
            raise DigestError(f"malformed member: {member!r}")
        if len(value) < 2 or value[0] != ":" or value[-1] != ":":
            raise DigestError(f"value is not a byte sequence: {member!r}")
        try:
            result[key] = base64.b64decode(value[1:-1], validate=True)
        except ValueError as exc:
            raise DigestError(f"invalid base64 in {member!r}") from exc
    if not result:
        raise DigestError("no dictionary members")
    return result


def verify(header: str, body: bytes) -> bool:
    """Return whether every supported digest in ``header`` matches ``body``.

    Unsupported algorithms are ignored. If the header carries no supported
    algorithm there is nothing to check, so a :class:`DigestError` is raised.
    """
    checkable = {name: digest for name, digest in parse(header).items() if name in _HASHERS}
    if not checkable:
        raise DigestError("header has no supported digest algorithm")
    return all(
        hmac.compare_digest(digest, _HASHERS[name](body).digest())
        for name, digest in checkable.items()
    )
