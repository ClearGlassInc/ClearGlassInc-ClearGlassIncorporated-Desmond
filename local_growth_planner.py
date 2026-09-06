"""Governed local-search planning for ClearGlassInc Artemis.

The planner is deliberately draft-only.  It converts measured service-area
signals into reviewable page and channel recommendations; it does not publish,
edit a Google Business Profile, request reviews, or contact prospects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


class Intent(str, Enum):
    MONEY = "money"
    SUPPORT = "support"


class ReviewState(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class KeywordSignal:
    phrase: str
    intent: Intent
    service: str
    location: str
    impressions: int
    clicks: int
    qualified_leads: int
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.phrase.strip() or not self.service.strip() or not self.location.strip():
            raise ValueError("phrase, service, and location are required")
        if min(self.impressions, self.clicks, self.qualified_leads) < 0:
            raise ValueError("metrics cannot be negative")
        if self.clicks > self.impressions or self.qualified_leads > self.clicks:
            raise ValueError("metrics must satisfy leads <= clicks <= impressions")
        if not self.evidence_ref.strip():
            raise ValueError("an evidence reference is required")


@dataclass(frozen=True)
class PageDraft:
    path: str
    primary_keyword: str
    title: str
    meta_description: str
    h1: str
    sections: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    state: ReviewState = ReviewState.DRAFT

    @property
    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class WeeklyMetrics:
    organic_impressions: int
    map_actions: int
    calls: int
    form_fills: int
    quote_requests: int
    new_reviews: int
    service_page_sessions: int

    @property
    def conversion_rate(self) -> Decimal:
        if self.service_page_sessions == 0:
            return Decimal("0")
        conversions = self.calls + self.form_fills + self.quote_requests
        return Decimal(conversions) / Decimal(self.service_page_sessions)


class LocalGrowthPlanner:
    """Produce deterministic, evidence-linked drafts for human review."""

    SECTION_TEMPLATE = (
        "Problems we solve",
        "Service details and materials",
        "How the service works",
        "Verified project gallery",
        "Visible customer testimonials",
        "Service-area coverage",
        "Frequently asked questions",
        "Request a quote",
    )

    def __init__(self, brand: str = "ClearGlassInc Artemis") -> None:
        self.brand = brand
        self._audit: list[dict[str, str]] = []

    @property
    def audit_records(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(record) for record in self._audit)

    def build_page_drafts(self, signals: Iterable[KeywordSignal]) -> tuple[PageDraft, ...]:
        money_signals = sorted(
            (signal for signal in signals if signal.intent is Intent.MONEY),
            key=lambda item: (-item.qualified_leads, -item.clicks, item.phrase.casefold()),
        )
        used_paths: set[str] = set()
        drafts: list[PageDraft] = []
        for signal in money_signals:
            service_slug = _slug(signal.service)
            location_slug = _slug(signal.location)
            path = f"/services/{service_slug}/{location_slug}/"
            if path in used_paths:
                continue
            used_paths.add(path)
            title = f"{signal.service} in {signal.location} | ClearGlassInc"
            meta = (
                f"Professional {signal.service.lower()} serving {signal.location}. "
                "See verified project proof and request a quote from ClearGlassInc."
            )
            drafts.append(
                PageDraft(
                    path=path,
                    primary_keyword=signal.phrase,
                    title=title[:60],
                    meta_description=meta[:155],
                    h1=f"{signal.service} in {signal.location}",
                    sections=self.SECTION_TEMPLATE,
                    evidence_refs=(signal.evidence_ref,),
                )
            )
        self._append("page_drafts.generated", str(len(drafts)))
        return tuple(drafts)

    def decide_draft(
        self, draft: PageDraft, *, reviewer: str, approve: bool, rationale: str
    ) -> PageDraft:
        if draft.state is not ReviewState.DRAFT:
            raise ValueError("only a draft can be reviewed")
        if not reviewer.strip() or not rationale.strip():
            raise ValueError("reviewer and rationale are required")
        decision = ReviewState.APPROVED if approve else ReviewState.REJECTED
        reviewed = PageDraft(**{**asdict(draft), "state": decision})
        self._append(
            f"page_draft.{decision.value}",
            reviewed.digest,
            actor=reviewer,
            rationale=rationale,
        )
        return reviewed

    def _append(
        self, event: str, subject: str, actor: str = "planner", rationale: str = ""
    ) -> None:
        previous_hash = self._audit[-1]["record_hash"] if self._audit else "GENESIS"
        record = {
            "sequence": str(len(self._audit) + 1),
            "event": event,
            "subject": subject,
            "actor": actor,
            "rationale": rationale,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "previous_hash": previous_hash,
        }
        record["record_hash"] = sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self._audit.append(record)


def _slug(value: str) -> str:
    slug = "-".join("".join(c.lower() if c.isalnum() else " " for c in value).split())
    if not slug:
        raise ValueError("value cannot produce an empty URL slug")
    return slug
