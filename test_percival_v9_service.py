# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""E2E tests for the Percival v9 governor service and capability schema.

Covers the ``cmd/governor.py`` HTTP surface (OPA-compatible contract), the
versioned ``policies/capabilities.json`` schema loader, and transport-level
fail-closed behaviour (malformed input / unknown routes never grant).
"""

from __future__ import annotations

import json
import threading
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest

from percival_v9.cmd.governor import (
    AUTHZ_PATH,
    DEFAULT_POLICIES,
    load_governor,
    make_server,
    self_check,
)


@pytest.fixture(scope="module")
def server_url() -> Iterator[str]:
    server = make_server(port=0)  # OS-assigned free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _post(url: str, body: bytes) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


# -- schema loader -----------------------------------------------------------


def test_schema_loads_and_is_deny_by_default() -> None:
    governor = load_governor(DEFAULT_POLICIES)
    assert governor.evaluate("orchestrator-worker", "read_metrics").allow
    assert not governor.evaluate("orchestrator-worker", "update_pricing").allow  # gated
    assert not governor.evaluate("eval-ops", "update_pricing").allow  # never granted
    assert not governor.evaluate("unknown-identity", "read_metrics").allow


def test_self_check_passes_on_shipped_schema() -> None:
    report = self_check()
    assert report["ok"], report


# -- HTTP contract (OPA-compatible) ------------------------------------------


def test_authz_allow_for_granted_low_risk(server_url: str) -> None:
    body = json.dumps(
        {"input": {"identity": "orchestrator-worker", "capability": "read_metrics"}}
    ).encode()
    status, payload = _post(server_url + AUTHZ_PATH, body)
    assert status == 200
    assert payload["result"]["allow"] is True


def test_authz_denies_gated_risk_without_approval(server_url: str) -> None:
    body = json.dumps(
        {"input": {"identity": "orchestrator-worker", "capability": "update_pricing"}}
    ).encode()
    status, payload = _post(server_url + AUTHZ_PATH, body)
    assert status == 200
    assert payload["result"]["allow"] is False
    assert "escalation gate" in payload["result"]["reason"]


def test_authz_denies_unknown_identity(server_url: str) -> None:
    body = json.dumps({"input": {"identity": "intruder", "capability": "read_metrics"}}).encode()
    _, payload = _post(server_url + AUTHZ_PATH, body)
    assert payload["result"]["allow"] is False


# -- transport-level fail-closed ----------------------------------------------


def test_malformed_body_is_denied_not_erroring_open(server_url: str) -> None:
    status, payload = _post(server_url + AUTHZ_PATH, b"not json at all")
    assert status == 400
    assert payload["result"]["allow"] is False


def test_missing_fields_are_denied(server_url: str) -> None:
    status, payload = _post(server_url + AUTHZ_PATH, json.dumps({"input": {}}).encode())
    assert status == 400
    assert payload["result"]["allow"] is False


def test_unknown_route_is_denied(server_url: str) -> None:
    status, payload = _post(server_url + "/v1/data/other/allow", b"{}")
    assert status == 404
    assert payload["result"]["allow"] is False


def test_healthz_reports_state(server_url: str) -> None:
    with urllib.request.urlopen(server_url + "/healthz") as resp:
        payload = json.loads(resp.read())
    assert payload["ok"] is True
    assert payload["deny_all"] is False
