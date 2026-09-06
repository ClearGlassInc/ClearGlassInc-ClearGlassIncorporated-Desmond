# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validation for the Percival v9 deploy layer (authored, not applied).

These do not touch cloud/K8s. They assert the committed IaC is well-formed and,
critically, that the K8s policy ConfigMap stays in sync with the source
capability schema — drift there would silently ship a stale policy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from percival_v9.deploy.temporal.worker import (
    ActionRequest,
    governed_action,
    temporal_available,
)

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "percival_v9" / "deploy"
yaml = pytest.importorskip("yaml")  # pyyaml is installed in the Python Tests job


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((DEPLOY / rel).read_text())


# -- k8s manifests -----------------------------------------------------------


def test_orchestrator_has_governor_sidecar() -> None:
    dep = _load_yaml("k8s/orchestrator.yaml")
    assert dep["kind"] == "Deployment"
    containers = dep["spec"]["template"]["spec"]["containers"]
    names = {c["name"] for c in containers}
    assert {"orchestrator-worker", "policy-governor-sidecar"} <= names


def test_sidecar_mounts_policies_read_only() -> None:
    dep = _load_yaml("k8s/orchestrator.yaml")
    sidecar = next(
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "policy-governor-sidecar"
    )
    mount = next(m for m in sidecar["volumeMounts"] if m["name"] == "opa-policies")
    assert mount["readOnly"] is True


def test_images_are_not_floating_latest() -> None:
    dep = _load_yaml("k8s/orchestrator.yaml")
    for container in dep["spec"]["template"]["spec"]["containers"]:
        assert not container["image"].endswith(":latest"), container["name"]


def test_configmap_capabilities_match_source_schema() -> None:
    """The mounted policy bundle must equal the authoritative schema file."""
    cm = _load_yaml("k8s/governor-configmap.yaml")
    embedded = json.loads(cm["data"]["capabilities.json"])
    source = json.loads((ROOT / "percival_v9" / "policies" / "capabilities.json").read_text())
    assert embedded == source, "ConfigMap policy bundle has drifted from policies/capabilities.json"


# -- terraform (structural only; no terraform binary in CI) ------------------


def test_terraform_files_present_and_nonempty() -> None:
    for name in ("main.tf", "variables.tf"):
        text = (DEPLOY / "terraform" / name).read_text()
        assert text.strip(), f"{name} is empty"
    assert 'object_lock_enabled = true' in (DEPLOY / "terraform" / "main.tf").read_text()


# -- temporal worker (import-safe, governor-gated) ---------------------------


def test_worker_module_is_import_safe() -> None:
    # Importing must not require the temporalio SDK.
    assert isinstance(temporal_available(), bool)


def test_governed_action_denies_ungranted() -> None:
    result = governed_action(ActionRequest("orchestrator-worker", "delete_everything"))
    assert result.allowed is False


def test_governed_action_allows_granted_low_risk() -> None:
    result = governed_action(ActionRequest("orchestrator-worker", "read_metrics"))
    assert result.allowed is True


def test_governed_action_gates_high_risk() -> None:
    result = governed_action(ActionRequest("orchestrator-worker", "update_pricing"))
    assert result.allowed is False
    assert "escalation gate" in result.reason
