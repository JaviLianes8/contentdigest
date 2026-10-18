"""Build the wheel and sdist, inspect them, install the wheel in a throwaway venv, drive it.

Slow and needs the build backend and network, so it runs only with CONTENTDIGEST_E2E=1 and
from a source tree. tests/test_e2e_upgrade.py adds the upgrade from PyPI.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BODY = b'{"hello": "world"}'
FIELD = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTDIGEST_E2E") != "1" or not (ROOT / "src").is_dir(),
    reason="set CONTENTDIGEST_E2E=1 in a source tree to build and install",
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle, typing
import contentdigest as cd
from contentdigest import (
    ACTIVE_ALGORITHMS, DEPRECATED_ALGORITHMS, SUPPORTED_ALGORITHMS, DigestError, Digester,
    Verifier, choose_algorithm, make_digest, make_want, parse, parse_want, verify,
)

assert "site-packages" in cd.__file__, cd.__file__
assert cd.__version__ == "1.0.0" == importlib.metadata.version("contentdigest")
public = sorted(name for name in dir(cd) if not name.startswith("_"))
assert sorted(cd.__all__) == public and len(public) == 12, public
assert importlib.resources.files("contentdigest").joinpath("py.typed").is_file()
classifiers = importlib.metadata.metadata("contentdigest").get_all("Classifier")
assert "Development Status :: 5 - Production/Stable" in classifiers
assert all("extra ==" in r for r in importlib.metadata.requires("contentdigest"))
body = b'{"hello": "world"}'
assert make_digest(body) == "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
assert make_digest(body, algos=["crc32c", "UNIXSUM"]) == "crc32c=:Q3lHIA==:, unixsum=:GQU=:"
assert verify("sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg==:", body + b"\n")
assert verify(make_digest(body, algos=["md5"]), body, accept=["md5"])
assert sorted(ACTIVE_ALGORITHMS) == ["sha-256", "sha-512"] and len(DEPRECATED_ALGORITHMS) == 6
assert SUPPORTED_ALGORITHMS == ACTIVE_ALGORITHMS | DEPRECATED_ALGORITHMS
digester = Digester(["sha-512"])
digester.update(memoryview(body))
verifier = Verifier([digester.value().encode()])
verifier.update(bytearray(body))
assert verifier.verify() and verifier.algorithms == ("sha-512",)
assert choose_algorithm("sha-512=3, sha-256=10, unixsum=0") == "sha-256"
assert parse_want(make_want({"SHA-256": 0})) == {"sha-256": 0}
assert list(parse(["md5=:AAAA:", b"sha=:AAAA:"])) == ["md5", "sha"]
for bad in ["sha-256=:AAAA:,", "sha-256=1", "SHA-256=:AAAA:"]:
    try:
        parse(bad)
    except DigestError as error:
        assert isinstance(error, ValueError) and len(str(error)) < 300
    else:
        raise AssertionError(bad)
for call in (lambda: verify(make_digest(body, algos=["md5"]), body),
             lambda: make_want({"sha-256": 10**5000})):
    try:
        call()
    except DigestError:
        pass
    else:
        raise AssertionError("no DigestError")
assert typing.get_type_hints(make_digest)["return"] is str
assert repr(DigestError) == "<class 'contentdigest.DigestError'>"
assert pickle.loads(pickle.dumps(DigestError("x"))).args == ("x",)
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True)


def install(dist: Path, folder: Path, *requirements: str) -> Path:
    """Make a venv, install the requirements (default: the built wheel), return its bin."""
    venv.create(folder, with_pip=True)
    bindir = folder / ("Scripts" if sys.platform == "win32" else "bin")
    wanted = requirements or (str(next(dist.glob("contentdigest-*.whl"))),)
    done = _run(bindir / "python", "-m", "pip", "install", "-q", *wanted, cwd=folder)
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    return bindir


def check_program(bindir: Path, work: Path) -> None:
    """Run the consumer program and the command from an empty folder."""
    work.mkdir(exist_ok=True)
    done = _run(bindir / "python", "-I", "-c", PROGRAM, cwd=work)
    assert (done.returncode, done.stdout.decode().split()) == (0, ["e2e ok"]), done.stderr
    script = bindir / ("contentdigest.exe" if sys.platform == "win32" else "contentdigest")
    printed = _run(script, "-", cwd=work, stdin=BODY)
    assert (printed.returncode, printed.stdout.decode().strip()) == (0, FIELD)
    (work / "body.json").write_bytes(BODY)
    many = _run(script, "body.json", "-a", "sha-512", "-a", "crc32c", cwd=work)
    assert many.stdout.decode().strip().endswith(", crc32c=:Q3lHIA==:")
    module = (bindir / "python", "-I", "-m", "contentdigest")
    for argv, stdin, status, out in [
        (("--verify", FIELD), BODY, 0, "match"),
        (("--verify", FIELD), b"other", 1, "mismatch"),
        (("--verify", "sha-256=:AAAA:,"), BODY, 2, ""),
        (("--verify", "md5=:Sd/dVLAcvNLSq16eXua5uQ==:"), BODY, 2, ""),
        (("--verify", "md5=:Sd/dVLAcvNLSq16eXua5uQ==:", "-a", "md5"), BODY, 0, "match"),
        (("missing.json",), b"", 2, ""),
    ]:
        done = _run(*module, *argv, cwd=work, stdin=stdin)
        assert (done.returncode, done.stdout.decode().strip()) == (status, out), argv
        assert done.stderr.decode().startswith("contentdigest: ") is (status == 2)
    helped = _run(*module, "--help", cwd=work)
    assert helped.returncode == 0 and b"Exit status" in helped.stdout


def test_wheel_and_sdist_contents(dist: Path) -> None:
    (wheel,) = dist.glob("contentdigest-*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert "contentdigest/py.typed" in names and "contentdigest/_types.py" in names
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert all(
        name.startswith(("contentdigest/", "contentdigest-1.0.0.dist-info/")) for name in names
    )
    (sdist,) = dist.glob("contentdigest-*.tar.gz")
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[-1] for name in archive.getnames()]
    for present in ("LICENSE", "README.md", "GUIDE.md", "CHANGELOG.md", "PKG-INFO"):
        assert present in listing, present
    for present in ("tests/upstream/MANIFEST.json", "tests/program_output.json"):
        assert present in listing, present
    assert "scripts/fetch_upstream.py" in listing
    upstream = [name for name in listing if name.startswith("tests/upstream/")]
    assert upstream == ["tests/upstream/MANIFEST.json"]
    for absent in ("IMPROVEMENTS-round", "CERT-1.0-", ".github", "__pycache__", ".pyc", "dist/"):
        assert not any(absent in name for name in listing), absent


def test_installed_wheel_end_to_end(dist: Path, tmp_path: Path) -> None:
    check_program(install(dist, tmp_path / "venv"), tmp_path / "work")


def test_the_installed_command_exits_quietly_when_its_reader_goes_away(
    dist: Path, tmp_path: Path
) -> None:
    bindir = install(dist, tmp_path / "venv")
    script = bindir / ("contentdigest.exe" if sys.platform == "win32" else "contentdigest")
    process = subprocess.Popen(
        [str(script), "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert process.stdout is not None
    process.stdout.close()
    process.stdout = None
    _, err = process.communicate(BODY, timeout=120)
    assert (process.returncode, err) == (2, b"")
