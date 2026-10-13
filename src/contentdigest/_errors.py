"""The one exception type for malformed fields and unknown algorithms."""

from __future__ import annotations


class DigestError(ValueError):
    """Raised when a field value is malformed or names an unsupported algorithm."""
