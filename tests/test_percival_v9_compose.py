# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validation for the Percival v9 local docker-compose stack.

No Docker in CI, so these assert the compose file is well-formed and wires the
gateway to the governor correctly: the gateway waits for the governor to be
healthy, mounts the real Envoy config read-only, and the governor is not exposed
to the host (only reachable via the gateway's ext_authz path).
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

DEPLOY = Path(__file__).resolve().parents[1] / "percival_v9" / "deploy"


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load((DEPLOY / "docker-compose.yml").read_text())


def test_has_governor_and_gateway_services(compose: dict) -> None:
    assert {"governor", "gateway"} <= set(compose["services"])


def test_gateway_waits_for_healthy_governor(compose: dict) -> None:
    dep = compose["services"]["gateway"]["depends_on"]
    assert dep["governor"]["condition"] == "service_healthy"


def test_gateway_mounts_real_envoy_config_read_only(compose: dict) -> None:
    mounts = compose["services"]["gateway"]["volumes"]
    envoy_mount = next(m for m in mounts if "envoy.yaml" in m)
    assert envoy_mount.endswith(":ro")
    assert (DEPLOY / "gateway" / "envoy.yaml").exists()


def test_governor_not_published_to_host(compose: dict) -> None:
    # Governor must be reachable only inside the network, never bound to the host.
    assert "ports" not in compose["services"]["governor"]
    assert compose["services"]["governor"]["expose"] == ["8181"]


def test_governor_has_healthcheck(compose: dict) -> None:
    assert "healthcheck" in compose["services"]["governor"]


def test_dockerfile_is_stdlib_only_no_pip(compose: dict) -> None:
    dockerfile = (DEPLOY / "Dockerfile.governor").read_text()
    assert "pip install" not in dockerfile  # stdlib-only image
    assert "USER percival" in dockerfile  # drops root
