"""The README examples run and print what they say; metadata agrees with the code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import contentdigest

ROOT = Path(__file__).resolve().parents[1]

SHA256 = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
OUTPUTS = [
    [SHA256, "True", "5f8f04f6a3a892aa", "True False"],
    [SHA256, "('sha-256', 'sha-512')", "True"],
    ["['sha-256', 'sha-512']", "md5=:Sd/dVLAcvNLSq16eXua5uQ==:", "DigestError", "True"],
    ["{'sha-512': 3, 'sha-256': 10, 'unixsum': 0}", "sha-256", "None", "sha-512=10, sha-256=5"],
]


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _blocks() -> list[str]:
    return re.findall(r"```python\n(.*?)```", _readme(), flags=re.DOTALL)


def test_there_is_one_expected_output_per_example() -> None:
    assert len(_blocks()) == len(OUTPUTS)


@pytest.mark.parametrize("index", range(len(OUTPUTS)))
def test_each_example_prints_its_output(index: int, capsys: pytest.CaptureFixture[str]) -> None:
    exec(compile(_blocks()[index], "README.md", "exec"), {"__name__": "readme"})

    assert capsys.readouterr().out.splitlines() == OUTPUTS[index]


@pytest.mark.parametrize("index", range(len(OUTPUTS)))
def test_each_printed_line_is_shown_as_a_comment(index: int) -> None:
    comments = re.findall(r"^# (.+)$", _blocks()[index], flags=re.MULTILINE)

    assert [text.strip() for text in comments] == OUTPUTS[index]


def test_the_command_line_example_prints_what_the_readme_shows() -> None:
    body = b'{"hello": "world"}'
    assert f"$ contentdigest body.json\n{contentdigest.make_digest(body)}\n" in _readme()


def test_every_public_name_appears_in_the_readme() -> None:
    for name in contentdigest.__all__:
        assert f"`{name}" in _readme(), name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == contentdigest.__version__


def test_changelog_has_an_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{contentdigest.__version__}]" in text


def test_no_em_dash_in_any_shipped_text() -> None:
    files = [*ROOT.glob("*.md"), *ROOT.glob("src/**/*.py"), *ROOT.glob("tests/*.py")]
    for path in files:
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_every_source_file_stays_under_two_hundred_lines() -> None:
    for path in [*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/*.py")]:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path
