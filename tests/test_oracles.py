"""Independent implementations as oracles; each test skips when its oracle is not installed.

- http_sf 1.3.1 and 1.4.0 (by Mark Nottingham, an author of RFC 9651): on seeded valid and
  broken dictionary fields, this parser with a strict byte-sequence decoder swapped in (the
  one http_sf uses, base64 with validate=True) gives the same fields, values and failures;
  the real parser accepts a superset, the padding leniencies of RFC 9651 section 4.2.7, with
  the same values wherever the strict one succeeds. The differences are http_sf's: before
  1.4.0 it refused an empty dictionary, and it stops at dates a Python datetime cannot hold.
  It runs from Python 3.12, whose strict base64 refuses excess padding as this parser does.
- requests-http-signature 0.7.1 and 1.0.0 (pyauth): the Content-Digest it builds for
  sha-256 and sha-512 is the one make_digest builds, and verify accepts it.
"""

from __future__ import annotations

import base64
import binascii
import random
import sys
from datetime import datetime
from decimal import Decimal
from importlib import metadata
from typing import Any

import generators
import pytest

from contentdigest import make_digest, verify
from contentdigest._errors import DigestError
from contentdigest._sf import parse_dictionary
from contentdigest._sf_items import Reader

STRICT = "byte sequence refused by strict base64"


def _strict_byte_sequence(self: Reader) -> bytes:
    end = self.text.find(":", self.pos + 1)
    if end < 0:
        raise self.fail("unterminated byte sequence")
    try:
        data = base64.b64decode(self.text[self.pos + 1 : end], validate=True)
    except (binascii.Error, ValueError):
        raise self.fail(STRICT) from None
    self.pos = end + 1
    return data


def _bare(value: Any) -> tuple[str, Any]:
    name = type(value).__name__
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, datetime):
        return ("date", int(value.timestamp()))
    if name in ("Date", "Token", "DisplayString"):
        return (name.lower(), int(value) if name == "Date" else str(value))
    for kind in (int, Decimal, bytes, str):
        if isinstance(value, kind):
            return (kind.__name__, value)
    raise AssertionError(type(value))


def _member(member: Any) -> Any:
    value, params = member
    shown = [(key, _bare(item)) for key, item in params.items()]
    if isinstance(value, list):
        return ("inner", [_member(item) for item in value], shown)
    return ("item", _bare(value), shown)


def _ours(text: str) -> Any:
    try:
        return ("ok", [(key, _member(m)) for key, m in parse_dictionary(text).items()])
    except DigestError as error:
        return ("fail", STRICT in str(error))


def _theirs(http_sf: Any, text: str) -> Any:
    try:
        parsed = http_sf.parse(text.encode("latin-1"), tltype="dictionary")
    except http_sf.StructuredFieldError as error:
        # datetime cannot hold every 15-digit date; RFC 9651 dates are plain integers.
        return ("date-limit",) if "Date value out of range" in str(error) else ("fail", False)
    return ("ok", [(key, _member(m)) for key, m in parsed.items()])


def _texts(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    texts = []
    for _ in range(count):
        text = generators.dictionary(rng)
        texts.append(generators.mutate(rng, text) if rng.random() < 0.5 else text)
    return texts


# Before Python 3.12, base64 with validate=True accepts "=" padding beyond what the data needs,
# so http_sf (and the strict decoder below) did too; this parser refuses it on every version.
@pytest.mark.skipif(sys.version_info < (3, 12), reason="strict base64 changed in Python 3.12")
@pytest.mark.parametrize("seed", [9651, 8941])
def test_http_sf_agrees_with_the_strict_parser(seed: int, monkeypatch: pytest.MonkeyPatch) -> None:
    http_sf = pytest.importorskip("http_sf")
    release = tuple(int(part) for part in metadata.version("http-sf").split(".")[:2])
    empty = ("ok", []) if release >= (1, 4) else ("fail", False)
    texts = _texts(seed, 15_000)
    with monkeypatch.context() as patch:
        patch.setattr(Reader, "byte_sequence", _strict_byte_sequence)
        strict = [_ours(text) for text in texts]
    lenient = [_ours(text) for text in texts]
    counts = {"agree": 0, "valid": 0, "date-limit": 0, "lenient": 0, "empty": 0}
    for text, ours, loose in zip(texts, strict, lenient, strict=True):
        theirs = _theirs(http_sf, text)
        if theirs == ("date-limit",):
            counts["date-limit"] += 1  # http_sf stopped early; nothing to compare
        elif not text.strip(" "):
            # RFC 9651 4.2.2 step 3 (and the httpwg "empty dictionary" case) give an empty
            # dictionary; http_sf before 1.4.0 raises "Trailing delimiter" instead.
            assert (ours, theirs) == (("ok", []), empty), repr(text)
            counts["empty"] += 1
        else:
            assert (ours if ours[0] == "ok" else ("fail", False)) == theirs, text
            counts["agree"] += 1
        if ours[0] == "ok":
            assert loose == ours, text
            counts["valid"] += 1
        elif ours == ("fail", True):
            counts["lenient"] += loose[0] == "ok"
        else:
            assert loose == ours, text
    assert counts["agree"] > 14_000 and counts["valid"] > 5_000 and counts["lenient"] > 500
    assert counts["date-limit"] < len(texts) // 10


def test_requests_http_signature_builds_the_same_content_digest() -> None:
    signing = pytest.importorskip("requests_http_signature")
    requests = pytest.importorskip("requests")
    rng = random.Random(9421)
    for algo in ("sha-256", "sha-512"):
        auth = signing.HTTPSignatureAuth(
            signature_algorithm=signing.algorithms.HMAC_SHA256, key=b"k" * 32, key_id="test"
        )
        auth.signing_content_digest_algorithm = algo
        for _ in range(200):
            body = rng.randbytes(rng.randrange(1, 3000))
            request = requests.Request("POST", "https://example.invalid/", data=body).prepare()
            auth.add_digest(request)
            field = request.headers["Content-Digest"]
            assert field == make_digest(body, algos=[algo])
            assert verify(field, body) and not verify(field, body + b"x")
