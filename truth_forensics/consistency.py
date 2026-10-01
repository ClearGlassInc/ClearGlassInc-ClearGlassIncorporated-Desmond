# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Consistency Engine: WHO / WHAT / WHEN / WHERE / HOW / SOURCE /
PROVENANCE tested against the evidence, one row per dimension.

Each row carries the evidence ids behind it, a status in the claim-verdict
vocabulary, a confidence label and the rule that produced both. Confidence
comes from the assessment rules in `claims.py`, never from a model score:

    HIGH      supported by 3+ independent groups, none carrying anomalies
    MODERATE  supported by 2+ groups, or by 3+ with caveats
    LOW       single-source support, or any conflict
    NONE      no evidence addresses the dimension
"""
from __future__ import annotations

from . import vocab
from .claims import combine
from .correlation import CONFLICTS, compare

ROWS = (
    ("WHO", ("identity",)),
    ("WHAT", ("event",)),
    ("WHEN", ("time",)),
    ("WHERE", ("location",)),
    ("SEQUENCE", ("sequence",)),
    ("HOW", ("device",)),
    ("SOURCE", ("source",)),
    ("PROVENANCE", ("provenance",)),
)
RANK = {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}


def matrix(assessment: dict, ctx: dict) -> list[dict]:
    props = assessment["propositions"]
    rows = []
    for label, dims in ROWS:
        chosen = [p for p in props if p["dimension"] in dims]
        if label == "HOW":
            rows.append(_how_row(ctx))
            continue
        if not chosen:
            if label == "SEQUENCE":
                continue
            rows.append({"dimension": label, "evidence": [], "status": vocab.UNVERIFIED,
                         "confidence": "NONE", "rationale": "the claim makes no testable "
                         "statement on this dimension"})
            continue
        ids = sorted({x["evidence_id"] for p in chosen for x in p["agreeing"] + p["conflicting"]
                      if x["evidence_id"]})
        status = combine([p["verdict"] for p in chosen])
        confidence = min((p["confidence"] for p in chosen), key=lambda c: RANK[c])
        rationale = "; ".join(f"{p['id']} {p['verdict']}: {p['rule']}" for p in chosen)
        rows.append({"dimension": label, "evidence": ids, "status": status,
                     "confidence": confidence, "rationale": rationale})
    return rows


def _how_row(ctx: dict) -> dict:
    """Capture method: do independent device observations agree with each other?"""
    obs = []
    for e in ctx["evidence"]:
        eid = e["evidence_id"]
        if eid in ctx.get("excluded", {}):
            continue
        for o in ctx["observations"].get(eid, []):
            if o["dimension"] == "device":
                obs.append((eid, o["value"]))
    if not obs:
        return {"dimension": "HOW", "evidence": [], "status": vocab.UNVERIFIED,
                "confidence": "NONE", "rationale": "no capture-device observation in any item"}
    conflicts = []
    for i, (a, va) in enumerate(obs):
        for b, vb in obs[i + 1:]:
            same_group = ctx["membership"][a] == ctx["membership"][b]
            if not same_group and compare("device", va, vb, ctx["tolerances"]) == CONFLICTS:
                conflicts.append(f"{a} vs {b}")
    ids = sorted({a for a, _ in obs})
    if conflicts:
        return {"dimension": "HOW", "evidence": ids, "status": vocab.INCONCLUSIVE,
                "confidence": "LOW", "rationale": "device observations conflict: "
                + ", ".join(conflicts)}
    return {"dimension": "HOW", "evidence": ids, "status": vocab.PARTIALLY_SUPPORTED,
            "confidence": "LOW", "rationale": "device named in metadata or channel records; "
            "unsigned, so it describes the file, not the capture"}
