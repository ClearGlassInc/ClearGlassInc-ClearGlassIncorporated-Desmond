# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Intelligence Agent — cross-reference sources, detect contradictions, score.

Implements the rule "never treat a single source as truth". Given claims about
entities from multiple sources with per-source authority, it resolves claims by
entity, flags contradictions, and assigns a confidence per entity that is
*penalised* when sources disagree and when only a single source is available.

Deterministic and stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Claim:
    """A single assertion about an entity from one source."""

    entity: str
    value: str
    source: str
    authority: float = 0.5  # 0..1


@dataclass
class EntityFinding:
    """Resolved view of one entity across all its claims."""

    entity: str
    value: str                       # highest-authority-supported value
    confidence: float                # 0..1
    contradicted: bool
    supporting_sources: list[str] = field(default_factory=list)
    conflicting_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "entity": self.entity,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "contradicted": self.contradicted,
            "supporting_sources": list(self.supporting_sources),
            "conflicting_values": list(self.conflicting_values),
        }


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def cross_reference(claims: list[Claim]) -> list[EntityFinding]:
    """Resolve claims per entity, flag contradictions, assign confidence.

    Confidence rises with corroboration and source authority; it is penalised
    when sources disagree, and capped for single-source entities (a lone source
    is never treated as ground truth).
    """
    by_entity: dict[str, list[Claim]] = {}
    for c in claims:
        by_entity.setdefault(c.entity, []).append(c)

    findings: list[EntityFinding] = []
    for entity in sorted(by_entity):
        group = by_entity[entity]
        # Aggregate authority weight per distinct (normalised) value.
        weight: dict[str, float] = {}
        display: dict[str, str] = {}
        sources: dict[str, list[str]] = {}
        for c in group:
            key = _norm(c.value)
            weight[key] = weight.get(key, 0.0) + max(0.0, min(1.0, c.authority))
            display.setdefault(key, c.value)
            sources.setdefault(key, []).append(c.source)

        best_key = max(weight, key=lambda k: (weight[k], k))
        contradicted = len(weight) > 1
        distinct_sources = {c.source for c in group}

        total_w = sum(weight.values()) or 1.0
        agreement = weight[best_key] / total_w  # 1.0 when unanimous

        base = weight[best_key] / len(sources[best_key])  # avg authority of winners
        confidence = base * agreement
        if len(distinct_sources) == 1:
            confidence = min(confidence, 0.5)  # single-source cap
        if contradicted:
            confidence *= 0.6

        conflicting = sorted(display[k] for k in weight if k != best_key)
        findings.append(
            EntityFinding(
                entity=entity,
                value=display[best_key],
                confidence=max(0.0, min(1.0, confidence)),
                contradicted=contradicted,
                supporting_sources=sorted(set(sources[best_key])),
                conflicting_values=conflicting,
            )
        )
    return findings


def aggregate_confidence(findings: list[EntityFinding]) -> float | None:
    """Overall confidence = the *minimum* entity confidence (never inflate)."""
    if not findings:
        return None
    return round(min(f.confidence for f in findings), 4)
