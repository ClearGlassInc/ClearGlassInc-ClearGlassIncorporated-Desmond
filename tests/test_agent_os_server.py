# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The head agent's HTTP front end, over a real socket.

Authentication fails closed, the token that submits work cannot approve it,
inputs are bounded, and a mission submitted over HTTP is planned, approved,
executed by a worker thread and reported back — with no credential in any
response.
"""
from __future__ import annotations

import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from agent_os.freshness import report as freshness_report
from agent_os.freshness import validate as validate_freshness
from agent_os.head import HeadAgent, RunRequest, RunResult
from agent_os.readiness import validate as validate_readiness
from agent_os.server import AgentServer, Config, ConfigError
from agent_os.tasks import TaskStore

REPO = Path(__file__).resolve().parents[1]
API = "operator-" + "a" * 30
APPROVER = "approver-" + "b" * 30


def ok_runner(request: RunRequest) -> RunResult:
    return RunResult(0, f"ran {' '.join(request.argv[1:])} with token {API}", "", 3, "completed")


class Client:
    def __init__(self, port: int) -> None:
        self.port = port

    def __call__(self, method: str, path: str, body=None, token: str | None = API, raw: bytes | None = None,
                 content_type: str = "application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if payload is not None:
            headers["Content-Type"] = content_type
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        text = res.read().decode()
        conn.close()
        try:
            data = json.loads(text)
        except ValueError:
            data = text
        return res.status, data, dict(res.getheaders())


def _serve(tmp_path, *, approver: str | None = APPROVER, workers: bool = True):
    config = Config(api_token=API, approver_token=approver, db=str(tmp_path / "t.sqlite3"), port=0,
                    shutdown_grace=2)
    head = HeadAgent(TaskStore(config.db), root=REPO, runner=ok_runner, secrets=(API,))
    server = AgentServer(config, head=head)
    if workers:
        server.start_workers()
    thread = threading.Thread(target=server.httpd.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    return server, Client(server.address[1])


@pytest.fixture()
def served(tmp_path):
    server, client = _serve(tmp_path)
    yield server, client
    server.shutdown()


def _settle(client, cid: str, timeout: float = 15) -> dict:
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        _, mission, _ = client("GET", f"/api/missions/{cid}")
        if mission["status"] not in ("queued", "running"):
            return mission
        time.sleep(0.1)
    raise AssertionError(f"mission {cid} did not settle: {mission['status']}")


# --------------------------------------------------------------------------- configuration
@pytest.mark.parametrize("env, message", [
    ({}, "AGENT_OS_API_TOKEN"),
    ({"AGENT_OS_API_TOKEN": "short"}, "at least"),
    ({"AGENT_OS_API_TOKEN": API, "AGENT_OS_APPROVER_TOKEN": API}, "must differ"),
    ({"AGENT_OS_API_TOKEN": API, "AGENT_OS_WORKERS": "9"}, "between 1 and 4"),
])
def test_the_server_refuses_to_start_open_or_misconfigured(env, message):
    with pytest.raises(ConfigError, match=message):
        Config.from_env(env)


def test_defaults_bind_to_loopback():
    config = Config.from_env({"AGENT_OS_API_TOKEN": API})
    assert config.bind == "127.0.0.1" and config.approver_token is None


# --------------------------------------------------------------------------- authentication
def test_api_routes_need_the_operator_token(served):
    _, client = served
    assert client("GET", "/api/missions", token=None)[0] == 401
    assert client("GET", "/api/missions", token="wrong-" + "x" * 30)[0] == 401
    assert client("GET", "/api/missions")[0] == 200
    status, _, headers = client("GET", "/api/missions", token=None)
    assert headers.get("WWW-Authenticate", "").startswith("Bearer")


def test_the_token_that_submits_work_cannot_approve_it_and_vice_versa(served):
    _, client = served
    status, mission, _ = client("POST", "/api/missions", {"objective": "regenerate links"})
    assert status == 201
    gated = mission["tasks"][0]
    assert gated["status"] == "waiting_for_approval"
    path = f"/api/tasks/{gated['task_id']}/decision"
    body = {"decision": "approve", "reason": "reviewed"}
    assert client("POST", path, body, token=API)[0] == 403
    assert client("POST", "/api/missions", {"objective": "check links"}, token=APPROVER)[0] == 403
    assert client("POST", path, body, token=APPROVER)[0] == 200


def test_with_no_approver_configured_every_decision_is_refused(tmp_path):
    server, client = _serve(tmp_path, approver=None)
    try:
        _, mission, _ = client("POST", "/api/missions", {"objective": "regenerate links"})
        path = f"/api/tasks/{mission['tasks'][0]['task_id']}/decision"
        status, body, _ = client("POST", path, {"decision": "approve", "reason": "x" * 5}, token=API)
        assert status == 403 and "not configured" in body["error"]
    finally:
        server.shutdown()


# --------------------------------------------------------------------------- input bounds
def test_inputs_are_validated_and_bounded(served):
    _, client = served
    assert client("POST", "/api/missions", {"objective": "x"})[0] == 400
    assert client("POST", "/api/missions", {"objective": "check links", "extra": 1})[0] == 400
    assert client("POST", "/api/missions", {"objective": "check links", "idempotency_key": "bad key!"})[0] == 400
    assert client("POST", "/api/missions", raw=b"{nope")[0] == 400
    assert client("POST", "/api/missions", raw=b"{}", content_type="text/plain")[0] == 415
    assert client("POST", "/api/missions", raw=b"[" + b"1," * 20000 + b"1]")[0] == 413
    assert client("GET", "/api/missions/msn-0000000000000000")[0] == 404
    assert client("GET", "/api/missions/../../etc/passwd")[0] == 404


def test_a_retried_submit_with_the_same_key_does_not_duplicate_work(served):
    _, client = served
    body = {"objective": "check data freshness", "idempotency_key": "console-retry-1"}
    first = client("POST", "/api/missions", body)
    second = client("POST", "/api/missions", body)
    assert (first[0], second[0]) == (201, 200)
    assert first[1]["correlation_id"] == second[1]["correlation_id"]


# --------------------------------------------------------------------------- the journey
def test_submit_approve_execute_and_report_over_http(served):
    _, client = served
    status, mission, _ = client("POST", "/api/missions", {"objective": "regenerate links then link check"})
    assert status == 201 and mission["status"] == "waiting_for_approval"
    gated = next(t for t in mission["tasks"] if t["status"] == "waiting_for_approval")
    client("POST", f"/api/tasks/{gated['task_id']}/decision",
           {"decision": "approve", "reason": "reviewed the generator", "approver": "owner"}, token=APPROVER)
    final = _settle(client, mission["correlation_id"])
    assert final["status"] == "succeeded"
    assert {t["assigned_agent"] for t in final["tasks"]} == {"repository", "verification"}
    assert all(t["evidence"] for t in final["tasks"])
    events = client("GET", f"/api/missions/{mission['correlation_id']}/events")[1]
    assert events["chain_verified"] is True
    assert "approval_decision" in {e["kind"] for e in events["events"]}

    everything = json.dumps([client("GET", f"/api/missions/{mission['correlation_id']}")[1],
                             events, client("GET", "/api/metrics")[1]])
    assert API not in everything and APPROVER not in everything


def test_cancel_over_http(served):
    _, client = served
    _, mission, _ = client("POST", "/api/missions", {"objective": "regenerate links"})
    status, counts, _ = client("POST", f"/api/missions/{mission['correlation_id']}/cancel")
    assert status == 200 and counts["cancelled"] == len(mission["tasks"])
    assert client("GET", f"/api/missions/{mission['correlation_id']}")[1]["status"] == "cancelled"


def test_metrics_report_queue_and_data_freshness(served):
    _, client = served
    metrics = client("GET", "/api/metrics")[1]
    for key in ("queue_depth", "awaiting_approval", "retries", "tasks_by_status", "data_freshness", "data_sources"):
        assert key in metrics
    assert {s["state"] for s in metrics["data_sources"]} <= {"fresh", "warning", "stale", "never_retrieved",
                                                               "unknown", "missing"}


# --------------------------------------------------------------------------- liveness, readiness, console
def test_liveness_is_not_readiness(tmp_path):
    server, client = _serve(tmp_path, workers=False)
    try:
        assert client("GET", "/healthz", token=None)[0] == 200
        status, body, _ = client("GET", "/readyz", token=None)
        assert status == 503 and body["checks"]["workers_alive"] == 0
        server.start_workers()
        time.sleep(0.3)
        assert client("GET", "/readyz", token=None)[0] == 200
    finally:
        server.shutdown()


def test_the_console_is_served_with_a_strict_policy(served):
    _, client = served
    status, page, headers = client("GET", "/", token=None)
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert "default-src 'none'" in headers["Content-Security-Policy"] and headers["X-Frame-Options"] == "DENY"
    assert "/console.js" in page and "<script>" not in page  # no inline script under the CSP
    assert client("GET", "/console.js", token=None)[0] == 200


def test_the_console_markup_is_not_published_as_a_site_page():
    """GitHub Pages serves this repository's root; an ops console must not be a page there."""
    assert not list((REPO / "agent_os").rglob("*.html"))


# --------------------------------------------------------------------------- reporters
def _feeds(tmp_path, ieso_success, minerals_retrieved):
    (tmp_path / "data/grid").mkdir(parents=True)
    (tmp_path / "feeds/minerals").mkdir(parents=True)
    (tmp_path / "data/grid/ieso-public.json").write_text(json.dumps({"sources": [
        {"id": "PUB_Demand", "url": "https://example.test", "last_success_utc": ieso_success}]}))
    (tmp_path / "feeds/minerals/manifest.json").write_text(json.dumps({"feeds": [
        {"id": "policy", "retrieved_at": minerals_retrieved, "warning_threshold_hours": 36,
         "stale_threshold_hours": 72, "status": "OK"}]}))


def test_freshness_never_calls_missing_data_fresh(tmp_path):
    from datetime import UTC, datetime
    _feeds(tmp_path, None, "2026-10-20T12:00:00Z")
    result = freshness_report(tmp_path, now=datetime(2026, 10, 22, 12, 0, tzinfo=UTC))
    states = {s["id"]: s["state"] for s in result["sources"]}
    assert states == {"PUB_Demand": "never_retrieved", "policy": "warning"}
    assert result["all_fresh"] is False and validate_freshness(result) == []


def test_freshness_ages_through_its_thresholds(tmp_path):
    from datetime import UTC, datetime
    _feeds(tmp_path, "2026-10-22T11:00:00Z", "2026-10-18T00:00:00Z")
    result = freshness_report(tmp_path, now=datetime(2026, 10, 22, 12, 0, tzinfo=UTC))
    assert {s["id"]: s["state"] for s in result["sources"]} == {"PUB_Demand": "fresh", "policy": "stale"}


def test_a_missing_feed_file_is_reported_not_hidden(tmp_path):
    result = freshness_report(tmp_path)
    assert {s["state"] for s in result["sources"]} == {"missing"}


def test_a_readiness_report_may_never_claim_a_deploy():
    good = {"schema": "clearglass.agent_os.readiness/1", "head": "a" * 40, "deploy_executed": False}
    assert validate_readiness(good) == []
    assert validate_readiness({**good, "deploy_executed": True})
