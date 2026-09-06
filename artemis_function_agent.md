# Artemis Function Agent

**ClearGlassInc Artemis Function Agent** is a production-oriented Python execution plane for typed tools, model-driven workflows, and controlled automation.

It is not an unrestricted shell agent. Power is added through explicit capability registration, and every capability is classified, validated, audited, bounded, and subject to deterministic policy.

## Architecture

```text
LLM client / API / CLI
          |
      AgentRunner
          |
  FunctionAgent execution plane
   |       |       |       |
Registry Policy Guardrails Approvals
   |                       |
Typed capabilities     HMAC + SQLite
   |
Bounded connectors
(filesystem / HTTP / process / custom)
   |
Memory + tamper-evident audit chain
```

### Core properties

- Async-first single and batch execution.
- Automatic JSON Schema generation from Python type hints.
- Strict rejection of undeclared tool arguments.
- Risk levels: `safe`, `read`, `write`, `external`, `destructive`, and `financial`.
- One-use approvals bound to the actor, capability, exact argument digest, and expiry.
- Durable approval challenges and signing key for restart-safe CLI/API operation.
- Input and output guardrail interceptors.
- Timeouts, bounded retries for idempotent tools, output limits, and circuit breaking.
- Working, episodic, semantic/vector, and durable SQLite memory adapters.
- Workspace-confined atomic file operations.
- Optional allowlisted HTTPS and no-shell process connectors.
- Hash-chained JSONL audit ledger with integrity verification.
- Vendor-neutral LLM client protocol and an optional OpenAI Responses API adapter.
- FastAPI control plane and CLI.

## Install

Core runtime:

```bash
python -m pip install -e .[dev]
```

Include the OpenAI adapter:

```bash
python -m pip install -e .[dev,openai]
```

## CLI

```bash
artemis-function-agent list
artemis-function-agent execute system.ping
artemis-function-agent audit-verify
artemis-function-agent serve --host 127.0.0.1 --port 8080
```

A write or external action returns `approval_required` and an `approval_id`.
Grant it locally, then repeat the exact request with the returned token:

```bash
artemis-function-agent grant <approval-id>
artemis-function-agent execute files.write_text \
  --actor local-cli \
  --arguments '{"path":"output.txt","content":"approved","overwrite":false}' \
  --approval-token '<token>'
```

Approval tokens are one-use and fail when the actor, capability, arguments, or expiry differ.

## API

Start the service:

```bash
artemis-function-agent serve
```

Primary routes:

| Route | Purpose |
| --- | --- |
| `GET /health/live` | Process liveness |
| `GET /health/ready` | Audit integrity and runtime readiness |
| `GET /v1/capabilities` | Typed capability catalog and JSON Schemas |
| `POST /v1/execute` | Execute one capability |
| `POST /v1/execute/batch` | Bounded concurrent execution |
| `POST /v1/approvals/{id}/grant` | Operator-key-gated approval grant |
| `GET /v1/audit/verify` | Verify the hash chain |

Configure the API approval endpoint:

```bash
export ARTEMIS_FUNCTION_AGENT_OPERATOR_KEY='replace-with-a-long-random-secret'
```

Deploy the API behind an authenticated reverse proxy or service mesh. `X-Artemis-Actor` is an audit label, not a complete identity system. Only a valid `X-Artemis-Operator-Key` grants the internal `operator` role.

## Runtime configuration

All settings use the `ARTEMIS_FUNCTION_AGENT_` prefix.

```bash
export ARTEMIS_FUNCTION_AGENT_WORKSPACE='/absolute/approved/workspace'
export ARTEMIS_FUNCTION_AGENT_STATE_DIR='/var/lib/artemis-function-agent'
export ARTEMIS_FUNCTION_AGENT_OPERATOR_KEY='long-random-operator-key'
export ARTEMIS_FUNCTION_AGENT_APPROVAL_SECRET='long-random-signing-secret'
```

The runtime creates a local approval signing key when no signing secret is supplied. Runtime state is stored under `.artemis/function-agent` by default and is excluded from Git.

### Optional process connector

The process connector is disabled by default. To enable it, provide an explicit executable allowlist:

```bash
export ARTEMIS_FUNCTION_AGENT_ENABLE_PROCESS_CONNECTOR=true
export ARTEMIS_FUNCTION_AGENT_ALLOWED_EXECUTABLES='["git","pytest","ruff"]'
```

It uses `asyncio.create_subprocess_exec`, never `shell=True`. Approval is still required for every invocation. An allowlisted executable can remain powerful; use container, OS, and service-account isolation in production.

### Optional HTTP connector

The HTTP connector is disabled by default and requires explicit hosts:

```bash
export ARTEMIS_FUNCTION_AGENT_ENABLE_HTTP_CONNECTOR=true
export ARTEMIS_FUNCTION_AGENT_ALLOWED_HTTP_HOSTS='["api.github.com"]'
```

It permits HTTPS only, rejects URL credentials and non-standard ports, disables redirects, checks resolved addresses, limits response size, and strips sensitive response headers.

## Register a custom capability

```python
from artemis.function_agent import RiskLevel, build_runtime

runtime = build_runtime()

async def customer_lookup(customer_id: str) -> dict[str, str]:
    """Retrieve an approved customer record by identifier."""
    return {"customer_id": customer_id, "status": "active"}

runtime.agent.registry.register(
    customer_lookup,
    name="crm.customer_lookup",
    risk=RiskLevel.READ,
    tags={"crm", "customer"},
    idempotent=True,
)
```

The registry resolves postponed annotations, builds a strict Pydantic input model, and publishes its JSON Schema to model clients and the capability API.

## Add a guardrail

```python
from artemis.function_agent import PredicateGuardrail

runtime.agent.guardrails.add(
    PredicateGuardrail(
        name="tenant-boundary",
        input_predicate=lambda request: request.context.metadata.get("tenant") == "clearglass",
        rejection_reason="Tenant boundary rejected the request",
    )
)
```

Input guardrails run before policy and execution. Output guardrails run after normalization and before success is returned.

## Model-driven runner

```python
from artemis.function_agent import AgentRunner, build_runtime
from artemis.function_agent.llm_clients import OpenAIResponsesClient

runtime = build_runtime()
client = OpenAIResponsesClient(model="gpt-5.5")
runner = AgentRunner(runtime.agent, client)

result = await runner.run("Check whether Artemis is operational.")
print(result.text)
```

`AgentRunner.stream()` preserves the complete multi-turn tool loop. Provider text deltas, tool calls, execution results, approval stops, and completion events are emitted as structured stream events.

## Security boundaries

- `destructive` and `financial` capabilities are denied by default.
- `write` and `external` capabilities require approval by default.
- The API never accepts roles or execution context from the JSON request body.
- Approval tokens are one-use and exact-request-bound.
- Filesystem paths are resolved against the configured workspace.
- Process and network connectors are off until explicitly configured.
- Secrets must be supplied through environment or secret-management infrastructure, never tool arguments or source control.
- The hash chain detects audit modification; it does not replace remote append-only log retention.
- For hostile workloads, run the service in a locked-down container or VM with a dedicated low-privilege account.

## Verification

```bash
python -m compileall -q artemis/function_agent
ruff check artemis/function_agent artemis/tests/test_function_agent_*.py
pytest -q artemis/tests/test_function_agent_*.py
```

The dedicated GitHub Actions workflow runs the function-agent tests across supported Python versions without external credentials or network calls.
