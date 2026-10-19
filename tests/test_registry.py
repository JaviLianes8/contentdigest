"""The algorithm sets against the registry, as RFC 9530 created it and as IANA serves it.

Sources (fetched 2026-10-18 into tests/upstream, see MANIFEST.json): Table 2 of
https://www.rfc-editor.org/rfc/rfc9530.txt and
https://www.iana.org/assignments/http-digest-hash-alg/http-digest-hash-alg.xml (updated
2024-05-22). A new registration changes the registry file, so its manifest entry fails and
this test is revisited.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree

from conftest import upstream_bytes, upstream_text

from contentdigest import ACTIVE_ALGORITHMS, DEPRECATED_ALGORITHMS, SUPPORTED_ALGORITHMS

NS = {"iana": "http://www.iana.org/assignments"}


def _statuses(rows: list[tuple[str, str]]) -> dict[str, frozenset[str]]:
    return {
        status: frozenset(key for key, value in rows if value == status)
        for status in {value for _, value in rows}
    }


def test_rfc_9530_table_2_is_the_algorithm_sets() -> None:
    text = upstream_text("rfc9530.txt")
    table = text[text.index("\n7.2.  Creation") : text.index("Table 2: Initial Hash Algorithms")]
    rows = re.findall(r"^   \| ([a-z0-9-]+) +\| ([A-Za-z]+) +\|", table, re.M)
    assert len(rows) == 8
    assert _statuses(rows) == {"Active": ACTIVE_ALGORITHMS, "Deprecated": DEPRECATED_ALGORITHMS}


def test_the_iana_registry_is_the_algorithm_sets() -> None:
    root = ElementTree.fromstring(upstream_bytes("http-digest-hash-alg.xml"))
    assert root.findtext("iana:updated", namespaces=NS) == "2024-05-22"
    records = root.findall("iana:registry/iana:record", NS)
    rows = [(r.findtext("iana:key", "", NS), r.findtext("iana:status", "", NS)) for r in records]
    assert len(rows) == len(SUPPORTED_ALGORITHMS)
    assert _statuses(rows) == {"Active": ACTIVE_ALGORITHMS, "Deprecated": DEPRECATED_ALGORITHMS}


def test_the_rfc_names_the_three_statuses_and_their_use() -> None:
    text = re.sub(r"\s+", " ", upstream_text("rfc9530.txt"))
    assert '"Active": Algorithms without known problems' in text
    assert '"Provisional": Unproven algorithms' in text
    assert "MUST NOT be used in a potentially adversarial setting" in text
