# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH event bus — typed, ordered, replay-protected agent coordination.

Agents never call each other directly. They publish typed :class:`Event`
objects and subscribe to patterns, which is what lets a subsystem be rebuilt or
taken offline without the others noticing.

Guarantees, in the order they matter:

* **Total order.** Every accepted event gets a monotonic ``seq``. Replay from a
  sequence number reconstructs exactly what a subscriber would have seen.
* **Exactly-once acceptance.** A duplicate ``event_id`` is dropped, so a
  retrying publisher cannot double-apply an effect.
* **Handler isolation.** A raising handler is quarantined into the dead-letter
  queue; it can never take down the publisher or starve sibling handlers.
* **Typed envelopes.** Event types are dotted namespaces (``threat.ioc.observed``)
  matched by exact name, tail wildcard (``threat.*``) or ``*``.

Stdlib only.
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .constants import LatticeError

#: Default ring-buffer depth for replayable history.
DEFAULT_HISTORY = 2048

Handler = Callable[["Event"], None]


class BusError(LatticeError):
    """Raised for malformed events or invalid subscriptions."""


@dataclass(frozen=True)
class Event:
    """One typed message on the bus.

    ``trace_id`` threads an event to the mission that caused it, which is how
    the executive layer reassembles a causal chain across domains.
    """

    type: str
    source: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=time.time)
    seq: int = 0

    def with_seq(self, seq: int) -> "Event":
        return Event(
            type=self.type,
            source=self.source,
            payload=self.payload,
            trace_id=self.trace_id,
            event_id=self.event_id,
            ts=self.ts,
            seq=seq,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "event_id": self.event_id,
            "type": self.type,
            "source": self.source,
            "ts": self.ts,
            "trace_id": self.trace_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class DeadLetter:
    """A handler failure, preserved with the event that triggered it."""

    event: Event
    pattern: str
    error: str

    def as_dict(self) -> dict[str, Any]:
        return {"event": self.event.as_dict(), "pattern": self.pattern, "error": self.error}


class EventBus:
    """Synchronous, ordered, in-process bus.

    Synchronous by design: delivery completes before ``publish`` returns, so a
    caller that publishes then reads the audit ledger sees a consistent world.
    """

    def __init__(self, history: int = DEFAULT_HISTORY) -> None:
        if history <= 0:
            raise ValueError("history must be positive")
        self._subscribers: dict[str, list[Handler]] = {}
        self._history: deque[Event] = deque(maxlen=history)
        self._dead_letters: deque[DeadLetter] = deque(maxlen=history)
        self._seen: set[str] = set()
        self._seq = 0
        self._counts: dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Subscription
    # ------------------------------------------------------------------ #
    def subscribe(self, pattern: str, handler: Handler) -> Callable[[], None]:
        """Register ``handler`` for ``pattern``; returns an unsubscribe callable."""
        if not pattern or not pattern.strip():
            raise BusError("subscription pattern is required")
        if not callable(handler):
            raise BusError("handler must be callable")
        pattern = pattern.strip()
        self._subscribers.setdefault(pattern, []).append(handler)

        def unsubscribe() -> None:
            handlers = self._subscribers.get(pattern, [])
            if handler in handlers:
                handlers.remove(handler)
            if not handlers:
                self._subscribers.pop(pattern, None)

        return unsubscribe

    def subscribers_for(self, event_type: str) -> tuple[tuple[str, Handler], ...]:
        matched: list[tuple[str, Handler]] = []
        for pattern, handlers in self._subscribers.items():
            if _matches(pattern, event_type):
                matched.extend((pattern, h) for h in handlers)
        return tuple(matched)

    # ------------------------------------------------------------------ #
    # Publication
    # ------------------------------------------------------------------ #
    def publish(self, event: Event) -> Event | None:
        """Accept, sequence and deliver an event.

        Returns the sequenced event, or ``None`` when the event was rejected as
        a duplicate. Handler exceptions are captured as dead letters rather
        than propagated — one bad subscriber must not break the lattice.
        """
        if not event.type or not event.type.strip():
            raise BusError("event type is required")
        if not event.source or not event.source.strip():
            raise BusError("event source is required")
        if event.event_id in self._seen:
            return None

        self._seq += 1
        sequenced = event.with_seq(self._seq)
        self._seen.add(sequenced.event_id)
        self._history.append(sequenced)
        self._counts[sequenced.type] = self._counts.get(sequenced.type, 0) + 1

        for pattern, handler in self.subscribers_for(sequenced.type):
            try:
                handler(sequenced)
            except Exception as exc:  # noqa: BLE001 - isolation is the point
                self._dead_letters.append(
                    DeadLetter(event=sequenced, pattern=pattern, error=f"{type(exc).__name__}: {exc}")
                )
        return sequenced

    def emit(
        self,
        type: str,
        source: str,
        payload: Mapping[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> Event | None:
        """Convenience constructor + publish."""
        return self.publish(
            Event(type=type, source=source, payload=dict(payload or {}), trace_id=trace_id)
        )

    # ------------------------------------------------------------------ #
    # Replay & inspection
    # ------------------------------------------------------------------ #
    def replay(self, since_seq: int = 0, types: Iterable[str] | None = None) -> tuple[Event, ...]:
        """Every retained event after ``since_seq``, optionally type-filtered."""
        patterns = tuple(types) if types else None
        return tuple(
            event
            for event in self._history
            if event.seq > since_seq
            and (patterns is None or any(_matches(p, event.type) for p in patterns))
        )

    def trace(self, trace_id: str) -> tuple[Event, ...]:
        """Every retained event belonging to one causal chain, in order."""
        return tuple(e for e in self._history if e.trace_id == trace_id)

    @property
    def dead_letters(self) -> tuple[DeadLetter, ...]:
        return tuple(self._dead_letters)

    @property
    def sequence(self) -> int:
        return self._seq

    def stats(self) -> dict[str, Any]:
        return {
            "published": self._seq,
            "retained": len(self._history),
            "dead_letters": len(self._dead_letters),
            "subscriptions": sum(len(h) for h in self._subscribers.values()),
            "by_type": dict(sorted(self._counts.items())),
        }


def _matches(pattern: str, event_type: str) -> bool:
    """``*`` matches everything; ``a.b.*`` matches ``a.b.c`` but not ``a.bc``."""
    if pattern == "*" or pattern == event_type:
        return True
    if pattern.endswith(".*"):
        return event_type.startswith(pattern[:-1])
    return False
