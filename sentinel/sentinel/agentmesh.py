"""PERCIVAL · Agent Mesh — org-scoped multi-agent OSINT orchestration.

A ClearGlass-only mesh of named intelligence agents that accept a structured
"SIGINT-PRMPT" mission packet, route it through the SENTINEL fail-closed privacy
gate, and dispatch it to the right agent — with a full hash-chained audit trail.

DELIBERATE GUARDRAILS (this is the corrected, charter-compliant design):
  * **Org-only.** Only ClearGlass-authorized principals are served; everyone
    else is refused (fail-closed) — and refused TRANSPARENTLY, never deceptively.
  * **No person targeting.** OSINT scope is organizations / brands / domains /
    facilities / infrastructure / public incidents / approved watchlists /
    public telemetry / vulnerability intel. Missions that would identify,
    locate, track, profile, or de-anonymize a PRIVATE INDIVIDUAL are DENIED by
    the SENTINEL policy gate (no exceptions without documented authorization +
    verified jurisdiction, which then escalate to human review).
  * **Approved sources only.** Unknown/disallowed data domains are refused.
  * **Lawful collection only.** No covert accounts, deceptive access, or
    unauthorized scraping; respect robots.txt / ToS / rate limits at the
    collector layer (enforced by the SENTINEL charter, not bypassed here).
  * **Transparent identity.** Agents identify honestly; they never hide that
    access is org-restricted.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .audit import AuditLog
from .policy import PolicyOutcome, PrivacyPolicy, RequestContext

AUTHORIZED_ORG = "clearglassinc"
AUTHORIZED_EMAIL_SUFFIX = "@clearglassinc.com"

TRANSPARENT_IDENTITY = (
    "ClearGlass Inc. internal intelligence agent. Access is restricted to "
    "ClearGlass-authorized principals; I state that restriction openly and "
    "refuse out-of-scope or unauthorized requests rather than concealing them."
)

# Mission domains -> the approved SENTINEL data source they map to.
DOMAIN_SOURCE = {
    "web": "public_source_brand_mentions",
    "social": "public_source_brand_mentions",
    "news": "public_source_brand_mentions",
    "financial": "public_source_brand_mentions",
    "legal": "public_source_brand_mentions",
    "geospatial": "authorized_sensor_feeds",
    "telecom": "authorized_sensor_feeds",        # public ADS-B/AIS telemetry only
    "vuln": "vulnerability_intel",
}


class Mission(str, Enum):
    RECON = "recon"
    TRACKING = "tracking"
    ASSOCIATION = "association"
    PATTERN = "pattern"


class Dispatch(str, Enum):
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class Principal:
    user_id: str
    org_id: str
    role: str
    email: str = ""

    @property
    def authorized(self) -> bool:
        return (self.org_id or "").strip().lower() == AUTHORIZED_ORG or \
            (self.email or "").strip().lower().endswith(AUTHORIZED_EMAIL_SUFFIX)


@dataclass(frozen=True)
class MissionPacket:
    """The SIGINT-PRMPT packet — a structured OSINT tasking."""
    target: str                                  # entity / pattern (org/brand/domain/asset)
    mission: Mission
    domain: str                                  # web|social|news|financial|legal|geospatial|telecom|vuln
    sources: tuple[str, ...] = ()
    time_window: str = "past 30 days"
    jurisdiction: str = ""
    target_is_individual: bool = False           # honest caller declaration


@dataclass(frozen=True)
class Agent:
    name: str
    role: str
    domains: frozenset[str]
    capabilities: tuple[str, ...]


# Named agents — corporate/asset OSINT only; none is a person-tracker.
AGENTS: tuple[Agent, ...] = (
    Agent("Agent.ClearGlass.OSINT-Harvest", "public-source collection",
          frozenset({"web", "social", "news"}), ("collect_public", "normalize")),
    Agent("Agent.ClearGlass.Entity-Link", "organization entity graphs",
          frozenset({"web", "financial", "legal"}), ("link_org_entities", "topic_graph")),
    Agent("Agent.ClearGlass.Legal-Sig", "corporate legal/compliance signals",
          frozenset({"legal"}), ("filing_match", "ownership_map")),
    Agent("Agent.ClearGlass.Financial-Sig", "corporate financial risk patterns",
          frozenset({"financial"}), ("aml_style_org_flags",)),
    Agent("Agent.ClearGlass.Geo-Telemetry", "public ADS-B/AIS + sensor telemetry",
          frozenset({"geospatial", "telecom"}), ("public_telemetry",)),
    Agent("Agent.ClearGlass.Vuln-Intel", "vulnerability/exposure of owned assets",
          frozenset({"vuln"}), ("cve_exposure",)),
)


@dataclass
class Tasking:
    dispatch: Dispatch
    reasons: list[str]
    identity: str
    agent: Optional[str]
    packet_domain: str
    report_template: dict
    audit_ref: str
    requires_human_review: bool = False


def _route_agent(domain: str) -> Optional[Agent]:
    # Pick the most specialized agent (fewest domains), ties broken by registry
    # order — so 'financial' -> Financial-Sig, not the broader Entity-Link.
    candidates = [(len(a.domains), i, a) for i, a in enumerate(AGENTS) if domain in a.domains]
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    return candidates[0][2]


def _intent_for(packet: MissionPacket) -> str:
    if packet.target_is_individual:
        return {Mission.TRACKING: "track_individual",
                Mission.ASSOCIATION: "profile_individual",
                Mission.RECON: "identify_individual",
                Mission.PATTERN: "profile_individual"}[packet.mission]
    return packet.mission.value


class AgentMesh:
    """Org-scoped router. Fail-closed at the org boundary AND the privacy gate."""

    def __init__(self, audit: Optional[AuditLog] = None,
                 policy: Optional[PrivacyPolicy] = None) -> None:
        self.audit = audit or AuditLog()
        self.policy = policy or PrivacyPolicy()

    def dispatch(self, principal: Principal, packet: MissionPacket) -> Tasking:
        # 1. Org-only — refused transparently if not ClearGlass-authorized.
        if not principal.authorized:
            return self._deny(packet, ["principal is not ClearGlass-authorized — "
                                       "access is restricted to ClearGlass principals (stated openly)"],
                              actor=principal.user_id)

        # 2. Approved data domain only.
        source = DOMAIN_SOURCE.get(packet.domain)
        if source is None:
            return self._deny(packet, [f"domain '{packet.domain}' is not an approved OSINT domain"],
                              actor=principal.user_id)

        # 3. SENTINEL privacy gate — denies person de-anonymization/tracking, etc.
        ctx = RequestContext(
            actor_role=principal.role,
            purpose=f"{packet.mission.value} over {packet.domain} OSINT",
            data_source=source,
            intent=_intent_for(packet),
            jurisdiction=packet.jurisdiction or None,
            targets_private_individual=packet.target_is_individual,
            subject_consenting=False,
            authorization_ref=None,
            output_is_aggregate=True,
        )
        decision = self.policy.evaluate(ctx)
        if decision.outcome is PolicyOutcome.DENY:
            return self._deny(packet, list(decision.reasons), actor=principal.user_id)

        agent = _route_agent(packet.domain)
        if agent is None:                           # defensive; domain mapped but no agent
            return self._deny(packet, [f"no agent available for domain '{packet.domain}'"],
                              actor=principal.user_id)

        escalate = decision.outcome is PolicyOutcome.ESCALATE
        entry = self.audit.record(
            actor=f"{principal.org_id}/{principal.user_id}", action="mesh_dispatch",
            detail={"agent": agent.name, "domain": packet.domain, "mission": packet.mission.value,
                    "outcome": "ESCALATE" if escalate else "ACCEPTED",
                    "individual": packet.target_is_individual})
        return Tasking(
            dispatch=Dispatch.ESCALATE if escalate else Dispatch.ACCEPTED,
            reasons=(["human review required"] + list(decision.reasons)) if escalate
                    else ["org-authorized + within approved OSINT scope"],
            identity=TRANSPARENT_IDENTITY, agent=agent.name, packet_domain=packet.domain,
            report_template=self._report_template(packet, agent),
            audit_ref=entry.entry_hash[:12], requires_human_review=escalate,
        )

    def _deny(self, packet: MissionPacket, reasons: list[str], *, actor: str) -> Tasking:
        entry = self.audit.record(actor=actor, action="mesh_dispatch",
                                  detail={"domain": packet.domain, "mission": packet.mission.value,
                                          "outcome": "DENIED", "reasons": reasons})
        return Tasking(Dispatch.DENIED, reasons, TRANSPARENT_IDENTITY, None,
                       packet.domain, {}, entry.entry_hash[:12])

    @staticmethod
    def _report_template(packet: MissionPacket, agent: Agent) -> dict:
        """The structured report shape an accepted mission returns — entities,
        relationships, timestamps, confidence; ClearGlass-processed summaries
        only (never raw third-party data)."""
        return {
            "agent": agent.name,
            "target": packet.target,
            "domain": packet.domain,
            "schema": {
                "entities": "[{id, type, name}]  (organizations/assets only)",
                "relationships": "[{from, to, kind, confidence}]",
                "timestamps": "[ISO 8601]",
                "confidence": "0..1 per finding",
                "anomalies": "[pattern/flag, rationale]",
                "provenance": "approved source + collected_at; aggregate summaries only",
            },
            "constraints": {"time_window": packet.time_window,
                            "jurisdiction": packet.jurisdiction or "unspecified"},
        }
