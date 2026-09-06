# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Minimal trace context contract for Percival v10 service boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TraceContext:
    correlation_id: str
    trace_id: str
    degraded: bool = False

    @classmethod
    def new(cls, correlation_id: str | None = None) -> "TraceContext":
        cid = correlation_id or f"corr-{uuid4().hex}"
        return cls(correlation_id=cid, trace_id=f"trace-{uuid4().hex}")

    def mark_degraded(self) -> "TraceContext":
        return TraceContext(self.correlation_id, self.trace_id, True)
