# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH reference constellation — the deployment the command surface renders.

A deterministic, offline lattice used three ways: as the fixture the CI gate
exercises, as the source of the operator feed at ``data/xenolith/lattice.json``,
and as the worked example of how the pieces fit together.

Everything here is synthetic and self-contained. No network, no credentials, no
external feeds — the connectors return fixed observations, so the same input
always produces the same governance decisions and the same feed can be diffed
between runs.
"""
from __future__ import annotations

import time
from typing import Any

from .constants import Domain
from .executive import TaskSpec
from .fusion import Connector, Observation
from .lattice import ExecutionContext, Lattice

#: The named agents of the reference deployment: codename → (domain, role,
#: mission scope, permissions). Codenames are reserved slots in the ClearGlass
#: namespace, consistent with the registry on `intelligence-platform.html`.
CONSTELLATION: dict[str, tuple[Domain, str, str, tuple[str, ...]]] = {
    "ORACLE": (
        Domain.EXECUTIVE,
        "Executive reasoning nucleus",
        "Translate objectives into policy-constrained missions",
        ("executive.command", "intel.read", "telemetry.read", "agent.delegate"),
    ),
    "MERIDIAN": (
        Domain.INTELLIGENCE,
        "Fusion and correlation",
        "Turn observations into intelligence packets",
        ("intel.read", "intel.ingest", "intel.analyze", "intel.publish", "graph.write"),
    ),
    "PRISM": (
        Domain.INTELLIGENCE,
        "Entity resolution and provenance",
        "Maintain the knowledge graph and contradiction record",
        ("intel.read", "graph.write"),
    ),
    "BASTION": (
        Domain.CYBERSECURITY,
        "Containment and response",
        "Detect, contain and preserve evidence",
        ("cyber.respond", "cyber.forensics", "intel.read"),
    ),
    "IRONGATE": (
        Domain.CYBERSECURITY,
        "Zero-trust enforcement",
        "Enforce segmentation and access policy",
        ("cyber.respond", "telemetry.read"),
    ),
    "WATCHTOWER": (
        Domain.THREAT_INTEL,
        "Adversary surveillance",
        "Track actors, exposures and emerging attack surface",
        ("threat.analyze", "threat.curate", "intel.read"),
    ),
    "DEEPTRACE": (
        Domain.THREAT_INTEL,
        "Signal correlation",
        "Correlate external threat data with internal telemetry",
        ("threat.analyze", "intel.read", "telemetry.read"),
    ),
    "PULSE": (
        Domain.OPERATIONS,
        "Telemetry and observability",
        "Metrics, traces and anomaly surfacing",
        ("telemetry.read", "intel.read"),
    ),
    "CATALYST": (
        Domain.AUTONOMY,
        "Workflow execution",
        "Run governed workflows and collapse sub-agent results",
        ("agent.delegate", "intel.read", "intel.ingest"),
    ),
}

SPONSOR = "ClearGlass Operations"

_FEED_ALPHA = (
    "Repeated authentication failures from 198.51.100.24 against the edge gateway, "
    "followed by a successful session. Pattern matches CVE-2026-10514 exploitation.",
    "Outbound beacon observed to updates.cdn-delivery.example every 300s from the same "
    "segment that contacted 198.51.100.24.",
)

_FEED_BRAVO = (
    "Threat feed: 198.51.100.24 attributed to a commodity access broker; recent "
    "activity targets edge gateways via CVE-2026-10514.",
    "Newly registered domain updates.cdn-delivery.example resolves to infrastructure "
    "reused across three unrelated intrusions this quarter.",
)

_FEED_CHARLIE = (
    "Procurement mailbox reported an invoice-themed lure from billing@cdn-delivery.example "
    "with a password-protected attachment.",
)


def _connector(name: str, lines: tuple[str, ...], reliability: float, domain: str) -> Connector:
    base = time.time() - 5400

    def fetch() -> list[Observation]:
        return [
            Observation(source=name, content=line, ts=base + (index * 900))
            for index, line in enumerate(lines)
        ]

    return Connector(name=name, fetch=fetch, reliability=reliability, domain=domain)


def build(seed_traffic: bool = True) -> Lattice:
    """Assemble the reference lattice.

    With ``seed_traffic`` the lattice also runs a representative cycle: fuse
    three feeds, plan a containment mission, and submit one low-risk and one
    high-risk action so the governance queue is non-empty and the command
    surface has something real to render.
    """
    lattice = Lattice()

    for codename, (domain, role, scope, permissions) in CONSTELLATION.items():
        lattice.enlist(
            codename=codename,
            domain=domain,
            role=role,
            mission_scope=scope,
            sponsor=SPONSOR,
            permissions=permissions,
        )
        lattice.registry.heartbeat(codename, health=0.97 if domain is Domain.EXECUTIVE else 0.93)

    # Cross-domain read grants: fusion may read what threat-intel remembered,
    # and the executive may read everything. Writes stay subtree-confined.
    lattice.memory.grant_read("threat-intel/WATCHTOWER", "intelligence/MERIDIAN")
    for domain in Domain:
        lattice.memory.grant_read(domain.value, "executive/ORACLE")

    _register_executors(lattice)

    if not seed_traffic:
        return lattice

    lattice.connect(_connector("edge-telemetry", _FEED_ALPHA, 0.82, "cybersecurity"))
    lattice.connect(_connector("threat-exchange", _FEED_BRAVO, 0.74, "threat-intel"))
    lattice.connect(_connector("reported-mail", _FEED_CHARLIE, 0.55, "operations"))
    lattice.fusion.collect()

    for packet in lattice.fusion.packets():
        lattice.memory.write(
            actor_partition="intelligence/MERIDIAN",
            key=packet.packet_id,
            value={"headline": packet.headline, "confidence": packet.confidence},
            author="MERIDIAN",
            confidence=packet.confidence,
        )

    lattice.submit("MERIDIAN", "intel.correlate", {"clusters": len(lattice.fusion.cluster())})
    lattice.submit(
        "WATCHTOWER",
        "threat.watchlist_add",
        {"indicator": "ipv4:198.51.100.24", "reason": "access broker infrastructure"},
    )
    lattice.submit(
        "BASTION",
        "cyber.contain",
        {"asset": "edge-gateway-01", "method": "network isolation"},
        targets=("edge-gateway-01",),
    )

    objective = lattice.declare(
        "Contain the edge-gateway intrusion and confirm no lateral movement",
        value=88,
        deadline=time.time() + 21600,
    )
    lattice.plan(
        objective,
        [
            TaskSpec(
                action="cyber.forensic_capture",
                domain=Domain.CYBERSECURITY,
                summary="Capture volatile evidence from edge-gateway-01",
                assigned_to="BASTION",
                targets=("edge-gateway-01",),
            ),
            TaskSpec(
                action="intel.correlate",
                domain=Domain.INTELLIGENCE,
                summary="Correlate gateway telemetry against the broker profile",
                assigned_to="MERIDIAN",
            ),
            TaskSpec(
                action="cyber.contain",
                domain=Domain.CYBERSECURITY,
                summary="Isolate edge-gateway-01 pending eradication",
                assigned_to="BASTION",
                targets=("edge-gateway-01",),
            ),
            TaskSpec(
                action="threat.watchlist_add",
                domain=Domain.THREAT_INTEL,
                summary="Watchlist the broker infrastructure reuse pattern",
                assigned_to="WATCHTOWER",
            ),
            TaskSpec(
                action="outbound.notify",
                domain=Domain.OPERATIONS,
                summary="Notify the affected business unit once contained",
                assigned_to="PULSE",
                targets=("business-unit-ops",),
            ),
        ],
    )

    for series, values in (
        ("auth.failures", (4, 5, 3, 6, 4, 5, 4, 5, 61)),
        ("egress.mb", (12, 11, 13, 12, 14, 12, 13, 12, 12)),
    ):
        for value in values:
            anomaly = lattice.anomalies.observe(series, value)
            lattice.metrics.observe(series, value)
            if anomaly is not None:
                lattice.bus.emit(
                    "telemetry.anomaly", source="PULSE", payload=anomaly.as_dict()
                )

    return lattice


def _register_executors(lattice: Lattice) -> None:
    """Bind the reference side effects.

    Each one runs *after* the gate has cleared it, which is why they can be
    this direct — the authority question is already settled.
    """

    def contain(ctx: ExecutionContext) -> dict[str, Any]:
        asset = str(ctx.payload.get("asset", "unknown"))
        ctx.lattice.graph.upsert_entity(f"asset:{asset}", kind="asset", labels={"contained"})
        ctx.lattice.graph.assert_fact(
            subject=f"asset:{asset}",
            predicate="containment_state",
            value="isolated",
            source=ctx.actor,
            confidence=1.0,
        )
        return {"asset": asset, "state": "isolated"}

    def watchlist(ctx: ExecutionContext) -> dict[str, Any]:
        indicator = str(ctx.payload.get("indicator", ""))
        ctx.lattice.graph.upsert_entity(indicator or "indicator:unknown", kind="indicator", labels={"watchlist"})
        return {"indicator": indicator, "state": "watchlisted"}

    def correlate(ctx: ExecutionContext) -> dict[str, Any]:
        packets = ctx.lattice.fusion.packets()
        return {"packets": len(packets), "top": packets[0].packet_id if packets else None}

    lattice.register_executor("cyber.contain", contain)
    lattice.register_executor("threat.watchlist_add", watchlist)
    lattice.register_executor("intel.correlate", correlate)
