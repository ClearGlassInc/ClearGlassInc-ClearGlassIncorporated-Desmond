from pathlib import Path

from legal_intelligence_core import (
    CLEARGLASS_LEGAL_AGENT_PROMPT_PATH,
    LEGAL_AGENT_STATEMENT_CLASSES,
    LEGAL_AGENT_OUTPUT_SECTIONS,
    render_clearglass_legal_agent_prompt,
)


def test_clearglass_legal_agent_prompt_file_exists_and_is_loadable():
    prompt = render_clearglass_legal_agent_prompt()

    assert CLEARGLASS_LEGAL_AGENT_PROMPT_PATH.as_posix() == "prompts/clearglass_legal_agent_system_prompt.md"
    assert Path(CLEARGLASS_LEGAL_AGENT_PROMPT_PATH).is_file()
    assert prompt.startswith("# CLEARGLASS LEGAL AGENT — System Prompt")
    assert "Do not send communications" in prompt
    assert "LEGAL VERIFICATION REQUIRED" in prompt


def test_legal_agent_output_contract_is_bounded_and_human_gated():
    assert LEGAL_AGENT_OUTPUT_SECTIONS == (
        "Executive Summary",
        "Confirmed Facts and Assumptions",
        "Legal Analysis",
        "Risks and Options",
        "Recommended Actions",
    )
    assert tuple(LEGAL_AGENT_STATEMENT_CLASSES) == (
        "CONFIRMED FACT",
        "CONFIRMED LAW",
        "LEGAL INTERPRETATION",
        "RISK ASSESSMENT",
        "STRATEGIC RECOMMENDATION",
        "OPEN QUESTION",
        "LEGAL VERIFICATION REQUIRED",
    )


def test_prompt_requires_human_control_for_binding_actions():
    prompt = render_clearglass_legal_agent_prompt()

    required_fragments = (
        "READ_ONLY → ANALYSIS → DRAFT → HUMAN_REVIEW → APPROVED → EXECUTION",
        "You may not, without explicit approval:",
        "Sign or accept contracts",
        "Approve settlements",
        "Delete evidence",
        "Change retention settings",
        "Create binding commitments",
        "REQUIRES LICENSED COUNSEL",
    )
    for fragment in required_fragments:
        assert fragment in prompt
