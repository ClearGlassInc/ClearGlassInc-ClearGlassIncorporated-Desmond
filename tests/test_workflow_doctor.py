"""Regression tests for scripts.workflow_doctor."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# The doctor calls sys.exit(2) at import if pyyaml is missing; skip cleanly
# so the suite reports a clear "skip" instead of a fixture crash.
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
DOCTOR_PATH = ROOT / "scripts" / "workflow_doctor.py"


@pytest.fixture(scope="module")
def doctor():
    spec = importlib.util.spec_from_file_location("workflow_doctor", DOCTOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow_doctor"] = module
    spec.loader.exec_module(module)
    return module


def test_dump_yaml_preserves_on_key(doctor):
    # PyYAML 1.1 parses bare `on:` into the Python boolean True; if dump_yaml
    # doesn't normalize it back, the rewritten workflow loses its triggers
    # and becomes a no-op.
    parsed = doctor.yaml.safe_load("on:\n  push:\n    branches: [main]\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n")
    assert True in parsed, "fixture precondition: PyYAML must parse on: as True"

    rendered = doctor.dump_yaml(parsed)
    assert "true:" not in rendered.splitlines()[0:3]
    reparsed = doctor.yaml.safe_load(rendered)
    assert "on" in reparsed or True in reparsed
    trigger = reparsed.get("on") or reparsed.get(True)
    assert "push" in trigger


def test_patch_action_versions_bumps_stable(doctor):
    text = "      - uses: actions/checkout@v4\n      - uses: actions/upload-artifact@v4\n"
    new_text, changes = doctor.patch_action_versions(text)
    assert "actions/checkout@v6" in new_text
    assert "actions/upload-artifact@v7" in new_text
    assert any("checkout" in c for c in changes)
    assert any("upload-artifact" in c for c in changes)


def test_patch_action_versions_leaves_sha_pins_alone(doctor):
    text = "      - uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332\n"
    new_text, changes = doctor.patch_action_versions(text)
    assert new_text == text
    assert changes == []


def test_unpinned_external_actions_checks_composite_steps(doctor, tmp_path):
    action_file = tmp_path / "action.yml"
    mutable = "runs:\n  using: composite\n  steps:\n    - uses: actions/setup-python@v6\n"
    assert doctor.unpinned_external_actions(action_file, mutable) == [
        f"ERROR {action_file}: external action is not pinned to a full commit SHA: actions/setup-python@v6"
    ]

    pinned = mutable.replace("@v6", "@a309ff8b426b58ec0e2a45f0f869d46889d02405")
    assert doctor.unpinned_external_actions(action_file, pinned) == []


# --- GitHub trigger-schema limits -------------------------------------------
# Both rules below are GitHub hard limits. Breaking either produces a failure
# that is invisible locally and nearly invisible on GitHub: the run is rejected
# before a runner is assigned, so it has no logs, no steps, and is listed by
# file path instead of workflow name. `.github/workflows/auto-heal.yml` sat
# broken that way for 203 consecutive runs. These tests keep the detector
# honest, since a checker that cannot fail is worth nothing.

def _workflow(trigger: str) -> str:
    return trigger + "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"


def test_workflow_run_without_workflows_key_is_an_error(doctor):
    # This exact shape made the whole file invalid, so Auto Heal never ran on
    # any trigger — not the schedule, not manual dispatch, not workflow_run.
    text = _workflow("on:\n  workflow_run:\n    types: [completed]\n")
    findings = doctor.event_schema_violations(Path("wf.yml"), text)
    assert len(findings) == 1
    assert "workflow_run" in findings[0]


def test_workflow_run_with_an_empty_workflows_list_is_an_error(doctor):
    text = _workflow("on:\n  workflow_run:\n    workflows: []\n    types: [completed]\n")
    assert len(doctor.event_schema_violations(Path("wf.yml"), text)) == 1


@pytest.mark.parametrize("listed", ['["*"]', "[CI]", '["CI", "Security"]'])
def test_workflow_run_with_a_populated_workflows_list_is_accepted(doctor, listed):
    text = _workflow(f"on:\n  workflow_run:\n    workflows: {listed}\n    types: [completed]\n")
    assert doctor.event_schema_violations(Path("wf.yml"), text) == []


def test_workflow_dispatch_over_the_input_limit_is_an_error(doctor):
    limit = doctor.WORKFLOW_DISPATCH_INPUT_LIMIT
    inputs = "".join(
        f"      i{n}:\n        type: string\n        required: false\n" for n in range(limit + 1)
    )
    findings = doctor.event_schema_violations(
        Path("wf.yml"), _workflow(f"on:\n  workflow_dispatch:\n    inputs:\n{inputs}")
    )
    assert len(findings) == 1
    assert str(limit + 1) in findings[0]


def test_workflow_dispatch_at_the_input_limit_is_accepted(doctor):
    # The boundary matters: edge-security.yml was cut to exactly the limit, so
    # an off-by-one here would fail the very workflow this check was added for.
    limit = doctor.WORKFLOW_DISPATCH_INPUT_LIMIT
    inputs = "".join(
        f"      i{n}:\n        type: string\n        required: false\n" for n in range(limit)
    )
    assert doctor.event_schema_violations(
        Path("wf.yml"), _workflow(f"on:\n  workflow_dispatch:\n    inputs:\n{inputs}")
    ) == []


def test_workflow_dispatch_without_inputs_is_accepted(doctor):
    assert doctor.event_schema_violations(Path("wf.yml"), _workflow("on:\n  workflow_dispatch:\n")) == []


def test_composite_action_files_have_no_trigger_block_and_are_skipped(doctor):
    # iter_targets() feeds .github/actions/*/action.yml through the same loop;
    # those have `inputs:` at the top level and no `on:`, so a naive check
    # would flag every one of them.
    text = "name: composite\ninputs:\n  a:\n    required: false\nruns:\n  using: composite\n  steps: []\n"
    assert doctor.event_schema_violations(Path("action.yml"), text) == []


def test_the_live_workflow_tree_satisfies_both_limits(doctor):
    # The end-to-end assertion: every registered workflow is dispatchable and
    # registrable as committed.
    offenders = [
        f
        for path in doctor.iter_targets()
        for f in doctor.event_schema_violations(path.relative_to(doctor.ROOT), path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], "\n".join(offenders)
