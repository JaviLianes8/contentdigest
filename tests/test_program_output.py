"""Every algorithm against real programs: values they printed, and a live run when present.

tests/program_output.json was written on 2026-10-18 by scripts/capture_program_output.py
from GNU coreutils 8.32 (sum, cksum, md5sum, sha1sum, sha256sum, sha512sum), Windows
certutil, the OpenJDK 21 runtime (java.util.zip.Adler32 and CRC32C) and Node.js 24 (Brotli).
The live test runs the coreutils found on PATH, or in $CONTENTDIGEST_COREUTILS, on fresh
inputs; it skips where they are missing.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from contentdigest import make_digest, parse

DATA = json.loads((Path(__file__).parent / "program_output.json").read_text(encoding="utf-8"))
CASES = sorted(DATA["cases"])
TOOLS = ["sum", "cksum", "md5sum", "sha1sum", "sha256sum", "sha512sum"]


def _number(width: int) -> Callable[[str], bytes]:
    return lambda value: int(value, 10).to_bytes(width, "big")


SOURCES: dict[str, list[tuple[str, Callable[[str], bytes]]]] = {
    "unixsum": [("sum", _number(2))],
    "unixcksum": [("cksum", _number(4))],
    "md5": [("md5sum", bytes.fromhex), ("certutil-md5", bytes.fromhex)],
    "sha": [("sha1sum", bytes.fromhex), ("certutil-sha1", bytes.fromhex)],
    "sha-256": [("sha256sum", bytes.fromhex), ("certutil-sha256", bytes.fromhex)],
    "sha-512": [("sha512sum", bytes.fromhex), ("certutil-sha512", bytes.fromhex)],
    "adler": [("java-adler32", bytes.fromhex)],
    "crc32c": [("java-crc32c", bytes.fromhex)],
}


def make_input(name: str) -> bytes:
    """The bytes a case name stands for (the same function is in the capture script)."""
    kind, _, spec = name.partition(":")
    if kind == "text":
        return spec.encode("ascii")
    if kind == "fill":
        byte, size = spec.split("*")
        return bytes([int(byte, 16)]) * int(size)
    if kind == "count":
        return bytes(i % 256 for i in range(int(spec)))
    seed, size = spec.split("*")
    out = bytearray()
    while len(out) < int(size):
        out += hashlib.sha256(f"{seed}:{len(out) // 32}".encode()).digest()
    return bytes(out[: int(size)])


@pytest.mark.parametrize("name", CASES)
def test_inputs_are_the_bytes_the_programs_read(name: str) -> None:
    data = make_input(name)
    assert len(data) == DATA["cases"][name]["size"]
    assert hashlib.sha256(data).hexdigest() == DATA["cases"][name]["sha256sum"]


@pytest.mark.parametrize("name", CASES)
def test_every_algorithm_matches_the_programs(name: str) -> None:
    digests = parse(make_digest(make_input(name), algos=list(SOURCES)))
    for algo, sources in SOURCES.items():
        for key, convert in sources:
            value = DATA["cases"][name][key]
            if value is None:
                continue
            assert digests[algo] == convert(value), (algo, key)


def test_every_program_answered_every_case() -> None:
    assert len(CASES) == 27
    certutil = {"certutil-md5", "certutil-sha1", "certutil-sha256", "certutil-sha512"}
    for name in CASES:
        missing = {key for key, value in DATA["cases"][name].items() if value is None}
        # certutil refuses an empty file; every other program answered every input.
        assert missing == (certutil if name == "text:" else set()), name


def test_node_decodes_only_the_corrected_brotli_bytes() -> None:
    (published, failure), (corrected, decoded) = DATA["brotli"].items()
    assert published.startswith("8b08") and failure.startswith("error")
    assert corrected.startswith("0b09") and bytes.fromhex(decoded) == b'{"hello": "world"}\n'


def _tool(name: str) -> str | None:
    folder = os.environ.get("CONTENTDIGEST_COREUTILS")
    return shutil.which(name, path=folder) if folder else shutil.which(name)


def test_live_coreutils_on_fresh_inputs(tmp_path: Path) -> None:
    tools = {name: _tool(name) for name in TOOLS}
    found = {name: path for name, path in tools.items() if path}
    if len(found) < len(TOOLS):
        pytest.skip("GNU coreutils not found; set CONTENTDIGEST_COREUTILS to their folder")
    rng = random.Random(9530)
    for index in range(6):
        data = rng.randbytes(rng.choice([0, 1, 255, 256, 4097, 65536, 70000]))
        path = tmp_path / f"input{index}.bin"
        path.write_bytes(data)
        printed = {
            name: subprocess.run([exe, str(path)], capture_output=True, text=True, check=True)
            .stdout.split()[0]
            .lstrip("\\*")
            for name, exe in found.items()
        }
        algos = ["unixsum", "unixcksum", "md5", "sha", "sha-256", "sha-512"]
        digests = parse(make_digest(data, algos=algos))
        assert digests["unixsum"] == int(printed["sum"]).to_bytes(2, "big")
        assert digests["unixcksum"] == int(printed["cksum"]).to_bytes(4, "big")
        assert digests["md5"].hex() == printed["md5sum"]
        assert digests["sha"].hex() == printed["sha1sum"]
        assert digests["sha-256"].hex() == printed["sha256sum"]
        assert digests["sha-512"].hex() == printed["sha512sum"]
