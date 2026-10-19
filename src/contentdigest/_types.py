"""The bytes-like annotation, resolvable at run time on every supported Python, and its test."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, cast

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
elif TYPE_CHECKING:
    from typing_extensions import Buffer
else:
    # typing.get_type_hints needs a run-time value; type checkers read the import above.
    Buffer = bytes | bytearray | memoryview


def is_bytes_like(value: object) -> bool:
    """Whether ``value`` exports the buffer protocol, even if it refuses its bytes for now."""
    try:
        memoryview(cast("Buffer", value)).release()
    except TypeError:
        return False
    except ValueError:
        # The exporter refuses its bytes for now (a closed mmap, a released view): still bytes-like.
        return True
    return True


__all__ = ["Buffer", "is_bytes_like"]
