"""Access to the fetched third-party files, checked against their manifest."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def manifest() -> dict[str, dict[str, Any]]:
    """The manifest entries by file name."""
    entries: dict[str, dict[str, Any]] = json.loads(
        (UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8")
    )
    return entries


def upstream_bytes(name: str) -> bytes:
    """Return a third-party file, checked against its manifest entry.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their tests
    skip while a file is absent and fail if it differs from the manifest.
    """
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = manifest()[name]
    body = path.read_bytes()
    assert (len(body), hashlib.sha256(body).hexdigest()) == (entry["size"], entry["sha256"]), name
    return body


def upstream_text(name: str) -> str:
    """Return a fetched RFC as text, without its page breaks and running headers."""
    text = upstream_bytes(name).decode("utf-8")
    return re.sub(r"\n+[^\n]*\[Page \d+\]\n\x0c\n[^\n]*\n+", "\n", text)


def upstream_prose(name: str) -> str:
    """Return a fetched HTML page as plain text: tags removed, whitespace collapsed."""
    text = re.sub(r"<[^>]+>", " ", upstream_bytes(name).decode("utf-8"))
    return re.sub(r"\s+", " ", html.unescape(text))


def unfold(text: str) -> str:
    """Undo RFC 8792 single-backslash line wrapping: a final backslash joins the next line."""
    return re.sub(r"\\\n[ ]*", "", text)
