"""Every digest value printed in RFC 9530 that can be reproduced, copied from the RFC text.

Source: https://www.rfc-editor.org/rfc/rfc9530.txt, fetched 2026-10-12. Errata:
https://www.rfc-editor.org/errata/rfc9530 (erratum 8890 for the Brotli bytes of B.4 and B.6).
Bodies are as the RFC describes them ("followed by an LF" where it says so); the multi-line
JSON bodies are typed in with the two-space indentation the RFC shows.
"""

from __future__ import annotations

import base64

import pytest

from contentdigest import choose_algorithm, make_digest, parse, parse_want, verify

HELLO = b'{"hello": "world"}'
HELLO_LF = HELLO + b"\n"
NEW_TITLE = b'{"title": "New Title"}\n'
B7 = b'{\n  "id": "123",\n  "title": "New Title"\n}\n'
B8 = (
    b'{\n  "status": "created",\n  "id": "123",\n  "ts": 1569327729,\n'
    b'  "instance": "/books/123"\n}\n'
)
B10 = (
    b'{\n  "title": "Not Found",\n  "detail": "Cannot PATCH a non-existent resource",\n'
    b'  "status": 404\n}\n'
)
# Figure 18 as published, and as erratum 8890 corrects it (first two bytes 0B 09).
BROTLI_PUBLISHED = bytes.fromhex("8B08807B2268656C6C6F223A2022776F726C64227D0A03")
BROTLI_CORRECTED = bytes.fromhex("0B09807B2268656C6C6F223A2022776F726C64227D0A03")

# Appendix D: {"hello": "world"} under every registered algorithm.
APPENDIX_D = {
    "sha-512": "WZDPaVn/7XgHaAy8pmojAkGWoRx2UFChF41A2svX+TaPm+"
    "AbwAgBWnrIiYllu7BNNyealdVLvRwEmTHWXvJwew==",
    "sha-256": "X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=",
    "md5": "Sd/dVLAcvNLSq16eXua5uQ==",
    "sha": "07CavjDP4u3/TungoUHJO/Wzr4c=",
    "unixsum": "GQU=",
    "unixcksum": "7zsHAA==",
    "adler": "OZkGFw==",
    "crc32c": "Q3lHIA==",
}

FIGURES = [
    ("B.1 figure 12", HELLO_LF, "sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=:"),
    ("B.2 figure 14", b"", "sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:"),
    ("B.3 figure 16", b'"world"}\n', "sha-256=:jjcgBDWNAtbYUXI37CVG3gRuGOAjaaDRGpIUFsdyepQ=:"),
    ("B.7 figure 22", NEW_TITLE, "sha-256=:mEkdbO7Srd9LIOegftO0aBX+VPTVz7/CSHes2Z27gc4=:"),
    ("B.7 figure 23", B7, "sha-256=:uVSlinTTdQUwm2On4k8TJUikGN1bf/Ds8WPX4oe0h9I=:"),
    ("B.8 figure 25", B8, "sha-256=:yXIGDTN5VrfoyisKlXgRKUHHMs35SNtyC3szSz1dbO8=:"),
    ("B.10 figure 28", B10, "sha-256=:EXB0S2VF2H7ijkAVJkH1Sm0pBho0iDZcvVUHHXTTZSA=:"),
    (
        "C.2 figure 34",
        HELLO_LF,
        "sha-512=:YMAam51Jz/jOATT6/zvHrLVgOYTGFy1d6GJiOHTohq4yP+pgk4vf2aCs"
        "yRZOtw8MjkM7iw7yZ/WkppmM44T3qg==:",
    ),
    (
        "B.6 figure 21, erratum 8890",
        BROTLI_CORRECTED,
        "sha-256=:d435Qo+nKZ+gLcUHn7GQtQ72hiBVAgqoLsZnZPiTGPk=:, "
        "sha-512=:db7fdBbgZMgX1Wb2MjA8zZj+rSNgfmDCEEXM8qLWfpfoNY0sCpHAzZbj"
        "09X1/7HAb7Od5Qfto4QpuBsFbUO3dQ==:",
    ),
]

# B.5, B.6, B.11 and C.1 print this value with one "=" too many; RFC 9651 parsers accept it.
OVER_PADDED = "sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg==:"


@pytest.mark.parametrize(("algo", "encoded"), APPENDIX_D.items())
def test_appendix_d_value_is_reproduced(algo: str, encoded: str) -> None:
    assert make_digest(HELLO, algos=[algo]) == f"{algo}=:{encoded}:"


@pytest.mark.parametrize(("algo", "encoded"), APPENDIX_D.items())
def test_appendix_d_value_verifies_when_accepted(algo: str, encoded: str) -> None:
    field = f"{algo}=:{encoded}:"
    assert verify(field, HELLO, accept=[algo]) is True
    assert verify(field, HELLO_LF, accept=[algo]) is False


@pytest.mark.parametrize(("name", "body", "field"), FIGURES, ids=[f[0] for f in FIGURES])
def test_figure_value_is_reproduced(name: str, body: bytes, field: str) -> None:
    algos = list(parse(field))
    assert make_digest(body, algos=algos) == field
    assert verify(field, body) is True


def test_published_brotli_bytes_give_the_digest_the_erratum_reports() -> None:
    expected = "sha-256=:MklYnI/SsUF/5X7enJ2TU+DFjodRObdKLFaPPLe/Kcw=:"
    assert make_digest(BROTLI_PUBLISHED) == expected


def test_the_rfc_over_padded_example_parses_and_verifies() -> None:
    raw = base64.b64decode("RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=")
    assert parse(OVER_PADDED) == {"sha-256": raw}
    assert verify(OVER_PADDED, HELLO_LF) is True


def test_section_2_multi_line_example_is_one_field() -> None:
    # The two members of the section 2 example, as two field lines.
    lines = [
        "sha-256=:d435Qo+nKZ+gLcUHn7GQtQ72hiBVAgqoLsZnZPiTGPk=:",
        "sha-512=:YMAam51Jz/jOATT6/zvHrLVgOYTGFy1d6GJiOHTohq4yP+pgk4vf2aCs"
        "yRZOtw8MjkM7iw7yZ/WkppmM44T3qg==:",
    ]
    assert list(parse(lines)) == ["sha-256", "sha-512"]


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("sha-256=1", {"sha-256": 1}),
        ("sha-512=3, sha-256=10, unixsum=0", {"sha-512": 3, "sha-256": 10, "unixsum": 0}),
        ("sha-256=3, sha=10", {"sha-256": 3, "sha": 10}),
        ("sha=10", {"sha": 10}),
    ],
)
def test_section_4_and_appendix_c_preferences_parse(field: str, expected: dict[str, int]) -> None:
    assert parse_want(field) == expected


def test_appendix_c_server_choices() -> None:
    assert choose_algorithm("sha-512=3, sha-256=10, unixsum=0") == "sha-256"
    # C.1: the client prefers "sha", the server answers with sha-256 anyway.
    assert choose_algorithm("sha-256=3, sha=10") == "sha-256"
    # C.2: "sha" is all the client wants; an Active-only server has nothing to match.
    assert choose_algorithm("sha=10") is None
