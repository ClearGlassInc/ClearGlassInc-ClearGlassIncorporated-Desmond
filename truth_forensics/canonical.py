# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Canonical JSON and SHA-256 helpers.

Same canonical form as `bots/rfed_audit_bot.canonical_json` (sorted keys, no
whitespace, ASCII-escaped), so a record hashed here can be re-hashed by anyone
with `json` and `hashlib`. Engine output never carries floats: ratios are
integer percentages, times are integer milliseconds. That keeps the Python and
browser engines byte-identical.
"""
from __future__ import annotations

import hashlib
import json

GENESIS_HASH = "0" * 64


def canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def digest(payload: object) -> str:
    return sha256_text(canonical_json(payload))


def pct(numerator: int, denominator: int) -> int | None:
    """Integer percentage, half-up. None when there is nothing to measure."""
    if denominator <= 0:
        return None
    return (200 * numerator + denominator) // (2 * denominator)
