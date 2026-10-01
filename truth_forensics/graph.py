# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Evidence Graph.

Nodes: Evidence, Person, Organization, Subject (a non-person subject such as a
vehicle), Device, Location, Event, Timestamp, Source, Claim, Analysis,
Transformation.

Edges: CREATED, CAPTURED_BY, DERIVED_FROM, REFERENCES, CONTRADICTS, SUPPORTS,
OCCURRED_AT, ASSOCIATED_WITH, ANALYZED_BY.

Every edge carries a basis. FACTUAL edges are things the engine itself did or
measured: acquired a file, hashed it, recorded a derivation, ran an analyzer,
found two identical hashes. Everything else (a device named in metadata, a
place an analyst read off a sign, a claim an item supports) is an INFERENCE
and is labelled as one, with the source of the inference beside it.
"""
from __future__ import annotations

from . import vocab

NODE_TYPES = ("Evidence", "Person", "Organization", "Subject", "Device", "Location", "Event",
              "Timestamp", "Source", "Claim", "Analysis", "Transformation")
EDGE_TYPES = ("CREATED", "CAPTURED_BY", "DERIVED_FROM", "REFERENCES", "CONTRADICTS", "SUPPORTS",
              "OCCURRED_AT", "ASSOCIATED_WITH", "ANALYZED_BY")


def _nid(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def build(evidence: list[dict], observations: dict[str, list[dict]],
          analyses: dict[str, dict], assessment: dict | None, groups: dict) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(kind: str, key: str, label: str, **extra) -> str:
        nid = _nid(kind, key)
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": kind, "label": label, **extra}
        return nid

    def edge(src: str, rel: str, dst: str, basis: str, why: str) -> None:
        edges.append({"source": src, "type": rel, "target": dst, "basis": basis, "why": why})

    for e in evidence:
        eid = e["evidence_id"]
        ev = node("Evidence", eid, e.get("label") or eid, sha256=e["content_sha256"],
                  object_kind=e["object_kind"], demonstration=bool(e.get("demonstration")))
        if e.get("upstream_source"):
            src = node("Source", e["upstream_source"], e["upstream_source"])
            edge(ev, "ASSOCIATED_WITH", src, vocab.INFERENCE, "declared upstream source")
        if e.get("parent_id"):
            t = node("Transformation", eid, e.get("transformation") or "declared transformation")
            edge(ev, "DERIVED_FROM", _nid("Evidence", e["parent_id"]), vocab.FACTUAL,
                 "derivation recorded in the provenance ledger")
            edge(t, "CREATED", ev, vocab.FACTUAL, "transformation recorded at acquisition")
        if eid in analyses:
            a = node("Analysis", eid, f"analysis of {eid}",
                     analyzer=analyses[eid].get("analyzer", ""))
            edge(ev, "ANALYZED_BY", a, vocab.FACTUAL, "analyzer run recorded in the audit trail")
        for o in observations.get(eid, []):
            dim, value, basis = o["dimension"], o["value"], o["basis"]
            if dim == "device":
                edge(ev, "CAPTURED_BY", node("Device", value, value), vocab.INFERENCE, basis)
            elif dim == "location":
                edge(ev, "OCCURRED_AT", node("Location", value, value), vocab.INFERENCE, basis)
            elif dim in ("time", "time_window"):
                edge(ev, "OCCURRED_AT", node("Timestamp", value, value), vocab.INFERENCE, basis)
            elif dim == "identity":
                kind = {"person": "Person", "organization": "Organization"}.get(
                    o.get("entity", ""), "Subject")
                edge(node(kind, value, value),
                     "ASSOCIATED_WITH", ev, vocab.INFERENCE, basis)
            elif dim == "event":
                edge(ev, "REFERENCES", node("Event", value, value), vocab.INFERENCE, basis)
    for rel in groups.get("relations", []):
        if rel["reason"] == "DUPLICATE_CONTENT":
            edge(_nid("Evidence", rel["b"]), "DERIVED_FROM", _nid("Evidence", rel["a"]),
                 vocab.FACTUAL, "identical SHA-256: the same bytes")
    if assessment:
        claim = node("Claim", "claim", assessment.get("claim", "claim"),
                     verdict=assessment["verdict"])
        for p in assessment["propositions"]:
            if p["dimension"] == "source":
                for x in p["agreeing"]:
                    edge(claim, "REFERENCES", _nid("Evidence", x["evidence_id"]), vocab.FACTUAL,
                         "the claim names this item")
                continue
            for x in p["agreeing"]:
                if x["evidence_id"]:
                    edge(_nid("Evidence", x["evidence_id"]), "SUPPORTS", claim, vocab.INFERENCE,
                         f"{p['id']} {p['dimension']}: {x['basis']}")
            for x in p["conflicting"]:
                if x["evidence_id"]:
                    edge(_nid("Evidence", x["evidence_id"]), "CONTRADICTS", claim,
                         vocab.INFERENCE, f"{p['id']} {p['dimension']}: {x['basis']}")
    seen = set()
    unique = []
    for e in sorted(edges, key=lambda x: (x["source"], x["type"], x["target"], x["why"])):
        key = (e["source"], e["type"], e["target"], e["why"])
        if key not in seen and e["source"] in nodes and e["target"] in nodes:
            seen.add(key)
            unique.append(e)
    return {"nodes": [nodes[k] for k in sorted(nodes)], "edges": unique,
            "counts": {"factual": sum(1 for e in unique if e["basis"] == vocab.FACTUAL),
                       "inference": sum(1 for e in unique if e["basis"] == vocab.INFERENCE)}}
