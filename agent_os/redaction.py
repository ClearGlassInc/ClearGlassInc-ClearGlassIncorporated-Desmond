# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Credential redaction for anything the head agent stores or logs.

Task output is persisted and served over the API, and log lines leave the
process. Both pass through :func:`redact` first. The patterns are the
high-signal shapes from ``scripts/secret_scan.py`` plus bearer headers, so a
capability that echoes a credential never lands it in the task store.

Literal values (the API tokens the server was started with) are redacted too:
a pattern can miss a credential with an unusual shape, an exact match cannot.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

MASK = "[REDACTED]"

PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"AKIA[0-9A-Z]{16}",
        r"gh[pousr]_[A-Za-z0-9]{36,}",
        r"github_pat_[A-Za-z0-9_]{22,}",
        r"glpat-[A-Za-z0-9_-]{20,}",
        r"(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}",
        r"whsec_[A-Za-z0-9]{16,}",
        r"xox[abprs]-[A-Za-z0-9-]{10,}",
        r"sk-ant-[A-Za-z0-9_-]{20,}",
        r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    )
)


def redact(text: str, *, literals: Iterable[str] = ()) -> str:
    """Return ``text`` with every recognised credential replaced by ``MASK``."""
    if not text:
        return text
    for value in literals:
        if value and len(value) >= 8:
            text = text.replace(value, MASK)
    for pattern in PATTERNS:
        text = pattern.sub(MASK, text)
    return text
