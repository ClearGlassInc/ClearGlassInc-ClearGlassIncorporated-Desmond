"""SENTINEL — privacy-preserving vision operations.

Two charter-compliant capabilities, both intended to run BEHIND the
``PrivacyPolicy`` gate. Neither identifies, recognizes, or re-identifies a
person, and neither stores biometric templates.

1. ``PresenceMonitor`` — ANONYMOUS presence / occupancy / safety analytics on
   owned cameras. It detects *that* people or objects are present (counts,
   zones, dwell time) — never *who*. No identity, no face templates, no
   recognition. This is the only "camera analytics" the charter permits without
   individual authorization.

2. ``ConsentedAccessControl`` — verifies an ENROLLED, opt-in credential
   reference against a consented roster, gated by documented authorization and a
   verified jurisdiction; every decision escalates to human review and is
   logged. It does NOT identify arbitrary or non-consenting individuals — an
   unknown credential simply returns "no consented enrollment".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .policy import PolicyOutcome, PrivacyPolicy, RequestContext

# Zones that are access-controlled (used for tailgating logic).
ACCESS_ZONES = {"entry", "lobby", "dock", "server_room", "gate", "turnstile"}


# ---------------------------------------------------------------------------
# 1. Anonymous presence / safety analytics  (no identity, ever)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    """One anonymous, per-frame detection. Deliberately carries NO identity,
    name, or biometric data — only an ephemeral per-frame tag."""

    blob_id: str          # ephemeral frame-local tag, NOT a person identifier
    zone: str
    dwell_s: float
    is_object: bool = False  # True for an unattended object (e.g. a bag)


@dataclass(frozen=True)
class PresenceEvent:
    kind: str             # occupancy | tailgating | abandoned_object | loitering | clear
    zone: str
    count: int
    confidence: float
    note: str


class PresenceMonitor:
    def __init__(
        self,
        *,
        occupancy_limit: int = 10,
        tailgate_window_s: float = 4.0,
        abandoned_s: float = 60.0,
        loiter_s: float = 300.0,
    ) -> None:
        self.occupancy_limit = occupancy_limit
        self.tailgate_window_s = tailgate_window_s
        self.abandoned_s = abandoned_s
        self.loiter_s = loiter_s

    def analyze(self, zone: str, observations: list[Observation]) -> list[PresenceEvent]:
        persons = [o for o in observations if not o.is_object]
        objects = [o for o in observations if o.is_object]
        count = len(persons)
        events: list[PresenceEvent] = []

        if count > self.occupancy_limit:
            events.append(PresenceEvent("occupancy", zone, count, 0.9,
                                        f"{count} people exceeds limit {self.occupancy_limit}"))

        if zone in ACCESS_ZONES:
            entering = [p for p in persons if p.dwell_s <= self.tailgate_window_s]
            if len(entering) >= 2:
                events.append(PresenceEvent("tailgating", zone, len(entering), 0.8,
                                            f"{len(entering)} people through access point within "
                                            f"{self.tailgate_window_s:.0f}s"))

        for obj in objects:
            if obj.dwell_s >= self.abandoned_s:
                events.append(PresenceEvent("abandoned_object", zone, 1, 0.85,
                                            f"object unattended {obj.dwell_s:.0f}s"))

        for p in persons:
            if p.dwell_s >= self.loiter_s:
                events.append(PresenceEvent("loitering", zone, 1, 0.7,
                                            f"anonymous dwell {p.dwell_s:.0f}s"))
                break

        if not events:
            events.append(PresenceEvent("clear", zone, count, 0.95,
                                        f"{count} present, nominal"))
        return events


# ---------------------------------------------------------------------------
# 2. Consented access control  (enrolled, opt-in, gated, escalated)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Enrollment:
    """An opt-in enrolled credential. ``subject_ref`` is an opaque token (e.g. a
    hashed badge id) — never a name or biometric template."""

    subject_ref: str
    consent: bool
    jurisdiction: str


@dataclass(frozen=True)
class AccessResult:
    access: str           # GRANT_PENDING_REVIEW | DENY
    reasons: tuple[str, ...]
    audit_ref: str
    subject_ref: Optional[str] = None
    requires_human_review: bool = True


class ConsentedAccessControl:
    """Verifies a presented enrolled credential against the consented roster,
    behind the privacy policy gate. Does not identify non-consenting people."""

    def __init__(self, enrollments: list[Enrollment], policy: Optional[PrivacyPolicy] = None) -> None:
        # Only consenting enrollments are retained.
        self._roster = {e.subject_ref: e for e in enrollments if e.consent}
        self._policy = policy or PrivacyPolicy()

    def verify(self, *, presented_ref: str, ctx: RequestContext) -> AccessResult:
        decision = self._policy.evaluate(ctx)
        # Gate must not DENY (it returns ESCALATE for a consented, authorized,
        # jurisdiction-verified individual-scoped request).
        if decision.outcome is PolicyOutcome.DENY:
            return AccessResult("DENY", decision.reasons, decision.audit_ref)

        enr = self._roster.get(presented_ref)
        if enr is None:
            # No consented enrollment matches. We do NOT attempt to identify who
            # this is — simply refuse.
            return AccessResult("DENY", ("no consented enrollment for presented credential",),
                                decision.audit_ref)

        return AccessResult(
            "GRANT_PENDING_REVIEW",
            ("enrolled + consented credential verified",) + decision.reasons,
            decision.audit_ref,
            subject_ref=enr.subject_ref,
            requires_human_review=True,
        )
