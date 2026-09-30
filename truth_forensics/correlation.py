# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Cross-source correlation and independence.

Two copies of one file are one source. So are a file and anything derived
from it, two files that name the same upstream origin (the same camera, the
same original post), and two images whose 64-bit difference hashes differ in
10 bits or fewer (a re-save, crop or edit of the same picture). The last is an
inference, and the relation says so. `independence_groups` collapses all of
them before anything is counted as corroboration.

The comparison rules (`compare`) are shared with claim assessment and are
deliberately literal:

    time       ranges at their stated precision; agree within the tolerance
    location   name tokens: agree when one contains the other; conflict when
               both give the same place type with a different identifier
               ("dock 2" vs "dock 4"); coordinates agree within the tolerance
    identity   as location, for names and designators
    event      agree when half the claim's content words appear; never conflict,
               because free text cannot contradict free text reliably
"""
from __future__ import annotations

import math
import re

AGREES = "AGREES"
CONFLICTS = "CONFLICTS"
NOT_COMPARABLE = "NOT_COMPARABLE"

DIMENSIONS = ("identity", "event", "time", "location", "device", "sequence")
NEAR_DUPLICATE_BITS = 10  # of 64 difference-hash bits

STOPWORDS = frozenset(
    "a an the of to in on at out from into and or is was are were be been by with for as "
    "it its this that shows show showing shown seen near inside outside".split())

_TIME = re.compile(
    r"(?:(\d{4}-\d{2}-\d{2}))?(?:[T ]?(\d{2}):(\d{2})(?::(\d{2}))?)?Z?", re.ASCII)
_COORD = re.compile(r"\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*", re.ASCII)


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def stem(word: str) -> str:
    for suffix in ("ing", "es", "ed", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def content_words(text: str) -> list[str]:
    return [stem(t) for t in tokens(text) if t not in STOPWORDS]


def _identifier_like(tok: str) -> bool:
    return len(tok) == 1 or any(c.isdigit() for c in tok)


def parse_time(value: str) -> tuple[str, int | None, int | None] | None:
    """-> (date or '', start_second_of_day, end_second_of_day) at stated precision."""
    m = _TIME.fullmatch((value or "").strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    date, hh, mm, ss = m.groups()
    if hh is None:
        return date or "", None, None
    h, mi = int(hh), int(mm)
    if h > 23 or mi > 59:
        return None
    start = h * 3600 + mi * 60 + (int(ss) if ss else 0)
    return date or "", start, start + (0 if ss else 59)


def _time_range(value: str) -> tuple[str, int | None, int | None] | None:
    if "/" in value:
        a, b = (parse_time(p) for p in value.split("/", 1))
        if a and b and a[1] is not None and b[1] is not None:
            return a[0], a[1], b[2]
        return None
    return parse_time(value)


def compare_time(claim: str, observed: str, tolerance_s: int) -> str:
    a, b = _time_range(claim), _time_range(observed)
    if not a or not b:
        return NOT_COMPARABLE
    if a[0] and b[0] and a[0] != b[0]:
        return CONFLICTS
    if a[1] is None or b[1] is None:
        return AGREES if a[0] and a[0] == b[0] else NOT_COMPARABLE
    distance = max(0, a[1] - b[2], b[1] - a[2])
    return AGREES if distance <= tolerance_s else CONFLICTS


def _coords(value: str) -> tuple[float, float] | None:
    m = _COORD.fullmatch(value or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> int:
    """Equirectangular approximation; adequate at the tolerance scales used here."""
    lat = math.radians((a[0] + b[0]) / 2)
    dx = math.radians(b[1] - a[1]) * math.cos(lat) * 6371000
    dy = math.radians(b[0] - a[0]) * 6371000
    return int(math.floor(math.sqrt(dx * dx + dy * dy)))


def compare_names(claim: str, observed: str) -> str:
    p, o = tokens(claim), tokens(observed)
    if not p or not o:
        return NOT_COMPARABLE
    if set(p) <= set(o) or set(o) <= set(p):
        return AGREES
    for i, tok in enumerate(p[:-1]):
        nxt = p[i + 1]
        for j, otok in enumerate(o[:-1]):
            if otok == tok and o[j + 1] != nxt and _identifier_like(nxt) \
                    and _identifier_like(o[j + 1]):
                return CONFLICTS
    return NOT_COMPARABLE


def compare_location(claim: str, observed: str, tolerance_m: int) -> str:
    a, b = _coords(claim), _coords(observed)
    if a and b:
        return AGREES if distance_m(a, b) <= tolerance_m else CONFLICTS
    if a or b:
        return NOT_COMPARABLE
    return compare_names(claim, observed)


def compare_event(claim: str, observed: str) -> str:
    p = set(content_words(claim))
    if not p:
        return NOT_COMPARABLE
    hits = len(p & set(content_words(observed)))
    return AGREES if 2 * hits >= len(p) else NOT_COMPARABLE


def compare_sequence(first: str, second: str, observed: str) -> str:
    """Observed sequences are written 'A > B > C'."""
    steps = [s.strip() for s in observed.split(">")]

    def index(side: str) -> int | None:
        want = set(content_words(side))
        if not want:
            return None
        for k, step in enumerate(steps):
            if 2 * len(want & set(content_words(step))) >= len(want):
                return k
        return None

    i, j = index(first), index(second)
    if i is None or j is None or i == j:
        return NOT_COMPARABLE
    return AGREES if i < j else CONFLICTS


def compare(dimension: str, claim_value, observed: str, tolerances: dict) -> str:
    if dimension == "time":
        return compare_time(claim_value, observed, tolerances.get("time_seconds", 120))
    if dimension == "location":
        return compare_location(claim_value, observed, tolerances.get("location_meters", 250))
    if dimension in ("identity", "device"):
        return compare_names(claim_value, observed)
    if dimension == "event":
        return compare_event(claim_value, observed)
    if dimension == "sequence":
        return compare_sequence(claim_value[0], claim_value[1], observed)
    return NOT_COMPARABLE


# --------------------------------------------------------------------------
# Independence
# --------------------------------------------------------------------------
def independence_groups(evidence: list[dict]) -> dict:
    ids = sorted(e["evidence_id"] for e in evidence)
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if rb < ra:
                ra, rb = rb, ra
            parent[rb] = ra

    relations = []
    by_id = {e["evidence_id"]: e for e in evidence}
    ordered = [by_id[i] for i in ids]
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if a.get("content_sha256") and a.get("content_sha256") == b.get("content_sha256"):
                relations.append({"a": a["evidence_id"], "b": b["evidence_id"],
                                  "reason": "DUPLICATE_CONTENT"})
                union(a["evidence_id"], b["evidence_id"])
            elif a.get("upstream_source") and a.get("upstream_source") == b.get("upstream_source"):
                relations.append({"a": a["evidence_id"], "b": b["evidence_id"],
                                  "reason": "SHARED_UPSTREAM"})
                union(a["evidence_id"], b["evidence_id"])
            elif a.get("perceptual_hash") and b.get("perceptual_hash"):
                bits = bin(int(a["perceptual_hash"], 16) ^ int(b["perceptual_hash"], 16)).count("1")
                if bits <= NEAR_DUPLICATE_BITS:
                    relations.append({"a": a["evidence_id"], "b": b["evidence_id"],
                                      "reason": f"NEAR_DUPLICATE_IMAGE ({bits}/64 bits differ)"})
                    union(a["evidence_id"], b["evidence_id"])
    for e in ordered:
        if e.get("parent_id") and e["parent_id"] in parent:
            relations.append({"a": e["parent_id"], "b": e["evidence_id"], "reason": "DERIVATIVE_OF"})
            union(e["parent_id"], e["evidence_id"])
    roots = sorted({find(i) for i in ids})
    names = {root: f"G{k + 1}" for k, root in enumerate(roots)}
    membership = {i: names[find(i)] for i in ids}
    groups = [{"group": names[r], "members": [i for i in ids if find(i) == r]} for r in roots]
    relations.sort(key=lambda r: (r["a"], r["b"], r["reason"]))
    return {"membership": membership, "groups": groups, "relations": relations}


def corroboration_matrix(evidence: list[dict], observations: dict[str, list[dict]],
                         membership: dict[str, str], tolerances: dict) -> dict:
    ids = sorted(e["evidence_id"] for e in evidence)
    grid = {i: {d: sorted({o["value"] for o in observations.get(i, [])
                           if o["dimension"] == d or (d == "time" and o["dimension"] == "time_window")})
                for d in DIMENSIONS} for i in ids}
    pairs = []
    for x, a in enumerate(ids):
        for b in ids[x + 1:]:
            for dim in DIMENSIONS:
                va, vb = grid[a][dim], grid[b][dim]
                if not va or not vb or dim == "sequence":
                    continue
                results = {compare(dim, p, q, tolerances) for p in va for q in vb}
                results.discard(NOT_COMPARABLE)
                if not results:
                    continue
                rel = "MIXED" if len(results) > 1 else results.pop()
                pairs.append({"a": a, "b": b, "dimension": dim, "relation": rel,
                              "independent": membership[a] != membership[b]})
    independent = [p for p in pairs if p["independent"]]
    return {
        "grid": grid,
        "pairs": pairs,
        "summary": {
            "agreeing": sum(1 for p in independent if p["relation"] == AGREES),
            "conflicting": sum(1 for p in independent if p["relation"] in (CONFLICTS, "MIXED")),
            "dependent": sum(1 for p in pairs if not p["independent"]),
        },
        "missing": [d for d in DIMENSIONS if not any(grid[i][d] for i in ids)],
        "temporal_conflicts": [p for p in independent if p["dimension"] == "time"
                               and p["relation"] in (CONFLICTS, "MIXED")],
    }
