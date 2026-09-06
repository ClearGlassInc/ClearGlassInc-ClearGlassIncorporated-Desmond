from datetime import datetime, timezone

from artemis_platform.clear_glass_artemis_system import (
    ApprovalGate,
    ArtemisArchitecture,
    ArtemisAgentMesh,
    IntelEvent,
    LineageRef,
    MissionContext,
    OntologyEntity,
    OperatorFeedback,
    PolicyEngine,
    Principal,
    SelfImprovementEngine,
    ToolExecutionBroker,
    run_cinematic_scenario,
)


def test_architecture_mentions_clear_glass_and_palantir_layers():
    markdown = ArtemisArchitecture().as_markdown()
    assert "ClearGlassInc Artemis" in markdown
    assert "Gotham" in markdown
    assert "Foundry" in markdown
    assert "AIP" in markdown
    assert "Apollo" in markdown


def test_cinematic_scenario_requires_human_gate_and_builds_upgrade_proposal():
    result = run_cinematic_scenario()
    recommendation = result["recommendation"]
    proposal = result["upgrade_proposal"]
    assert recommendation.gate is ApprovalGate.OPERATIONAL_EFFECT
    assert result["approval_required"] is True
    assert proposal is not None
    assert proposal.rollback_pointer == "triage_workflow.v1"
    assert result["promotion_decision"] in {"approve", "reject", "revise"}


def test_self_improvement_requires_enough_feedback_before_proposing():
    engine = SelfImprovementEngine()
    feedback = [OperatorFeedback("r1", "approve", "good", 0.9, 100)]
    assert engine.propose(feedback, "v1", [0.8, 0.81, 0.82, 0.83, 0.84]) is None


def test_tool_execution_broker_blocks_operational_effect_without_human_approval():
    policy = PolicyEngine()
    mission = MissionContext(
        mission_id="ARTEMIS-MSN-BROKER",
        objective="Validate tool gating",
        commander_intent="Fail closed before operational effects",
        allowed_tools=frozenset({"prepare_action_package"}),
        prohibited_tools=frozenset(),
        compartments=frozenset({"CYBER"}),
        coalition=frozenset({"FVEY"}),
    )
    principal = Principal(
        principal_id="operator.artemis.watchfloor",
        clearance="SECRET",
        compartments=frozenset({"CYBER"}),
        coalition=frozenset({"FVEY"}),
        purpose="mission_operations",
    )
    payload = {"sensor": "foundry.live.alerts", "severity": 0.9}
    entity = OntologyEntity(
        entity_id="evt-gated-action",
        entity_type="event",
        name="Gated operational event",
        classification="SECRET",
        compartments=frozenset({"CYBER"}),
        coalition_releasability=frozenset({"FVEY"}),
        confidence=0.95,
        valid_from=datetime.now(timezone.utc),
        attributes=payload,
        lineage=(LineageRef.from_payload("foundry_stream", "ri.foundry.dataset.alerts", "normalize.v1", payload),),
    )
    recommendation = ArtemisAgentMesh(policy).triage(
        IntelEvent("live-broker-1", entity, 0.9, "Operationally significant alert"),
        principal,
        mission,
    )

    broker = ToolExecutionBroker(policy)
    denied = broker.evaluate(principal, mission, recommendation)
    approved = broker.evaluate(principal, mission, recommendation, approved_by="operator.approver")

    assert denied.allowed is False
    assert denied.redacted_reason == "Human approval is required before execution."
    assert approved.allowed is True
    assert broker.dispatch(approved)["status"] == "queued_for_adapter_dispatch"
