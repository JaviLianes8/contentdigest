"""Build and verify RFC 9530 Content-Digest and Repr-Digest headers, zero dependencies."""

from __future__ import annotations

from ._digest import (
    SUPPORTED_ALGORITHMS,
    DigestError,
    make_digest,
    parse,
    verify,
)

__version__ = "0.1.0"

__all__ = [
    "SUPPORTED_ALGORITHMS",
    "DigestError",
    "make_digest",
    "parse",
    "verify",
]
