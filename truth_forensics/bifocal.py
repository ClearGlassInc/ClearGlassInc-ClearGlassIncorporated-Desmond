# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Bifocal Evidence Verification.

A single media stream is one lens. Bifocal verification holds it against
channels that did not come through the same pipeline:

    PRIMARY_MEDIA        the stream under examination
    INDEPENDENT_SENSOR   a different device that observed the same scene
    TIME_SOURCE          a reference clock for the primary device
    PROVENANCE_RECORD    a custody record that fixed the primary's hash earlier

Each applicable check agrees or conflicts. The consistency score is the share
of applicable checks that agree, as an integer percentage. It is only reported
when at least two channels are present, and always with BIFOCAL_DISCLAIMER.
A channel in the same independence group as the primary is not independent
and is excluded from scoring.
"""
from __future__ import annotations

from . import vocab
from .canonical import pct
from .correlation import AGREES, CONFLICTS, compare, parse_time
from .indicators import quote

KINDS = ("PRIMARY_MEDIA", "INDEPENDENT_SENSOR", "TIME_SOURCE", "PROVENANCE_RECORD")

ADAPTERS = (
    {"id": "declared_hash", "name": "Custody-record hash comparison", "implemented": True},
    {"id": "structured_channel", "name": "Structured channel records (JSON)", "implemented": True},
    {"id": "camera_telemetry", "name": "Camera telemetry feed", "implemented": False},
    {"id": "rfc3161", "name": "RFC 3161 trusted timestamp tokens", "implemented": False},
    {"id": "signature", "name": "Detached cryptographic signatures", "implemented": False},
    {"id": "sensor_feed", "name": "Live sensor feeds", "implemented": False},
    {"id": "device_attestation", "name": "Device attestation", "implemented": False},
    {"id": "c2pa", "name": "C2PA / Content Credentials validation", "implemented": False},
    {"id": "secure_log", "name": "Secure / append-only logging systems", "implemented": False},
)


def _window(value: str) -> tuple[str, int, int] | None:
    if "/" not in (value or ""):
        t = parse_time(value)
        return (t[0], t[1], t[2]) if t and t[1] is not None else None
    a, b = (parse_time(p) for p in value.split("/", 1))
    if a and b and a[1] is not None and b[1] is not None:
        return a[0], a[1], b[2]
    return None


def verify(channels: list[dict], membership: dict[str, str], hashes: dict[str, str],
           tolerances: dict) -> dict:
    by_kind: dict[str, dict] = {}
    for ch in channels:
        if ch.get("kind") in KINDS and ch["kind"] not in by_kind:
            by_kind[ch["kind"]] = ch
    present = [k for k in KINDS if k in by_kind]
    checks: list[dict] = []
    primary = by_kind.get("PRIMARY_MEDIA")
    out = {"channels": [{"kind": k, "evidence_id": by_kind[k].get("evidence_id", ""),
                         "label": by_kind[k].get("label", "")} for k in present],
           "coverage": f"{len(present)}/{len(KINDS)}", "checks": checks, "score": None,
           "status": "INSUFFICIENT_CHANNELS", "disclaimer": vocab.BIFOCAL_DISCLAIMER,
           "adapters": [dict(a) for a in ADAPTERS]}
    if not primary or len(present) < 2:
        return out
    pid = primary.get("evidence_id", "")

    def independent(ch: dict) -> bool:
        cid = ch.get("evidence_id", "")
        return not cid or cid not in membership or membership.get(cid) != membership.get(pid)

    sensor = by_kind.get("INDEPENDENT_SENSOR")
    if sensor:
        indep = independent(sensor)
        pw, sw = _window(primary.get("time_window", "")), _window(sensor.get("time_window", ""))
        if pw and sw:
            overlap = pw[0] == sw[0] or not pw[0] or not sw[0]
            overlap = overlap and pw[1] <= sw[2] and sw[1] <= pw[2]
            checks.append({"check": "TIME_OVERLAP", "channel": "INDEPENDENT_SENSOR",
                           "result": AGREES if overlap else CONFLICTS, "independent": indep,
                           "detail": f"primary {primary['time_window']}; sensor "
                                     f"{sensor['time_window']}"})
        if primary.get("location") and sensor.get("location"):
            rel = compare("location", sensor["location"], primary["location"], tolerances)
            if rel != "NOT_COMPARABLE":
                checks.append({"check": "LOCATION", "channel": "INDEPENDENT_SENSOR",
                               "result": rel, "independent": indep,
                               "detail": f"primary {quote(primary['location'])}; sensor "
                                         f"{quote(sensor['location'])}"})
    clock = by_kind.get("TIME_SOURCE")
    if clock and isinstance(clock.get("offset_seconds"), int):
        off = clock["offset_seconds"]
        limit = tolerances.get("clock_seconds", 5)
        checks.append({"check": "CLOCK_OFFSET", "channel": "TIME_SOURCE",
                       "result": AGREES if abs(off) <= limit else CONFLICTS,
                       "independent": independent(clock),
                       "detail": f"primary device clock offset {off:+d} s against the reference "
                                 f"(tolerance {limit} s)"})
    record = by_kind.get("PROVENANCE_RECORD")
    if record and record.get("declared_sha256"):
        actual = hashes.get(pid, "")
        match = actual == record["declared_sha256"]
        checks.append({"check": "INTEGRITY", "channel": "PROVENANCE_RECORD",
                       "result": AGREES if match else CONFLICTS,
                       "independent": independent(record),
                       "detail": ("SHA-256 matches the custody record" if match else
                                  "SHA-256 differs from the custody record"),
                       "state": vocab.CRYPTOGRAPHICALLY_VERIFIED if match else
                       vocab.ANOMALY_DETECTED,
                       "note": vocab.CRYPTO_NOTE})
    scored = [c for c in checks if c["independent"]]
    agree = sum(1 for c in scored if c["result"] == AGREES)
    out["score"] = pct(agree, len(scored))
    out["scored_checks"] = len(scored)
    out["status"] = ("NO_APPLICABLE_CHECKS" if not scored else
                     vocab.NORMAL if agree == len(scored) else vocab.REVIEW_REQUIRED)
    return out
