# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH knowledge graph — entities, relationships, confidence, provenance.

The lattice's shared model of the world. Four things distinguish it from a
plain graph store, and all four exist because intelligence work is adversarial:

* **Every assertion carries provenance.** Who said it, when, and how sure they
  were. An entity's confidence is derived from its assertions, never set
  directly, so nobody can declare something true by fiat.
* **Contradictions are recorded, not resolved.** When two sources disagree on
  the same attribute, both survive and the pair is surfaced. Silently picking a
  winner is how bad intelligence becomes invisible.
* **Confidence decays with disagreement.** A contradicted attribute is
  automatically less trusted than a corroborated one.
* **Retraction is explicit.** Assertions are withdrawn by id, leaving the
  history intact for audit.

Stdlib only.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from .constants import LatticeError


class GraphError(LatticeError):
    """Unknown node, malformed assertion, or illegal edge."""


@dataclass(frozen=True)
class Assertion:
    """One sourced claim about an entity attribute or a relationship.

    ``multivalued`` marks predicates that legitimately hold several values at
    once — ``observed_by`` is true of every source that saw the entity, and two
    sources naming themselves is corroboration, not disagreement. Only
    single-valued predicates can contradict.
    """

    assertion_id: str
    subject: str
    predicate: str
    value: Any
    source: str
    confidence: float
    ts: float = field(default_factory=time.time)
    retracted: bool = False
    multivalued: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self.value,
            "source": self.source,
            "confidence": round(self.confidence, 3),
            "ts": self.ts,
            "retracted": self.retracted,
            "multivalued": self.multivalued,
        }


@dataclass
class Entity:
    """A node: an identity, asset, threat actor, event or indicator."""

    entity_id: str
    kind: str
    labels: set[str] = field(default_factory=set)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "labels": sorted(self.labels),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass(frozen=True)
class Relationship:
    """A directed, typed edge with its own confidence and provenance."""

    src: str
    kind: str
    dst: str
    confidence: float
    source: str
    ts: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "src": self.src,
            "kind": self.kind,
            "dst": self.dst,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "ts": self.ts,
        }


@dataclass(frozen=True)
class Contradiction:
    """Two live assertions that disagree on the same subject/predicate."""

    subject: str
    predicate: str
    left: Assertion
    right: Assertion

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "left": self.left.as_dict(),
            "right": self.right.as_dict(),
        }


class KnowledgeGraph:
    """Entity/relationship store with confidence and contradiction tracking."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._assertions: dict[str, Assertion] = {}
        self._by_subject: dict[str, list[str]] = defaultdict(list)
        self._relationships: list[Relationship] = []
        self._counter = 0

    # ------------------------------------------------------------------ #
    # Entities
    # ------------------------------------------------------------------ #
    def upsert_entity(self, entity_id: str, kind: str, labels: Iterable[str] = ()) -> Entity:
        """Create or refresh a node; labels accumulate, they never reset."""
        entity_id = _require(entity_id, "entity_id")
        existing = self._entities.get(entity_id)
        if existing is None:
            entity = Entity(entity_id=entity_id, kind=_require(kind, "kind"), labels=set(labels))
            self._entities[entity_id] = entity
            return entity
        existing.labels |= set(labels)
        existing.last_seen = time.time()
        return existing

    def entity(self, entity_id: str) -> Entity:
        try:
            return self._entities[entity_id]
        except KeyError:
            raise GraphError(f"unknown entity: {entity_id}") from None

    def entities(self, kind: str | None = None) -> tuple[Entity, ...]:
        items = sorted(self._entities.values(), key=lambda e: e.entity_id)
        return tuple(e for e in items if kind is None or e.kind == kind)

    # ------------------------------------------------------------------ #
    # Assertions
    # ------------------------------------------------------------------ #
    def assert_fact(
        self,
        subject: str,
        predicate: str,
        value: Any,
        source: str,
        confidence: float = 0.7,
        multivalued: bool = False,
    ) -> Assertion:
        """Record a sourced claim. The subject is auto-created if unseen.

        Set ``multivalued`` for predicates that may hold several values at once
        (``observed_by``, ``tagged``), so co-existing values are treated as
        corroboration rather than as a contradiction to be surfaced.
        """
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if subject not in self._entities:
            self.upsert_entity(subject, kind="unknown")
        else:
            self._entities[subject].last_seen = time.time()

        self._counter += 1
        assertion = Assertion(
            assertion_id=f"asr-{self._counter:06d}",
            subject=subject,
            predicate=_require(predicate, "predicate"),
            value=value,
            source=_require(source, "source"),
            confidence=confidence,
            multivalued=multivalued,
        )
        self._assertions[assertion.assertion_id] = assertion
        self._by_subject[subject].append(assertion.assertion_id)
        return assertion

    def retract(self, assertion_id: str) -> Assertion:
        """Withdraw a claim, keeping it in the record marked as retracted."""
        current = self._assertions.get(assertion_id)
        if current is None:
            raise GraphError(f"unknown assertion: {assertion_id}")
        retracted = Assertion(
            assertion_id=current.assertion_id,
            subject=current.subject,
            predicate=current.predicate,
            value=current.value,
            source=current.source,
            confidence=current.confidence,
            ts=current.ts,
            retracted=True,
            multivalued=current.multivalued,
        )
        self._assertions[assertion_id] = retracted
        return retracted

    def assertions(self, subject: str | None = None, include_retracted: bool = False) -> tuple[Assertion, ...]:
        ids = self._by_subject.get(subject, []) if subject else list(self._assertions)
        items = [self._assertions[i] for i in ids]
        if not include_retracted:
            items = [a for a in items if not a.retracted]
        return tuple(sorted(items, key=lambda a: a.assertion_id))

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    def relate(
        self, src: str, kind: str, dst: str, source: str, confidence: float = 0.7
    ) -> Relationship:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        for node in (src, dst):
            if node not in self._entities:
                self.upsert_entity(node, kind="unknown")
        edge = Relationship(
            src=src, kind=_require(kind, "kind"), dst=dst, confidence=confidence, source=source
        )
        self._relationships.append(edge)
        return edge

    def neighbors(self, entity_id: str, kind: str | None = None) -> tuple[Relationship, ...]:
        return tuple(
            e
            for e in self._relationships
            if (e.src == entity_id or e.dst == entity_id) and (kind is None or e.kind == kind)
        )

    def relationships(self) -> tuple[Relationship, ...]:
        return tuple(self._relationships)

    def paths(self, start: str, depth: int = 2) -> tuple[tuple[str, ...], ...]:
        """Breadth-first walk out to ``depth`` hops, returning distinct paths.

        Cycle-safe: a node already on the current path is not revisited, so a
        mutually-referencing cluster cannot spin the walk.
        """
        if depth < 1:
            raise ValueError("depth must be at least 1")
        if start not in self._entities:
            raise GraphError(f"unknown entity: {start}")
        found: list[tuple[str, ...]] = []
        frontier: list[tuple[str, ...]] = [(start,)]
        for _ in range(depth):
            next_frontier: list[tuple[str, ...]] = []
            for path in frontier:
                tail = path[-1]
                for edge in self.neighbors(tail):
                    nxt = edge.dst if edge.src == tail else edge.src
                    if nxt in path:
                        continue
                    extended = path + (nxt,)
                    found.append(extended)
                    next_frontier.append(extended)
            frontier = next_frontier
        return tuple(found)

    # ------------------------------------------------------------------ #
    # Confidence & contradictions
    # ------------------------------------------------------------------ #
    def confidence(self, subject: str, predicate: str) -> float:
        """Aggregate confidence for one attribute of one entity.

        Corroborating sources reinforce each other (noisy-OR, so two 0.6
        sources beat one 0.8); disagreement discounts the result in proportion
        to how much confidence sits on the losing side. For a multi-valued
        predicate there is no losing side — every value corroborates the whole.
        """
        live = [
            a
            for a in self.assertions(subject)
            if a.predicate == predicate and not a.retracted
        ]
        if not live:
            return 0.0

        def combine(items: list[Assertion]) -> float:
            residual = 1.0
            for item in items:
                residual *= 1.0 - item.confidence
            return 1.0 - residual

        if any(a.multivalued for a in live):
            return round(combine(live), 4)

        by_value: dict[str, list[Assertion]] = defaultdict(list)
        for assertion in live:
            by_value[repr(assertion.value)].append(assertion)

        scored = {value: combine(items) for value, items in by_value.items()}
        best_value = max(scored, key=lambda v: scored[v])
        best = scored[best_value]
        dissent = sum(score for value, score in scored.items() if value != best_value)
        if dissent <= 0:
            return round(best, 4)
        return round(max(0.0, best * (1.0 - dissent / (best + dissent))), 4)

    def contradictions(self) -> tuple[Contradiction, ...]:
        """Every pair of live assertions that disagree on the same attribute.

        Multi-valued predicates are exempt — several sources naming themselves
        under ``observed_by`` corroborate the entity, they do not conflict.
        """
        grouped: dict[tuple[str, str], list[Assertion]] = defaultdict(list)
        for assertion in self._assertions.values():
            if not assertion.retracted and not assertion.multivalued:
                grouped[(assertion.subject, assertion.predicate)].append(assertion)

        found: list[Contradiction] = []
        for (subject, predicate), items in sorted(grouped.items()):
            items.sort(key=lambda a: a.assertion_id)
            for i, left in enumerate(items):
                for right in items[i + 1 :]:
                    if left.value != right.value:
                        found.append(
                            Contradiction(
                                subject=subject, predicate=predicate, left=left, right=right
                            )
                        )
        return tuple(found)

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def snapshot(self) -> dict[str, Any]:
        live = [a for a in self._assertions.values() if not a.retracted]
        by_kind: dict[str, int] = {}
        for entity in self._entities.values():
            by_kind[entity.kind] = by_kind.get(entity.kind, 0) + 1
        return {
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "assertions": len(live),
            "retracted": len(self._assertions) - len(live),
            "contradictions": len(self.contradictions()),
            "by_kind": dict(sorted(by_kind.items())),
        }


def _require(value: str, label: str) -> str:
    if not value or not str(value).strip():
        raise GraphError(f"{label} is required")
    return str(value).strip()
