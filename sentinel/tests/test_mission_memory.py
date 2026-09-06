# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for sentinel/sentinel/mission_memory.py — Percival's persistent,
governed operator model."""
from __future__ import annotations

import pytest

from sentinel.mission_memory import (
    SECTIONS,
    Feedback,
    MemoryItem,
    MissionMemory,
    requires_approval,
)


# --------------------------------------------------------------------------- #
# remember / provenance / no-fabrication
# --------------------------------------------------------------------------- #
def test_remember_stores_with_provenance():
    mem = MissionMemory()
    item = mem.remember("goals", "Ship governed commerce OS", source="operator:kickoff")
    assert isinstance(item, MemoryItem)
    assert item.section == "goals"
    assert item.source == "operator:kickoff"
    assert item.confidence == "stated"
    assert mem.items("goals")[0].content == "Ship governed commerce OS"


def test_remember_requires_source():
    mem = MissionMemory()
    with pytest.raises(ValueError):
        mem.remember("goals", "unsourced claim", source="   ")


def test_remember_rejects_unknown_section():
    mem = MissionMemory()
    with pytest.raises(ValueError):
        mem.remember("nonsense", "x", source="op")


def test_remember_rejects_bad_confidence():
    mem = MissionMemory()
    with pytest.raises(ValueError):
        mem.remember("risks", "x", source="op", confidence="maybe")


def test_inferred_items_are_labeled_in_briefing():
    mem = MissionMemory()
    mem.remember("constraints", "Budget likely under $5k/mo", source="percival:inference", confidence="inferred")
    briefing = mem.briefing()
    assert "inferred — unverified" in briefing


# --------------------------------------------------------------------------- #
# forget
# --------------------------------------------------------------------------- #
def test_forget_removes_and_is_idempotent():
    mem = MissionMemory()
    item = mem.remember("projects", "Percival v3", source="op")
    assert mem.forget(item.id) is True
    assert mem.forget(item.id) is False
    assert mem.items("projects") == []


# --------------------------------------------------------------------------- #
# feedback / adaptive depth
# --------------------------------------------------------------------------- #
def test_feedback_clamps_and_records():
    mem = MissionMemory()
    fb = mem.record_feedback("weekly brief", 9, "too long")
    assert isinstance(fb, Feedback)
    assert fb.rating == 2  # clamped


def test_preferred_depth_adapts_to_feedback():
    mem = MissionMemory()
    assert mem.preferred_depth() == "balanced"
    mem.record_feedback("brief", 2)
    mem.record_feedback("brief", 2)
    assert mem.preferred_depth() == "concise"
    neg = MissionMemory()
    neg.record_feedback("brief", -2)
    assert neg.preferred_depth() == "thorough"


# --------------------------------------------------------------------------- #
# reconstruction
# --------------------------------------------------------------------------- #
def test_reconstruct_covers_all_sections_and_counts():
    mem = MissionMemory()
    mem.remember("goals", "g1", source="op")
    mem.remember("risks", "r1", source="op")
    model = mem.reconstruct()
    assert set(model["operator_model"]) == SECTIONS
    assert model["counts"] == {"goals": 1, "risks": 1}
    assert model["total_items"] == 2
    assert model["audit_ok"] is True


def test_empty_briefing_does_not_fabricate():
    mem = MissionMemory()
    assert "will not fabricate" in mem.briefing()


def test_mission_graph_sections_supported():
    # v4/v5 mission graph: dependencies, approval boundaries, approved workflows,
    # and decision history are first-class sections.
    for section in ("dependencies", "approval_boundaries", "approved_workflows", "decision_history"):
        assert section in SECTIONS
    mem = MissionMemory()
    dep = mem.remember("dependencies", "Storefront deploy blocks payout tests", source="op")
    bnd = mem.remember("approval_boundaries", "Any pricing change requires founder sign-off", source="op")
    wf = mem.remember("approved_workflows", "Weekly SEO sweep via seo_optimizer_bot", source="op")
    hist = mem.remember("decision_history", "Chose Interac e-Transfer over publishing bank details", source="op")
    assert mem.items("dependencies")[0].id == dep.id
    assert mem.items("approval_boundaries")[0].id == bnd.id
    assert mem.items("approved_workflows")[0].id == wf.id
    assert mem.items("decision_history")[0].id == hist.id


# --------------------------------------------------------------------------- #
# persistence round-trip + audit integrity
# --------------------------------------------------------------------------- #
def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "mission.json"
    mem = MissionMemory(path)
    mem.remember("stakeholders", "Founder: Desmond", source="op")
    mem.record_feedback("intro", 1)

    reloaded = MissionMemory(path)
    items = reloaded.items("stakeholders")
    assert len(items) == 1
    assert items[0].content == "Founder: Desmond"
    # Feedback survived the round-trip and still drives adaptive depth.
    assert reloaded.preferred_depth() == "concise"


def test_audit_chain_verifies():
    mem = MissionMemory()
    mem.remember("deadlines", "Launch Q3", source="op")
    mem.forget(mem.items("deadlines")[0].id)
    assert mem.verify() is True


# --------------------------------------------------------------------------- #
# approval gating (fail-closed)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "kind",
    ["money_movement", "pricing_change", "payment", "refund", "fulfillment",
     "production_change", "external_send", "destructive", "credential_access"],
)
def test_sensitive_actions_require_approval(kind):
    assert requires_approval(kind) is True


def test_unknown_action_fails_closed():
    assert requires_approval("frobnicate") is True


def test_safe_read_actions_pass():
    for kind in ("read", "summarize", "draft", "analyze", "recall"):
        assert requires_approval(kind) is False


def test_high_risk_safe_kind_still_gated():
    assert requires_approval("draft", technical_risk=5) is True
