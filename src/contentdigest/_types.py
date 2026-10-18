"""The bytes-like annotation, resolvable at run time on every supported Python."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
elif TYPE_CHECKING:
    from typing_extensions import Buffer
else:
    # typing.get_type_hints needs a run-time value; type checkers read the import above.
    Buffer = bytes | bytearray | memoryview

__all__ = ["Buffer"]
