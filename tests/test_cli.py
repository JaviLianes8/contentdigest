"""The contentdigest command: streams are injected, files come from tmp_path."""

from __future__ import annotations

import io
import runpy
import sys
from pathlib import Path

import pytest

from contentdigest import make_digest
from contentdigest._cli import run

BODY = b'{"hello": "world"}'


def _run(*argv: str, stdin: bytes = b"") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = run(list(argv), stdin=io.BytesIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_prints_the_sha_256_value_of_stdin() -> None:
    assert _run(stdin=BODY) == (0, make_digest(BODY) + "\n", "")


def test_prints_the_requested_algorithms_of_a_file(tmp_path: Path) -> None:
    path = tmp_path / "body.json"
    path.write_bytes(BODY * 50000)
    code, out, _ = _run(str(path), "-a", "sha-512", "-a", "crc32c")
    assert code == 0
    assert out == make_digest(BODY * 50000, algos=["sha-512", "crc32c"]) + "\n"


def test_verify_exits_0_on_a_match() -> None:
    assert _run("--verify", make_digest(BODY), stdin=BODY) == (0, "match\n", "")


def test_verify_exits_1_on_a_mismatch() -> None:
    assert _run("--verify", make_digest(BODY), stdin=b"other") == (1, "mismatch\n", "")


def test_verify_accepts_only_active_algorithms_by_default() -> None:
    field = make_digest(BODY, algos=["md5"])
    code, _, err = _run("--verify", field, stdin=BODY)
    assert code == 2
    assert "no accepted algorithm" in err
    assert _run("--verify", field, "-a", "md5", stdin=BODY)[0] == 0


def test_bad_field_exits_2() -> None:
    code, out, err = _run("--verify", "sha-256=:AAAA:,", stdin=BODY)
    assert (code, out) == (2, "")
    assert err.startswith("contentdigest: ")


def test_unknown_algorithm_exits_2() -> None:
    assert _run("-a", "sha3", stdin=BODY)[0] == 2


def test_missing_file_exits_2(tmp_path: Path) -> None:
    code, _, err = _run(str(tmp_path / "absent"))
    assert code == 2
    assert "contentdigest:" in err


def test_bad_option_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run("--nope")[0] == 2


def test_help_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run("--help")[0] == 0
    assert "Exit status" in capsys.readouterr().out


def test_module_entry_point_exits_with_the_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["contentdigest", "--verify", "sha-256=:AAAA:,"])
    with pytest.raises(SystemExit) as exit_:
        runpy.run_module("contentdigest", run_name="__main__")
    assert exit_.value.code == 2
