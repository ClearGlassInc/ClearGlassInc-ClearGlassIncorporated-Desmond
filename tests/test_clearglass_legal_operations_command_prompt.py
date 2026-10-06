import re
from pathlib import Path

from legal_intelligence_core import (
    CLEARGLASS_LEGAL_OPERATIONS_COMMAND_PROMPT_PATH,
    CLOC_ESCALATION_FLAGS,
    CLOC_FACT_CLASSIFICATIONS,
    CLOC_OUTPUT_SECTIONS,
    render_clearglass_legal_operations_command_prompt,
    render_single_page_elite_prompt,
)


def _section(prompt: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", prompt, re.M | re.S)
    assert match, f"missing section: {heading}"
    return match.group(1)


def test_cloc_prompt_file_exists_and_is_loadable():
    prompt = render_clearglass_legal_operations_command_prompt()

    assert (
        CLEARGLASS_LEGAL_OPERATIONS_COMMAND_PROMPT_PATH.as_posix()
        == "prompts/clearglass_legal_operations_command_system_prompt.md"
    )
    assert Path(CLEARGLASS_LEGAL_OPERATIONS_COMMAND_PROMPT_PATH).is_file()
    assert prompt.startswith("# CLEARGLASS LEGAL OPERATIONS COMMAND (CLOC) — System Prompt")
    assert "Begin in COUNSEL-READINESS MODE." in prompt


def test_output_format_matches_the_declared_sections_in_order():
    body = _section(render_clearglass_legal_operations_command_prompt(), "OUTPUT FORMAT")
    numbered = re.findall(r"^(\d+)\. (.+)$", body, re.M)

    assert [int(n) for n, _ in numbered] == list(range(1, len(CLOC_OUTPUT_SECTIONS) + 1))
    assert tuple(title for _, title in numbered) == CLOC_OUTPUT_SECTIONS


def test_fact_classifications_and_escalation_flags_match_the_prompt():
    prompt = render_clearglass_legal_operations_command_prompt()
    bold = re.compile(r"^\*\*([A-Z][A-Z ]+)\*\*$", re.M)

    assert tuple(bold.findall(_section(prompt, "EVIDENTIARY DISCIPLINE"))) == CLOC_FACT_CLASSIFICATIONS
    assert tuple(bold.findall(_section(prompt, "ESCALATION RULES"))) == CLOC_ESCALATION_FLAGS


def test_prompt_keeps_legal_judgment_and_external_action_with_humans():
    prompt = render_clearglass_legal_operations_command_prompt()

    required_fragments = (
        "You are NOT a lawyer, law firm, substitute for licensed counsel",
        "LICENSED COUNSEL BEFORE LEGAL ACTION.",
        "Never convert an assumption, allegation, inference, or unverified claim into a fact.",
        "Do not assume that material provided to you is solicitor-client privileged.",
        "Without explicit instruction from an authorized ClearGlass representative",
        "Delete, alter, backdate, selectively edit, or destroy records",
        "Claim solicitor-client privilege exists merely because material was shared with you.",
        "Do not declare a contract enforceable, invalid, breached, terminated, compliant, or non-compliant",
        "DRAFT — FOR LICENSED COUNSEL REVIEW",
        "Do not act externally.",
    )
    for fragment in required_fragments:
        assert fragment in prompt


def test_supreme_core_routes_matter_files_to_cloc():
    assert "prompts/clearglass_legal_operations_command_system_prompt.md" in render_single_page_elite_prompt()
