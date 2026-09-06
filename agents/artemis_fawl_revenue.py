"""ARTEMIS // FAWL evidence-weighted revenue opportunity agent.

This module ranks authorized opportunities. It does not scrape, send messages,
place trades, move money, deploy code, or bypass a human approval gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
import hashlib
import json
from typing import Iterable


class Gate(str, Enum):
    REVIEW = "review"
    APPROVED = "approved"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    title: str
    source_ids: tuple[str, ...]
    evidence_quality: int
    expected_value_cad: Decimal
    strategic_fit: int
    effort: int
    risk: int
    source_authorized: bool
    human_gate: Gate = Gate.REVIEW

    def validate(self) -> None:
        if not self.opportunity_id or not self.title:
            raise ValueError("identity fields are required")
        if not self.source_ids:
            raise ValueError("at least one provenance source is required")
        for name in ("evidence_quality", "strategic_fit", "effort", "risk"):
            value = getattr(self, name)
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be an integer from 0 to 100")
        if self.expected_value_cad < 0:
            raise ValueError("expected value cannot be negative")


@dataclass(frozen=True)
class RankedOpportunity:
    opportunity_id: str
    title: str
    score: int
    expected_value_cad: str
    status: Gate
    reason: str
    provenance: tuple[str, ...]
    audit_hash: str


def _score(item: Opportunity) -> int:
    raw = (
        Decimal(item.evidence_quality) * Decimal("0.35")
        + min(item.expected_value_cad / Decimal("100"), Decimal(100)) * Decimal("0.25")
        + Decimal(item.strategic_fit) * Decimal("0.20")
        + Decimal(100 - item.effort) * Decimal("0.10")
        + Decimal(100 - item.risk) * Decimal("0.10")
    )
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rank(item: Opportunity) -> RankedOpportunity:
    item.validate()
    score = _score(item)
    if not item.source_authorized:
        status, reason = Gate.BLOCKED, "Source authorization failed."
    elif item.evidence_quality < 60:
        status, reason = Gate.BLOCKED, "Evidence quality is below the policy floor."
    elif item.human_gate is not Gate.APPROVED:
        status, reason = Gate.REVIEW, "Human approval is required before any external action."
    else:
        status, reason = Gate.APPROVED, "Approved for a separately controlled executor."
    event = {
        "id": item.opportunity_id,
        "score": score,
        "status": status.value,
        "sources": sorted(item.source_ids),
        "expected_value_cad": str(item.expected_value_cad),
    }
    serialized = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(serialized).hexdigest()
    return RankedOpportunity(
        item.opportunity_id,
        item.title,
        score,
        str(item.expected_value_cad.quantize(Decimal("0.01"))),
        status,
        reason,
        item.source_ids,
        digest,
    )


def rank_all(items: Iterable[Opportunity]) -> list[dict]:
    ranked = [rank(item) for item in items]
    ranked.sort(key=lambda result: (-result.score, result.opportunity_id))
    return [asdict(result) for result in ranked]


if __name__ == "__main__":
    demo = Opportunity(
        "demo-001",
        "Ontario SME cyber readiness review",
        ("demo-public-source",),
        88,
        Decimal("5000"),
        92,
        25,
        18,
        True,
        Gate.REVIEW,
    )
    print(json.dumps(rank_all([demo]), indent=2, default=str))
