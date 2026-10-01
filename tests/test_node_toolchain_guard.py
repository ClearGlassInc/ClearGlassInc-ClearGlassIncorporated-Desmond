"""Fail, don't skip, when CI runs the root suite without the Node it needs.

Seven test modules shell out to ``node`` and skip when it is missing or too
old: the admin login guard (needs Node 22.6+ to strip TypeScript types), the
RFED Python/n8n hash-parity gate, Truth Forensics parity, page JavaScript
syntax, Sentinel Core, the homepage subscribe handler and the side store.
Run with no Node on ``PATH``, ``pytest tests/`` reports 1863 passed and 35
skipped and exits 0: 24 of those skips are these tests, and the run is green.

The CI ``python-tests`` job installed Python only. It relied on whatever Node
the runner image happens to ship, which ``test_admin_login_guard.py`` itself
records as 20 on ``ubuntu-latest``, so the admin login guard's behavioural
suite would skip there even once Actions dispatches runners again.

This is the same failure mode ``control-plane/tests/test_web_stack_guard.py``
closes for ``httpx``: a security gate that passes by skipping.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"

# node --experimental-strip-types arrived in 22.6; test_admin_login_guard.py needs it.
REQUIRED = (22, 6)


def _node_version() -> tuple[int, int] | None:
    node = shutil.which("node")
    if node is None:
        return None
    out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout
    match = re.match(r"v(\d+)\.(\d+)", out.strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


def _python_tests_steps() -> list[dict]:
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    return workflow["jobs"]["python-tests"]["steps"]


def test_ci_python_tests_job_installs_node_before_pytest() -> None:
    steps = _python_tests_steps()
    node_steps = [
        i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/setup-node@")
    ]
    pytest_steps = [i for i, step in enumerate(steps) if "pytest tests/" in str(step.get("run", ""))]
    assert node_steps, (
        "ci.yml python-tests never runs actions/setup-node, so the Node-dependent "
        "tests depend on the runner image and the admin login guard skips on Node 20"
    )
    assert pytest_steps and node_steps[0] < pytest_steps[0], "setup-node must run before pytest"

    declared = str(steps[node_steps[0]].get("with", {}).get("node-version", ""))
    major = re.match(r"\d+", declared)
    assert major and int(major.group(0)) >= REQUIRED[0], (
        f"python-tests pins node-version {declared!r}; it needs {REQUIRED[0]}.{REQUIRED[1]}+"
    )


def test_github_actions_runs_the_node_dependent_tests() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        # Locally the skips stay visible with `pytest -rs`; CI is where a skip reads as a pass.
        pytest.skip("enforced on GitHub Actions only")
    version = _node_version()
    assert version is not None, "node is not on PATH: 24 Node-dependent tests are skipping"
    assert version >= REQUIRED, (
        f"node {version[0]}.{version[1]} cannot strip TypeScript types; "
        f"the admin login guard suite needs {REQUIRED[0]}.{REQUIRED[1]}+ and is skipping"
    )
