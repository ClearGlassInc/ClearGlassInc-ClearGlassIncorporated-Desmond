from pathlib import Path

import yaml


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "auto-store.yml"


def test_auto_store_gate_runs_only_release_relevant_root_tests() -> None:
    """Unrelated agent failures must not block store health or deployment."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    test_steps = document["jobs"]["test"]["steps"]
    command = next(step["run"] for step in test_steps if step.get("name") == "Auto-store root regression suite")

    assert "pytest tests/" not in command
    assert "tests/test_store_smoke_bot.py" in command
    assert "tests/test_store_sync.py" in command
    assert "tests/test_validate_production_deploy.py" in command
