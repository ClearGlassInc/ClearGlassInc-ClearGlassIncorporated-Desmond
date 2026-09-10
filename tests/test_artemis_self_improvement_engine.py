from datetime import datetime, timezone

from tools.artemis_self_improvement_engine import (
    ApprovalDecision,
    ApprovalState,
    ArtemisImprovementEngine,
    ChangeProposal,
    EvalResult,
    FeedbackSignal,
    GovernedProposalLifecycle,
    ProposalType,
    SignalType,
)


def _signal(signal_id: str, signal_type: SignalType, payload: dict) -> FeedbackSignal:
    return FeedbackSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        mission_id="mission-alpha",
        ontology_object_id="alert-001",
        actor="operator.test",
        classification="SECRET",
        compartment="ARTEMIS",
        payload=payload,
        observed_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )


def _passing_proposal() -> ChangeProposal:
    return ChangeProposal(
        proposal_id="prop-mission-alpha-triage-001",
        proposal_type=ProposalType.PROMPT_PATCH,
        target_component="aip.agent.triage_copilot",
        current_version="2.4.9",
        proposed_version="2.4.10",
        rationale="Improve evidence thresholds after verified operator corrections.",
        patch={"minimum_evidence": 2},
        evidence_hashes=["sha256:evidence"],
        eval_result=EvalResult(0.96, 0.90, 410.0, 0.87, 0, 50),
        approval_state=ApprovalState.NEEDS_HUMAN_APPROVAL,
        policy_decision="human_approval_required",
        rollback_version="2.4.9",
    )


def _approval(
    lifecycle: GovernedProposalLifecycle, proposal: ChangeProposal
) -> ApprovalDecision:
    return ApprovalDecision(
        proposal_id=proposal.proposal_id,
        manifest_digest=lifecycle.manifest_digest(proposal),
        reviewer="reviewer.artemis",
        reviewer_roles=frozenset({"mission_owner", "model_governance"}),
        decision="approve",
        rationale="Offline evidence and rollback controls satisfy the release gate.",
    )


def test_three_operator_corrections_generate_human_approved_prompt_proposal() -> None:
    engine = ArtemisImprovementEngine({"aip.agent.triage_copilot": "2.4.9"})
    signals = [
        _signal(
            "s1",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "missed_context", "theme": "temporal_linkage"},
        ),
        _signal(
            "s2",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "false_positive", "theme": "evidence_threshold"},
        ),
        _signal(
            "s3",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "missed_context", "theme": "coalition_caveat"},
        ),
        _signal("s4", SignalType.ALERT_OUTCOME, {"final_disposition": "validated"}),
        _signal("s5", SignalType.LATENCY_SAMPLE, {"latency_ms": 412}),
    ]

    proposals = engine.synthesize_proposals(signals)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == ProposalType.PROMPT_PATCH
    assert proposal.current_version == "2.4.9"
    assert proposal.proposed_version == "2.4.10"
    assert proposal.approval_required is True
    assert proposal.rollout_ring == "staging-canary"
    assert "Never convert a recommendation" in " ".join(proposal.patch["guardrail_additions"])
    assert proposal.signed_manifest["signature"]


def test_fewer_than_three_operator_corrections_do_not_generate_proposal() -> None:
    engine = ArtemisImprovementEngine({"aip.agent.triage_copilot": "2.4.9"})
    signals = [
        _signal("s1", SignalType.OPERATOR_CORRECTION, {"correction": "missed_context"}),
        _signal("s2", SignalType.OPERATOR_CORRECTION, {"correction": "false_positive"}),
    ]

    assert engine.synthesize_proposals(signals) == []


def test_generated_proposal_carries_eval_gate_and_drift_controls() -> None:
    engine = ArtemisImprovementEngine({"aip.agent.triage_copilot": "2.4.9"})
    signals = [
        _signal(
            "s1",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "missed_context", "theme": "temporal_linkage"},
        ),
        _signal(
            "s2",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "missed_context", "theme": "temporal_linkage"},
        ),
        _signal(
            "s3",
            SignalType.OPERATOR_CORRECTION,
            {"correction": "missed_context", "theme": "temporal_linkage"},
        ),
    ]

    proposal = engine.synthesize_proposals(signals)[0]

    assert proposal.approval_state.value == "eval_failed"
    assert proposal.policy_decision == "blocked_eval_threshold"
    assert proposal.drift_score == 1.0
    assert proposal.patch["rollout_controls"] == {
        "canary_percentage": 5,
        "rollback_on_policy_violation": True,
        "rollback_on_p95_latency_ms": 1200,
    }


def test_invalid_component_version_fails_closed() -> None:
    engine = ArtemisImprovementEngine({"aip.agent.triage_copilot": "latest"})
    signals = [
        _signal("s1", SignalType.OPERATOR_CORRECTION, {"correction": "missed_context"}),
        _signal("s2", SignalType.OPERATOR_CORRECTION, {"correction": "false_positive"}),
        _signal("s3", SignalType.OPERATOR_CORRECTION, {"correction": "missed_context"}),
    ]

    try:
        engine.synthesize_proposals(signals)
    except ValueError as exc:
        assert "MAJOR.MINOR.PATCH" in str(exc)
    else:
        raise AssertionError("invalid component versions must fail closed")


def test_entity_merge_corrections_create_draft_only_human_review() -> None:
    engine = ArtemisImprovementEngine({"ontology.entity_resolution": "1.3.5"})
    signals = [
        _signal(
            "m1",
            SignalType.ENTITY_MERGE_CORRECTION,
            {"candidate_pair": ["person-a", "person-b"], "theme": "duplicate_identity"},
        ),
        _signal(
            "m2",
            SignalType.ENTITY_MERGE_CORRECTION,
            {"candidate_pair": ["person-a", "person-b"], "theme": "duplicate_identity"},
        ),
    ]

    proposal = engine.synthesize_proposals(signals)[0]

    assert proposal.proposal_type == ProposalType.ONTOLOGY_MERGE_REVIEW
    assert proposal.current_version == "1.3.5"
    assert proposal.proposed_version == "1.3.6"
    assert proposal.patch["merge_execution"] == "draft_only_until_approved"
    assert proposal.policy_decision == "human_approval_required_entity_merge"
    assert proposal.risk_tier == "high"
    assert proposal.rollback_version == "1.3.5"


def test_cross_compartment_entity_merge_fails_closed() -> None:
    def signal(signal_id: str, compartment: str) -> FeedbackSignal:
        base = _signal(
            signal_id,
            SignalType.ENTITY_MERGE_CORRECTION,
            {"candidate_pair": ["device-a", "device-b"], "theme": "duplicate_asset"},
        )
        return FeedbackSignal(
            base.signal_id,
            base.signal_type,
            base.mission_id,
            base.ontology_object_id,
            base.actor,
            base.classification,
            compartment,
            base.payload,
            base.observed_at,
        )

    engine = ArtemisImprovementEngine({"ontology.entity_resolution": "1.3.5"})
    proposal = engine.synthesize_proposals([signal("m1", "ARTEMIS"), signal("m2", "PARTNER")])[0]

    assert proposal.approval_state.value == "blocked_policy_boundary"
    assert proposal.policy_decision == "blocked_cross_compartment_merge"
    assert proposal.proposed_version == "1.3.5"
    assert proposal.risk_tier == "critical"


def test_user_facing_payload_is_sanitized_in_proposal_manifest() -> None:
    engine = ArtemisImprovementEngine({"ontology.entity_resolution": "1.3.5"})
    proposal = engine.synthesize_proposals(
        [
            _signal(
                "m1",
                SignalType.ENTITY_MERGE_CORRECTION,
                {"candidate_pair": ["<script>alert(1)</script>", "person-b"]},
            ),
            _signal(
                "m2",
                SignalType.ENTITY_MERGE_CORRECTION,
                {"candidate_pair": ["<script>alert(1)</script>", "person-b"]},
            ),
        ]
    )[0]

    manifest = proposal.signed_manifest

    assert "<script>" not in str(manifest)
    assert "&lt;script&gt;" in str(manifest)


def test_governed_lifecycle_requires_exact_manifest_and_dual_role_authority() -> None:
    lifecycle = GovernedProposalLifecycle()
    proposal = _passing_proposal()
    stale_decision = ApprovalDecision(
        proposal_id=proposal.proposal_id,
        manifest_digest="0" * 64,
        reviewer="reviewer.artemis",
        reviewer_roles=frozenset({"mission_owner", "model_governance"}),
        decision="approve",
        rationale="Reviewed.",
    )

    try:
        lifecycle.approve_for_canary(proposal, stale_decision)
    except PermissionError as exc:
        assert "changed after approval" in str(exc)
    else:
        raise AssertionError("a stale approval must fail closed")

    underprivileged_decision = ApprovalDecision(
        proposal_id=proposal.proposal_id,
        manifest_digest=lifecycle.manifest_digest(proposal),
        reviewer="reviewer.artemis",
        reviewer_roles=frozenset({"mission_owner"}),
        decision="approve",
        rationale="Reviewed.",
    )
    try:
        lifecycle.approve_for_canary(proposal, underprivileged_decision)
    except PermissionError as exc:
        assert "required approval roles" in str(exc)
    else:
        raise AssertionError("single-role authority must fail closed")

    assert lifecycle.records == ()


def test_governed_lifecycle_never_promotes_without_human_approval() -> None:
    lifecycle = GovernedProposalLifecycle()

    try:
        lifecycle.start_canary(_passing_proposal(), "apollo.controller")
    except PermissionError as exc:
        assert "valid human approval" in str(exc)
    else:
        raise AssertionError("canary must not start without human approval")


def test_governed_lifecycle_emits_promotion_intent_and_verifiable_audit_chain() -> None:
    lifecycle = GovernedProposalLifecycle()
    proposal = _passing_proposal()
    approved = lifecycle.approve_for_canary(proposal, _approval(lifecycle, proposal))
    active = lifecycle.start_canary(approved, "apollo.controller")
    promoted = lifecycle.complete_canary(
        active,
        EvalResult(0.97, 0.91, 430.0, 0.89, 0, 100),
        "modelops.monitor",
    )

    assert promoted.approval_state == ApprovalState.PROMOTED
    assert promoted.policy_decision == "canary_passed_release_intent"
    assert [record.event_type for record in lifecycle.records] == [
        "proposal.approved",
        "canary.started",
        "proposal.promotion_intent",
    ]
    assert lifecycle.verify_audit_chain() is True


def test_canary_policy_violation_rolls_back_instead_of_promoting() -> None:
    lifecycle = GovernedProposalLifecycle()
    proposal = _passing_proposal()
    approved = lifecycle.approve_for_canary(proposal, _approval(lifecycle, proposal))
    active = lifecycle.start_canary(approved, "apollo.controller")
    rolled_back = lifecycle.complete_canary(
        active,
        EvalResult(0.98, 0.95, 390.0, 0.92, 1, 100),
        "modelops.monitor",
    )

    assert rolled_back.approval_state == ApprovalState.ROLLED_BACK
    assert rolled_back.rollback_version == "2.4.9"
    assert lifecycle.records[-1].event_type == "canary.rolled_back"
