from __future__ import annotations

import sys
from pathlib import Path

import pytest

from artemis.function_agent import EpisodicMemory, SQLiteMemory, VectorMemory, WorkingMemory
from artemis.function_agent.connectors import (
    AllowlistedHTTPConnector,
    AllowlistedProcessConnector,
    ConnectorError,
    WorkspaceFileConnector,
)


@pytest.mark.asyncio
async def test_filesystem_connector_full_lifecycle(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    connector = WorkspaceFileConnector(workspace, max_read_bytes=1_024)

    health = await connector.health()
    assert health.data["readable"] is True

    written = await connector.write_text("nested/report.txt", "clear glass")
    assert written["path"] == "nested/report.txt"
    assert written["bytes"] == 11
    assert len(str(written["sha256"])) == 64

    assert await connector.read_text("nested/report.txt") == "clear glass"
    assert await connector.sha256("nested/report.txt") == written["sha256"]

    items = await connector.list_files("nested")
    assert items == [{"path": "nested/report.txt", "type": "file", "bytes": 11}]

    overwritten = await connector.write_text(
        "nested/report.txt",
        "approved",
        overwrite=True,
    )
    assert overwritten["bytes"] == 8

    with pytest.raises(ConnectorError, match="Refusing to overwrite"):
        await connector.write_text("nested/report.txt", "blocked")
    with pytest.raises(ConnectorError, match="File not found"):
        await connector.read_text("missing.txt")
    with pytest.raises(ConnectorError, match="byte write limit"):
        await connector.write_text("large.txt", "x" * 1_025)
    with pytest.raises(ConnectorError, match="between 1 and 10000"):
        await connector.list_files(limit=0)


@pytest.mark.asyncio
async def test_process_connector_enforces_allowlist_and_workspace(tmp_path: Path) -> None:
    executable = Path(sys.executable).name
    connector = AllowlistedProcessConnector(
        tmp_path,
        allowed_executables={executable},
        timeout_seconds=10,
    )

    health = await connector.health()
    assert health.data["executables"][executable] is True

    result = await connector.run(executable, ["-c", "print('operational')"])
    assert result["returncode"] == 0
    assert result["stdout"].strip() == "operational"
    assert result["stderr"] == ""

    with pytest.raises(ConnectorError, match="not allowlisted"):
        await connector.run("definitely-not-approved")
    with pytest.raises(ConnectorError, match="escapes workspace"):
        await connector.run(executable, ["--version"], cwd="../outside")
    with pytest.raises(ConnectorError, match="Working directory not found"):
        await connector.run(executable, ["--version"], cwd="missing")


@pytest.mark.asyncio
async def test_http_connector_rejects_unsafe_requests_before_network() -> None:
    connector = AllowlistedHTTPConnector({"api.example.com"})

    health = await connector.health()
    assert health.data == {"allowed_hosts": ["api.example.com"]}

    with pytest.raises(ConnectorError, match="Only HTTPS"):
        await connector.request("GET", "http://api.example.com/data")
    with pytest.raises(ConnectorError, match="Credentials"):
        await connector.request("GET", "https://user:pass@api.example.com/data")
    with pytest.raises(ConnectorError, match="not allowlisted"):
        await connector.request("GET", "https://other.example.com/data")
    with pytest.raises(ConnectorError, match="standard HTTPS port"):
        await connector.request("GET", "https://api.example.com:8443/data")


@pytest.mark.asyncio
async def test_http_connector_rejects_methods_after_safe_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = AllowlistedHTTPConnector({"api.example.com"})

    async def accept_address(host: str) -> None:
        assert host == "api.example.com"

    monkeypatch.setattr(connector, "_validate_addresses", accept_address)
    with pytest.raises(ConnectorError, match="method is not supported"):
        await connector.request("TRACE", "https://api.example.com/data")


def test_working_episodic_and_sqlite_memory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="capacity"):
        WorkingMemory(capacity=0)

    working = WorkingMemory(capacity=2)
    working.add("first", "crypto market")
    working.add("second", "security operations", {"priority": "high"})
    assert working.retrieve("security", top_k=1)[0].key == "second"
    assert working.retrieve("", top_k=2)[0].metadata == {"priority": "high"}

    store = SQLiteMemory(tmp_path / "memory.sqlite3")
    store.set("system", "status", {"ready": True})
    assert store.get("system", "status") == {"ready": True}
    assert store.list_namespace("system") == {"status": {"ready": True}}
    assert store.delete("system", "status") is True
    assert store.delete("system", "status") is False
    assert store.get("system", "missing", "fallback") == "fallback"

    store.set("system", "expired", "gone", ttl_seconds=-1)
    assert store.get("system", "expired", "fallback") == "fallback"
    assert store.prune_expired() == 0

    episodic = EpisodicMemory(store, "session-1")
    episodic.add("decision", "deploy approved", {"actor": "operator"})
    episode = episodic.retrieve("deploy", top_k=1)[0]
    assert episode.value == "deploy approved"
    assert episode.metadata == {"actor": "operator"}


def test_vector_memory_edge_conditions() -> None:
    vectors = {
        "empty": [],
        "query": [1.0, 0.0],
        "zero": [0.0, 0.0],
        "wrong": [1.0],
    }
    memory = VectorMemory(lambda text: vectors[text])

    with pytest.raises(ValueError, match="empty vector"):
        memory.add("empty", "empty")

    memory.add("zero", "zero")
    assert memory.retrieve("query")[0].score == 0.0

    memory.add("wrong", "wrong")
    with pytest.raises(ValueError, match="dimensions"):
        memory.retrieve("query")

    empty_query_memory = VectorMemory(lambda _text: [])
    assert empty_query_memory.retrieve("anything") == []
