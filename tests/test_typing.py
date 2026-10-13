"""The public API is typed: mypy infers results and rejects bad calls."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
import contentdigest as cd
reveal_type(cd.make_digest(b"x"))
reveal_type(cd.parse("a=:AA==:"))
reveal_type(cd.verify("a=:AA==:", b"x", accept=["sha-256"]))
reveal_type(cd.parse_want(b"a=1"))
reveal_type(cd.choose_algorithm(None))
reveal_type(cd.Verifier(["a=:AA==:"]).verify())
reveal_type(cd.SUPPORTED_ALGORITHMS)
cd.make_digest("text")
cd.verify("a=:AA==:", b"x", ["sha-256"])
cd.make_want({"sha-256": "high"})
cd.Digester().update(5)
cd.parse(5)
cd.make_digest(bytearray(b"x"))
cd.make_digest(memoryview(b"x"), algos=("sha-512",))
cd.Digester(["sha-256"]).update(memoryview(b"x"))
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    out, err, _ = api.run(
        ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    )
    return str(out) + str(err)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (3, r"builtins\.str"),
        (4, r"builtins\.dict\[builtins\.str, builtins\.bytes\]"),
        (5, r"builtins\.bool"),
        (6, r"builtins\.dict\[builtins\.str, builtins\.int\]"),
        (7, r"builtins\.str \| None"),
        (8, r"builtins\.bool"),
        (9, r"builtins\.frozenset\[builtins\.str\]"),
    ],
)
def test_results_are_typed(mypy_output: str, line: int, expected: str) -> None:
    # Older mypy releases print the builtins prefix, newer ones do not.
    pattern = expected.replace(r"builtins\.", r"(builtins\.)?")
    assert re.search(rf'snippet\.py:{line}: note: Revealed type is "{pattern}"', mypy_output), (
        mypy_output
    )


@pytest.mark.parametrize(
    ("line", "code"),
    [(10, "arg-type"), (11, "call-arg"), (12, "dict-item"), (13, "arg-type"), (14, "arg-type")],
)
def test_wrong_calls_are_rejected(mypy_output: str, line: int, code: str) -> None:
    assert re.search(rf"snippet\.py:{line}: error: .*\[{code}\]", mypy_output), mypy_output


def test_bytes_like_calls_are_accepted(mypy_output: str) -> None:
    assert not re.search(r"snippet\.py:1[5-7]: error", mypy_output), mypy_output
