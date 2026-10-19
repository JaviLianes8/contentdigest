"""Upgrade in place from the PyPI release 0.2.0 to the built wheel.

Needs PyPI, so it runs only with CONTENTDIGEST_E2E=1 and CONTENTDIGEST_E2E_PYPI=1, from a
source tree.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from test_e2e_wheel import BODY, ROOT, _run, check_program, install

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTDIGEST_E2E") != "1"
    or os.environ.get("CONTENTDIGEST_E2E_PYPI") != "1"
    or not (ROOT / "src").is_dir(),
    reason="set CONTENTDIGEST_E2E=1 and CONTENTDIGEST_E2E_PYPI=1 in a source tree",
)

PROBE = r"""
import json
import contentdigest as cd
body = b'{"hello": "world"}'
every = sorted(cd.SUPPORTED_ALGORITHMS)
out = {"version": cd.__version__, "made": cd.make_digest(body, algos=every)}
out["parsed"] = {key: value.hex() for key, value in cd.parse(out["made"]).items()}
out["verified"] = cd.verify(out["made"], body, accept=every)
out["want"] = cd.parse_want("sha-512=3, sha-256=10, unixsum=0")
out["chosen"] = cd.choose_algorithm("sha-512=3, sha-256=10, unixsum=0")
out["made_want"] = cd.make_want({"SHA-512": 10, "md5": 0})
calls = {
    "bad field": lambda: cd.parse("sha-256=1"),
    "md5 only": lambda: cd.verify(cd.make_digest(body, algos=["md5"]), body),
    "text body": lambda: cd.make_digest("x"),
    "bare string": lambda: cd.make_digest(body, algos="sha-256"),
}
errors = {}
for name, call in calls.items():
    try:
        call()
        errors[name] = None
    except Exception as error:
        errors[name] = type(error).__name__
out["errors"] = errors
print(json.dumps(out, sort_keys=True))
"""


def _probe(bindir: Path, work: Path) -> dict[str, Any]:
    done = _run(bindir / "python", "-I", "-c", PROBE, cwd=work)
    assert done.returncode == 0, done.stderr
    result: dict[str, Any] = json.loads(done.stdout)
    return result


def _command(bindir: Path, work: Path) -> list[tuple[int, str]]:
    script = bindir / ("contentdigest.exe" if sys.platform == "win32" else "contentdigest")
    field = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
    outcomes = []
    for argv, stdin in [(("-",), BODY), (("--verify", field), BODY), (("--verify", field), b"x")]:
        done = _run(script, *argv, cwd=work, stdin=stdin)
        outcomes.append((done.returncode, done.stdout.decode().strip()))
    return outcomes


def test_upgrade_in_place_from_the_pypi_release(dist: Path, tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    bindir = install(dist, tmp_path / "venv", "contentdigest==0.2.0")
    before, commands_before = _probe(bindir, work), _command(bindir, work)
    assert before.pop("version") == "0.2.0"
    wheel = next(dist.glob("contentdigest-*.whl"))
    done = _run(bindir / "python", "-m", "pip", "install", "-q", "--upgrade", wheel, cwd=work)
    assert done.returncode == 0, done.stderr
    after, commands_after = _probe(bindir, work), _command(bindir, work)
    assert after.pop("version") == "1.0.0"
    assert after == before
    assert (
        commands_after
        == commands_before
        == [
            (0, "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"),
            (0, "match"),
            (1, "mismatch"),
        ]
    )
    check_program(bindir, tmp_path / "program")
