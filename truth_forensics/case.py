# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Case pipeline: SOURCE -> ACQUISITION -> HASH -> PROVENANCE -> METADATA ->
CONTENT ANALYSIS -> TEMPORAL ANALYSIS -> CROSS-SOURCE CORRELATION ->
MANIPULATION INDICATORS -> CONFIDENCE ASSESSMENT -> EVIDENCE GRAPH ->
AUDIT RECORD -> HUMAN REVIEW.

Two phases, so a reviewer's decision re-derives statuses without
re-analysing any bytes:

    analyze_evidence(case, files)      per-item analyzers (the expensive part)
    assess_case(case, analyzed, ...)   correlation, claims, bifocal, graph,
                                       statuses, audit trail (cheap, pure)

`run_case` does both. Output contains no floats and, apart from the
`telemetry` block, no wall-clock values, so the same inputs give the same
bytes; `assets/js/truth-forensics-engine.js` is held to that output by
`tests/test_truth_forensics_parity.py`.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from . import audio, bifocal, claims, consistency, correlation, events, graph, image, intake
from . import timeline, video, vocab
from .canonical import digest, pct
from .indicators import Indicator, assign_finding_ids
from .provenance import ProvenanceLedger
from .review import ReviewLog, final_status


class CaseError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def analyze_item(record: intake.EvidenceRecord, data: bytes | None) -> dict:
    """Dispatch by sniffed type. An analyzer crash is contained and reported."""
    mime = record.mime_sniffed
    try:
        if record.processing_boundary == "HASH_ONLY" or data is None:
            result = {"analyzer": "boundary@" + vocab.ENGINE_VERSION, "metadata": {},
                      "indicators": [], "observations": [],
                      "not_performed": [f"{record.processing_boundary}: {mime} is hashed and "
                                        "recorded but never parsed, decompressed or executed"]}
        elif record.processing_boundary == "REFERENCE_ONLY":
            result = {"analyzer": "reference@" + vocab.ENGINE_VERSION, "metadata": {},
                      "indicators": [], "observations": [],
                      "not_performed": ["URL content was not fetched or acquired"]}
        elif mime.startswith("image/"):
            result = image.analyze_image(data, mime)
        elif mime in ("video/mp4", "video/quicktime", "audio/mp4"):
            result = video.analyze_video(data, mime)
        elif mime.startswith("audio/") or mime == "application/ogg":
            result = audio.analyze_audio(data, mime)
        elif mime == "application/json":
            result = events.analyze_event(data)
        elif mime == "text/plain":
            result = events.analyze_text(data)
        else:
            result = {"analyzer": "none@" + vocab.ENGINE_VERSION, "metadata": {},
                      "indicators": [], "observations": [],
                      "not_performed": [f"No analyzer for {mime}"]}
    except Exception:  # isolation boundary: one bad file must not stop the case
        result = {"analyzer": "failed@" + vocab.ENGINE_VERSION, "metadata": {},
                  "observations": [], "not_performed": ["analysis aborted"],
                  "indicators": [Indicator(
                      code="CONTAINER.ANALYZER_FAILED", category="CONTAINER",
                      title="Analyzer failed on this item",
                      evidence="the analyzer raised an internal error (details withheld)",
                      method="Analyzer isolation boundary.", confidence="HIGH",
                      limitation="No findings exist for this item; absence of indicators here "
                                 "means nothing.",
                      alternatives=("Malformed or unsupported input", "Analyzer defect"),
                      state=vocab.INCONCLUSIVE, analyzer="case@" + vocab.ENGINE_VERSION)]}
    mismatch = intake.declared_mime_indicator(record)
    inds = ([mismatch] if mismatch else []) + list(result["indicators"])
    result["indicators"] = [i.to_dict() for i in assign_finding_ids(record.evidence_id, inds)]
    for o in result["observations"]:
        o.setdefault("source", "analyzer")
    return result


def _record_for(item: dict, data: bytes, demonstration: bool) -> intake.EvidenceRecord:
    required = ("evidence_id", "label", "acquired_at", "acquired_by")
    missing = [k for k in required if not str(item.get(k, "")).strip()]
    if missing:
        raise CaseError(f"evidence item is missing {', '.join(missing)}")
    return intake.acquire_bytes(
        data, label=item["label"], acquired_at=item["acquired_at"],
        acquired_by=item["acquired_by"], declared_name=item.get("file", ""),
        declared_mime=item.get("declared_mime", ""), evidence_id=item["evidence_id"],
        method=item.get("method", "file"),
        object_kind=item.get("object_kind", vocab.ORIGINAL),
        parent_id=item.get("parent_id", ""), transformation=item.get("transformation", ""),
        upstream_source=item.get("upstream_source", ""), demonstration=demonstration)


def analyze_evidence(case: dict, files: dict[str, bytes]) -> dict:
    """Acquire and analyse every item. `files` maps evidence_id -> bytes."""
    if case.get("schema") != vocab.CASE_SCHEMA:
        raise CaseError(f"case schema must be {vocab.CASE_SCHEMA}")
    items = case.get("evidence")
    if not isinstance(items, list) or not items:
        raise CaseError("case has no evidence")
    ids = [i.get("evidence_id") for i in items]
    if len(set(ids)) != len(ids):
        raise CaseError("evidence ids must be unique")
    demo = bool(case.get("demonstration"))
    records, analyses, telemetry = [], {}, []
    for item in items:
        eid = item.get("evidence_id")
        if eid not in files:
            raise CaseError(f"no content supplied for {eid}")
        record = _record_for(item, files[eid], demo)
        started = time.perf_counter()
        analysis = analyze_item(record, files[eid])
        telemetry.append({"stage": "CONTENT_ANALYSIS", "evidence_id": eid,
                          "size_bytes": record.size_bytes, "analyzer": analysis["analyzer"],
                          "duration_ms": int((time.perf_counter() - started) * 1000),
                          "outcome": "failed" if analysis["analyzer"].startswith("failed@")
                          else "ok"})
        for o in item.get("observations", []):
            if o.get("dimension") and o.get("value"):
                analysis["observations"].append({
                    "dimension": str(o["dimension"]), "value": str(o["value"])[:300],
                    "basis": "analyst: " + str(o.get("basis", "observation"))[:200],
                    "source": "analyst", **({"entity": o["entity"]} if o.get("entity") else {})})
        records.append(record)
        analyses[eid] = analysis
    return {"records": records, "analyses": analyses, "telemetry": telemetry}


def _integrity(records, analyses, case) -> dict[str, str]:
    receipts: dict[str, str] = {}
    for a in analyses.values():
        for entry in a.get("custody", []):
            receipts.setdefault(entry["evidence_id"], entry["sha256"])
    out = {}
    for r in records:
        declared = receipts.get(r.evidence_id)
        out[r.evidence_id] = ("NO_RECORD" if not declared else
                              "MATCH" if declared == r.content_sha256 else "MISMATCH")
    return out


def _channels(case: dict, observations: dict, receipts: dict[str, str]) -> list[dict]:
    out = []
    for ch in case.get("channels", []):
        eid = ch.get("evidence_id", "")
        obs = observations.get(eid, [])
        resolved = {"kind": ch.get("kind"), "evidence_id": eid, "label": ch.get("label", "")}
        tw = next((o["value"] for o in obs if o["dimension"] == "time_window"), "")
        loc = next((o["value"] for o in obs if o["dimension"] == "location"), "")
        if tw:
            resolved["time_window"] = tw
        if loc:
            resolved["location"] = loc
        off = next((o["value"] for o in obs if o["dimension"] == "clock_offset"), None)
        if off is not None:
            resolved["offset_seconds"] = int(off)
        if ch.get("kind") == "PROVENANCE_RECORD":
            primary = next((c.get("evidence_id") for c in case.get("channels", [])
                            if c.get("kind") == "PRIMARY_MEDIA"), "")
            if primary in receipts:
                resolved["declared_sha256"] = receipts[primary]
        out.append(resolved)
    return out


def assess_case(case: dict, analyzed: dict, reviews: list[dict] | None = None,
                claim: str | None = None, at: str | None = None) -> dict:
    records: list[intake.EvidenceRecord] = analyzed["records"]
    analyses: dict = analyzed["analyses"]
    demo = bool(case.get("demonstration"))
    analyst = str(case.get("analyst", "")).strip() or "analyst"
    at = at or case.get("analysis_at") or _now()
    tolerances = {"time_seconds": 120, "location_meters": 250, "clock_seconds": 5,
                  **case.get("tolerances", {})}
    evidence = [r.to_dict() for r in records]
    for e in evidence:
        e["perceptual_hash"] = (analyses[e["evidence_id"]].get("pixels") or {}).get("dhash", "")
    by_id = {e["evidence_id"]: e for e in evidence}

    # PROVENANCE: acquisition and derivation, in case order.
    ledger = ProvenanceLedger()
    for r in records:
        ledger.acquired(r)
        if r.parent_id:
            parent = by_id.get(r.parent_id)
            ledger.derived(r, parent_sha256=parent["content_sha256"] if parent else "")
    for r in records:
        a = analyses[r.evidence_id]
        ledger.append("ANALYZED", r.evidence_id, actor=analyst, at=at, detail={
            "analyzer": a["analyzer"], "output_sha256": digest(a),
            "indicators": len(a["indicators"])})

    # HUMAN REVIEW replay.
    log = ReviewLog(analyst, reviews or [])
    for rec in log.records:
        ledger.append("REVIEWED", rec["target"], actor=rec["reviewer"], at=rec["at"],
                      detail={"action": rec["action"], "review_hash": rec["record_hash"]})
    excluded = {}
    for e in evidence:
        d = log.decision(e["evidence_id"])
        if d["state"] == "DECIDED" and d["action"] == "REJECT":
            excluded[e["evidence_id"]] = f"rejected by {d['reviewer']} at {d['at']}: {d['note']}"

    # MANIPULATION INDICATORS with review resolution.
    indicators = []
    for e in evidence:
        for ind in analyses[e["evidence_id"]]["indicators"]:
            d = log.decision(ind["finding_id"])
            resolution = ("CONFIRMED" if d["action"] == "ACCEPT" else
                          "DISMISSED" if d["action"] == "REJECT" else "OPEN")
            indicators.append({**ind, "evidence_id": e["evidence_id"], "review": d,
                               "resolution": resolution})
    open_by_item: dict[str, list[dict]] = {}
    for ind in indicators:
        if ind["resolution"] != "DISMISSED" and ind["state"] != vocab.NORMAL:
            open_by_item.setdefault(ind["evidence_id"], []).append(ind)

    observations = {e["evidence_id"]: analyses[e["evidence_id"]]["observations"] for e in evidence}
    receipts = {}
    for a in analyses.values():
        for entry in a.get("custody", []):
            receipts.setdefault(entry["evidence_id"], entry["sha256"])
    integrity = _integrity(records, analyses, case)

    # CROSS-SOURCE CORRELATION.
    groups = correlation.independence_groups(evidence)
    membership = groups["membership"]
    active = [e for e in evidence if e["evidence_id"] not in excluded]
    matrix = correlation.corroboration_matrix(active, observations, membership, tolerances)
    provenance_conflicts = []
    for e in evidence:
        if integrity[e["evidence_id"]] == "MISMATCH":
            provenance_conflicts.append({"evidence_id": e["evidence_id"],
                                         "issue": "SHA-256 differs from the custody receipt"})
        if e["parent_id"] and e["parent_id"] not in by_id:
            provenance_conflicts.append({"evidence_id": e["evidence_id"],
                                         "issue": "declared parent is not in the evidence set"})
        if e["provenance_state"] == vocab.PROVENANCE_GAP:
            provenance_conflicts.append({"evidence_id": e["evidence_id"],
                                         "issue": "content not acquired (reference only)"})
    matrix["provenance_conflicts"] = provenance_conflicts
    matrix["groups"] = groups["groups"]
    matrix["relations"] = groups["relations"]

    caveated = {k: [i["finding_id"] for i in v if i["state"] in
                    (vocab.ANOMALY_DETECTED, vocab.PROVENANCE_GAP)] for k, v in open_by_item.items()}
    caveated = {k: v for k, v in caveated.items() if v}
    ctx = {"evidence": evidence, "observations": observations, "membership": membership,
           "excluded": excluded, "caveated": caveated, "integrity": integrity,
           "tolerances": tolerances}

    # CLAIM + CONSISTENCY.
    claim_text = case.get("claim", "") if claim is None else claim
    assessment = claims.verify_claim(claim_text, ctx) if claim_text.strip() else None
    if assessment:
        d = log.decision("CLAIM")
        assessment["review"] = d
        if d["state"] == "PENDING":
            assessment["final_verdict"] = "PENDING_REVIEW"
        elif d["state"] != "DECIDED":
            assessment["final_verdict"] = vocab.INCONCLUSIVE
        else:
            assessment["final_verdict"] = {"ACCEPT": assessment["verdict"],
                                           "REJECT": vocab.UNVERIFIED,
                                           "MARK_INCONCLUSIVE": vocab.INCONCLUSIVE}[d["action"]]
    rows = consistency.matrix(assessment, ctx) if assessment else []

    # BIFOCAL.
    bif = bifocal.verify(_channels(case, observations, receipts), membership,
                         {e["evidence_id"]: e["content_sha256"] for e in evidence}, tolerances)

    # TEMPORAL: rebuild timelines with the sensor window overlaid.
    timelines = _timelines(analyses, case, observations)

    # CONFIDENCE ASSESSMENT: per-item statuses.
    agree_pairs = {p["a"] for p in matrix["pairs"] if p["independent"] and
                   p["relation"] == correlation.AGREES}
    agree_pairs |= {p["b"] for p in matrix["pairs"] if p["independent"] and
                    p["relation"] == correlation.AGREES}
    conflict_items = {x for p in matrix["pairs"] if p["independent"] and
                      p["relation"] in (correlation.CONFLICTS, "MIXED") for x in (p["a"], p["b"])}
    for e in evidence:
        eid = e["evidence_id"]
        opened = open_by_item.get(eid, [])
        proposed, reason = _proposed_status(e, integrity[eid], opened, eid in agree_pairs,
                                            eid in conflict_items)
        d = log.decision(eid)
        e.update({"group": membership[eid], "integrity": integrity[eid],
                  "integrity_state": {"MATCH": vocab.CRYPTOGRAPHICALLY_VERIFIED,
                                      "MISMATCH": vocab.ANOMALY_DETECTED,
                                      "NO_RECORD": vocab.PROVENANCE_GAP
                                      if e["provenance_state"] == vocab.PROVENANCE_GAP
                                      else vocab.REVIEW_REQUIRED}[integrity[eid]],
                  "open_findings": len(opened), "proposed_status": proposed,
                  "status_rule": reason, "review": d,
                  "final_status": final_status(proposed, d, demo),
                  "lineage": ledger.lineage(eid), "excluded": eid in excluded})

    gauges = _gauges(evidence, indicators, assessment, matrix, timelines, excluded, observations)
    g = graph.build(evidence, observations, analyses, assessment, groups)
    ai_audit = [{
        "run_id": f"RUN-{e['evidence_id']}",
        "evidence_id": e["evidence_id"],
        "analyzer": analyses[e["evidence_id"]]["analyzer"],
        "provider": "clearglass-local",
        "model": "deterministic rule set (no machine-learning model)",
        "model_version": analyses[e["evidence_id"]]["analyzer"].split("@")[-1],
        "prompt_template_version": None,
        "input_sha256": e["content_sha256"],
        "output_sha256": digest(analyses[e["evidence_id"]]),
        "at": at,
        "analyst": analyst,
        "confidence": max((i["confidence"] for i in analyses[e["evidence_id"]]["indicators"]),
                          key=lambda c: {"LOW": 1, "MODERATE": 2, "HIGH": 3}[c], default="NONE"),
        "limitations": analyses[e["evidence_id"]].get("not_performed", []),
        "human_review_status": e["review"]["state"],
    } for e in evidence]

    open_count = sum(1 for i in indicators
                     if i["resolution"] != "DISMISSED" and i["state"] != vocab.NORMAL)
    decided = all(e["review"]["state"] == "DECIDED" for e in evidence) and (
        not assessment or assessment["review"]["state"] == "DECIDED")
    ok, bad = ledger.verify()
    rv_ok, rv_bad = log.verify()
    job_history = ["QUEUED", "PROCESSING", "ANALYZING", "REVIEW_REQUIRED"]
    if decided:
        job_history.append("COMPLETE")
    stages = [{"stage": s, "status": "DONE"} for s in vocab.PIPELINE]
    stages[-1]["status"] = "DONE" if decided else "PENDING_HUMAN_REVIEW"
    return {
        "schema": vocab.RESULT_SCHEMA,
        "engine": {"name": vocab.ENGINE_NAME, "version": vocab.ENGINE_VERSION},
        "case_id": case.get("case_id", ""),
        "title": case.get("title", ""),
        "demonstration": demo,
        "label": vocab.DEMO_LABEL if demo else "",
        "disclaimer": vocab.DISCLAIMER,
        "analysis_at": at,
        "analyst": analyst,
        "tolerances": tolerances,
        "job": {"state": job_history[-1], "history": job_history},
        "pipeline": stages,
        "evidence": evidence,
        "analyses": analyses,
        "indicators": indicators,
        "observations": observations,
        "correlation": matrix,
        "claim": assessment,
        "consistency": rows,
        "bifocal": bif,
        "timelines": timelines,
        "integrity_indicators": gauges,
        "graph": g,
        "provenance": {"records": [r.to_dict() for r in ledger.records], "verified": ok,
                       "first_bad_seq": bad, "head": ledger.head},
        "reviews": {"records": log.records, "verified": rv_ok, "first_bad_seq": rv_bad},
        "ai_audit": ai_audit,
        "external_ai": {"enabled": False, "note": "No external AI provider is configured or "
                        "called. An adapter must be explicitly enabled, and every call is then "
                        "recorded in ai_audit with input and output hashes."},
        "summary": {
            "statement": vocab.INDICATORS_FOUND if open_count else vocab.NO_INDICATORS,
            "open_findings": open_count,
            "evidence_items": len(evidence),
            "independent_groups": len(groups["groups"]),
            "claim_verdict": assessment["verdict"] if assessment else None,
            "crypto_note": vocab.CRYPTO_NOTE,
        },
    }


def _proposed_status(e: dict, integrity: str, opened: list[dict], corroborated: bool,
                     conflicted: bool) -> tuple[str, str]:
    if e["provenance_state"] == vocab.PROVENANCE_GAP:
        return vocab.UNVERIFIED, "content not acquired"
    if integrity == "MISMATCH":
        return vocab.UNVERIFIED, "hash differs from the custody receipt"
    if any(i["state"] == vocab.ANOMALY_DETECTED for i in opened):
        return vocab.INCONCLUSIVE, "open anomaly indicators"
    if conflicted:
        return vocab.INCONCLUSIVE, "independent sources conflict with this item"
    review_open = any(i["state"] in (vocab.REVIEW_REQUIRED, vocab.INCONCLUSIVE) for i in opened)
    if integrity == "MATCH":
        return ((vocab.SUPPORTED, "custody hash matches; review indicators open") if review_open
                else (vocab.VERIFIED, "custody hash matches; no open indicators "
                      "(VERIFIED needs a human ACCEPT)"))
    if corroborated:
        return ((vocab.INCONCLUSIVE, "corroborated, but review indicators open") if review_open
                else (vocab.SUPPORTED, "an independent source agrees; no open indicators"))
    return vocab.UNVERIFIED, "no custody record and no independent corroboration"


def _timelines(analyses: dict, case: dict, observations: dict) -> dict:
    out = {}
    primary = next((c.get("evidence_id") for c in case.get("channels", [])
                    if c.get("kind") == "PRIMARY_MEDIA"), "")
    sensor = next((c.get("evidence_id") for c in case.get("channels", [])
                   if c.get("kind") == "INDEPENDENT_SENSOR"), "")
    for eid, a in analyses.items():
        tl = a.get("timeline")
        if not tl:
            continue
        out[eid] = tl
        if eid == primary and sensor:
            pw = next((o["value"] for o in observations.get(eid, [])
                       if o["dimension"] == "time_window"), "")
            sw = next((o["value"] for o in observations.get(sensor, [])
                       if o["dimension"] == "time_window"), "")
            win = _relative_window(pw, sw)
            runs = a.get("frame_runs")
            if win and runs:
                out[eid] = timeline.build([(c, d) for c, d in runs], tl["timescale"], [win])
                out[eid]["corroborated_by"] = sensor
    return out


def _relative_window(primary: str, sensor: str) -> tuple[int, int] | None:
    p = correlation._time_range(primary) if primary else None
    s = correlation._time_range(sensor) if sensor else None
    if not p or not s or p[1] is None or s[1] is None:
        return None
    start, end = max(p[1], s[1]) - p[1], min(p[2], s[2]) - p[1]
    return (start * 1000, end * 1000) if end > start else None


def _gauges(evidence, indicators, assessment, matrix, timelines, excluded, observations) -> dict:
    by_id = {e["evidence_id"]: e for e in evidence}
    open_codes: dict[str, list[dict]] = {}
    for i in indicators:
        if i["resolution"] != "DISMISSED" and i["state"] != vocab.NORMAL:
            open_codes.setdefault(i["evidence_id"], []).append(i)
    active = [e for e in evidence if e["evidence_id"] not in excluded]

    def prov_ok(e: dict, depth: int = 0) -> bool:
        if e["integrity"] == "MATCH":
            return True
        parent = by_id.get(e["parent_id"]) if e["parent_id"] else None
        return bool(parent) and depth < 16 and prov_ok(parent, depth + 1)

    integ = [e for e in active if e["integrity"] != "MISMATCH" and not any(
        i["category"] == "CONTAINER" and i["state"] in (vocab.ANOMALY_DETECTED, vocab.INCONCLUSIVE)
        for i in open_codes.get(e["evidence_id"], []))]
    timed_ids = {e["evidence_id"] for e in active if e["evidence_id"] in timelines or any(
        o["dimension"] in ("time", "time_window") for o in observations.get(e["evidence_id"], []))}
    temporal_conflict = {x for p in matrix["temporal_conflicts"] for x in (p["a"], p["b"])}
    temporal_ok = [eid for eid in timed_ids if eid not in temporal_conflict and not any(
        i["category"] == "TEMPORAL" for i in open_codes.get(eid, []))]
    parsed = [e for e in active if e["processing_boundary"] == "PARSE"]
    meta_ok = [e for e in parsed if not any(
        i["category"] == "METADATA" for i in open_codes.get(e["evidence_id"], []))]
    explicit = [p for p in (assessment or {}).get("propositions", [])
                if not p["implicit"] and p["dimension"] != "source"]
    return {
        "label": "ANALYTICAL INDICATORS",
        "note": "Integer percentages of items or propositions meeting each rule. They are not "
                "truth scores and do not combine into one.",
        "values": {
            "PROVENANCE": pct(sum(1 for e in active if prov_ok(e)), len(active)),
            "INTEGRITY": pct(len(integ), len(active)),
            "CORROBORATION": pct(sum(1 for p in explicit if p["verdict"] == vocab.SUPPORTED),
                                 len(explicit)),
            "TEMPORAL_CONSISTENCY": pct(len(temporal_ok), len(timed_ids)),
            "METADATA_CONSISTENCY": pct(len(meta_ok), len(parsed)),
        },
        "definitions": {
            "PROVENANCE": "items whose hash matches a custody receipt, directly or through a "
                          "recorded parent",
            "INTEGRITY": "items with no custody mismatch and no open container anomaly",
            "CORROBORATION": "claim propositions supported by two or more independent groups",
            "TEMPORAL_CONSISTENCY": "timed items with no open temporal indicator and no "
                                    "independent time conflict",
            "METADATA_CONSISTENCY": "parsed items with no open metadata indicator",
        },
    }


def run_case(case: dict, files: dict[str, bytes], reviews: list[dict] | None = None,
             claim: str | None = None) -> dict:
    analyzed = analyze_evidence(case, files)
    result = assess_case(case, analyzed, reviews or case.get("reviews", []), claim)
    result["telemetry"] = analyzed["telemetry"]
    return result
