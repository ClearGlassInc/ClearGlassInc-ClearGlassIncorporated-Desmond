"""Keep the local CI mirror aligned with the root Python CI gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_LOCAL_PATH = ROOT / "scripts" / "ci_local.py"
CI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"


def _load_ci_local():
    spec = importlib.util.spec_from_file_location("ci_local_contract_target", CI_LOCAL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_python_gate_preserves_ci_coverage_validation_and_cleanup() -> None:
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    commands = [
        str(step.get("run", ""))
        for step in workflow["jobs"]["python-tests"]["steps"]
    ]
    assert any("pytest tests/ --cov --cov-report=xml -q" in command for command in commands)

    ci_local = _load_ci_local()
    gate = next(gate for gate in ci_local.GATES if gate.name == "pytest tests/")
    assert gate.command == [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov",
        "--cov-report=xml",
        "-q",
    ]
    assert "coverage.xml" in gate.artifacts
