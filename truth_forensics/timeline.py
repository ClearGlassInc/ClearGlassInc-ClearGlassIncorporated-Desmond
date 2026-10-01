# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Frame-timing timeline.

Input is run-length frame intervals `[(count, delta), ...]` in a timescale
(exactly what an MP4 `stts` box stores), or a list of frame timestamps from a
structured frame log. Output is a list of segments:

    NORMAL             interval equals the nominal interval (within 10%)
    REVIEW_REQUIRED    irregular interval, more than 10% off nominal
    ANOMALY_DETECTED   gap of 1.5x nominal or more, a zero interval (duplicate
                       timestamp) or a backwards step (non-monotonic time)
    SUPPORTED          a NORMAL stretch that an independent channel covers

The nominal interval is the one covering the most frames. A gap estimates how
many frames are missing; it cannot say whether they were dropped by the
encoder or removed afterwards.
"""
from __future__ import annotations

from . import vocab

LABELS = {
    vocab.NORMAL: "NORMAL",
    vocab.REVIEW_REQUIRED: "REVIEW",
    vocab.ANOMALY_DETECTED: "ANOMALY",
    vocab.SUPPORTED: "SUPPORTED",
}


def runs_from_timestamps(stamps_ms: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for a, b in zip(stamps_ms, stamps_ms[1:]):
        d = b - a
        if runs and runs[-1][1] == d:
            runs[-1] = (runs[-1][0] + 1, d)
        else:
            runs.append((1, d))
    return runs


def nominal_delta(runs: list[tuple[int, int]]) -> int:
    totals: dict[int, int] = {}
    for count, delta in runs:
        if delta > 0:
            totals[delta] = totals.get(delta, 0) + count
    if not totals:
        return 0
    return min(totals, key=lambda d: (-totals[d], d))


def classify(delta: int, nominal: int) -> tuple[str, str]:
    if delta < 0:
        return vocab.ANOMALY_DETECTED, "time runs backwards (non-monotonic)"
    if delta == 0:
        return vocab.ANOMALY_DETECTED, "duplicate timestamp"
    if 2 * delta >= 3 * nominal:
        missing = (delta + nominal // 2) // nominal - 1
        return vocab.ANOMALY_DETECTED, f"gap of about {missing} frame interval(s)"
    if abs(delta - nominal) * 10 <= nominal:
        return vocab.NORMAL, "nominal interval"
    return vocab.REVIEW_REQUIRED, "irregular frame interval"


def build(runs: list[tuple[int, int]], timescale: int,
          supported_ms: list[tuple[int, int]] | None = None) -> dict:
    """Segments with integer millisecond bounds."""
    nominal = nominal_delta(runs)
    out: dict = {"timescale": timescale, "nominal_delta": nominal, "fps_x100": 0,
                 "intervals": sum(c for c, _ in runs), "segments": [],
                 "gaps": 0, "duplicates": 0, "backwards": 0, "irregular": 0}
    if not runs or timescale <= 0 or nominal <= 0:
        return out
    out["fps_x100"] = (timescale * 100 * 2 + nominal) // (2 * nominal)
    raw: list[dict] = []
    t = 0
    for count, delta in runs:
        state, reason = classify(delta, nominal)
        if state == vocab.ANOMALY_DETECTED:
            key = "gaps" if delta > 0 else "duplicates" if delta == 0 else "backwards"
            out[key] += count
        elif state == vocab.REVIEW_REQUIRED:
            out["irregular"] += count
        start = t
        t += count * delta
        lo, hi = (start, t) if t >= start else (t, start)
        a, b = lo * 1000 // timescale, hi * 1000 // timescale
        if raw and raw[-1]["state"] == state and raw[-1]["reason"] == reason \
                and raw[-1]["end_ms"] == a:
            raw[-1]["end_ms"] = b
        else:
            raw.append({"start_ms": a, "end_ms": b, "state": state, "reason": reason})
    segments = _overlay(raw, sorted(supported_ms or []))
    for seg in segments:
        seg["label"] = LABELS[seg["state"]]
    out["segments"] = segments
    return out


def _overlay(segments: list[dict], windows: list[tuple[int, int]]) -> list[dict]:
    """Relabel the parts of NORMAL segments that an independent channel covers."""
    if not windows:
        return segments
    out: list[dict] = []
    for seg in segments:
        if seg["state"] != vocab.NORMAL:
            out.append(seg)
            continue
        cuts = {seg["start_ms"], seg["end_ms"]}
        for a, b in windows:
            for edge in (a, b):
                if seg["start_ms"] < edge < seg["end_ms"]:
                    cuts.add(edge)
        points = sorted(cuts)
        for a, b in zip(points, points[1:]):
            covered = any(wa <= a and b <= wb for wa, wb in windows)
            piece = {"start_ms": a, "end_ms": b,
                     "state": vocab.SUPPORTED if covered else vocab.NORMAL,
                     "reason": ("nominal interval; covered by an independent channel"
                                if covered else seg["reason"])}
            if out and out[-1]["state"] == piece["state"] and out[-1]["end_ms"] == a \
                    and out[-1]["reason"] == piece["reason"]:
                out[-1]["end_ms"] = b
            else:
                out.append(piece)
    return out


def fmt_ms(ms: int) -> str:
    sign = "-" if ms < 0 else ""
    ms = abs(ms)
    return f"{sign}{ms // 60000:02d}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"
