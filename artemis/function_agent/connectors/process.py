# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Allowlisted subprocess connector with no shell interpolation."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from shutil import which

from .base import ConnectorError, ConnectorResponse


class AllowlistedProcessConnector:
    name = "process"

    def __init__(
        self,
        workspace: str | Path,
        allowed_executables: set[str] | None = None,
        timeout_seconds: float = 60.0,
        max_output_bytes: int = 1_000_000,
        allowed_environment: set[str] | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.allowed_executables = (
            set(allowed_executables) if allowed_executables is not None else set()
        )
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.allowed_environment = (
            set(allowed_environment)
            if allowed_environment is not None
            else {
                "PATH",
                "HOME",
                "USERPROFILE",
                "SYSTEMROOT",
                "TEMP",
                "TMP",
            }
        )

    async def health(self) -> ConnectorResponse:
        available = {
            executable: which(executable) is not None
            for executable in sorted(self.allowed_executables)
        }
        return ConnectorResponse(
            connector=self.name,
            operation="health",
            data={"workspace": str(self.workspace), "executables": available},
        )

    async def run(
        self,
        executable: str,
        arguments: list[str] | None = None,
        cwd: str = ".",
        timeout_seconds: float | None = None,
    ) -> dict[str, object]:
        executable_name = Path(executable).name
        if executable_name not in self.allowed_executables:
            raise ConnectorError(f"Executable is not allowlisted: {executable_name}")
        resolved_executable = which(executable_name)
        if resolved_executable is None:
            raise ConnectorError(f"Executable not found: {executable_name}")

        working_directory = (self.workspace / cwd).resolve()
        try:
            working_directory.relative_to(self.workspace)
        except ValueError as exc:
            raise ConnectorError(f"Working directory escapes workspace: {cwd}") from exc
        if not working_directory.is_dir():
            raise ConnectorError(f"Working directory not found: {cwd}")

        clean_arguments = [str(item) for item in (arguments or [])]
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in self.allowed_environment
        }
        process = await asyncio.create_subprocess_exec(
            resolved_executable,
            *clean_arguments,
            cwd=working_directory,
            env=environment,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timeout = timeout_seconds or self.timeout_seconds
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ConnectorError(f"Process exceeded {timeout} second timeout") from exc

        if len(stdout) + len(stderr) > self.max_output_bytes:
            raise ConnectorError(
                f"Process output exceeded {self.max_output_bytes} byte limit"
            )
        return {
            "executable": executable_name,
            "arguments": clean_arguments,
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
