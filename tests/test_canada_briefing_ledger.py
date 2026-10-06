"""The Canada strategic briefing and its claim ledger must agree.

blog/canada-strategic-briefing-october-2026.html carries a status chip next to
every checkable claim and a static tally of the ledger, so the article reads
correctly without JavaScript. The ledger JSON is the source of truth, and its
manifest publishes the SHA-256 the in-browser console checks before rendering.
Three things can drift silently, and each has a test here:

- the manifest hash goes stale after a ledger edit, and every reader then sees
  HASH MISMATCH;
- a chip's colour/glyph says one status while the ledger says another;
- a claim is marked confirmed, corrected or updated with no source behind it.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "blog/canada-strategic-briefing-october-2026.html"
LEDGER = ROOT / "blog/data/canada-strategic-briefing-2026-10.json"
MANIFEST = ROOT / "blog/data/canada-strategic-briefing-2026-10.manifest.json"

STATUSES = {"confirmed", "corrected", "updated", "assessment", "target"}
SOURCED = {"confirmed", "corrected", "updated"}
GLYPH = {"confirmed": "✓", "corrected": "≠", "updated": "↻", "assessment": "◇", "target": "◎"}
CHIP_RE = re.compile(
    r'<a class="claim s-(?P<cls>[a-z]+)" href="#ledger" data-claim="(?P<id>CA-\d{2})"'
    r' aria-label="Claim (?P<aid>CA-\d{2}), (?P<astatus>[a-z]+)">(?P<glyph>\S) (?P<tid>CA-\d{2})</a>'
)


@pytest.fixture(scope="module")
def ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_manifest_hash_matches_ledger_bytes(ledger: dict) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
    assert manifest["sha256"] == actual, (
        "ledger edited without refreshing its manifest; readers would see HASH MISMATCH. "
        f"Set sha256 to {actual}"
    )
    assert manifest["records"] == len(ledger["records"])
    assert manifest["asOf"] == ledger["asOf"]


def test_records_are_well_formed(ledger: dict) -> None:
    ids = [r["id"] for r in ledger["records"]]
    assert len(ids) == len(set(ids)), "duplicate ledger id"
    assert set(ledger["statuses"]) == STATUSES
    for r in ledger["records"]:
        assert re.fullmatch(r"CA-\d{2}", r["id"]), r["id"]
        assert r["status"] in STATUSES, r
        for field in ("domain", "draft", "finding", "confidence", "checkedVia"):
            assert str(r.get(field, "")).strip(), f"{r['id']} has no {field}"


def test_verified_statuses_carry_https_sources(ledger: dict) -> None:
    for r in ledger["records"]:
        if r["status"] in SOURCED:
            assert r["sources"], f"{r['id']} is {r['status']} with no source"
        for s in r["sources"]:
            assert s["url"].startswith("https://"), f"{r['id']}: {s['url']}"
            assert s["publisher"].strip() and s["title"].strip()


def test_every_chip_matches_its_record(ledger: dict, page: str) -> None:
    records = {r["id"]: r for r in ledger["records"]}
    chips = list(CHIP_RE.finditer(page))
    assert chips, "no claim chips found; did the chip markup change?"
    # Any data-claim the strict pattern missed is malformed markup.
    assert len(chips) == page.count('data-claim="'), "a claim chip does not match the expected markup"
    for m in chips:
        rid = m["id"]
        assert rid in records, f"chip {rid} has no ledger record"
        want = records[rid]["status"]
        assert m["aid"] == m["tid"] == rid
        assert m["cls"] == m["astatus"] == want, f"{rid}: chip says {m['cls']}, ledger says {want}"
        assert m["glyph"] == GLYPH[want], f"{rid}: wrong glyph for {want}"


def test_every_record_is_surfaced_in_the_article(ledger: dict, page: str) -> None:
    cited = {m["id"] for m in CHIP_RE.finditer(page)}
    missing = sorted({r["id"] for r in ledger["records"]} - cited)
    assert not missing, f"ledger records never cited in the article: {missing}"


def test_static_tally_matches_ledger(ledger: dict, page: str) -> None:
    counts = Counter(r["status"] for r in ledger["records"])
    counts["total"] = len(ledger["records"])
    found = dict(re.findall(r'data-count="([a-z]+)">(\d+)<', page))
    assert set(found) == STATUSES | {"total"}
    for key, value in found.items():
        assert int(value) == counts[key], f"tally {key}: page says {value}, ledger has {counts[key]}"


def test_no_leaked_citation_markers(page: str) -> None:
    # A sibling brief shipped with raw "citeturn0search7" tokens from a chat
    # export. Keep that from happening here.
    assert "citeturn" not in page
    assert "" not in page
