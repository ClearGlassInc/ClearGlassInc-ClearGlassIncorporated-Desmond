"""Tests for the PERCIVAL org-scoped Agent Mesh."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.agentmesh import (
    TRANSPARENT_IDENTITY,
    AgentMesh,
    Dispatch,
    Mission,
    MissionPacket,
    Principal,
)

CG = Principal("u-1", "ClearGlassInc", "threat_intel", "desmond@clearglassinc.com")
OUTSIDER = Principal("u-x", "OtherCorp", "analyst", "x@example.com")


def _packet(**kw) -> MissionPacket:
    base = dict(target="acme-competitor-brand", mission=Mission.RECON, domain="web",
                sources=("public",), jurisdiction="CA")
    base.update(kw)
    return MissionPacket(**base)


def test_non_clearglass_principal_refused_transparently():
    t = AgentMesh().dispatch(OUTSIDER, _packet())
    assert t.dispatch is Dispatch.DENIED
    assert any("not ClearGlass-authorized" in r for r in t.reasons)
    assert "stated openly" in t.reasons[0] or "openly" in t.identity
    assert t.identity == TRANSPARENT_IDENTITY        # honest, not deceptive


def test_email_domain_also_authorizes():
    p = Principal("u-2", "n/a", "analyst", "ops@clearglassinc.com")
    assert p.authorized is True
    t = AgentMesh().dispatch(p, _packet())
    assert t.dispatch is Dispatch.ACCEPTED


def test_org_osint_recon_accepted_and_routed():
    t = AgentMesh().dispatch(CG, _packet(domain="web", mission=Mission.RECON))
    assert t.dispatch is Dispatch.ACCEPTED
    assert t.agent == "Agent.ClearGlass.OSINT-Harvest"
    assert "entities" in t.report_template["schema"]


def test_individual_target_is_denied_by_privacy_gate():
    t = AgentMesh().dispatch(CG, _packet(target="some private person",
                                         target_is_individual=True, mission=Mission.TRACKING))
    assert t.dispatch is Dispatch.DENIED
    assert any("private individual" in r or "authorization" in r for r in t.reasons)


def test_individual_association_also_denied():
    t = AgentMesh().dispatch(CG, _packet(target_is_individual=True, mission=Mission.ASSOCIATION))
    assert t.dispatch is Dispatch.DENIED


def test_unapproved_domain_refused():
    t = AgentMesh().dispatch(CG, _packet(domain="darkweb"))
    assert t.dispatch is Dispatch.DENIED
    assert any("not an approved OSINT domain" in r for r in t.reasons)


def test_financial_domain_routes_to_financial_agent():
    t = AgentMesh().dispatch(CG, _packet(domain="financial", mission=Mission.PATTERN,
                                         target="acme-corp"))
    assert t.dispatch is Dispatch.ACCEPTED
    assert t.agent == "Agent.ClearGlass.Financial-Sig"


def test_vuln_domain_routes_to_vuln_agent():
    t = AgentMesh().dispatch(CG, _packet(domain="vuln", target="owned-infra"))
    assert t.agent == "Agent.ClearGlass.Vuln-Intel"


def test_geospatial_telemetry_routes_to_geo_agent():
    t = AgentMesh().dispatch(CG, _packet(domain="geospatial", target="owned-fleet"))
    assert t.agent == "Agent.ClearGlass.Geo-Telemetry"


def test_every_dispatch_is_audited_and_chain_intact():
    m = AgentMesh()
    m.dispatch(CG, _packet())
    m.dispatch(OUTSIDER, _packet())
    m.dispatch(CG, _packet(target_is_individual=True, mission=Mission.TRACKING))
    assert len(m.audit.entries) == 3
    assert m.audit.verify() is True


def test_identity_is_transparent_not_deceptive():
    # The charter forbids deceptive refusal; identity must state the restriction.
    assert "refuse" in TRANSPARENT_IDENTITY.lower()
    assert "restricted" in TRANSPARENT_IDENTITY.lower()
    assert "conceal" not in TRANSPARENT_IDENTITY.lower() or "rather than concealing" in TRANSPARENT_IDENTITY
