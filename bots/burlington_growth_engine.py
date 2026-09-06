"""Deterministic ClearGlass Burlington growth controls.

The module is intentionally stdlib-only so repository CI can validate the
approval, suppression, scoring, and audit invariants without external services.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

APPROVAL_REQUIRED_ACTIONS = {
    "send_email",
    "send_linkedin_message",
    "publish_content",
    "launch_advertisement",
    "change_budget",
    "contact_government_official",
    "submit_procurement_response",
    "collect_personal_data",
    "connect_third_party_account",
    "delete_campaign_record",
}
UNSUPPORTED_CLAIMS = ("guaranteed security", "unhackable", "government affiliated", "military capability")
APPROVED_GEOS = {"burlington", "halton", "hamilton", "oakville", "mississauga", "toronto", "ontario"}
MAX_CAMPAIGN_BUDGET_CAD = 5000

LEAD_WEIGHTS = {
    "location_fit": 15,
    "industry_risk": 12,
    "company_size": 8,
    "m365_dependence": 10,
    "privacy_sensitive": 10,
    "regulatory_exposure": 8,
    "recent_growth": 5,
    "no_visible_security_leadership": 8,
    "content_engagement": 8,
    "expressed_urgency": 8,
    "budget_indicator": 4,
    "service_fit": 4,
}

@dataclass(frozen=True)
class LeadRecord:
    organization: str
    domain: str
    city: str
    industry: str
    size_band: str
    source_url: str
    evidence: dict[str, str] = field(default_factory=dict)

    @property
    def dedupe_key(self) -> str:
        canonical = self.domain.strip().lower() or self.organization.strip().lower()
        return sha256(canonical.encode()).hexdigest()[:16]

@dataclass(frozen=True)
class Approval:
    action: str
    approved_by: str | None = None
    approved_at: str | None = None

    @property
    def valid(self) -> bool:
        return bool(self.approved_by and self.approved_at)

@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    timestamp: str
    actor: str
    action: str
    target: str
    decision: str
    prev_hash: str
    event_hash: str


def prevent_duplicate_leads(existing: list[LeadRecord], candidate: LeadRecord) -> bool:
    return candidate.dedupe_key not in {lead.dedupe_key for lead in existing}


def suppression_allows_contact(identifier: str, suppression_list: set[str]) -> bool:
    return identifier.strip().lower() not in {item.strip().lower() for item in suppression_list}


def require_approval(action: str, approval: Approval | None) -> None:
    if action in APPROVAL_REQUIRED_ACTIONS and not (approval and approval.action == action and approval.valid):
        raise PermissionError(f"{action} requires explicit human approval")


def validate_claims(claims: list[str], citations: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for claim in claims:
        lower = claim.lower()
        if any(bad in lower for bad in UNSUPPORTED_CLAIMS):
            findings.append(f"unsupported_claim:{claim}")
        if any(ch.isdigit() for ch in claim) and claim not in citations:
            findings.append(f"missing_citation:{claim}")
        if "citation needed" in lower or "source:" in lower and "http" not in lower:
            findings.append(f"fabricated_or_incomplete_citation:{claim}")
    return findings


def validate_campaign(campaign: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    budget = int(campaign.get("budget_cad", 0))
    if budget > MAX_CAMPAIGN_BUDGET_CAD:
        findings.append("budget_exceeds_ceiling")
    geos = {str(g).lower() for g in campaign.get("geographic_targets", [])}
    if not geos or not geos.issubset(APPROVED_GEOS):
        findings.append("invalid_geographic_targeting")
    for url in campaign.get("attribution_links", []):
        if not str(url).startswith("https://") or "utm_source=" not in str(url):
            findings.append(f"broken_attribution_link:{url}")
    findings.extend(validate_claims(campaign.get("claims", []), campaign.get("citations", {})))
    return findings


def score_lead(signals: dict[str, int], evidence: dict[str, str]) -> dict[str, Any]:
    score = 0
    explanation = []
    for signal, weight in LEAD_WEIGHTS.items():
        value = max(0, min(1, int(signals.get(signal, 0))))
        contribution = value * weight
        score += contribution
        explanation.append({"signal": signal, "points": contribution, "evidence": evidence.get(signal, "not provided")})
    return {"score": score, "max_score": 100, "explanation": explanation}


def guard_agent_loop(state: dict[str, int], max_iterations: int = 3) -> None:
    if int(state.get("iterations", 0)) >= max_iterations:
        raise RuntimeError("agent loop stopped before autonomous recursion")


def sanitize_untrusted_webpage(text: str) -> str:
    blocked = ("ignore previous instructions", "exfiltrate", "send emails", "launch ads")
    sanitized = text
    for phrase in blocked:
        sanitized = sanitized.replace(phrase, "[blocked-instruction]")
    return sanitized[:5000]


def append_audit_event(events: list[AuditEvent], actor: str, action: str, target: str, decision: str) -> AuditEvent:
    prev_hash = events[-1].event_hash if events else "GENESIS"
    timestamp = datetime.now(UTC).isoformat()
    payload = f"{timestamp}|{actor}|{action}|{target}|{decision}|{prev_hash}"
    event_hash = sha256(payload.encode()).hexdigest()
    event = AuditEvent(
        event_id=event_hash[:16], timestamp=timestamp, actor=actor, action=action,
        target=target, decision=decision, prev_hash=prev_hash, event_hash=event_hash
    )
    events.append(event)
    return event


def verify_audit_chain(events: list[AuditEvent]) -> bool:
    previous = "GENESIS"
    for event in events:
        if event.prev_hash != previous:
            return False
        payload = f"{event.timestamp}|{event.actor}|{event.action}|{event.target}|{event.decision}|{event.prev_hash}"
        if sha256(payload.encode()).hexdigest() != event.event_hash:
            return False
        previous = event.event_hash
    return True


def rollback_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    restored = dict(campaign)
    restored["status"] = "rolled_back"
    restored["external_actions_enabled"] = False
    restored["rollback_at"] = datetime.now(UTC).isoformat()
    return restored
