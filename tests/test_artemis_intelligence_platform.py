from dataclasses import replace
from datetime import UTC, datetime, timedelta

from artemis.intelligence import (
    AccessContext,
    AgentAction,
    ApprovalGate,
    Alert,
    FeedbackEvent,
    ImmutableAuditLog,
    ModelRouter,
    OntologyEntity,
    PromotionController,
    ReleaseCandidate,
    SelfImprovementEngine,
    compile_feedback_to_eval,
    WorkflowState,
)
from artemis.intelligence.platform import InMemoryOntologyStore, PolicyEngine, TriageAgent


def test_triage_agent_requires_approval_for_visible_alert() -> None:
    ontology = InMemoryOntologyStore()
    ontology.entities["entity-1"] = OntologyEntity(
        entity_id="entity-1",
        kind="infrastructure",
        canonical_name="edge-node-17",
        confidence=0.91,
        markings=frozenset({"ARTEMIS"}),
        lineage=("obs-1",),
    )
    context = AccessContext(
        operator_id="op-1",
        roles=frozenset({"analyst"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="triage",
    )
    alert = Alert(
        alert_id="alert-1",
        mission_id="mission-1",
        severity="high",
        hypothesis="Suspicious infrastructure behavior",
        entity_ids=("entity-1",),
        evidence_refs=("obs-1",),
        markings=frozenset({"ARTEMIS"}),
        workflow_state=WorkflowState.RECEIVED,
    )

    action = TriageAgent(ontology, PolicyEngine()).triage(context, alert)

    assert action.required_approval is True
    assert action.risk_tier == "high"
    assert action.parameters["visible_entity_count"] == 1


def test_self_improvement_requires_eval_gates() -> None:
    engine = SelfImprovementEngine(minimum_precision=0.90, maximum_latency_ms=1_500)
    feedback = [
        FeedbackEvent(
            feedback_id="fb-1",
            operator_id="op-1",
            artifact_id="alert-1",
            workflow_version="triage.v1",
            rating=1,
            correction="Maintenance window was not considered before escalation.",
            outcome="false_positive",
        )
    ]

    proposal = engine.proposal_from_feedback(
        feedback=feedback,
        target="triage_prompt",
        current_version="triage.v1",
        candidate_prompt="Check maintenance windows before severity escalation.",
        eval_metrics={"precision": 0.94, "recall": 0.91, "p95_latency_ms": 900},
    )

    assert proposal is not None
    assert proposal.requires_human_approval is True
    assert proposal.candidate_version.startswith("triage.v1+")


def test_approval_gate_blocks_high_risk_non_commander_and_audits() -> None:
    context = AccessContext(
        operator_id="analyst-1",
        roles=frozenset({"analyst"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="triage",
    )
    action = AgentAction(
        action_id="act-1",
        action_type="operational_posture_change",
        mission_id="mission-1",
        risk_tier="critical",
        summary="Increase monitoring posture.",
        required_approval=True,
        evidence_refs=("obs-1",),
        parameters={},
    )
    audit_log = ImmutableAuditLog()

    decision = ApprovalGate(PolicyEngine(), audit_log).approve(
        context, action, decision="approve", reason="operator requested posture change"
    )

    assert decision.allowed is False
    assert decision.reason == "high-risk action requires commander role"
    assert audit_log.verify() is True
    assert audit_log.records[0].decision == "REJECT"


def test_approval_token_is_package_bound_short_lived_and_single_use() -> None:
    context = AccessContext(
        operator_id="commander-1",
        roles=frozenset({"commander"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="command_briefing",
    )
    action = AgentAction(
        action_id="act-approved",
        action_type="operational_posture_change",
        mission_id="mission-1",
        risk_tier="critical",
        summary="Increase monitoring posture.",
        required_approval=True,
        evidence_refs=("obs-1",),
        parameters={"posture": "heightened"},
    )
    decided_at = datetime(2026, 7, 26, 12, tzinfo=UTC)
    audit_log = ImmutableAuditLog()
    gate = ApprovalGate(PolicyEngine(), audit_log)

    token = gate.approve_and_issue(
        context,
        action,
        decision="approve",
        reason="validated against mission intent",
        ttl=timedelta(minutes=5),
        now=decided_at,
    )

    assert token is not None
    assert gate.consume(token, action, now=decided_at + timedelta(minutes=1)).allowed is True
    replay = gate.consume(token, action, now=decided_at + timedelta(minutes=2))
    assert replay.allowed is False
    assert replay.reason == "approval token already consumed"
    assert audit_log.verify() is True


def test_approval_token_rejects_expired_or_mutated_action_package() -> None:
    context = AccessContext(
        operator_id="commander-1",
        roles=frozenset({"commander"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="command_briefing",
    )
    action = AgentAction(
        action_id="act-bound",
        action_type="notify_commander",
        mission_id="mission-1",
        risk_tier="high",
        summary="Send the reviewed warning.",
        required_approval=True,
        evidence_refs=("obs-2",),
        parameters={"audience": "watch-floor"},
    )
    decided_at = datetime(2026, 7, 26, 12, tzinfo=UTC)
    gate = ApprovalGate(PolicyEngine(), ImmutableAuditLog())
    token = gate.approve_and_issue(
        context, action, decision="approve", reason="release authorized", now=decided_at
    )

    assert token is not None
    mutated = replace(action, parameters={"audience": "external-partner"})
    mutation_decision = gate.consume(token, mutated, now=decided_at + timedelta(minutes=1))
    expiry_decision = gate.consume(token, action, now=decided_at + timedelta(minutes=6))
    assert mutation_decision.allowed is False
    assert mutation_decision.reason == "action package changed after approval"
    assert expiry_decision.allowed is False
    assert expiry_decision.reason == "approval token expired"


def test_model_router_uses_hardened_path_for_restricted_data() -> None:
    route = ModelRouter().route(
        task_type="correlation",
        classification="COALITION_RESTRICTED",
        latency_budget_ms=250,
        requires_deep_reasoning=False,
    )

    assert route.model_id == "aip-secure-reasoner"
    assert route.execution_tier == "isolated"


def test_feedback_compiles_to_eval_case_without_secret_payloads() -> None:
    feedback = FeedbackEvent(
        feedback_id="fb-42",
        operator_id="operator-7",
        artifact_id="recommendation-9",
        workflow_version="commander.v3",
        rating=1,
        correction="Require fresh lineage before recommending isolation.",
        outcome="rejected_operational_risk",
    )

    eval_case = compile_feedback_to_eval(feedback)

    assert eval_case["eval_id"] == "eval-fb-42"
    assert eval_case["source_feedback_ids"] == ["fb-42"]
    assert eval_case["expected_behavior"]["correction"] == "Require fresh lineage before recommending isolation."
    assert "operator-7" not in repr(eval_case)


def test_promotion_controller_blocks_unapproved_candidate_and_audits() -> None:
    context = AccessContext(
        operator_id="modelops-1",
        roles=frozenset({"modelops"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="evaluation",
    )
    candidate = ReleaseCandidate(
        candidate_id="rc-1",
        proposal_id="proposal-1",
        artifact_type="prompt",
        baseline_version="triage.v1",
        candidate_version="triage.v2",
        rollback_version="triage.v1",
        eval_metrics={"precision": 0.96, "recall": 0.91, "p95_latency_ms": 850},
        human_approved=False,
    )
    audit_log = ImmutableAuditLog()

    decision = PromotionController(SelfImprovementEngine(), audit_log).review_for_canary(
        context, candidate
    )

    assert decision.safe_to_review is False
    assert decision.canary_allowed is False
    assert decision.rollback_version == "triage.v1"
    assert "human approval is required" in decision.reasons
    assert audit_log.records[0].decision == "DENY"
    assert audit_log.verify() is True


def test_promotion_controller_allows_human_approved_candidate_with_stable_rollback() -> None:
    context = AccessContext(
        operator_id="modelops-1",
        roles=frozenset({"modelops"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="evaluation",
    )
    candidate = ReleaseCandidate(
        candidate_id="rc-2",
        proposal_id="proposal-2",
        artifact_type="workflow",
        baseline_version="alert_graph.v4",
        candidate_version="alert_graph.v5",
        rollback_version="alert_graph.v4",
        eval_metrics={"precision": 0.96, "recall": 0.91, "p95_latency_ms": 850},
        human_approved=True,
    )

    decision = PromotionController(SelfImprovementEngine(), ImmutableAuditLog()).review_for_canary(
        context, candidate
    )

    assert decision.safe_to_review is True
    assert decision.canary_allowed is True
    assert decision.reasons == ()


def test_promotion_controller_requires_evaluation_purpose() -> None:
    context = AccessContext(
        operator_id="modelops-1",
        roles=frozenset({"modelops"}),
        mission_ids=frozenset({"mission-1"}),
        compartments=frozenset({"ARTEMIS"}),
        coalition="internal",
        purpose="investigation",
    )
    candidate = ReleaseCandidate(
        candidate_id="rc-3",
        proposal_id="proposal-3",
        artifact_type="model_route",
        baseline_version="router.v2",
        candidate_version="router.v3",
        rollback_version="router.v2",
        eval_metrics={"precision": 0.96, "recall": 0.91, "p95_latency_ms": 850},
        human_approved=True,
    )

    decision = PromotionController(SelfImprovementEngine(), ImmutableAuditLog()).review_for_canary(
        context, candidate
    )

    assert decision.safe_to_review is False
    assert decision.canary_allowed is False
    assert "canary review requires evaluation purpose" in decision.reasons
