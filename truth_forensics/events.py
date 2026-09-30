# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Structured event records and plain-text documents.

Recognised JSON record types (anything else is kept as an opaque event):

    sensor-window      {"record_type", "sensor", "location", "start", "end"}
    clock-reference    {"record_type", "device", "offset_seconds", "reference"}
    custody-receipt    {"record_type", "issued_by", "issued_at",
                        "entries": [{"evidence_id", "sha256"}]}

A custody receipt is what lets integrity be *verified* rather than merely
recorded: it fixes a hash before this acquisition, so a later match shows the
bytes are unchanged since the receipt was issued.
"""
from __future__ import annotations

import json
import re

from . import vocab

ANALYZER = "event@" + vocab.ENGINE_VERSION
MAX_EVENT_BYTES = 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{64}$")


def analyze_event(data: bytes) -> dict:
    result: dict = {"analyzer": ANALYZER, "metadata": {}, "indicators": [], "observations": [],
                    "not_performed": [], "custody": []}
    if len(data) > MAX_EVENT_BYTES:
        result["not_performed"].append("event record over 1 MiB; not parsed")
        return result
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        result["not_performed"].append("event record is not valid JSON")
        return result
    if not isinstance(record, dict):
        result["metadata"] = {"record_type": "opaque"}
        return result
    rtype = str(record.get("record_type", "opaque"))[:60]
    result["metadata"] = {"record_type": rtype, "keys": sorted(str(k)[:60] for k in record)[:50]}
    obs = result["observations"]
    if rtype == "sensor-window":
        start, end = str(record.get("start", "")), str(record.get("end", ""))
        if start and end:
            obs.append({"dimension": "time_window", "value": f"{start}/{end}",
                        "basis": "sensor log window (structured record)"})
        if record.get("location"):
            obs.append({"dimension": "location", "value": str(record["location"])[:200],
                        "basis": "sensor log location (structured record)"})
        if record.get("sensor"):
            obs.append({"dimension": "device", "value": str(record["sensor"])[:200],
                        "basis": "sensor log device id (structured record)"})
    elif rtype == "clock-reference":
        off = record.get("offset_seconds")
        if isinstance(off, int) and not isinstance(off, bool):
            obs.append({"dimension": "clock_offset", "value": str(off),
                        "basis": f"clock reference for {str(record.get('device', ''))[:80]}"
                                 " (structured record)"})
    elif rtype == "custody-receipt":
        for entry in record.get("entries", [])[:1000]:
            if isinstance(entry, dict) and _SHA.match(str(entry.get("sha256", ""))):
                result["custody"].append({
                    "evidence_id": str(entry.get("evidence_id", ""))[:80],
                    "sha256": entry["sha256"],
                    "issued_at": str(record.get("issued_at", ""))[:40],
                    "issued_by": str(record.get("issued_by", ""))[:80],
                })
    return result


def analyze_text(data: bytes) -> dict:
    text = data.decode("utf-8", "replace")
    return {
        "analyzer": "text@" + vocab.ENGINE_VERSION,
        "metadata": {"characters": len(text), "lines": text.count("\n") + (1 if text else 0)},
        "indicators": [],
        "observations": [],
        "not_performed": ["Automated fact extraction from text (analyst transcription only)"],
    }
