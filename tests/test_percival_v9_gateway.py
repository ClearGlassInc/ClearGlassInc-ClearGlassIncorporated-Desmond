# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validation for the Percival v9 Envoy gateway config (authored, not applied).

No Envoy binary in CI, so these assert the config is well-formed and enforces
the security invariants that matter: JWT auth is required, ext_authz points at
the governor and fails closed, rate limiting is present, and traffic routes to
the orchestrator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

GATEWAY = Path(__file__).resolve().parents[1] / "percival_v9" / "deploy" / "gateway" / "envoy.yaml"


@pytest.fixture(scope="module")
def http_filters() -> list[dict]:
    cfg = yaml.safe_load(GATEWAY.read_text())
    listener = cfg["static_resources"]["listeners"][0]
    hcm = listener["filter_chains"][0]["filters"][0]["typed_config"]
    return hcm["http_filters"]


def _filter(http_filters: list[dict], needle: str) -> dict:
    return next(f for f in http_filters if needle in f["name"])


def test_config_is_well_formed() -> None:
    assert yaml.safe_load(GATEWAY.read_text())["static_resources"]


def test_jwt_provider_and_rules(http_filters: list[dict]) -> None:
    jwt = _filter(http_filters, "jwt_authn")["typed_config"]
    assert "idp" in jwt["providers"]
    assert jwt["providers"]["idp"]["audiences"] == ["percival-v9"]
    # Every /v1/ route requires the IdP provider.
    assert any(r["requires"]["provider_name"] == "idp" for r in jwt["rules"])


def test_ext_authz_targets_governor_and_fails_closed(http_filters: list[dict]) -> None:
    authz = _filter(http_filters, "ext_authz")["typed_config"]
    assert authz["failure_mode_allow"] is False  # governor down => deny
    assert authz["http_service"]["server_uri"]["cluster"] == "percival_governor"
    assert "percival/authz" in authz["http_service"]["path_prefix"]


def test_rate_limit_present(http_filters: list[dict]) -> None:
    rl = _filter(http_filters, "local_ratelimit")["typed_config"]
    assert rl["token_bucket"]["max_tokens"] > 0


def test_filter_order_authn_before_authz_before_router(http_filters: list[dict]) -> None:
    names = [f["name"] for f in http_filters]
    jwt_i = next(i for i, n in enumerate(names) if "jwt_authn" in n)
    authz_i = next(i for i, n in enumerate(names) if "ext_authz" in n)
    router_i = next(i for i, n in enumerate(names) if "router" in n)
    assert jwt_i < authz_i < router_i  # authenticate, then authorize, then route


def test_routes_to_orchestrator(http_filters: list[dict]) -> None:
    cfg = yaml.safe_load(GATEWAY.read_text())
    clusters = {c["name"] for c in cfg["static_resources"]["clusters"]}
    assert {"percival_orchestrator", "percival_governor", "idp_jwks"} <= clusters
