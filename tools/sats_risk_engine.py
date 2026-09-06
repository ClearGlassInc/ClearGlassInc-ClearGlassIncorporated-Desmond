#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""SATS — Storm-Adaptive Transit System digital-twin risk engine.

The simulation core behind the ClearGlass SATS digital-twin module
(`sats-digital-twin.html`): a physics-aware, hour-by-hour storm simulation
over a transit network (stations, tunnels, drainage, surface routes) that
produces per-asset flood depth, 0–100 risk scores, and *proposed* operational
actions.

Governance model (mirrors the commerce control plane): the engine never
executes anything. Every proposal is routed by tier —

  - ``advisory``            → safe to auto-publish (passenger guidance, monitoring)
  - ``service_adjustment``  → queue for operator approval (frequency, rerouting)
  - ``protective_closure``  → blocked until a human approves (closures, pump crews)

so an orchestration layer (LangGraph/Temporal agents, or the commerce-style
approvals table) can consume ``build_twin_state()`` as its shared twin state
and enforce read-only analysis → draft → human approval → execution.

stdlib only, fully deterministic — runs in minimal CI environments.

    python3 tools/sats_risk_engine.py --list-scenarios
    python3 tools/sats_risk_engine.py --scenario cloudburst-2h --json
    python3 tools/sats_risk_engine.py --scenario design-storm-100yr --out data/sats/twin_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "sats-twin/1.0"

# --------------------------------------------------------------------------
# Domain model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StormScenario:
    """A design storm: triangular rainfall ramp peaking mid-duration."""

    scenario_id: str
    name: str
    peak_rainfall_mm_per_hr: float
    duration_hours: int
    storm_surge_m: float = 0.0
    wind_kph: float = 0.0

    def rainfall_at(self, hour: int) -> float:
        """Rainfall intensity (mm/hr) at a given hour, triangular profile.

        Sampled at the hour's midpoint so short storms (1–2 h) still deliver
        their ramp instead of landing on the triangle's zero-height feet.
        """
        if hour < 0 or hour >= self.duration_hours:
            return 0.0
        half = self.duration_hours / 2
        distance = abs((hour + 0.5) - half) / half
        return self.peak_rainfall_mm_per_hr * max(0.0, 1.0 - distance)


@dataclass(frozen=True)
class TransitAsset:
    """A node in the transit twin: station, tunnel, drainage, surface route."""

    asset_id: str
    name: str
    kind: str  # station | tunnel | drainage | surface_route
    elevation_m: float
    drainage_capacity_mm_per_hr: float
    criticality: float  # 0..1 network importance
    depends_on: tuple[str, ...] = ()


@dataclass
class AssetState:
    """Simulated end-state of one asset after a storm run."""

    asset: TransitAsset
    peak_flood_depth_mm: float = 0.0
    hours_above_threshold: int = 0
    risk_score: int = 0
    status: str = "nominal"  # nominal | degraded | critical
    flood_series_mm: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class ActionProposal:
    """A proposed operational action. Never executed by this engine."""

    asset_id: str
    action: str
    tier: str  # advisory | service_adjustment | protective_closure
    approval_required: bool
    rationale: str


# --------------------------------------------------------------------------
# Scenario & network libraries
# --------------------------------------------------------------------------

SCENARIOS: dict[str, StormScenario] = {
    s.scenario_id: s
    for s in (
        StormScenario("nuisance-rain", "Nuisance rain", 8.0, 6),
        StormScenario("cloudburst-2h", "2-hour cloudburst", 120.0, 2),
        StormScenario("hurricane-remnant-12h", "Hurricane remnant, 12h", 45.0, 12, storm_surge_m=1.2, wind_kph=95.0),
        StormScenario("design-storm-100yr", "100-year design storm", 90.0, 8, storm_surge_m=1.8, wind_kph=110.0),
    )
}

# A compact demonstration network. Real deployments load this from the asset
# core (Bentley iTwin / Azure DT export) — the simulation is network-agnostic.
DEFAULT_NETWORK: tuple[TransitAsset, ...] = (
    TransitAsset("drn-canal", "Canal Trunk Drain", "drainage", 1.0, 55.0, 0.85),
    TransitAsset("drn-hillside", "Hillside Interceptor", "drainage", 14.0, 75.0, 0.60),
    TransitAsset("stn-harborfront", "Harborfront Station", "station", 2.0, 35.0, 0.95, depends_on=("drn-canal",)),
    TransitAsset("stn-civic", "Civic Center Station", "station", 6.0, 45.0, 0.90, depends_on=("drn-canal",)),
    TransitAsset("stn-uptown", "Uptown Station", "station", 21.0, 50.0, 0.70, depends_on=("drn-hillside",)),
    TransitAsset("tun-river", "River Crossing Tunnel", "tunnel", -8.0, 40.0, 1.00, depends_on=("drn-canal",)),
    TransitAsset("tun-midtown", "Midtown Tunnel", "tunnel", -4.0, 48.0, 0.90, depends_on=("drn-hillside",)),
    TransitAsset("rte-shoreline", "Shoreline Busway", "surface_route", 3.0, 30.0, 0.55),
    TransitAsset("rte-ridge", "Ridge Corridor", "surface_route", 26.0, 40.0, 0.45),
)

# Simulation constants
DEGRADED_DEPTH_MM = 50.0     # platform-edge / roadway ponding
CRITICAL_DEPTH_MM = 200.0    # service-stopping inundation
DRAINDOWN_MM_PER_HR = 25.0   # recession once rainfall drops below capacity
LOW_ELEVATION_M = 5.0        # surge only reaches low-lying assets
SURGE_MM_PER_M = 60.0        # surge loading per metre for low-lying assets
CASCADE_FACTOR = 0.35        # overwhelmed upstream drainage spills downstream


# --------------------------------------------------------------------------
# Simulation core (pure functions)
# --------------------------------------------------------------------------


def simulate_storm(
    scenario: StormScenario,
    network: tuple[TransitAsset, ...] = DEFAULT_NETWORK,
) -> dict[str, AssetState]:
    """Run the hour-by-hour storm over the network. Deterministic."""
    states = {a.asset_id: AssetState(asset=a) for a in network}
    by_id = {a.asset_id: a for a in network}
    depth: dict[str, float] = {a.asset_id: 0.0 for a in network}
    # extra hours after rainfall ends let accumulated water drain down
    for hour in range(scenario.duration_hours + 4):
        rain = scenario.rainfall_at(hour)
        overflow: dict[str, float] = {}
        for asset in network:
            excess = rain - asset.drainage_capacity_mm_per_hr
            if excess > 0:
                depth[asset.asset_id] += excess
                if asset.kind == "drainage":
                    overflow[asset.asset_id] = excess * CASCADE_FACTOR
            else:
                depth[asset.asset_id] = max(0.0, depth[asset.asset_id] - DRAINDOWN_MM_PER_HR)
        # cascade: overwhelmed drainage spills into dependent assets
        for asset in network:
            spill = sum(overflow.get(dep, 0.0) for dep in asset.depends_on if dep in by_id)
            if spill > 0:
                depth[asset.asset_id] += spill
        # storm surge loads low-lying assets while the storm is active
        if rain > 0 and scenario.storm_surge_m > 0:
            for asset in network:
                if asset.elevation_m <= LOW_ELEVATION_M:
                    surge_reach = max(0.0, LOW_ELEVATION_M - asset.elevation_m) / LOW_ELEVATION_M
                    depth[asset.asset_id] += scenario.storm_surge_m * SURGE_MM_PER_M * surge_reach / scenario.duration_hours
        for asset in network:
            st = states[asset.asset_id]
            d = depth[asset.asset_id]
            st.flood_series_mm.append(round(d, 2))
            st.peak_flood_depth_mm = max(st.peak_flood_depth_mm, d)
            if d >= DEGRADED_DEPTH_MM:
                st.hours_above_threshold += 1
    for st in states.values():
        st.risk_score = risk_score(st, scenario)
        st.status = status_for(st.risk_score)
        st.peak_flood_depth_mm = round(st.peak_flood_depth_mm, 2)
    return states


def risk_score(state: AssetState, scenario: StormScenario) -> int:
    """0–100 risk: flood severity × exposure duration × asset criticality."""
    depth_term = min(1.0, state.peak_flood_depth_mm / CRITICAL_DEPTH_MM)
    duration_term = min(1.0, state.hours_above_threshold / max(scenario.duration_hours, 1))
    wind_term = min(1.0, scenario.wind_kph / 150.0) if state.asset.kind == "surface_route" else 0.0
    hazard = 0.6 * depth_term + 0.25 * duration_term + 0.15 * wind_term
    score = 100.0 * hazard * (0.5 + 0.5 * state.asset.criticality)
    return max(0, min(100, round(score)))


def status_for(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 35:
        return "degraded"
    return "nominal"


def propose_actions(states: dict[str, AssetState]) -> list[ActionProposal]:
    """Turn simulated states into governed, tiered action proposals."""
    proposals: list[ActionProposal] = []
    for st in sorted(states.values(), key=lambda s: -s.risk_score):
        a = st.asset
        if st.status == "critical":
            action = {
                "station": "close_station_and_reroute",
                "tunnel": "suspend_tunnel_service",
                "drainage": "dispatch_pump_crew",
                "surface_route": "close_route",
            }[a.kind]
            proposals.append(ActionProposal(
                a.asset_id, action, "protective_closure", True,
                f"risk {st.risk_score}/100, peak flood {st.peak_flood_depth_mm:.0f} mm — service-stopping inundation predicted",
            ))
        elif st.status == "degraded":
            proposals.append(ActionProposal(
                a.asset_id, "reduce_frequency_and_stage_crews", "service_adjustment", True,
                f"risk {st.risk_score}/100 — degraded operation predicted, pre-stage response",
            ))
        elif st.risk_score >= 15:
            proposals.append(ActionProposal(
                a.asset_id, "publish_passenger_advisory", "advisory", False,
                f"risk {st.risk_score}/100 — advise passengers of possible weather delays",
            ))
    return proposals


def network_risk(states: dict[str, AssetState]) -> int:
    """Criticality-weighted network risk, 0–100."""
    total_weight = sum(s.asset.criticality for s in states.values())
    if total_weight == 0:
        return 0
    weighted = sum(s.risk_score * s.asset.criticality for s in states.values())
    return max(0, min(100, round(weighted / total_weight)))


def build_twin_state(
    scenario: StormScenario,
    network: tuple[TransitAsset, ...] = DEFAULT_NETWORK,
    now: datetime | None = None,
) -> dict:
    """Full twin-sync payload: one JSON document a visualization layer
    (Cesium, Omniverse) or agent orchestrator can consume as shared state."""
    states = simulate_storm(scenario, network)
    proposals = propose_actions(states)
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": stamp,
        "scenario": {
            "id": scenario.scenario_id,
            "name": scenario.name,
            "peak_rainfall_mm_per_hr": scenario.peak_rainfall_mm_per_hr,
            "duration_hours": scenario.duration_hours,
            "storm_surge_m": scenario.storm_surge_m,
            "wind_kph": scenario.wind_kph,
        },
        "network_risk": network_risk(states),
        "assets": [
            {
                "id": st.asset.asset_id,
                "name": st.asset.name,
                "kind": st.asset.kind,
                "elevation_m": st.asset.elevation_m,
                "criticality": st.asset.criticality,
                "peak_flood_depth_mm": st.peak_flood_depth_mm,
                "hours_above_threshold": st.hours_above_threshold,
                "risk_score": st.risk_score,
                "status": st.status,
                "flood_series_mm": st.flood_series_mm,
            }
            for st in states.values()
        ],
        "proposals": [
            {
                "asset_id": p.asset_id,
                "action": p.action,
                "tier": p.tier,
                "approval_required": p.approval_required,
                "rationale": p.rationale,
            }
            for p in proposals
        ],
        "governance": {
            "model": "read-only analysis → draft → human approval → execution",
            "auto_executable_tiers": ["advisory"],
            "approval_required_tiers": ["service_adjustment", "protective_closure"],
        },
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SATS digital-twin storm risk engine")
    parser.add_argument("--scenario", default="design-storm-100yr", choices=sorted(SCENARIOS))
    parser.add_argument("--json", action="store_true", help="print twin state as JSON")
    parser.add_argument("--out", type=Path, help="write twin state JSON to a file")
    parser.add_argument("--list-scenarios", action="store_true")
    args = parser.parse_args(argv)

    if args.list_scenarios:
        for s in SCENARIOS.values():
            print(f"{s.scenario_id:24s} {s.name} — peak {s.peak_rainfall_mm_per_hr:.0f} mm/hr over {s.duration_hours}h")
        return 0

    state = build_twin_state(SCENARIOS[args.scenario])
    payload = json.dumps(state, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    if args.json or not args.out:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
