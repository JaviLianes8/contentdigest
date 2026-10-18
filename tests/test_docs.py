"""The README and GUIDE examples run and print what they say; docs and metadata agree."""

from __future__ import annotations

import contextlib
import io
import itertools
import re
from pathlib import Path

import pytest

import contentdigest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
BADGE = (
    "[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)]"
    "(https://lianes8studio.com/certified)"
)


def _blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def _expected(block: str) -> list[str]:
    """Each print line is followed by a comment line that holds what it prints."""
    lines = block.splitlines()
    return [
        after.strip()[2:]
        for line, after in itertools.pairwise(lines)
        if line.lstrip().startswith("print(") and after.lstrip().startswith("# ")
    ]


@pytest.mark.parametrize(
    ("name", "text", "count"), [("README", README, 4), ("GUIDE", GUIDE, 4)], ids=["README", "GUIDE"]
)
def test_every_example_prints_its_comments(name: str, text: str, count: int) -> None:
    assert len(_blocks(text)) == count, name
    for block in _blocks(text):
        prints = [line for line in block.splitlines() if line.lstrip().startswith("print(")]
        assert len(prints) == len(_expected(block)), block
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(block, name, "exec"), {"__name__": "docs"})
        assert out.getvalue().splitlines() == _expected(block)


def test_the_readme_links_are_absolute_and_reach_the_guide_and_changelog() -> None:
    for target in re.findall(r"\]\(([^)]+)\)", README):
        assert target.startswith("https://"), target
    assert "https://github.com/JaviLianes8/contentdigest/blob/main/GUIDE.md" in README
    assert "https://github.com/JaviLianes8/contentdigest/blob/main/CHANGELOG.md" in README


def test_the_readme_carries_the_certified_badge_under_the_title() -> None:
    assert README.splitlines()[:3] == ["# contentdigest", "", BADGE]


def test_the_api_table_lists_every_public_name() -> None:
    table = README.split("## API", 1)[1].split("\n## ", 1)[0]
    for name in contentdigest.__all__:
        assert f"`{name}" in table, name


def test_the_command_line_example_prints_what_the_library_gives() -> None:
    body = b'{"hello": "world"}'
    assert f"$ contentdigest body.json\n{contentdigest.make_digest(body)}\n" in README


def test_version_and_changelog_agree() -> None:
    match = re.search(r'^version = "([^"]+)"$', PYPROJECT, flags=re.MULTILINE)
    assert match is not None and match.group(1) == contentdigest.__version__
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(
        rf"^## \[{re.escape(contentdigest.__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
        changelog,
        flags=re.MULTILINE,
    )


def test_package_metadata_is_complete() -> None:
    assert "Development Status :: 5 - Production/Stable" in PYPROJECT
    assert 'requires-python = ">=3.10"' in PYPROJECT and "dependencies = []" in PYPROJECT
    versions = re.findall(r'"Programming Language :: Python :: (3\.\d+)"', PYPROJECT)
    assert versions == ["3.10", "3.11", "3.12", "3.13", "3.14"]
    for url in ("Homepage", "Source", "Issues", "Changelog"):
        assert re.search(rf"^{url} = \"https://", PYPROJECT, flags=re.MULTILINE), url
    assert 'license = "MIT"' in PYPROJECT and "keywords = [" in PYPROJECT


def _tree(*suffixes: str) -> list[Path]:
    found = []
    for path in ROOT.rglob("*"):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if parts[:2] == ("tests", "upstream") and path.name != "MANIFEST.json":
            continue  # third-party files, fetched locally
        if any(part.startswith(".") or part in ("__pycache__", "build", "dist") for part in parts):
            continue
        found.append(path)
    return found


def test_no_em_dash_anywhere_in_the_tree() -> None:
    for path in _tree(".py", ".md", ".toml", ".ps1", ".txt", ".json", ".java"):
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_source_files_stay_under_two_hundred_lines() -> None:
    for path in _tree(".py", ".java", ".ps1"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path
