from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_SHA = "df4cb1c069e1874edd31b4311f1884172cec0e10"
SETUP_PYTHON_SHA = "a309ff8b426b58ec0e2a45f0f869d46889d02405"


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_minerals_page_is_wired_and_semantic():
    html = (ROOT / "minerals.html").read_text(encoding="utf-8")
    assert html.lower().count("<h1") == 1
    assert 'id="main-content"' in html
    assert 'href="/minerals.css"' in html
    assert 'src="/minerals.js"' in html
    assert 'id="system-status"' in html
    assert 'id="mineral-query"' in html
    assert 'id="feed-table-body"' in html
    assert "Decision support, not legal determination" in html
    assert "SCENARIO ANALYSIS — NOT A FORECAST" in html


def test_manifest_is_truthful_and_complete():
    manifest = load_json("feeds/minerals/manifest.json")
    assert manifest["system"] == "ClearGlass Critical Minerals Intelligence"
    assert manifest["overall_status"] in {"DEGRADED", "OPERATIONAL"}
    feeds = manifest["feeds"]
    ids = {feed["id"] for feed in feeds}
    assert {"policy", "news", "prices", "production", "reserves", "trade", "sanctions", "supply-risk", "mineral-directory"} <= ids
    assert len(ids) == len(feeds)
    allowed = {
        "LIVE", "NEAR LIVE", "DELAYED", "DAILY", "WEEKLY", "MONTHLY",
        "STATIC REFERENCE", "STALE", "DEGRADED", "OFFLINE", "UNAVAILABLE",
        "OPERATIONAL", "HEALTHY", "UNKNOWN",
    }
    for feed in feeds:
        assert feed["status"] in allowed
        assert isinstance(feed["record_count"], int)
        assert feed["record_count"] >= 0
        assert feed["source"]
        assert feed["source_url"].startswith("https://")


def test_initial_live_feeds_fail_closed():
    for name in ("policy", "news"):
        payload = load_json(f"feeds/minerals/latest/{name}.json")
        assert payload["status"] == "UNAVAILABLE"
        assert payload["records"] == []
        assert payload["retrieved_at"] is None


def test_mineral_reference_directory_uses_unknown_for_quantitative_risk():
    payload = load_json("feeds/minerals/metadata/minerals.json")
    minerals = payload["minerals"]
    assert len(minerals) >= 12
    ids = [item["id"] for item in minerals]
    assert len(ids) == len(set(ids))
    assert "rare-earth-elements" in ids
    for item in minerals:
        assert item["risk_level"] == "UNKNOWN"
        assert item["canada_exposure"] == "UNKNOWN"
        assert item["confidence"] in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}


def test_frontend_has_timeout_error_states_and_no_hardcoded_live_claim():
    js = (ROOT / "minerals.js").read_text(encoding="utf-8")
    assert "AbortController" in js
    assert "REQUEST_TIMEOUT_MS" in js
    assert "Promise.allSettled" in js
    assert "renderManifestError" in js
    assert "renderPolicyError" in js
    assert "Missing data" not in js  # wording belongs to HTML, not executable state
    assert not re.search(r'textContent\s*=\s*["\']LIVE["\']', js)


def test_sync_pipeline_has_retry_lkg_validation_and_no_secrets():
    source = (ROOT / "scripts/minerals_data_sync.py").read_text(encoding="utf-8")
    assert "TRANSIENT_CODES" in source
    assert "Retry-After" in source
    assert "backup_last_known_good" in source
    assert "validate_records" in source
    assert "write_json_atomic" in source
    assert "GITHUB_STEP_SUMMARY" in source
    assert "api_key" not in source.lower()
    assert "token=" not in source.lower()


def test_workflow_is_non_overlapping_and_non_recursive():
    workflow = (ROOT / ".github/workflows/minerals-data-sync.yml").read_text(encoding="utf-8")
    assert "group: minerals-data-sync" in workflow
    assert "cancel-in-progress: false" in workflow
    assert f"actions/checkout@{CHECKOUT_SHA}" in workflow
    assert f"actions/setup-python@{SETUP_PYTHON_SHA}" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "bot(minerals): refresh validated public feeds [skip ci]" in workflow
    # A push trigger would risk recursively activating after generated-data commits.
    assert not re.search(r"^\s*push:\s*$", workflow, flags=re.MULTILINE)


def test_pages_hardener_tracks_replacement_state():
    source = (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")
    assert "metadata_replaced = False" in source
    assert "if not tags and not metadata_replaced:" in source
