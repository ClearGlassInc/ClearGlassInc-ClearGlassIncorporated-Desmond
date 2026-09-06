# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Recovery Agent — root-cause classification + bounded retry + escalation.

Deterministic, stdlib-only. Classifies a failure signal into one of the OS's
seven root-cause categories, computes an exponential-backoff retry schedule, and
decides when to stop and escalate. Fails closed: an unrecognised signal is
classified ``logic`` and escalated after the bounded retries, never retried
forever.
"""
from __future__ import annotations

from dataclasses import dataclass

from .roster import RECOVERY_CAUSES

# Ordered (cause, keyword) rules; first match wins. Specific causes first.
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("permissions", ("permission", "forbidden", "unauthorized", "403", "401", "denied")),
    ("dependency", ("modulenotfound", "importerror", "no module", "unresolved", "version")),
    ("external_service", ("timeout", "timed out", "connection", "5xx", "502", "503", "upstream")),
    ("environment", ("env", "not found on path", "disk", "memory", "oom", "config missing")),
    ("user_data", ("invalid input", "malformed", "schema", "parse error", "validation")),
    ("input", ("missing argument", "required", "none", "empty", "keyerror")),
)


@dataclass(frozen=True)
class RecoveryPlan:
    """Classification + bounded retry schedule for a failure."""

    cause: str
    signal: str
    retry_delays: tuple[float, ...]   # seconds; empty == do not retry
    escalate: bool
    recoverable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "cause": self.cause,
            "signal": self.signal,
            "retry_delays": list(self.retry_delays),
            "escalate": self.escalate,
            "recoverable": self.recoverable,
        }


def classify(signal: str) -> str:
    """Map a failure signal to one of RECOVERY_CAUSES. Unknown -> 'logic'."""
    s = signal.lower()
    for cause, keywords in _RULES:
        if any(kw in s for kw in keywords):
            return cause
    return "logic"


# Causes worth an automated retry (transient / environmental). The rest are
# deterministic faults that will fail identically on retry -> escalate directly.
_RETRYABLE = frozenset({"external_service", "environment", "dependency"})


def plan_recovery(
    signal: str,
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> RecoveryPlan:
    """Classify a failure and produce a bounded exponential-backoff plan."""
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    cause = classify(signal)
    recoverable = cause in _RETRYABLE
    delays = (
        tuple(base_delay * (2 ** i) for i in range(max_retries)) if recoverable else ()
    )
    # Escalate when there is no automated path, or after exhausting retries.
    escalate = not recoverable or max_retries == 0
    return RecoveryPlan(cause, signal, delays, escalate, recoverable)


# Every cause this module can emit must be a category the roster declares.
_KNOWN_CAUSES = frozenset(RECOVERY_CAUSES)
if not {c for c, _ in _RULES} <= _KNOWN_CAUSES:  # pragma: no cover - config guard
    raise RuntimeError("recovery rule references an unknown root cause")
