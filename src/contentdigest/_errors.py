"""The one exception type, and the helpers that keep every message short."""

from __future__ import annotations

from collections.abc import Sequence

# A hostile field can be megabytes long and error messages end up in logs.
_LIMIT = 40


class DigestError(ValueError):
    """Raised when a field is malformed or names an algorithm this library does not support.

    It is a :class:`ValueError`. A message quotes at most a short excerpt of any input.

    >>> from contentdigest import DigestError, parse
    >>> try:
    ...     parse("sha-256=1")
    ... except DigestError as error:
    ...     print(error)
    the value of 'sha-256' is not a byte sequence
    """


def excerpt(text: str) -> str:
    """Quote ``text`` for a message, cut to a short excerpt when it is long."""
    if len(text) <= _LIMIT:
        return repr(text)
    return f"{text[:_LIMIT]!r}... ({len(text)} characters)"


def listing(names: Sequence[str]) -> str:
    """Quote a few of ``names`` for a message and count the rest."""
    shown = ", ".join(excerpt(name) for name in names[:5]) or "none"
    return f"{shown} and {len(names) - 5} more" if len(names) > 5 else shown


def type_name(value: object) -> str:
    """The name of the type of ``value`` for a message, cut when it is long."""
    name = type(value).__name__
    return name if len(name) <= _LIMIT else f"{name[:_LIMIT]}..."
