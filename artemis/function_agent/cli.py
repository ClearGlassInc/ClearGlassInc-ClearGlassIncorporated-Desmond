# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Command-line interface for local Function Agent operation."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import uvicorn

from .api import create_app
from .models import ExecutionContext, ExecutionRequest
from .runtime import AgentRuntime, build_runtime


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("Arguments must decode to a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="artemis-function-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List registered capability schemas")
    subparsers.add_parser("audit-verify", help="Verify the audit hash chain")

    execute = subparsers.add_parser("execute", help="Execute one registered capability")
    execute.add_argument("capability")
    execute.add_argument("--arguments", type=_json_object, default={})
    execute.add_argument("--actor", default="local-cli")
    execute.add_argument("--role", action="append", default=[])
    execute.add_argument("--approval-token")

    grant = subparsers.add_parser("grant", help="Grant a pending local approval challenge")
    grant.add_argument("approval_id")

    serve = subparsers.add_parser("serve", help="Run the FastAPI control plane")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--log-level", default="info")

    return parser


async def _execute(runtime: AgentRuntime, arguments: argparse.Namespace) -> int:
    result = await runtime.agent.execute(
        ExecutionRequest(
            capability=arguments.capability,
            arguments=arguments.arguments,
            approval_token=arguments.approval_token,
            context=ExecutionContext(actor=arguments.actor, roles=set(arguments.role)),
        )
    )
    print(result.model_dump_json(indent=2))
    return 0 if result.status.value == "succeeded" else 2


def main() -> None:
    parser = build_parser()
    arguments = parser.parse_args()
    runtime = build_runtime()

    if arguments.command == "list":
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in runtime.agent.registry.list()],
                indent=2,
                sort_keys=True,
            )
        )
        return

    if arguments.command == "audit-verify":
        valid, records = runtime.agent.audit.verify()
        print(json.dumps({"valid": valid, "records": records}, indent=2))
        raise SystemExit(0 if valid else 3)

    if arguments.command == "execute":
        raise SystemExit(asyncio.run(_execute(runtime, arguments)))

    if arguments.command == "grant":
        try:
            grant = runtime.agent.approvals.grant(arguments.approval_id)
        except KeyError:
            parser.error("Approval challenge not found or expired")
        print(grant.model_dump_json(indent=2))
        return

    if arguments.command == "serve":
        uvicorn.run(
            create_app(runtime),
            host=arguments.host,
            port=arguments.port,
            log_level=arguments.log_level,
        )
        return

    parser.error(f"Unknown command: {arguments.command}")
