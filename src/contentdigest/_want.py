"""Want-Content-Digest and Want-Repr-Digest preference fields (RFC 9530 section 4)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from ._algorithms import ACTIVE_ALGORITHMS, algorithm_names
from ._errors import DigestError
from ._sf import FieldValue, parse_dictionary

_KEY = re.compile(r"[a-z*][a-z0-9_.*-]*")


def parse_want(field: FieldValue) -> dict[str, int]:
    """Parse a preference field into weights by algorithm key, in field order.

    Each weight is an integer from 0 (not acceptable) to 10 (most preferred). Anything else
    makes the whole field invalid and raises :class:`DigestError`. Unknown algorithms are
    kept; an empty field gives an empty dict.
    """
    result: dict[str, int] = {}
    for key, (value, _params) in parse_dictionary(field).items():
        if type(value) is not int or not 0 <= value <= 10:
            raise DigestError(f"the weight of {key!r} is not an integer from 0 to 10")
        result[key] = value
    return result


def make_want(preferences: Mapping[str, int]) -> str:
    """Serialize weights by algorithm key as a preference field value.

    Keys are lower-cased and must be valid structured-field keys; weights must be integers
    from 0 to 10. Unregistered algorithms are allowed, as the field is only a hint.
    """
    members: dict[str, int] = {}
    for name, weight in preferences.items():
        if not isinstance(name, str):
            raise TypeError(f"an algorithm name must be str, not {type(name).__name__}")
        key = name.lower()
        if not _KEY.fullmatch(key):
            raise DigestError(f"not a valid algorithm key: {name!r}")
        if type(weight) is not int:
            raise TypeError(f"the weight of {name!r} must be an int, not {type(weight).__name__}")
        if not 0 <= weight <= 10:
            raise DigestError(f"the weight of {name!r} must be from 0 to 10, not {weight}")
        members[key] = weight
    if not members:
        raise DigestError("at least one preference is required")
    return ", ".join(f"{key}={weight}" for key, weight in members.items())


def choose_algorithm(
    field: FieldValue | None, supported: Iterable[str] = ACTIVE_ALGORITHMS
) -> str | None:
    """Pick the algorithm to answer a preference field with.

    Returns the ``supported`` algorithm with the highest weight above 0, the first one listed
    in the field on a tie, or ``None`` when the field is absent or names none of them (the
    sender may then use any algorithm or none: preferences are only a hint).
    """
    allowed = algorithm_names(supported, "supported")
    if field is None:
        return None
    best: str | None = None
    best_weight = 0
    for key, weight in parse_want(field).items():
        if key in allowed and weight > best_weight:
            best, best_weight = key, weight
    return best
