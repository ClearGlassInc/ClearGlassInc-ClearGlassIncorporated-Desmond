# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from scripts.control_surface_feeds import (
    FEED_DEFS,
    SCHEMA_PATH,
    collect_offline,
    main,
    shape_activity,
    shape_alerts,
    shape_health,
    shape_metrics,
    shape_runs,
    status_for,
)

NOW = datetime(2026, 6, 12, 1, 0, tzinfo=timezone.utc)


# ── status_for ────────────────────────────────────────────────────────────────

def test_status_for_maps_conclusions():
    assert status_for("success") == "ok"
    assert status_for("failure") == "bad"
    assert status_for("timed_out") == "bad"
    assert status_for("cancelled") == "warn"
    assert status_for(None) == "warn"


# ── shaping ───────────────────────────────────────────────────────────────────

def _runs():
    runs, _, _ = collect_offline(NOW)
    return runs


def test_shape_runs_fields_and_limit():
    items = shape_runs(_runs() * 10)
    assert len(items) <= 20
    for it in items:
        assert it["status"] in {"ok", "warn", "bad"}
        assert it["title"] and it["detail"]


def test_shape_activity_prepends_refresh_marker():
    items = shape_activity(_runs(), NOW)
    assert items[0]["title"] == "Control Surface feeds refreshed"
    assert len(items) <= 50


def test_shape_alerts_only_latest_failures():
    alerts = shape_alerts(_runs())
    titles = [a["title"] for a in alerts]
    assert any("API Security Audit" in t for t in titles)
    assert all(a["status"] in {"warn", "bad"} for a in alerts)
    # a workflow whose latest run succeeds must not alert
    assert not any("Deploy GitHub Pages" in t for t in titles)


def test_shape_metrics_rates():
    metrics = shape_metrics(_runs(), page_count=55, workflow_count=16, deploys_7d=(4, 4), now=NOW)
    assert len(metrics) == 4
    by_label = {m["label"]: m for m in metrics}
    assert by_label["Workflows green (24h)"]["value"] == "4/5"
    assert by_label["Pages deploys (7d)"]["pct"] == 100
    for m in metrics:
        assert 0 <= m["pct"] <= 100


def test_shape_health_degrades_on_failed_probe():
    healthy = shape_health({"/": True, "/x.html": True}, (4, 4))
    assert healthy["status"] == "Operational"
    degraded = shape_health({"/": True, "/x.html": False}, (4, 4))
    assert degraded["status"] == "Degraded"
    assert "1/2" in degraded["detail"]


# ── end-to-end offline run validates against the published contract ──────────

def test_offline_run_writes_contract_valid_feeds(tmp_path):
    rc = main(["--offline", "--out", str(tmp_path)])
    assert rc == 0
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    for fname, def_name in FEED_DEFS.items():
        payload = json.loads((tmp_path / fname).read_text(encoding="utf-8"))
        wrapper = {**schema, "oneOf": [{"$ref": f"#/$defs/{def_name}"}]}
        jsonschema.Draft202012Validator(wrapper).validate(payload)


def test_strict_offline_run_succeeds_when_validator_present(tmp_path):
    pytest.importorskip("jsonschema")
    assert main(["--offline", "--strict", "--out", str(tmp_path)]) == 0
