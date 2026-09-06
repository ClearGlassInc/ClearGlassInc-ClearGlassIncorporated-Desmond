# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Environment-driven runtime assembly for the Artemis Function Agent."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .agent import FunctionAgent, FunctionAgentSettings
from .builtins import install_core_capabilities
from .connectors import (
    AllowlistedHTTPConnector,
    AllowlistedProcessConnector,
    WorkspaceFileConnector,
)
from .policy import AgentPolicy, ApprovalManager
from .registry import CapabilityRegistry


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARTEMIS_FUNCTION_AGENT_",
        env_file=".env",
        extra="ignore",
    )

    workspace: Path = Path(".")
    state_dir: Path = Path(".artemis/function-agent")
    approval_secret: SecretStr | None = None
    operator_key: SecretStr | None = None
    enable_process_connector: bool = False
    enable_http_connector: bool = False
    allowed_executables: set[str] = Field(default_factory=set)
    allowed_http_hosts: set[str] = Field(default_factory=set)
    max_file_bytes: int = Field(default=2_000_000, ge=1_024, le=20_000_000)
    max_output_bytes: int = Field(default=1_000_000, ge=1_024, le=10_000_000)


@dataclass(slots=True)
class AgentRuntime:
    settings: RuntimeSettings
    agent: FunctionAgent
    files: WorkspaceFileConnector
    processes: AllowlistedProcessConnector | None
    http: AllowlistedHTTPConnector | None


def build_runtime(settings: RuntimeSettings | None = None) -> AgentRuntime:
    config = settings or RuntimeSettings()
    workspace = config.workspace.resolve()
    state_dir = config.state_dir.resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    files = WorkspaceFileConnector(workspace, max_read_bytes=config.max_file_bytes)
    processes = (
        AllowlistedProcessConnector(
            workspace,
            allowed_executables=config.allowed_executables,
            max_output_bytes=config.max_output_bytes,
        )
        if config.enable_process_connector
        else None
    )
    http = (
        AllowlistedHTTPConnector(config.allowed_http_hosts)
        if config.enable_http_connector and config.allowed_http_hosts
        else None
    )

    secret = _resolve_approval_secret(config, state_dir)
    agent = FunctionAgent(
        registry=CapabilityRegistry(),
        policy=AgentPolicy(),
        approvals=ApprovalManager(
            secret=secret,
            state_path=state_dir / "approvals.sqlite3",
        ),
        settings=FunctionAgentSettings(
            state_dir=state_dir,
            max_output_bytes=config.max_output_bytes,
        ),
    )
    install_core_capabilities(
        agent,
        files=files,
        processes=processes,
        http=http,
    )
    return AgentRuntime(
        settings=config,
        agent=agent,
        files=files,
        processes=processes,
        http=http,
    )


def _resolve_approval_secret(config: RuntimeSettings, state_dir: Path) -> str:
    if config.approval_secret is not None:
        return config.approval_secret.get_secret_value()

    key_path = state_dir / "approval.key"
    if key_path.exists():
        value = key_path.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise RuntimeError(f"Approval key is invalid: {key_path}")
        return value

    value = secrets.token_urlsafe(48)
    try:
        file_descriptor = os.open(
            key_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        return key_path.read_text(encoding="utf-8").strip()
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return value
