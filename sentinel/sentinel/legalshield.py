"""AEGIS — Legal-Process Shield (PERCIVAL agent).

A *compliance and rights-protection* agent for lawful-access regimes (warrants,
production orders, subpoenas, preservation demands, oversight). It protects
ClearGlass Inc. and its principals by ensuring every legal-process request is
**validated, minimized, routed to counsel, and audited** — and by refusing
facially invalid or overbroad demands so they can be lawfully challenged.

WHAT THIS IS NOT
  AEGIS does **not** evade, obstruct, or defeat valid legal process or lawful
  oversight. It will not help destroy/alter evidence under legal hold, conceal
  assets, tip off a subject, or counsel unlawful non-compliance. Those are hard
  refusals (``guard_action`` -> REFUSE_UNLAWFUL).

NOT LEGAL ADVICE. A licensed lawyer in the relevant jurisdiction must review
every request before any response or disclosure. AEGIS is fail-closed: it never
authorizes disclosure on its own — counsel review is always required.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .audit import AuditLog

DISCLAIMER = (
    "Automated compliance workflow aid — NOT legal advice. A licensed lawyer in "
    "the relevant jurisdiction must review every legal-process request before any "
    "response or disclosure. AEGIS never evades, obstructs, or defeats valid legal "
    "process or lawful oversight."
)

# Principals AEGIS protects. Used to tag heightened-review requests.
PROTECTED_PRINCIPALS = frozenset({
    "clearglass inc", "clearglass inc.", "clearglassinc", "clearglass",
    "desmond otieno odhiambo", "desmond odhiambo", "desmond otieno",
})

# Scope language that signals an overbroad demand to be narrowed / challenged.
OVERBROAD_TERMS = (
    "all data", "all records", "everything", "entire database", "full account",
    "any and all", "complete copy", "all communications",
)

# Actions AEGIS will never assist with (obstruction of justice / evasion).
FORBIDDEN_ACTIONS = frozenset({
    "destroy_evidence", "delete_records_under_hold", "alter_records",
    "falsify_records", "conceal_assets", "tip_off_subject", "evade_warrant",
    "obstruct", "spoliate",
})


class RequestKind(str, Enum):
    WARRANT = "warrant"
    PRODUCTION_ORDER = "production_order"
    SUBPOENA = "subpoena"
    PRESERVATION_DEMAND = "preservation_demand"
    EMERGENCY_DISCLOSURE_REQUEST = "emergency_disclosure_request"
    INFORMAL_REQUEST = "informal_request"          # voluntary, no legal compulsion
    UNKNOWN = "unknown"


class Outcome(str, Enum):
    COMPLY_PENDING_COUNSEL = "COMPLY_PENDING_COUNSEL"   # valid + scoped; counsel must sign off
    ACKNOWLEDGE_ROUTE_COUNSEL = "ACKNOWLEDGE_ROUTE_COUNSEL"
    PRESERVE_IN_PLACE = "PRESERVE_IN_PLACE"             # legal hold; never delete/alter
    CHALLENGE = "CHALLENGE"                             # defective / overbroad / expired
    REFUSE_NO_LEGAL_BASIS = "REFUSE_NO_LEGAL_BASIS"     # informal/voluntary -> don't volunteer data
    REFUSE_UNLAWFUL = "REFUSE_UNLAWFUL"                 # our own conduct would be unlawful


@dataclass(frozen=True)
class LegalRequest:
    id: str
    kind: RequestKind
    issuing_authority: str = ""
    jurisdiction: str = ""
    target: str = ""                                   # org/person named
    scope: tuple[str, ...] = ()                        # specific data items requested
    signed: bool = False
    warrant_number: str = ""
    received_utc: str = ""
    expiry_utc: Optional[str] = None                   # ISO 8601, if any


@dataclass
class Assessment:
    outcome: Outcome
    reasons: list[str]
    requires_counsel_review: bool
    protected_principal: bool
    permitted_disclosure: list[str]                    # minimized set, AFTER counsel sign-off
    objections: list[str]
    next_actions: list[str]
    audit_ref: str
    disclaimer: str = DISCLAIMER


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _expired(expiry_utc: Optional[str]) -> bool:
    if not expiry_utc:
        return False
    try:
        exp = _dt.datetime.fromisoformat(expiry_utc.replace("Z", "+00:00"))
    except ValueError:
        return True                                    # unparseable expiry -> treat as defective
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=_dt.timezone.utc)
    return exp < _dt.datetime.now(_dt.timezone.utc)


def _is_protected(target: str) -> bool:
    return (target or "").strip().lower() in PROTECTED_PRINCIPALS


def _overbroad(scope: tuple[str, ...]) -> bool:
    if not scope:
        return True
    joined = " ".join(scope).lower()
    return any(term in joined for term in OVERBROAD_TERMS)


@dataclass
class RegisterEntry:
    """One row of the legal-process register (request + AEGIS assessment)."""
    request: LegalRequest
    assessment: "Assessment"


class LegalProcessShield:
    """Assess legal-process requests and gate our own conduct. Fail-closed.

    Pass a shared ``AuditLog`` to wire AEGIS decisions into a wider audit
    stream (e.g. the SENTINEL system ledger); otherwise AEGIS keeps its own.
    """

    def __init__(self, audit: Optional[AuditLog] = None) -> None:
        self.audit = audit or AuditLog()
        self.register: list[RegisterEntry] = []

    # ---- assess an incoming legal-process request --------------------------
    def assess(self, req: LegalRequest) -> Assessment:
        protected = _is_protected(req.target)
        defects: list[str] = []
        if not (req.issuing_authority or "").strip():
            defects.append("issuing authority not identified")
        if not (req.jurisdiction or "").strip():
            defects.append("jurisdiction unspecified")
        if req.kind in (RequestKind.WARRANT, RequestKind.PRODUCTION_ORDER) and not req.signed:
            defects.append("legal process is unsigned / authenticity unverified")
        if req.kind is RequestKind.WARRANT and not (req.warrant_number or "").strip():
            defects.append("no warrant / court file number")
        if _expired(req.expiry_utc):
            defects.append("legal process appears expired")
        if req.kind in (RequestKind.WARRANT, RequestKind.PRODUCTION_ORDER,
                        RequestKind.SUBPOENA) and _overbroad(req.scope):
            defects.append("scope is overbroad or unspecified — seek narrowing")

        objections = self._objections(req, defects, protected)
        common_next = [
            "Engage qualified counsel before ANY response or disclosure",
            "Preserve the request + chain of custody; do not alter or delete data",
            "Verify authenticity directly with the issuing authority/court",
            "Record in the legal-process register + transparency report",
        ]

        # --- routing ---------------------------------------------------------
        if req.kind is RequestKind.INFORMAL_REQUEST:
            outcome = Outcome.REFUSE_NO_LEGAL_BASIS
            reasons = ["informal/voluntary request carries no legal compulsion; "
                       "do not volunteer customer or personal data"]
            permitted: list[str] = []
            nxt = ["Decline to voluntarily disclose; require lawful process",
                   *common_next]
        elif req.kind is RequestKind.PRESERVATION_DEMAND:
            outcome = Outcome.PRESERVE_IN_PLACE
            reasons = ["preservation demand — place a legal hold; preserve in place; "
                       "do NOT disclose yet and do NOT alter or delete anything"]
            permitted = []
            nxt = ["Apply legal hold to the named data (no deletion/alteration)",
                   *common_next]
        elif req.kind is RequestKind.EMERGENCY_DISCLOSURE_REQUEST:
            outcome = Outcome.ACKNOWLEDGE_ROUTE_COUNSEL
            reasons = ["emergency disclosure claim — counsel must verify the statutory "
                       "basis and exigency before any minimal disclosure; never auto-disclose"]
            permitted = []
            nxt = ["Do not auto-disclose; counsel verifies legal basis + exigency first",
                   *common_next]
        elif defects:
            outcome = Outcome.CHALLENGE
            reasons = ["defective/overbroad legal process — route to counsel to "
                       "challenge or narrow before any disclosure:"] + [f"· {d}" for d in defects]
            permitted = []
            nxt = ["Counsel to challenge defects / move to quash or narrow",
                   *common_next]
        else:
            outcome = Outcome.COMPLY_PENDING_COUNSEL
            reasons = ["facially valid + scoped legal process; disclose ONLY the listed "
                       "items and ONLY after counsel sign-off (data minimization)"]
            permitted = list(req.scope)
            nxt = ["Counsel reviews + signs off; then disclose the minimized set only",
                   "Withhold privileged materials; log exactly what is produced",
                   *common_next]

        entry = self.audit.record(actor="AEGIS", action="assess_legal_request",
                                  detail={"request_id": req.id, "kind": req.kind.value,
                                          "outcome": outcome.value,
                                          "protected_principal": protected,
                                          "defects": defects})
        assessment = Assessment(
            outcome=outcome, reasons=reasons, requires_counsel_review=True,
            protected_principal=protected, permitted_disclosure=permitted,
            objections=objections, next_actions=nxt, audit_ref=entry.entry_hash[:12],
        )
        self.register.append(RegisterEntry(req, assessment))
        return assessment

    def _objections(self, req: LegalRequest, defects: list[str], protected: bool) -> list[str]:
        obj = ["assert solicitor-client / litigation privilege over privileged materials",
               "request a protective order / sealing for sensitive data"]
        if _overbroad(req.scope):
            obj.append("object to overbreadth; demand particularity of scope")
        if any("expired" in d for d in defects):
            obj.append("object: process appears expired / out of time")
        if protected:
            obj.append("heightened review: a protected principal is named")
        return obj

    # ---- gate our OWN conduct (refuse obstruction) -------------------------
    def guard_action(self, action: str) -> Assessment:
        act = (action or "").strip().lower()
        if act in FORBIDDEN_ACTIONS:
            entry = self.audit.record(actor="AEGIS", action="guard_action",
                                      detail={"action": act, "outcome": "REFUSE_UNLAWFUL"})
            return Assessment(
                outcome=Outcome.REFUSE_UNLAWFUL,
                reasons=[f"'{act}' would obstruct justice or evade lawful process — AEGIS "
                         "will not assist. Preserve data and route to counsel instead."],
                requires_counsel_review=True, protected_principal=False,
                permitted_disclosure=[], objections=[],
                next_actions=["Preserve in place", "Engage counsel"],
                audit_ref=entry.entry_hash[:12],
            )
        entry = self.audit.record(actor="AEGIS", action="guard_action",
                                  detail={"action": act, "outcome": "PERMITTED"})
        return Assessment(
            outcome=Outcome.ACKNOWLEDGE_ROUTE_COUNSEL,
            reasons=[f"'{act}' is a lawful compliance action"],
            requires_counsel_review=True, protected_principal=False,
            permitted_disclosure=[], objections=[],
            next_actions=["proceed under counsel oversight"],
            audit_ref=entry.entry_hash[:12],
        )

    # ---- proactive, lawful data-governance posture -------------------------
    @staticmethod
    def posture_recommendations() -> list[str]:
        return [
            "Data minimization + retention limits — hold only what you need, only as long as lawful",
            "Encryption at rest and in transit; key management you control",
            "Least-privilege access + access logging on sensitive stores",
            "Maintain a data inventory/map so any future scope can be answered precisely",
            "Vendor data-processing agreements; know where data lives (residency)",
            "Stand up a legal-hold process and name a custodian-of-records + counsel contact",
            "Publish a transparency report (counts of requests, challenges, disclosures)",
            "Notify affected parties when lawfully permitted (no gag) ",
        ]

    @staticmethod
    def rights_summary() -> dict:
        return {
            "your_rights": [
                "Require valid legal process; do not volunteer data on informal request",
                "Verify authenticity and scope before responding",
                "Challenge defective, overbroad, or expired demands (move to quash/narrow)",
                "Assert privilege; seek protective orders / sealing",
                "Disclose only the minimized set actually compelled",
                "Notify affected users where lawfully permitted",
                "Keep an immutable audit trail of every request and response",
            ],
            "disclaimer": DISCLAIMER,
        }
