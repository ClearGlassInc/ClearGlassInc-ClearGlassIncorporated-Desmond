# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Core capabilities installed into a FunctionAgent runtime."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .agent import FunctionAgent
from .connectors import (
    AllowlistedHTTPConnector,
    AllowlistedProcessConnector,
    WorkspaceFileConnector,
)
from .models import RiskLevel


def install_core_capabilities(
    agent: FunctionAgent,
    *,
    files: WorkspaceFileConnector,
    processes: AllowlistedProcessConnector | None = None,
    http: AllowlistedHTTPConnector | None = None,
) -> None:
    """Install safe defaults; risky operations remain policy/approval controlled."""

    async def ping() -> dict[str, str]:
        """Return agent liveness and current UTC timestamp."""
        return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    async def memory_get(namespace: str, key: str) -> Any:
        """Read a value from durable namespaced agent memory."""
        return agent.memory.get(namespace, key)

    async def memory_set(
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> dict[str, object]:
        """Write a value into durable namespaced agent memory."""
        agent.memory.set(namespace, key, value, ttl_seconds=ttl_seconds)
        return {"stored": True, "namespace": namespace, "key": key}

    async def verify_audit_chain() -> dict[str, object]:
        """Verify the tamper-evident execution audit chain."""
        valid, records = agent.audit.verify()
        return {"valid": valid, "records": records}

    agent.registry.register(
        ping,
        name="system.ping",
        risk=RiskLevel.SAFE,
        tags={"system", "health"},
        idempotent=True,
    )
    agent.registry.register(
        files.list_files,
        name="files.list",
        description="List files and directories inside the approved workspace.",
        risk=RiskLevel.READ,
        tags={"filesystem", "read"},
        idempotent=True,
    )
    agent.registry.register(
        files.read_text,
        name="files.read_text",
        description="Read a UTF-8 text file inside the approved workspace.",
        risk=RiskLevel.READ,
        tags={"filesystem", "read"},
        idempotent=True,
    )
    agent.registry.register(
        files.sha256,
        name="files.sha256",
        description="Calculate a SHA-256 digest for a workspace file.",
        risk=RiskLevel.READ,
        tags={"filesystem", "integrity"},
        idempotent=True,
    )
    agent.registry.register(
        files.write_text,
        name="files.write_text",
        description="Atomically write a text file inside the approved workspace.",
        risk=RiskLevel.WRITE,
        tags={"filesystem", "write"},
    )
    agent.registry.register(
        memory_get,
        name="memory.get",
        risk=RiskLevel.READ,
        tags={"memory", "read"},
        idempotent=True,
    )
    agent.registry.register(
        memory_set,
        name="memory.set",
        risk=RiskLevel.WRITE,
        tags={"memory", "write"},
    )
    agent.registry.register(
        verify_audit_chain,
        name="audit.verify",
        risk=RiskLevel.READ,
        tags={"audit", "integrity"},
        idempotent=True,
    )

    if processes is not None:
        agent.registry.register(
            processes.run,
            name="process.run",
            description=(
                "Run an allowlisted executable without shell interpolation inside the workspace."
            ),
            risk=RiskLevel.EXTERNAL,
            tags={"process", "automation"},
        )

    if http is not None:
        agent.registry.register(
            http.request,
            name="http.request",
            description="Send an HTTPS request to an explicitly allowlisted public host.",
            risk=RiskLevel.EXTERNAL,
            tags={"http", "connector", "external"},
        )
