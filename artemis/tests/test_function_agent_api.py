from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from artemis.function_agent.api import create_app
from artemis.function_agent.runtime import RuntimeSettings, build_runtime


@pytest.mark.asyncio
async def test_api_execution_and_operator_approval(tmp_path: Path) -> None:
    runtime = build_runtime(
        RuntimeSettings(
            workspace=tmp_path / "workspace",
            state_dir=tmp_path / "state",
            approval_secret="s" * 64,
            operator_key="operator-secret",
        )
    )
    app = create_app(runtime)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/health/live")
        assert live.status_code == 200

        capabilities = await client.get("/v1/capabilities")
        assert capabilities.status_code == 200
        names = {item["name"] for item in capabilities.json()}
        assert {"system.ping", "files.read_text", "files.write_text"} <= names
        assert "process.run" not in names

        payload = {
            "capability": "files.write_text",
            "arguments": {
                "path": "api.txt",
                "content": "approved through API",
                "overwrite": False,
            },
        }
        headers = {"X-Artemis-Actor": "api.user.with.dots"}
        challenge = await client.post("/v1/execute", json=payload, headers=headers)
        assert challenge.status_code == 200
        challenge_body = challenge.json()
        assert challenge_body["status"] == "approval_required"
        approval_id = challenge_body["approval_id"]

        unauthorized = await client.post(f"/v1/approvals/{approval_id}/grant")
        assert unauthorized.status_code == 401

        grant = await client.post(
            f"/v1/approvals/{approval_id}/grant",
            headers={"X-Artemis-Operator-Key": "operator-secret"},
        )
        assert grant.status_code == 200
        token = grant.json()["token"]

        approved = await client.post(
            "/v1/execute",
            json={**payload, "approval_token": token},
            headers=headers,
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "succeeded"
        assert (tmp_path / "workspace" / "api.txt").read_text(encoding="utf-8") == (
            "approved through API"
        )

        audit = await client.get("/v1/audit/verify")
        assert audit.status_code == 200
        assert audit.json()["valid"] is True


@pytest.mark.asyncio
async def test_api_rejects_client_supplied_identity_fields(tmp_path: Path) -> None:
    runtime = build_runtime(
        RuntimeSettings(
            workspace=tmp_path / "workspace",
            state_dir=tmp_path / "state",
            approval_secret="s" * 64,
        )
    )
    app = create_app(runtime)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/execute",
            json={
                "capability": "memory.set",
                "arguments": {"namespace": "test", "key": "role", "value": "admin"},
                "context": {"roles": ["admin"]},
            },
        )

    assert response.status_code == 422
