# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the SATS digital-twin storm risk engine (tools/sats_risk_engine.py)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from tools.sats_risk_engine import (
    DEFAULT_NETWORK,
    SCENARIOS,
    SCHEMA_VERSION,
    build_twin_state,
    network_risk,
    propose_actions,
    simulate_storm,
)


def test_nuisance_rain_leaves_network_nominal() -> None:
    states = simulate_storm(SCENARIOS["nuisance-rain"])
    assert all(s.status == "nominal" for s in states.values())
    assert network_risk(states) < 10


def test_design_storm_floods_low_lying_assets() -> None:
    states = simulate_storm(SCENARIOS["design-storm-100yr"])
    tunnel = states["tun-river"]
    ridge = states["rte-ridge"]
    assert tunnel.peak_flood_depth_mm > ridge.peak_flood_depth_mm
    assert tunnel.status == "critical"
    assert 0 <= network_risk(states) <= 100


def test_risk_scores_clamped_and_monotonic_with_intensity() -> None:
    mild = simulate_storm(SCENARIOS["nuisance-rain"])
    severe = simulate_storm(SCENARIOS["design-storm-100yr"])
    for asset_id in mild:
        assert 0 <= mild[asset_id].risk_score <= 100
        assert 0 <= severe[asset_id].risk_score <= 100
        assert severe[asset_id].risk_score >= mild[asset_id].risk_score


def test_cascade_raises_risk_for_drainage_dependents() -> None:
    """An asset downstream of an overwhelmed drain must flood deeper than the
    identical asset with the dependency removed."""
    from dataclasses import replace

    detached = tuple(
        replace(a, depends_on=()) if a.asset_id == "stn-harborfront" else a
        for a in DEFAULT_NETWORK
    )
    with_dep = simulate_storm(SCENARIOS["cloudburst-2h"], DEFAULT_NETWORK)
    without_dep = simulate_storm(SCENARIOS["cloudburst-2h"], detached)
    assert with_dep["drn-canal"].peak_flood_depth_mm > 0, "cloudburst must overwhelm the canal drain"
    assert (
        with_dep["stn-harborfront"].peak_flood_depth_mm
        > without_dep["stn-harborfront"].peak_flood_depth_mm
    )


def test_protective_closures_always_require_approval() -> None:
    states = simulate_storm(SCENARIOS["design-storm-100yr"])
    proposals = propose_actions(states)
    assert proposals, "a 100-year storm must produce proposals"
    for p in proposals:
        if p.tier in ("protective_closure", "service_adjustment"):
            assert p.approval_required, f"{p.action} on {p.asset_id} must require approval"
        if p.tier == "advisory":
            assert not p.approval_required


def test_twin_state_is_json_serializable_and_complete() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    state = build_twin_state(SCENARIOS["hurricane-remnant-12h"], now=now)
    payload = json.loads(json.dumps(state))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["generated_at"] == "2026-07-18T12:00:00+00:00"
    assert len(payload["assets"]) == len(DEFAULT_NETWORK)
    assert payload["governance"]["approval_required_tiers"] == [
        "service_adjustment",
        "protective_closure",
    ]
    for asset in payload["assets"]:
        assert set(asset) >= {"id", "name", "kind", "risk_score", "status", "flood_series_mm"}


def test_simulation_is_deterministic() -> None:
    a = build_twin_state(SCENARIOS["cloudburst-2h"], now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    b = build_twin_state(SCENARIOS["cloudburst-2h"], now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert a == b
