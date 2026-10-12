"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with CONTENTDIGEST_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTDIGEST_E2E") != "1", reason="set CONTENTDIGEST_E2E=1 to build"
)

PROGRAM = """
import importlib.metadata, importlib.resources
import contentdigest as cd

assert "site-packages" in cd.__file__, cd.__file__
assert importlib.metadata.version("contentdigest") == cd.__version__
assert importlib.resources.files("contentdigest").joinpath("py.typed").is_file()
assert len(cd.__all__) == 12

body = b'{"hello": "world"}'
assert cd.make_digest(body) == "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
assert cd.make_digest(body, algos=["crc32c"]) == "crc32c=:Q3lHIA==:"
assert cd.verify("sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg==:", body + b"\n")
assert cd.verify(cd.make_digest(body, algos=["md5"]), body, accept=["md5"])
d = cd.Digester(["sha-512"])
d.update(memoryview(body))
v = cd.Verifier([d.value().encode()])
v.update(bytearray(body))
assert v.verify()
assert cd.choose_algorithm("sha-512=3, sha-256=10, unixsum=0") == "sha-256"
assert cd.parse_want(cd.make_want({"sha-256": 0})) == {"sha-256": 0}
for bad in ["sha-256=:AAAA:,", "sha-256=1", "SHA-256=:AAAA:"]:
    try:
        cd.parse(bad)
    except cd.DigestError as error:
        assert isinstance(error, ValueError)
    else:
        raise AssertionError(bad)
try:
    cd.verify(cd.make_digest(body, algos=["md5"]), body)
except cd.DigestError:
    pass
else:
    raise AssertionError("deprecated algorithm verified by default")
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path | None = None, stdin: bytes | None = None) -> str:
    result = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return result.stdout.decode()


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _run(sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT)
    (wheel,) = dist.glob("contentdigest-*.whl")

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    _run(python, "-m", "pip", "install", "-q", wheel)

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    assert _run(python, "-I", "-c", PROGRAM, cwd=work).splitlines() == ["e2e ok"]

    body = b'{"hello": "world"}'
    script = bindir / ("contentdigest.exe" if sys.platform == "win32" else "contentdigest")
    printed = _run(script, "-", cwd=work, stdin=body).strip()
    assert printed == "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
    checked = _run(python, "-I", "-m", "contentdigest", "--verify", printed, cwd=work, stdin=body)
    assert checked.strip() == "match"
