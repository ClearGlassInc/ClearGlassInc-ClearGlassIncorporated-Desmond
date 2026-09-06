from legal_intelligence_core import (
    AUTHORITY_HIERARCHY,
    LegalAssignment,
    LegalStatus,
    SupremeLegalIntelligenceCore,
    render_single_page_elite_prompt,
)


def test_prompt_contains_command_hierarchy_and_boundary() -> None:
    prompt = render_single_page_elite_prompt()
    assert "Supreme legal intelligence core" in prompt
    assert "Controlling constitutional" in prompt
    assert "Never treat guidance as legislation" in prompt
    assert "must never claim to be a licensed lawyer" in prompt
    assert LegalStatus.COUNSEL_AUTHORIZATION_REQUIRED.value in prompt


def test_authority_hierarchy_is_ranked_strongest_to_weakest() -> None:
    ranks = [tier.rank for tier in AUTHORITY_HIERARCHY]
    assert ranks == sorted(ranks)
    assert AUTHORITY_HIERARCHY[0].label.startswith("Controlling")
    assert AUTHORITY_HIERARCHY[-1].label == "General legal reasoning"


def test_plan_flags_missing_jurisdiction_and_facts() -> None:
    plan = SupremeLegalIntelligenceCore().plan(LegalAssignment(objective="Review AI contract risk"))
    assert plan.final_status is LegalStatus.COUNSEL_AUTHORIZATION_REQUIRED
    assert any("jurisdiction" in question.lower() for question in plan.questions)
    assert "contracts" in plan.modules
    assert "privacy_ai" in plan.modules
