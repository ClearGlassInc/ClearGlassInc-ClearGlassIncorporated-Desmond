"""SENTINEL — privacy-first security-intelligence policy gate.

Executable enforcement of SENTINEL_CHARTER.md. Every analysis request is
classified and gated BEFORE any feed/record is touched. The gate is
fail-closed: any missing/unverifiable term resolves to DENY.

Outcomes:
  * ALLOW    — asset-focused / aggregate work on an approved source with a
               verified role + purpose, no private-person targeting.
  * ESCALATE — permitted-but-sensitive (e.g. consented watchlist under written
               policy); requires human review before proceeding.
  * DENY     — violates a hard rule (identify a private individual without
               authority, face-rec/re-id/cross-match on non-consenting people,
               OSINT de-anonymization, unapproved source, missing role/purpose).
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PolicyOutcome(str, Enum):
    ALLOW = "ALLOW"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class RequestClass(str, Enum):
    ASSET_PROTECTION = "asset_protection"
    COMPLIANCE = "compliance"
    EMERGENCY_RESPONSE = "emergency_response"
    INCIDENT_RESPONSE = "incident_response"
    SITUATIONAL_AWARENESS = "situational_awareness"
    UNCLASSIFIED = "unclassified"


# Approved data-source families (owned / consented / authorized only).
APPROVED_SOURCES = {
    "owned_camera_network",
    "public_source_brand_mentions",
    "consented_watchlist",
    "employee_access_zone",
    "authorized_telemetry",
    "authorized_logs",
    # geospatial / GEOINT
    "lawful_satellite_imagery",
    "authorized_sensor_feeds",
    "owned_site_imagery",
    # vulnerability / threat intelligence (defensive: exposure of OWNED assets)
    "vulnerability_intel",
}

# Approved public vulnerability / threat-intelligence feeds. Used only for
# defensive context — assessing which published exploits/CVEs affect the
# operator's OWNED software, assets, and infrastructure. Never for targeting
# people or for offensive operations against third parties.
THREAT_INTEL_FEEDS = {
    "exploit_db": "https://www.exploit-db.com/",
}

# Intents that are categorically forbidden by the charter.
PROHIBITED_INTENTS = {
    "de_anonymize",
    "stalk",
    "harass",
    "expose_private_person",
    "locate_private_person",
    "profile_private_person",
    "track_private_person",
    "unlawful_surveillance",
}

# Access methods that are never permitted.
PROHIBITED_ACCESS = {
    "covert",
    "deceptive",
    "impersonation",
    "unauthorized_scraping",
}

# Intents that are inherently individual-scoped (treated as targeting a person).
INDIVIDUAL_SCOPED_INTENTS = {
    "identify_individual",
    "locate_individual",
    "track_individual",
    "profile_individual",
    "monitor_individual",
}


@dataclass(frozen=True)
class RequestContext:
    actor_role: str                              # must be non-empty (role check)
    purpose: str                                 # must be non-empty (purpose check)
    data_source: str                             # must be in APPROVED_SOURCES
    intent: str = "monitor"                      # e.g. monitor, correlate, de_anonymize
    authorization_ref: Optional[str] = None      # documented legal authority / written policy
    jurisdiction: Optional[str] = None           # required when targeting an individual
    access_method: str = "authorized"            # authorized | covert | deceptive | unauthorized_scraping
    targets_private_individual: bool = False
    subject_consenting: bool = False
    uses_face_recognition: bool = False          # incl. person re-identification
    cross_source_matching: bool = False
    combines_geospatial_sources: bool = False    # satellite/camera/OSINT/location fusion
    output_is_aggregate: bool = True
    sensitive_inference: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    outcome: PolicyOutcome
    request_class: RequestClass
    reasons: tuple[str, ...]
    requires_human_review: bool
    audit_ref: str

    @property
    def allowed(self) -> bool:
        return self.outcome is PolicyOutcome.ALLOW


def _audit_ref(ctx: RequestContext) -> str:
    seed = f"{time.time()}|{ctx.actor_role}|{ctx.purpose}|{ctx.data_source}|{ctx.intent}"
    return "SENT-" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()


def _classify(purpose: str, intent: str) -> RequestClass:
    p = f"{purpose} {intent}".lower()
    if any(w in p for w in ("emergency", "disaster", "rescue", "weather", "flood",
                            "wildfire", "evacuat", "damage")):
        return RequestClass.EMERGENCY_RESPONSE
    if any(w in p for w in ("situational awareness", "situational", "awareness", "posture")):
        return RequestClass.SITUATIONAL_AWARENESS
    if any(w in p for w in ("incident", "breach", "intrusion", "timeline")):
        return RequestClass.INCIDENT_RESPONSE
    if any(w in p for w in ("compliance", "audit", "policy", "regulat")):
        return RequestClass.COMPLIANCE
    if any(w in p for w in ("asset", "perimeter", "monitor", "brand", "domain",
                            "safety", "facility", "vessel", "ship", "site", "infrastructure")):
        return RequestClass.ASSET_PROTECTION
    return RequestClass.UNCLASSIFIED


class PrivacyPolicy:
    """Stateless evaluator for SENTINEL requests (fail-closed)."""

    def evaluate(self, ctx: Optional[RequestContext]) -> PolicyDecision:
        # Fail-closed: an absent/uncomputable context denies.
        if ctx is None:
            return PolicyDecision(
                PolicyOutcome.DENY, RequestClass.UNCLASSIFIED,
                ("request context unavailable (fail-closed)",), True, "SENT-NULL",
            )

        ref = _audit_ref(ctx)
        cls = _classify(ctx.purpose, ctx.intent)
        deny: list[str] = []

        # An individual-scoped intent is treated exactly like targeting a person.
        targets_individual = ctx.targets_private_individual or (ctx.intent in INDIVIDUAL_SCOPED_INTENTS)

        # --- role + purpose checks ---
        if not ctx.actor_role.strip():
            deny.append("missing actor role (role check failed)")
        if not ctx.purpose.strip():
            deny.append("missing purpose (purpose check failed)")

        # --- approved source only ---
        if ctx.data_source not in APPROVED_SOURCES:
            deny.append(f"data source '{ctx.data_source}' is not approved")

        # --- access method: no covert / deceptive / unauthorized scraping ---
        if ctx.access_method in PROHIBITED_ACCESS:
            deny.append(f"prohibited access method: {ctx.access_method} "
                        "(no covert accounts, deceptive access, or unauthorized scraping)")

        # --- categorically prohibited intents ---
        if ctx.intent in PROHIBITED_INTENTS:
            deny.append(f"prohibited intent: {ctx.intent}")

        # --- biometric / re-id / cross-match on non-consenting people ---
        if (ctx.uses_face_recognition or ctx.cross_source_matching) and not ctx.subject_consenting:
            deny.append("face-recognition / re-identification / cross-source matching "
                        "on a non-consenting individual is prohibited")

        # --- geospatial fusion to de-anonymize / locate a person ---
        if ctx.combines_geospatial_sources and targets_individual and not ctx.subject_consenting:
            deny.append("combining satellite / camera / OSINT / location data to "
                        "de-anonymize or locate a person is prohibited")

        # --- identify / locate / track / profile a private individual ---
        # Documented authorization is mandatory; consent alone is insufficient.
        if targets_individual and not ctx.authorization_ref:
            deny.append("identifying/locating/tracking/profiling a private individual "
                        "requires explicit documented authorization")

        # --- jurisdiction must be verified when an individual is in scope ---
        if targets_individual and not (ctx.jurisdiction or "").strip():
            deny.append("jurisdiction not verified for an individual-scoped request")

        if deny:
            return PolicyDecision(PolicyOutcome.DENY, cls, tuple(deny), True, ref)

        # --- escalation: permitted-but-sensitive ---
        escalate: list[str] = []
        if targets_individual:                    # consented or authorized, but still sensitive
            escalate.append("targets an individual — human review required before proceeding")
        if ctx.sensitive_inference:
            escalate.append("potentially sensitive inference — human review required")
        if not ctx.output_is_aggregate:
            escalate.append("non-aggregate output on sensitive data — confirm need-to-know")
        if escalate:
            return PolicyDecision(PolicyOutcome.ESCALATE, cls, tuple(escalate), True, ref)

        # --- allow: asset-focused / aggregate ---
        return PolicyDecision(
            PolicyOutcome.ALLOW, cls,
            ("approved source", "role+purpose verified", "asset-focused / aggregate"),
            False, ref,
        )


@dataclass
class Report:
    """Charter response format."""

    top_line: str
    evidence: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    risk_notes: list[str] = field(default_factory=list)
    next_step: str = ""
    audit_ref: str = ""

    def render(self) -> str:
        ev = "\n".join(f"  - {e}" for e in self.evidence) or "  - (none)"
        rk = "\n".join(f"  - {r}" for r in self.risk_notes) or "  - (none)"
        return (
            f"TOP-LINE: {self.top_line}\n"
            f"EVIDENCE:\n{ev}\n"
            f"CONFIDENCE: {self.confidence}\n"
            f"RISK NOTES:\n{rk}\n"
            f"NEXT STEP: {self.next_step}\n"
            f"AUDIT REF: {self.audit_ref}"
        )
