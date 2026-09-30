# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Claim verification: decompose a claim into testable propositions, then
test each against the observations the evidence actually carries.

Decomposition is rule-based and deterministic (patterns for sources, times,
dates, places, subjects and sequence words). It is a starting point for an
analyst, who can edit propositions; it is not language understanding.

Verdict per proposition, counting independence groups rather than files:

    no agreeing and no conflicting group    UNVERIFIED
    conflicting groups only                 CONTRADICTED
    agreeing and conflicting groups         INCONCLUSIVE (corroboration conflict)
    one agreeing group                      PARTIALLY_SUPPORTED (single source)
    two or more agreeing groups             SUPPORTED

A claim is a conjunction: any contradicted proposition contradicts it, any
inconclusive one leaves it inconclusive, and it is SUPPORTED only when every
proposition, including provenance and corroboration, is supported.
"""
from __future__ import annotations

import re

from . import vocab
from .correlation import AGREES, CONFLICTS, compare, content_words

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")
_MONTH_ALT = "|".join(m.capitalize() for m in MONTHS)

TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b")
ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DMY_RE = re.compile(r"\b(\d{1,2})\s+(" + _MONTH_ALT + r")\s+(\d{4})\b")
MDY_RE = re.compile(r"\b(" + _MONTH_ALT + r")\s+(\d{1,2}),?\s+(\d{4})\b")
SOURCE_RE = re.compile(
    r"\b(video|footage|clip|recording|photo|photograph|image|picture|screenshot|audio|"
    r"document|log|timeline|email|post)\s+([A-Za-z0-9][\w-]{0,30})\b", re.I)
EVID_RE = re.compile(r"\bEV-[A-Z0-9-]+\b")
LOC_RE = re.compile(
    r"\b(?:[Aa]t|[Ii]n|[Nn]ear|[Oo]utside|[Ii]nside|[Oo]ut of|[Ff]rom|[Ii]nto)\s+"
    r"((?:the\s+)?[A-Z][\w'-]*(?:\s+(?:[A-Z0-9][\w'-]*|of|and))*)")
IDENT_RE = re.compile(r"\bshows?\s+((?:the\s+)?[A-Z][\w-]*(?:\s+[A-Z0-9][\w-]*)*)")
SEEN_RE = re.compile(r"\b([A-Z][\w-]*(?:\s+[A-Z0-9][\w-]*)+)\s+(?:was|is|were|are)\s+"
                     r"(?:seen|visible|shown|recorded|heard)\b")
SEQ_RE = re.compile(r"^(.*?)\b(before|after|followed by|prior to|then)\b(.*)$", re.I)


def _strip_tail(text: str) -> str:
    text = re.sub(r"\s+(?:of|and)$", "", text.strip())
    return re.sub(r"^the\s+", "", text)


def decompose(claim: str) -> list[dict]:
    """Claim text -> ordered propositions. Pure function of the text."""
    text = " ".join((claim or "").split())[:2000]
    spans: list[tuple[int, int]] = []
    props: list[dict] = []

    def add(dimension: str, value, statement: str, method: str, implicit: bool = False):
        props.append({"id": f"P{len(props) + 1}", "dimension": dimension, "value": value,
                      "text": statement, "method": method, "implicit": implicit})

    for m in SOURCE_RE.finditer(text):
        ident = m.group(2)
        if not (ident[0].isupper() or ident[0].isdigit()):
            continue
        label = f"{m.group(1).capitalize()} {ident}"
        spans.append(m.span())
        add("source", label, f"The source '{label}' is in the evidence set with a hash recorded "
            "at acquisition.", "pattern:source")
    for m in EVID_RE.finditer(text):
        spans.append(m.span())
        add("source", m.group(0), f"Evidence {m.group(0)} is in the evidence set.",
            "pattern:evidence-id")
    subject_end = None
    for rx in (IDENT_RE, SEEN_RE):
        for m in rx.finditer(text):
            who = _strip_tail(m.group(1))
            if who.lower() in MONTHS or not who:
                continue
            spans.append(m.span(1))
            subject_end = m.end(1) if subject_end is None else subject_end
            add("identity", who, f"The subject shown is {who}.", "pattern:subject")
    date = ""
    for rx, order in ((ISO_DATE_RE, "ymd"), (DMY_RE, "dmy"), (MDY_RE, "mdy")):
        m = rx.search(text)
        if m:
            spans.append(m.span())
            if order == "ymd":
                date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            elif order == "dmy":
                date = f"{m.group(3)}-{MONTHS.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}"
            else:
                date = f"{m.group(3)}-{MONTHS.index(m.group(1).lower()) + 1:02d}-{int(m.group(2)):02d}"
            break
    time_hits = list(TIME_RE.finditer(text))
    for m in time_hits:
        spans.append(m.span())
        hh, mm, ss = m.group(1), m.group(2), m.group(3)
        clock = f"{int(hh):02d}:{mm}" + (f":{ss}" if ss else "")
        value = f"{date}T{clock}" if date else clock
        add("time", value, f"The event occurred at {value.replace('T', ' ')}.", "pattern:time")
    if date and not time_hits:
        add("time", date, f"The event occurred on {date}.", "pattern:date")
    locations = []
    for m in LOC_RE.finditer(text):
        place = _strip_tail(m.group(1))
        if not place or place.lower() in MONTHS or any(place.startswith(w) for w in ("EV-",)):
            continue
        if any(a <= m.start(1) < b for a, b in spans):
            continue
        spans.append(m.span())
        locations.append((m.start(), place))
        add("location", place, f"The location is {place}.", "pattern:place")
    seq = SEQ_RE.match(text)
    if seq and seq.group(1).strip() and seq.group(3).strip():
        left, word, right = seq.group(1).strip(" ,."), seq.group(2).lower(), seq.group(3).strip(" ,.")
        first, second = (right, left) if word == "after" else (left, right)
        add("sequence", [first, second], f"'{first}' happened before '{second}'.",
            "pattern:sequence")
    # WHAT: the words between the subject and the next extracted element.
    if subject_end is not None:
        later = [a for a, _ in spans if a >= subject_end]
        stop = min(later) if later else len(text)
        what = text[subject_end:stop].strip(" ,.")
        if len(content_words(what)) >= 2:
            add("event", what, f"The event shown is: {what}.", "pattern:predicate")
    add("provenance", "", "The source evidence has intact provenance: a hash recorded at "
        "acquisition that matches any custody record, and lineage to an original.",
        "implicit", implicit=True)
    add("corroboration", "", "At least two independent sources beyond the claimed source "
        "agree with the claim.", "implicit", implicit=True)
    return props


def verdict_from_counts(agree: int, conflict: int) -> str:
    if agree == 0 and conflict == 0:
        return vocab.UNVERIFIED
    if agree == 0:
        return vocab.CONTRADICTED
    if conflict:
        return vocab.INCONCLUSIVE
    return vocab.SUPPORTED if agree >= 2 else vocab.PARTIALLY_SUPPORTED


def confidence_for(verdict: str, agree: int, conflict: int, caveats: int) -> str:
    if verdict == vocab.UNVERIFIED:
        return "NONE"
    if verdict == vocab.SUPPORTED:
        if agree >= 3 and caveats == 0:
            return "HIGH"
        return "MODERATE"
    if verdict == vocab.CONTRADICTED and conflict >= 2 and caveats == 0:
        return "MODERATE"
    return "LOW"


def combine(verdicts: list[str]) -> str:
    """Conjunction of verdicts."""
    if not verdicts:
        return vocab.UNVERIFIED
    if vocab.CONTRADICTED in verdicts:
        return vocab.CONTRADICTED
    if vocab.INCONCLUSIVE in verdicts:
        return vocab.INCONCLUSIVE
    if all(v == vocab.SUPPORTED for v in verdicts):
        return vocab.SUPPORTED
    if all(v == vocab.UNVERIFIED for v in verdicts):
        return vocab.UNVERIFIED
    return vocab.PARTIALLY_SUPPORTED


def find_sources(label: str, evidence: list[dict]) -> list[dict]:
    want = label.strip().lower()
    return [e for e in evidence
            if e["evidence_id"].lower() == want or e.get("label", "").strip().lower() == want]


def assess(propositions: list[dict], ctx: dict) -> dict:
    """Assess propositions against a case context built by `case.run_case`.

    ctx keys: evidence (list of dicts), observations {id: [obs]}, membership
    {id: group}, excluded {id: reason}, caveated {id: [reasons]}, integrity
    {id: 'MATCH'|'MISMATCH'|'NO_RECORD'}, tolerances.
    """
    evidence = ctx["evidence"]
    excluded = ctx.get("excluded", {})
    membership = ctx["membership"]
    results = []
    referenced: list[dict] = []
    for prop in propositions:
        dim = prop["dimension"]
        res = {**prop, "agreeing": [], "conflicting": [], "excluded": [], "rule": ""}
        if dim == "source":
            found = find_sources(prop["value"], evidence)
            referenced.extend(found)
            if found:
                res["agreeing"] = [{"evidence_id": e["evidence_id"], "value": e["content_sha256"],
                                    "basis": "evidence set; SHA-256 recorded at acquisition",
                                    "group": membership[e["evidence_id"]]} for e in found]
                res["verdict"] = vocab.SUPPORTED
                res["confidence"] = "HIGH"
                res["rule"] = "source present with an acquisition hash"
            else:
                res["verdict"] = vocab.UNVERIFIED
                res["confidence"] = "NONE"
                res["rule"] = "no evidence item carries this label"
            results.append(res)
            continue
        if dim in ("provenance", "corroboration"):
            results.append(res)  # resolved after the explicit propositions
            continue
        agree_groups, conflict_groups = set(), set()
        for e in evidence:
            eid = e["evidence_id"]
            obs_list = [o for o in ctx["observations"].get(eid, [])
                        if o["dimension"] == dim or (dim == "time" and o["dimension"] == "time_window")]
            if not obs_list:
                continue
            if eid in excluded:
                res["excluded"].append({"evidence_id": eid, "reason": excluded[eid]})
                continue
            for o in obs_list:
                rel = compare(dim, prop["value"], o["value"], ctx["tolerances"])
                entry = {"evidence_id": eid, "value": o["value"], "basis": o["basis"],
                         "group": membership[eid]}
                if rel == AGREES:
                    res["agreeing"].append(entry)
                    agree_groups.add(membership[eid])
                elif rel == CONFLICTS:
                    res["conflicting"].append(entry)
                    conflict_groups.add(membership[eid])
        caveats = sorted({x["evidence_id"] for x in res["agreeing"] + res["conflicting"]
                          if ctx.get("caveated", {}).get(x["evidence_id"])})
        res["verdict"] = verdict_from_counts(len(agree_groups), len(conflict_groups))
        res["confidence"] = confidence_for(res["verdict"], len(agree_groups),
                                           len(conflict_groups), len(caveats))
        res["caveats"] = caveats
        res["rule"] = (f"{len(agree_groups)} agreeing and {len(conflict_groups)} conflicting "
                       "independence group(s)")
        results.append(res)

    explicit = [r for r in results if not r["implicit"]]
    # Provenance of the referenced source (or of every item when none is named).
    targets = referenced or [e for e in evidence if e["evidence_id"] not in excluded]
    integrity = ctx.get("integrity", {})
    for res in results:
        if res["dimension"] == "provenance":
            states = {e["evidence_id"]: integrity.get(e["evidence_id"], "NO_RECORD") for e in targets}
            gaps = [e["evidence_id"] for e in targets
                    if e.get("provenance_state") == vocab.PROVENANCE_GAP]
            res["agreeing"] = [{"evidence_id": k, "value": v, "basis": "custody record",
                                "group": membership[k]} for k, v in sorted(states.items())
                               if v == "MATCH"]
            res["conflicting"] = [{"evidence_id": k, "value": v, "basis": "custody record",
                                   "group": membership[k]} for k, v in sorted(states.items())
                                  if v == "MISMATCH"]
            if not targets:
                res["verdict"], res["rule"] = vocab.UNVERIFIED, "no evidence to assess"
            elif res["conflicting"]:
                res["verdict"], res["rule"] = vocab.CONTRADICTED, "hash differs from custody record"
            elif gaps:
                res["verdict"], res["rule"] = vocab.INCONCLUSIVE, "content not acquired: " + \
                    ", ".join(gaps)
            elif all(v == "MATCH" for v in states.values()):
                res["verdict"], res["rule"] = vocab.SUPPORTED, \
                    "acquisition hash matches an earlier custody record"
            else:
                res["verdict"], res["rule"] = vocab.PARTIALLY_SUPPORTED, \
                    "hash recorded at acquisition; no earlier custody record to compare"
            res["confidence"] = "HIGH" if res["verdict"] in (vocab.SUPPORTED, vocab.CONTRADICTED) \
                else "LOW" if res["verdict"] != vocab.UNVERIFIED else "NONE"
            res["caveats"] = []
        elif res["dimension"] == "corroboration":
            own = {membership[e["evidence_id"]] for e in referenced}
            groups = sorted({x["group"] for r in explicit if r["dimension"] != "source"
                             for x in r["agreeing"]} - own)
            conflicted = any(r["conflicting"] for r in explicit)
            res["agreeing"] = [{"evidence_id": "", "value": g, "basis": "independence group",
                                "group": g} for g in groups]
            if conflicted:
                res["verdict"] = vocab.INCONCLUSIVE
                res["rule"] = "independent sources both agree and conflict"
            else:
                res["verdict"] = (vocab.SUPPORTED if len(groups) >= 2 else
                                  vocab.PARTIALLY_SUPPORTED if groups else vocab.UNVERIFIED)
                res["rule"] = f"{len(groups)} independent group(s) beyond the claimed source agree"
            res["confidence"] = ("MODERATE" if res["verdict"] == vocab.SUPPORTED else
                                 "NONE" if res["verdict"] == vocab.UNVERIFIED else "LOW")
            res["caveats"] = []
    overall = combine([r["verdict"] for r in results])
    conflict = any(r["agreeing"] and r["conflicting"] for r in explicit)
    return {
        "verdict": overall,
        "state": vocab.CORROBORATION_CONFLICT if conflict else (
            vocab.REVIEW_REQUIRED if overall != vocab.UNVERIFIED else vocab.INCONCLUSIVE),
        "propositions": results,
        "rule": "conjunction: contradicted > inconclusive > supported only if all supported",
    }


def verify_claim(claim: str, ctx: dict) -> dict:
    props = decompose(claim)
    out = assess(props, ctx)
    out["claim"] = " ".join((claim or "").split())[:2000]
    return out
