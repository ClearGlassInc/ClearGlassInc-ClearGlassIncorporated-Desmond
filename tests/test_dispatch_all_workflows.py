from pathlib import Path

from scripts.dispatch_all_workflows import discover_dispatchable


def test_discovers_dispatchable_and_skips_required_inputs(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "manual.yml").write_text(
        "name: Manual\non:\n  workflow_dispatch:\n", encoding="utf-8"
    )
    (workflows / "required.yml").write_text(
        "name: Required\non:\n  workflow_dispatch:\n    inputs:\n      target:\n        required: true\n",
        encoding="utf-8",
    )
    (workflows / "push.yml").write_text("name: Push\non: [push]\n", encoding="utf-8")

    plans = {plan.file_name: plan for plan in discover_dispatchable(workflows)}

    assert plans["manual.yml"].dispatchable is True
    assert plans["required.yml"].dispatchable is False
    assert "requires explicit input" in plans["required.yml"].reason
    assert plans["push.yml"].dispatchable is False
    assert plans["push.yml"].reason == "missing workflow_dispatch trigger"
