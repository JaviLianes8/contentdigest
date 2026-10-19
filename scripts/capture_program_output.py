"""Record what real programs compute for a set of inputs, into tests/program_output.json.

GNU coreutils (sum, cksum, md5sum, sha1sum, sha256sum, sha512sum), Windows certutil, the
Java runtime (scripts/Checksums.java: java.util.zip.Adler32 and CRC32C) and Node.js
(zlib.brotliDecompressSync on the two Brotli byte strings of RFC 9530 erratum 8890).
tests/test_program_output.py rebuilds the inputs from their names and compares.

    python scripts/capture_program_output.py

coreutils are looked up on PATH (Git for Windows ships them), or in $CAPTURE_COREUTILS.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "program_output.json"
HELLO = '{"hello": "world"}'
NAMES = [
    "text:",
    f"text:{HELLO}",
    f"text:{HELLO}\n",
    "text:123456789",
    *(f"fill:00*{n}" for n in (1, 255, 256, 65535, 65536, 65537)),
    *(f"fill:ff*{n}" for n in (32, 5552, 5553, 100000)),
    "count:256",
    "count:70000",
    *(f"stream:{seed}*{n}" for seed, n in enumerate((1, 2, 3, 7, 63, 64, 65, 1000), 1)),
    "stream:9*4096",
    "stream:10*100003",
    "stream:11*1048579",
]
BROTLI = [
    "8b08807b2268656c6c6f223a2022776f726c64227d0a03",  # RFC 9530 Figure 18, as published
    "0b09807b2268656c6c6f223a2022776f726c64227d0a03",  # as erratum 8890 corrects it
]
NODE = (
    "const z = require('zlib'); for (const h of process.argv.slice(1)) { try { console.log("
    "z.brotliDecompressSync(Buffer.from(h, 'hex')).toString('hex')) } catch (e) { "
    "console.log('error ' + e.code) } }"
)


def make_input(name: str) -> bytes:
    """The bytes a case name stands for (the same function is in the test)."""
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


def _tool(name: str) -> str:
    folder = os.environ.get("CAPTURE_COREUTILS")
    found = shutil.which(name, path=folder) if folder else shutil.which(name)
    if not found:
        sys.exit(f"{name} not found; put GNU coreutils on PATH or set CAPTURE_COREUTILS")
    return found


def _run(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _certutil(path: Path, algorithm: str) -> str | None:
    done = subprocess.run(["certutil", "-hashfile", str(path), algorithm], capture_output=True)
    lines = done.stdout.decode("ascii", "replace").splitlines()
    hexes = [line.replace(" ", "") for line in lines[1:2] if done.returncode == 0]
    return hexes[0].lower() if hexes else None  # certutil refuses empty files


def main() -> int:
    tools = {name: _tool(name) for name in ("sum", "cksum", "md5sum", "sha1sum")}
    tools |= {name: _tool(name) for name in ("sha256sum", "sha512sum")}
    cases: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory() as work:
        paths = {}
        for index, name in enumerate(NAMES):
            paths[name] = Path(work, f"case{index}.bin")
            paths[name].write_bytes(make_input(name))
        java = _run("java", str(ROOT / "scripts" / "Checksums.java"), *map(str, paths.values()))
        rows = {Path(row.split()[0]).name: row.split()[1:] for row in java.splitlines()}
        for name, path in paths.items():
            out: dict[str, object] = {"size": path.stat().st_size}
            for tool, exe in tools.items():
                out[tool] = _run(exe, str(path)).split()[0].lstrip("\\*")
            for algorithm in ("MD5", "SHA1", "SHA256", "SHA512"):
                out[f"certutil-{algorithm.lower()}"] = _certutil(path, algorithm)
            out["java-adler32"], out["java-crc32c"] = rows[path.name]
            cases[name] = out
    node = dict(zip(BROTLI, _run("node", "-e", NODE, *BROTLI).split("\n"), strict=False))
    programs = {
        "coreutils": _run(tools["sum"], "--version").splitlines()[0],
        "java": subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.split(
            "\n"
        )[0],
        "node": _run("node", "--version").strip(),
        "certutil": f"certutil -hashfile, Windows {platform.version()}",
    }
    data = {"captured": datetime.date.today().isoformat(), "programs": programs}
    data |= {"cases": cases, "brotli": node}
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(cases)} cases written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
