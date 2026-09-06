from artemis_legal_agent_mvp import (
    EFFICIENCY_TARGET_MULTIPLE,
    DocumentProcessorAgent,
    LegalCaseState,
    LegalDocument,
    LegalTechWorkflow,
    RecommendationAgent,
    RiskCorrelationAgent,
    RiskLevel,
    _UnstableEnrichmentAgent,
    demo_exception_scenario,
    demo_matter,
    efficiency_report,
    evaluate_workflow,
)


def test_demo_workflow_uses_multiple_agents_and_preserves_counsel_gate():
    state = LegalTechWorkflow().run(demo_matter())

    assert len(LegalTechWorkflow().agents) >= 2
    assert state.approval_required is True
    assert state.risk_level is RiskLevel.CRITICAL
    assert "privacy_ai" in state.extracted_clauses
    assert "Northstar Holdings LLC" in state.osint_entities
    assert any("recommendation_agent" in item for item in state.trace)


def test_eval_harness_meets_less_than_five_percent_error_target():
    fixtures = [
        (demo_matter(), RiskLevel.CRITICAL),
        (
            LegalCaseState(
                matter_id="low-001",
                jurisdiction="Ontario",
                documents=[LegalDocument("d1", "NDA", "The parties exchange general business information.")],
            ),
            RiskLevel.LOW,
        ),
        (
            LegalCaseState(
                matter_id="medium-001",
                jurisdiction="Delaware",
                documents=[LegalDocument("d2", "Terms", "Acme Corp may terminate for default. Governing law is Delaware.")],
            ),
            RiskLevel.MEDIUM,
        ),
    ]

    metrics = evaluate_workflow(fixtures)

    assert metrics["error_rate"] < 0.05
    assert metrics["counsel_gate_rate"] == 1.0


def test_failing_agent_is_isolated_and_workflow_completes():
    state = demo_exception_scenario()

    # The enrichment agent raised, but the pipeline still produced a packet.
    assert len(state.exceptions) == 1
    assert state.exceptions[0].agent == "osint_enrichment_agent"
    assert "ConnectionError" in state.exceptions[0].error
    assert state.degraded is True
    assert state.recommendations  # downstream agents still ran
    assert any("fail-closed" in line for line in state.trace)


def test_exception_forces_counsel_gate_and_escalates_low_risk():
    # A low-risk matter that would normally auto-classify LOW must escalate when
    # an agent fails, because handled exceptions are fail-closed.
    workflow = LegalTechWorkflow(agents=[
        DocumentProcessorAgent(),
        _UnstableEnrichmentAgent(),
        RiskCorrelationAgent(),
        RecommendationAgent(),
    ])
    benign = LegalCaseState(
        matter_id="benign-001",
        jurisdiction="Ontario",
        documents=[LegalDocument("d0", "Memo", "The parties exchange general business information.")],
    )

    result = workflow.run(benign)

    assert result.approval_required is True
    assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_transient_error_recovers_on_retry():
    class FlakyAgent(DocumentProcessorAgent):
        name = "document_processor_agent"

        def __init__(self) -> None:
            self.calls = 0

        def run(self, state):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("model warm-up")
            return super().run(state)

    flaky = FlakyAgent()
    workflow = LegalTechWorkflow(agents=[flaky], max_attempts=2)
    result = workflow.run(demo_matter())

    assert flaky.calls == 2
    assert result.exceptions == []  # recovered, not quarantined
    assert result.degraded is False


def test_efficiency_gain_meets_3x_baseline_target():
    report = efficiency_report(matters=1)

    assert report["efficiency_multiple"] >= EFFICIENCY_TARGET_MULTIPLE
    assert report["meets_3x_target"] is True
    assert report["minutes_saved"] > 0
    # Scaling across a batch preserves the same per-matter multiple.
    assert efficiency_report(matters=100)["efficiency_multiple"] == report["efficiency_multiple"]
