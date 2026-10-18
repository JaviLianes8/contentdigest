"""The command when its streams are missing, closed or broken, and its message lengths."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from contentdigest import _cli, make_digest
from contentdigest._cli import run

BODY = b'{"hello": "world"}'
SRC = Path(__file__).resolve().parents[1] / "src"


class Broken(io.StringIO):
    """A text stream whose reader went away."""

    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


def test_missing_standard_input_exits_2_with_a_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    err = io.StringIO()
    assert run([], stdout=io.StringIO(), stderr=err) == 2
    assert err.getvalue() == "contentdigest: there is no standard input to read\n"


@pytest.mark.parametrize("argv", [[], ["--verify", make_digest(BODY)]])
def test_a_result_that_cannot_be_written_exits_2(argv: list[str]) -> None:
    err = io.StringIO()
    assert run(argv, stdin=io.BytesIO(BODY), stdout=Broken(), stderr=err) == 2
    assert err.getvalue() == ""


def test_a_closed_output_stream_exits_2() -> None:
    out = io.StringIO()
    out.close()
    assert run([], stdin=io.BytesIO(BODY), stdout=out, stderr=io.StringIO()) == 2


def test_missing_standard_output_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    assert run([], stdin=io.BytesIO(BODY), stderr=io.StringIO()) == 2


def test_a_mismatch_keeps_exit_1_when_the_word_is_written() -> None:
    out = io.StringIO()
    assert run(["--verify", make_digest(b"x")], stdin=io.BytesIO(BODY), stdout=out) == 1
    assert out.getvalue() == "mismatch\n"


def test_main_points_a_broken_stdout_at_the_null_device(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = Broken()
    broken.fileno = lambda: 99  # type: ignore[method-assign]
    calls: list[int] = []
    monkeypatch.setattr(sys, "argv", ["contentdigest"])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(BODY)))
    monkeypatch.setattr(sys, "stdout", broken)
    monkeypatch.setattr(os, "dup2", lambda fd, target: calls.append(target))
    with pytest.raises(SystemExit) as exit_:
        _cli.main()
    assert (exit_.value.code, calls) == (2, [99])


@pytest.mark.parametrize(
    "argv",
    [["--" + "z" * 100_000], ["-a", "z" * 100_000], ["--verify", "k" * 100_000 + "=1"]],
)
def test_error_lines_stay_short(argv: list[str]) -> None:
    err = io.StringIO()
    assert run(argv, stdin=io.BytesIO(BODY), stdout=io.StringIO(), stderr=err) == 2
    assert 0 < len(err.getvalue()) < 600


def test_a_huge_file_name_is_cut_in_the_message(tmp_path: Path) -> None:
    err = io.StringIO()
    assert run([str(tmp_path / ("f" * 5000))], stdout=io.StringIO(), stderr=err) == 2
    assert err.getvalue().startswith("contentdigest: ")
    assert len(err.getvalue()) < 400


def _command(*argv: str) -> subprocess.Popen[bytes]:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.Popen(
        [sys.executable, "-m", "contentdigest", *argv],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


@pytest.mark.parametrize("argv", [[], ["--verify", make_digest(BODY)]])
def test_a_reader_that_went_away_gives_a_quiet_exit_2(argv: list[str]) -> None:
    process = _command(*argv)
    assert process.stdout is not None and process.stdin is not None
    # The command reads all of stdin before writing, so its write always meets a closed pipe.
    process.stdout.close()
    process.stdout = None
    _, err = process.communicate(BODY, timeout=60)
    assert (process.returncode, err) == (2, b"")


def test_the_process_prints_and_exits_0() -> None:
    process = _command()
    out, err = process.communicate(BODY, timeout=60)
    assert (process.returncode, out.decode().strip(), err) == (0, make_digest(BODY), b"")
