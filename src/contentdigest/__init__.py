"""Build and verify RFC 9530 digest fields and their preference fields, zero dependencies."""

from __future__ import annotations

from ._algorithms import ACTIVE_ALGORITHMS, DEPRECATED_ALGORITHMS, SUPPORTED_ALGORITHMS
from ._digest import Digester, Verifier, make_digest, parse, verify
from ._errors import DigestError
from ._want import choose_algorithm, make_want, parse_want

__version__ = "0.2.0"

__all__ = [
    "ACTIVE_ALGORITHMS",
    "DEPRECATED_ALGORITHMS",
    "SUPPORTED_ALGORITHMS",
    "DigestError",
    "Digester",
    "Verifier",
    "choose_algorithm",
    "make_digest",
    "make_want",
    "parse",
    "parse_want",
    "verify",
]
