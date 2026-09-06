# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH observability — hash-chained audit ledger, metrics, anomaly detection.

Three things every layer of the lattice writes into:

* :class:`AuditLedger` — append-only and hash-chained. Each entry commits to the
  previous entry's digest, so a tampered or removed record is detectable by
  re-walking the chain. This is the record of record for governance.
* :class:`MetricSink` — counters and gauges plus rolling windows, cheap enough
  to call on every event.
* :class:`AnomalyDetector` — running mean/standard-deviation per series, so an
  unusual rate is caught without a model or a threshold table.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Mapping

from .constants import LatticeError, RiskTier, canonical

#: Digest that seeds the chain — the "before anything happened" anchor.
GENESIS = "0" * 64

#: Minimum samples before the detector is willing to call anything anomalous.
MIN_SAMPLES_FOR_ANOMALY = 8


class LedgerTampering(LatticeError):
    """The audit chain failed verification."""


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable record in the append-only chain."""

    index: int
    ts: float
    actor: str
    action: str
    risk: RiskTier
    detail: Mapping[str, Any]
    prev_hash: str
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "ts": self.ts,
            "actor": self.actor,
            "action": self.action,
            "risk": self.risk.value,
            "detail": dict(self.detail),
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }


class AuditLedger:
    """Append-only, hash-chained record of every material action."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def record(
        self,
        actor: str,
        action: str,
        risk: RiskTier = RiskTier.LOW,
        detail: Mapping[str, Any] | None = None,
        ts: float | None = None,
    ) -> LedgerEntry:
        """Append an entry, chaining it to the current head."""
        if not actor.strip():
            raise ValueError("actor is required")
        if not action.strip():
            raise ValueError("action is required")
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS
        index = len(self._entries)
        body = {
            "index": index,
            "ts": ts if ts is not None else time.time(),
            "actor": actor,
            "action": action,
            "risk": RiskTier(risk).value,
            "detail": dict(detail or {}),
            "prev_hash": prev_hash,
        }
        entry = LedgerEntry(
            index=index,
            ts=body["ts"],
            actor=actor,
            action=action,
            risk=RiskTier(risk),
            detail=body["detail"],
            prev_hash=prev_hash,
            entry_hash=hashlib.sha256(canonical(body)).hexdigest(),
        )
        self._entries.append(entry)
        return entry

    def verify(self) -> bool:
        """Re-walk the chain. ``False`` means an entry was altered or removed."""
        prev = GENESIS
        for index, entry in enumerate(self._entries):
            if entry.index != index or entry.prev_hash != prev:
                return False
            body = {
                "index": entry.index,
                "ts": entry.ts,
                "actor": entry.actor,
                "action": entry.action,
                "risk": entry.risk.value,
                "detail": dict(entry.detail),
                "prev_hash": entry.prev_hash,
            }
            if hashlib.sha256(canonical(body)).hexdigest() != entry.entry_hash:
                return False
            prev = entry.entry_hash
        return True

    def require_intact(self) -> None:
        """Verify or raise — call before trusting the ledger for a decision."""
        if not self.verify():
            raise LedgerTampering("audit chain verification failed")

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def by_actor(self, actor: str) -> tuple[LedgerEntry, ...]:
        return tuple(e for e in self._entries if e.actor == actor)

    def by_risk(self, minimum: RiskTier) -> tuple[LedgerEntry, ...]:
        from .constants import RISK_ORDER

        floor = RISK_ORDER[RiskTier(minimum)]
        return tuple(e for e in self._entries if RISK_ORDER[e.risk] >= floor)

    def tail(self, count: int = 25) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries[-count:])

    def __len__(self) -> int:
        return len(self._entries)


class MetricSink:
    """Counters, gauges and rolling observation windows."""

    def __init__(self, window: int = 256) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        self._window = window
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._series: dict[str, deque[float]] = {}

    def increment(self, name: str, amount: float = 1.0) -> float:
        self._counters[name] = self._counters.get(name, 0.0) + amount
        return self._counters[name]

    def gauge(self, name: str, value: float) -> float:
        self._gauges[name] = float(value)
        return self._gauges[name]

    def observe(self, name: str, value: float) -> None:
        self._series.setdefault(name, deque(maxlen=self._window)).append(float(value))

    def series(self, name: str) -> tuple[float, ...]:
        return tuple(self._series.get(name, ()))

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": {k: round(v, 4) for k, v in sorted(self._counters.items())},
            "gauges": {k: round(v, 4) for k, v in sorted(self._gauges.items())},
            "series": {
                name: {
                    "n": len(values),
                    "mean": round(sum(values) / len(values), 4) if values else 0.0,
                    "last": round(values[-1], 4) if values else 0.0,
                }
                for name, values in sorted(self._series.items())
            },
        }


@dataclass(frozen=True)
class Anomaly:
    """A observation that fell outside the learned band for its series."""

    series: str
    value: float
    mean: float
    stdev: float
    z_score: float
    ts: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "series": self.series,
            "value": round(self.value, 4),
            "mean": round(self.mean, 4),
            "stdev": round(self.stdev, 4),
            "z_score": round(self.z_score, 3),
            "ts": self.ts,
        }


class AnomalyDetector:
    """Online mean/stdev outlier detection, one band per named series.

    Deliberately model-free: the lattice must be able to flag "this rate is
    unlike the last N" in a CI environment with no dependencies and no training
    data. ``sensitivity`` is the z-score above which an observation is flagged.
    """

    def __init__(self, sensitivity: float = 3.0, window: int = 128) -> None:
        if sensitivity <= 0:
            raise ValueError("sensitivity must be positive")
        if window < MIN_SAMPLES_FOR_ANOMALY:
            raise ValueError(f"window must be at least {MIN_SAMPLES_FOR_ANOMALY}")
        self._sensitivity = sensitivity
        self._window = window
        self._series: dict[str, deque[float]] = {}
        self._anomalies: list[Anomaly] = []

    def observe(self, series: str, value: float) -> Anomaly | None:
        """Record a value; return an :class:`Anomaly` if it breaks the band.

        The value is appended *after* the check, so a genuine spike does not
        immediately widen the band that is supposed to catch it.
        """
        history = self._series.setdefault(series, deque(maxlen=self._window))
        anomaly: Anomaly | None = None
        if len(history) >= MIN_SAMPLES_FOR_ANOMALY:
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            stdev = variance**0.5
            if stdev > 0:
                z_score = abs(value - mean) / stdev
                if z_score >= self._sensitivity:
                    anomaly = Anomaly(
                        series=series, value=value, mean=mean, stdev=stdev, z_score=z_score
                    )
                    self._anomalies.append(anomaly)
            elif value != mean:
                # A perfectly flat series broken by any deviation at all.
                anomaly = Anomaly(
                    series=series, value=value, mean=mean, stdev=0.0, z_score=float("inf")
                )
                self._anomalies.append(anomaly)
        history.append(float(value))
        return anomaly

    @property
    def anomalies(self) -> tuple[Anomaly, ...]:
        return tuple(self._anomalies)

    def snapshot(self) -> dict[str, Any]:
        return {
            "sensitivity": self._sensitivity,
            "series_tracked": len(self._series),
            "anomalies": [a.as_dict() for a in self._anomalies[-20:]],
            "anomaly_count": len(self._anomalies),
        }
