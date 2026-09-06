from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from artemis.function_agent import (
    ApprovalManager,
    CapabilityRegistry,
    ExecutionContext,
    ExecutionRequest,
    ExecutionStatus,
    FunctionAgent,
    FunctionAgentSettings,
    GuardrailPipeline,
    PredicateGuardrail,
    RiskLevel,
    RuntimeSettings,
    VectorMemory,
    build_runtime,
)
from artemis.function_agent.connectors import ConnectorError, WorkspaceFileConnector


@pytest.mark.asyncio
async def test_registry_generates_strict_json_schema() -> None:
    async def calculate(count: int, label: str = "item") -> dict[str, object]:
        return {"count": count, "label": label}

    registry = CapabilityRegistry()
    registered = registry.register(calculate, name="math.calculate")

    schema = registered.spec.input_schema
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["count"]["type"] == "integer"
    assert "count" in schema["required"]

    with pytest.raises(ValidationError):
        await registered.invoke({"count": "not-an-integer", "unexpected": True})


@pytest.mark.asyncio
async def test_safe_execution_idempotency_and_audit(tmp_path: Path) -> None:
    calls = 0

    async def add(left: int, right: int) -> int:
        nonlocal calls
        calls += 1
        return left + right

    agent = FunctionAgent(
        settings=FunctionAgentSettings(state_dir=tmp_path / "state")
    )
    agent.registry.register(
        add,
        name="math.add",
        risk=RiskLevel.SAFE,
        idempotent=True,
    )
    request = ExecutionRequest(
        capability="math.add",
        arguments={"left": 2, "right": 3},
        context=ExecutionContext(actor="test"),
    )

    first = await agent.execute(request)
    second = await agent.execute(request.model_copy(deep=True))

    assert first.status is ExecutionStatus.SUCCEEDED
    assert first.output == 5
    assert second.status is ExecutionStatus.SUCCEEDED
    assert second.output == {"cached": True, "value": 5}
    assert calls == 1
    assert agent.audit.verify() == (True, 2)


@pytest.mark.asyncio
async def test_guardrail_rejects_before_capability_runs(tmp_path: Path) -> None:
    executed = False

    async def sensitive() -> str:
        nonlocal executed
        executed = True
        return "should not run"

    guardrails = GuardrailPipeline(
        [
            PredicateGuardrail(
                name="deny-sensitive",
                input_predicate=lambda request: request.capability != "test.sensitive",
                rejection_reason="Capability blocked by test policy",
            )
        ]
    )
    agent = FunctionAgent(
        guardrails=guardrails,
        settings=FunctionAgentSettings(state_dir=tmp_path / "state"),
    )
    agent.registry.register(sensitive, name="test.sensitive")

    result = await agent.execute(ExecutionRequest(capability="test.sensitive"))

    assert result.status is ExecutionStatus.DENIED
    assert "deny-sensitive" in (result.error or "")
    assert executed is False


@pytest.mark.asyncio
async def test_durable_approval_survives_restart_and_is_one_use(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / "state"
    settings = RuntimeSettings(
        workspace=workspace,
        state_dir=state_dir,
        approval_secret="a" * 64,
    )
    first_runtime = build_runtime(settings)
    arguments = {"path": "approved.txt", "content": "clear", "overwrite": False}
    context = ExecutionContext(actor="desmond.operator")

    challenge_result = await first_runtime.agent.execute(
        ExecutionRequest(
            capability="files.write_text",
            arguments=arguments,
            context=context,
        )
    )
    assert challenge_result.status is ExecutionStatus.APPROVAL_REQUIRED
    assert challenge_result.approval_id

    separate_manager = ApprovalManager(
        secret="a" * 64,
        state_path=state_dir / "approvals.sqlite3",
    )
    grant = separate_manager.grant(challenge_result.approval_id)

    restarted_runtime = build_runtime(settings)
    approved = await restarted_runtime.agent.execute(
        ExecutionRequest(
            capability="files.write_text",
            arguments=arguments,
            approval_token=grant.token,
            context=context,
        )
    )
    assert approved.status is ExecutionStatus.SUCCEEDED
    assert (workspace / "approved.txt").read_text(encoding="utf-8") == "clear"

    replay = await restarted_runtime.agent.execute(
        ExecutionRequest(
            capability="files.write_text",
            arguments={**arguments, "overwrite": True},
            approval_token=grant.token,
            context=context,
        )
    )
    assert replay.status is ExecutionStatus.APPROVAL_REQUIRED


@pytest.mark.asyncio
async def test_workspace_connector_blocks_path_escape(tmp_path: Path) -> None:
    connector = WorkspaceFileConnector(tmp_path / "workspace")
    with pytest.raises(ConnectorError, match="escapes workspace"):
        await connector.read_text("../outside.txt")


def test_vector_memory_retrieves_highest_similarity() -> None:
    vectors = {
        "crypto": [1.0, 0.0],
        "security": [0.0, 1.0],
        "mixed": [0.5, 0.5],
    }
    memory = VectorMemory(lambda text: vectors[text])
    memory.add("a", "crypto")
    memory.add("b", "security")

    results = memory.retrieve("mixed", top_k=2)

    assert {result.key for result in results} == {"a", "b"}
    assert all(0.70 < result.score < 0.71 for result in results)


def test_audit_detects_tampering(tmp_path: Path) -> None:
    from artemis.function_agent.audit import HashChainAuditLog

    audit = HashChainAuditLog(tmp_path / "audit.jsonl")
    audit.append({"event": "original"})
    envelope = json.loads(audit.path.read_text(encoding="utf-8"))
    envelope["event"]["event"] = "tampered"
    audit.path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")

    assert audit.verify() == (False, 0)
