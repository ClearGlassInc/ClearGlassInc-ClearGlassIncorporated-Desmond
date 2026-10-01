# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Forensic report generator.

Fourteen sections in a fixed order. Every line is typed:

    OBSERVATION      what the bytes, metadata or records contain
    INTERPRETATION   what an analyzer or rule makes of an observation
    CONCLUSION       a status the rules assign, with its human-review state

Engine-authored text passes a language guard that refuses false certainty
("is fake", "proves authentic", "100% accurate" and similar). User-supplied
text (claims, labels, reviewer notes) is quoted and exempt, because the
report must be able to quote a claim it does not endorse.

`report_sha256` covers sections 1-13 and the provenance chain as it stood
before the REPORTED record, which then commits to that hash.
"""
from __future__ import annotations

import re

from . import vocab
from .canonical import digest
from .provenance import ProvenanceLedger, verify_records
from .timeline import fmt_ms

OBS, INT, CON = "OBSERVATION", "INTERPRETATION", "CONCLUSION"

SECTIONS = (
    "Executive Summary", "Evidence Inventory", "Acquisition Details", "Cryptographic Hashes",
    "Provenance", "Timeline", "Detected Indicators", "Corroboration", "Contradictions",
    "AI Analysis", "Human Review", "Limitations", "Final Evidence Status", "Audit Trail",
)

FORBIDDEN = (
    r"\b(?:is|are|was|were)\s+(?:definitely\s+|certainly\s+|clearly\s+)?(?:a\s+)?fake\b",
    r"\b(?:is|are)\s+(?:definitely\s+|certainly\s+)?(?:authentic|genuine|real|true)\b",
    r"\bprove[sn]?\s+(?:that\s+)?(?:the\s+)?(?:\w+\s+)?(?:is|are)\s+(?:authentic|genuine|fake|real)",
    r"\b100\s*%\s*(?:accurate|certain|reliable)",
    r"\bguarantee[sd]?\b",
    r"\binfallibl[ey]\b",
    r"\bdetects?\s+all\b",
    r"\bundeniabl[ey]\b",
    r"\bdefinitive(?:ly)?\s+(?:fake|authentic|proof)",
)
_FORBIDDEN_RE = [re.compile(p, re.I) for p in FORBIDDEN]


class LanguageError(ValueError):
    pass


def check_language(text: str) -> list[str]:
    return [m.group(0) for rx in _FORBIDDEN_RE for m in rx.finditer(text)]


# Placeholders that carry user-supplied text (labels, claims, notes, metadata
# values, ids). They are masked before the guard runs; everything else in a
# statement is engine-authored and must pass it.
USER_KEYS = frozenset({"id", "label", "claim", "by", "at", "d", "chain", "t", "a", "b", "fid",
                       "ev", "val", "e", "rule", "run", "who", "note", "sub", "actor", "detail",
                       "r_user"})


def _s(statement_kind: str, template: str, **values) -> dict:
    kind = statement_kind
    if kind not in vocab.STATEMENT_KINDS:
        raise ValueError(kind)
    masked = template.format(**{k: ("\u2026" if k in USER_KEYS else str(v))
                                for k, v in values.items()})
    bad = check_language(masked)
    if bad:
        raise LanguageError(f"engine text makes a false-certainty claim: {bad}")
    return {"kind": kind, "text": template.format(**{k: str(v) for k, v in values.items()})}


def build_report(result: dict, generated_at: str | None = None) -> dict:
    # Default to the latest time already in the record, so a regenerated report
    # is byte-identical and never predates the reviews it reports.
    at = generated_at or max([result["analysis_at"]]
                             + [r["at"] for r in result["reviews"]["records"]])
    ev = result["evidence"]
    S: dict[str, list[dict]] = {name: [] for name in SECTIONS}

    # 1. Executive summary
    ex = S["Executive Summary"]
    if result["demonstration"]:
        ex.append(_s(OBS, "{label}: every item in this case is synthetic.", label=vocab.DEMO_LABEL))
    ex.append(_s(OBS, "{n} evidence item(s) in {g} independence group(s).",
                 n=len(ev), g=result["summary"]["independent_groups"]))
    ex.append(_s(INT, "{statement}", statement=result["summary"]["statement"]))
    if result["claim"]:
        ex.append(_s(OBS, "Claim examined: “{claim}”", claim=result["claim"]["claim"]))
        ex.append(_s(CON, "Claim assessment: {v} (human review: {r}).",
                     v=result["claim"]["verdict"], r=result["claim"]["review"]["state"]))
    ex.append(_s(OBS, "{d}", d=vocab.DISCLAIMER))

    # 2-4. Inventory, acquisition, hashes
    for e in ev:
        S["Evidence Inventory"].append(_s(
            OBS, "{id} — {label}: {kind} {stype}, {mime}, {size} bytes, group {g}.",
            id=e["evidence_id"], label=e["label"], kind=e["object_kind"].lower(),
            stype=e["source_type"], mime=e["mime_sniffed"], size=e["size_bytes"], g=e["group"]))
        S["Acquisition Details"].append(_s(
            OBS, "{id} acquired {at} by {by} via {method}; processing boundary {b}.",
            id=e["evidence_id"], at=e["acquired_at"], by=e["acquired_by"],
            method=e["acquisition_method"], b=e["processing_boundary"]))
        if e["mime_declared"] and e["mime_declared"] != e["mime_sniffed"]:
            S["Acquisition Details"].append(_s(
                OBS, "{id} was declared as {d}; its bytes identify it as {m}.",
                id=e["evidence_id"], d=e["mime_declared"], m=e["mime_sniffed"]))
        S["Cryptographic Hashes"].append(_s(
            OBS, "{id} SHA-256 {h}; custody comparison {i} ({state}).", id=e["evidence_id"],
            h=e["content_sha256"], i=e["integrity"], state=e["integrity_state"]))
    S["Cryptographic Hashes"].append(_s(INT, "{n}", n=vocab.CRYPTO_NOTE))

    # 5. Provenance
    prov = result["provenance"]
    S["Provenance"].append(_s(
        OBS, "Provenance ledger: {n} hash-chained record(s); chain verification {ok}.",
        n=len(prov["records"]), ok="passed" if prov["verified"] else
        f"FAILED at record {prov['first_bad_seq']}"))
    for e in ev:
        if len(e["lineage"]) > 1:
            S["Provenance"].append(_s(OBS, "{id} lineage: {chain}; transformation: {t}.",
                                      id=e["evidence_id"], chain=" → ".join(e["lineage"]),
                                      t=e["transformation"] or "not stated"))
    for rel in result["correlation"]["relations"]:
        S["Provenance"].append(_s(INT, "{a} and {b}: {r}; they count as one source.",
                                  a=rel["a"], b=rel["b"], r=rel["reason"]))
    for pc in result["correlation"]["provenance_conflicts"]:
        S["Provenance"].append(_s(INT, "{id}: {issue}.", id=pc["evidence_id"],
                                  issue=pc["issue"]))

    # 6. Timeline
    for eid, tl in sorted(result["timelines"].items()):
        fps = f"{tl['fps_x100'] // 100}.{tl['fps_x100'] % 100:02d}"
        S["Timeline"].append(_s(OBS, "{id}: nominal {fps} fps over {n} frame interval(s).",
                                id=eid, fps=fps, n=tl["intervals"]))
        for seg in tl["segments"]:
            S["Timeline"].append(_s(INT, "{id} {a}–{b} {label}: {reason}.", id=eid,
                                    a=fmt_ms(seg["start_ms"]), b=fmt_ms(seg["end_ms"]),
                                    label=seg["label"], reason=seg["reason"]))
    if not result["timelines"]:
        S["Timeline"].append(_s(OBS, "No frame-timed media in this case."))

    # 7. Indicators
    for ind in result["indicators"]:
        S["Detected Indicators"].append(_s(
            INT, "{fid} [{state}, confidence {c}, review {r}]: {title}. Evidence: {ev}. "
            "Method: {m}. Other explanations: {alt}. Limitation: {lim}",
            fid=ind["finding_id"], state=ind["state"], c=ind["confidence"],
            r=ind["resolution"], title=ind["title"], ev=ind["evidence"], m=ind["method"],
            alt="; ".join(ind["alternatives"]), lim=ind["limitation"]))
    if not result["indicators"]:
        S["Detected Indicators"].append(_s(INT, "{msg}", msg=vocab.NO_INDICATORS))

    # 8-9. Corroboration and contradictions
    corr = result["correlation"]
    S["Corroboration"].append(_s(
        OBS, "Independent pairs agreeing: {a}; conflicting: {c}; dependent pairs not counted: {d}.",
        a=corr["summary"]["agreeing"], c=corr["summary"]["conflicting"],
        d=corr["summary"]["dependent"]))
    if result["claim"]:
        for p in result["claim"]["propositions"]:
            S["Corroboration"].append(_s(
                INT, "{id} {dim} “{val}”: {v} (confidence {c}); {rule}.", id=p["id"],
                dim=p["dimension"], val=(p["value"] if isinstance(p["value"], str) else
                                         " before ".join(p["value"])) or "implicit",
                v=p["verdict"], c=p["confidence"], rule=p["rule"]))
            for x in p["conflicting"]:
                S["Contradictions"].append(_s(
                    INT, "{id} is contradicted by {e} ({val}; basis: {b}).", id=p["id"],
                    e=x["evidence_id"] or x["group"], val=x["value"], b=x["basis"]))
    for row in result["consistency"]:
        S["Corroboration"].append(_s(INT, "Consistency {d}: {s}, confidence {c}.",
                                     d=row["dimension"], s=row["status"], c=row["confidence"]))
    bif = result["bifocal"]
    S["Corroboration"].append(_s(
        INT, "Bifocal verification: coverage {cov}, score {score}. {disc}", cov=bif["coverage"],
        score="not reported" if bif["score"] is None else f"{bif['score']}",
        disc=vocab.BIFOCAL_DISCLAIMER))
    for chk in bif["checks"]:
        if chk["result"] != "AGREES":
            S["Contradictions"].append(_s(INT, "Bifocal {chk}: {r} — {d}.",
                                          chk=chk["check"], r=chk["result"], d=chk["detail"]))
    for tc in corr["temporal_conflicts"]:
        S["Contradictions"].append(_s(INT, "Time conflict between {a} and {b}.",
                                      a=tc["a"], b=tc["b"]))
    if not S["Contradictions"]:
        S["Contradictions"].append(_s(OBS, "No contradictions found by the available rules."))

    # 10. AI analysis
    S["AI Analysis"].append(_s(OBS, "{n}", n=result["external_ai"]["note"]))
    for run in result["ai_audit"]:
        S["AI Analysis"].append(_s(
            OBS, "{run}: {an} ({model}), input {i}, output {o}, at {at}, analyst {who}, highest "
            "indicator confidence {c}, human review {h}.", run=run["run_id"], an=run["analyzer"],
            model=run["model"], i=run["input_sha256"][:16] + "…",
            o=run["output_sha256"][:16] + "…", at=run["at"], who=run["analyst"],
            c=run["confidence"], h=run["human_review_status"]))

    # 11. Human review
    for rec in result["reviews"]["records"]:
        S["Human Review"].append(_s(OBS, "#{n} {action} on {t} by {r_user} at {at}: “{note}”",
                                    n=rec["seq"], action=rec["action"], t=rec["target"],
                                    r_user=rec["reviewer"], at=rec["at"], note=rec["note"]))
    if not result["reviews"]["records"]:
        S["Human Review"].append(_s(OBS, "No human review recorded yet. Nothing in this report is "
                                    "final until a reviewer decides it."))

    # 12. Limitations
    seen = set()
    for eid, a in sorted(result["analyses"].items()):
        for lim in a.get("not_performed", []):
            if lim not in seen:
                seen.add(lim)
                S["Limitations"].append(_s(OBS, "Not performed: {item}.", item=lim))
    S["Limitations"].append(_s(INT, "Metadata is unsigned and can be rewritten; every metadata "
                               "observation describes the file, not the event."))
    S["Limitations"].append(_s(INT, "Indicators mark where to look. Their absence does not "
                               "establish authenticity."))

    # 13. Final status
    for e in ev:
        S["Final Evidence Status"].append(_s(
            CON, "{id}: {final} (analysis proposed {p}: {rule}; review {r}).", id=e["evidence_id"],
            final=e["final_status"], p=e["proposed_status"], rule=e["status_rule"],
            r=e["review"]["state"]))
    if result["claim"]:
        S["Final Evidence Status"].append(_s(CON, "Claim: {v}.", v=result["claim"]["final_verdict"]))

    body = {"case_id": result["case_id"], "sections": [
        {"title": t, "statements": S[t]} for t in SECTIONS[:-1]],
        "provenance_head": prov["head"]}
    report_sha = digest(body)
    ok, _ = verify_records(prov["records"])
    ledger = ProvenanceLedger()
    for rec in prov["records"]:
        ledger.append(rec["event"], rec["subject_id"], actor=rec["actor"], at=rec["at"],
                      parent_ids=tuple(rec["parent_ids"]), detail=rec["detail"])
    reported = ledger.append("REPORTED", result["case_id"] or "case", actor="report-generator",
                             at=at, detail={"report_sha256": report_sha})
    trail = S["Audit Trail"]
    for rec in ledger.records:
        trail.append(_s(OBS, "#{seq} {ev} {sub} by {actor} at {at} — {h}", seq=rec.seq,
                        ev=rec.event, sub=rec.subject_id, actor=rec.actor, at=rec.at,
                        h=rec.record_hash[:16] + "…"))
    trail.append(_s(OBS, "Chain verified before reporting: {ok}. Report SHA-256: {h}.",
                    ok="yes" if ok else "no", h=report_sha))
    return {
        "case_id": result["case_id"],
        "title": result["title"],
        "demonstration": result["demonstration"],
        "generated_at": at,
        "report_sha256": report_sha,
        "reported_record": reported.to_dict(),
        "sections": [{"title": t, "statements": S[t]} for t in SECTIONS],
        "disclaimer": vocab.DISCLAIMER,
    }


def render_markdown(report: dict) -> str:
    lines = [f"# ClearGlass Truth Forensics Report — {report['case_id']}", ""]
    if report["demonstration"]:
        lines += [f"> **{vocab.DEMO_LABEL}**", ""]
    lines += [f"_{report['title']}_" if report["title"] else "",
              f"Generated {report['generated_at']} · report SHA-256 `{report['report_sha256']}`",
              "", f"> {report['disclaimer']}", ""]
    for n, sec in enumerate(report["sections"], start=1):
        lines.append(f"## {n}. {sec['title']}")
        lines.append("")
        for st in sec["statements"]:
            lines.append(f"- **[{st['kind']}]** {st['text']}")
        lines.append("")
    return "\n".join(lines)
