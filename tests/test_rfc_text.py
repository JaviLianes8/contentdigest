"""RFC 9530, its erratum 8890 and RFC 9651 as fetched: the values are read from the text.

Sources (fetched 2026-10-18 into tests/upstream, see MANIFEST.json):
https://www.rfc-editor.org/rfc/rfc9530.txt, https://www.rfc-editor.org/errata/eid8890 and
https://www.rfc-editor.org/rfc/rfc9651.txt. The message bodies are the ones of
test_rfc_vectors.py, typed in from the figures (the text does not separate them from the
messages); every digest value and preference here comes from the fetched text.
"""

from __future__ import annotations

import re

import pytest
from conftest import unfold, upstream_prose, upstream_text
from test_rfc_vectors import (
    B7,
    B8,
    B10,
    BROTLI_CORRECTED,
    BROTLI_PUBLISHED,
    HELLO,
    HELLO_LF,
    NEW_TITLE,
)

from contentdigest import DigestError, choose_algorithm, make_digest, parse, parse_want, verify

BODIES = [HELLO_LF, b"", b'"world"}\n', NEW_TITLE, B7, B8, B10, BROTLI_CORRECTED]


def _rfc() -> str:
    return unfold(upstream_text("rfc9530.txt"))


def _section(text: str, start: str, end: str) -> str:
    # Headings start a line; the table of contents indents the same titles.
    begin = text.index("\n" + start)
    return text[begin : text.index("\n" + end, begin + 1)]


def test_the_bodies_are_the_ones_the_rfc_describes() -> None:
    text = re.sub(r"\s+", " ", _rfc())
    assert text.count('{"hello": "world"} followed by an LF') >= 5
    assert '{"title": "New Title"} followed by an LF' in text


def test_every_digest_value_printed_in_the_rfc_is_reproduced() -> None:
    members = sorted(set(re.findall(r"\b([a-z0-9-]+)=:([A-Za-z0-9+/=]*):", _rfc())))
    assert len(members) == 11
    for algo, value in members:
        field = f"{algo}=:{value}:"
        bodies = [body for body in BODIES if verify(field, body)]
        assert len(bodies) == 1, field
        made = make_digest(bodies[0], algos=[algo])
        # One value is printed with one "=" too many (B.5, B.6, B.11, C.1).
        assert made in (field, field.replace("==:", "=:")), field
    over_padded = [m for m in members if make_digest(HELLO_LF) == f"{m[0]}=:{m[1][:-1]}:"]
    assert over_padded == [("sha-256", "RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg==")]


def test_appendix_d_is_reproduced() -> None:
    text = _section(_rfc(), "Appendix D.  Sample Digest Values", "Appendix E.")
    assert 'The input value is the JSON object {"hello": "world"}.' in text
    rows = re.findall(r"^\s+([a-z0-9-]+) -\s+:([A-Za-z0-9+/=]+):$", text, re.M)
    algos = ["sha-512", "sha-256", "md5", "sha", "unixsum", "unixcksum", "adler", "crc32c"]
    assert [algo for algo, _ in rows] == algos
    for algo, value in rows:
        assert make_digest(HELLO, algos=[algo]) == f"{algo}=:{value}:"


def test_the_preference_examples_and_range() -> None:
    text = _section(_rfc(), "4.  Integrity Preference Fields", "5.  Hash Algorithm")
    assert "It must be in the range 0 to 10 inclusive." in re.sub(r"\s+", " ", text)
    fields = re.findall(r"^\s+Want-(?:Repr|Content)-Digest: (.+)$", text, re.M)
    assert len(fields) == 4
    for field in fields:
        pairs = (member.split("=") for member in field.split(", "))
        assert parse_want(field) == {key: int(weight) for key, weight in pairs}
    assert parse_want("a=0, b=10") == {"a": 0, "b": 10}
    for weight in ("-1", "11"):
        with pytest.raises(DigestError):
            parse_want(f"sha-256={weight}")


def test_appendix_c_preferences_and_answers() -> None:
    text = _section(_rfc(), "Appendix C.  Examples of Want", "Appendix D.")
    wants = re.findall(r"^\s+Want-Repr-Digest: (.+)$", text, re.M)
    assert wants == ["sha-256=3, sha=10", "sha=10", "sha=10"]
    answers = re.findall(r"^\s+Repr-Digest: (\S+)$", text, re.M)
    assert [list(parse(answer)) for answer in answers] == [["sha-256"], ["sha-512"]]
    # C.1: the client prefers "sha"; an Active-only server answers with sha-256, as there.
    assert choose_algorithm(wants[0]) == "sha-256"
    # C.2: nothing it supports is wanted, so the server is free to use another algorithm.
    assert choose_algorithm(wants[1]) is None
    assert all(verify(answer, HELLO_LF) for answer in answers)


def test_erratum_8890_corrects_the_brotli_bytes() -> None:
    prose = upstream_prose("rfc9530-erratum-8890.html")
    assert "Status: Reported" in prose
    says, should = re.findall(r"((?:[0-9A-F]{2} ){22}[0-9A-F]{2})", prose)[:2]
    assert (bytes.fromhex(says), bytes.fromhex(should)) == (BROTLI_PUBLISHED, BROTLI_CORRECTED)
    claim = re.search(r"SHA-256 over the bytes in the original text is (\S+=),", prose)
    assert claim is not None
    assert make_digest(BROTLI_PUBLISHED) == f"sha-256=:{claim.group(1)}:"
    section = _section(_rfc(), "B.6.  Client and Server", "B.7.  ")
    figure_18 = _section(_rfc(), "B.4.  Client and Server", "B.5.  ")
    dump = re.findall(r"^\s+((?:[0-9A-F]{2} )*[0-9A-F]{2})$", figure_18, re.M)
    assert bytes.fromhex(" ".join(dump)) == BROTLI_PUBLISHED
    field = re.findall(r"Repr-Digest: (\S+)", section)[-1]
    assert list(parse(field)) == ["sha-256", "sha-512"]
    assert verify(field, BROTLI_CORRECTED) and not verify(field, BROTLI_PUBLISHED)


def test_rfc_9651_byte_sequence_rules() -> None:
    text = re.sub(r"\s+", " ", upstream_text("rfc9651.txt"))
    assert 'parsers SHOULD NOT fail when "=" padding is not present' in text
    assert "parsers SHOULD NOT fail when non-zero pad bits are present" in text
    must = "parsers MUST fail on characters outside the base64 alphabet and on line feeds"
    assert must in text
    assert parse("a=:aGVsbG8:, b=:aGVsbG9=:") == {"a": b"hello", "b": b"hello"}
    for content in ("aGVs\nbG8=", "aGVs-bG8=", "aGVs bG8="):
        with pytest.raises(DigestError):
            parse(f"a=:{content}:")


def test_rfc_9651_ignores_the_whole_field_on_a_constraint_violation() -> None:
    text = re.sub(r"\s+", " ", upstream_text("rfc9651.txt"))
    assert "When field-specific constraints are violated, the entire field is also ignored" in text
    good = make_digest(HELLO)
    for field in (f"{good}, md5=1", f"{good}, sha=?1", f'{good}, x="s"'):
        with pytest.raises(DigestError):
            parse(field)
    with pytest.raises(DigestError):
        parse_want("sha-256=10, md5=:AAAA:")
