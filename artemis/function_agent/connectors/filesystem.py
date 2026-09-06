# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Workspace-confined filesystem connector."""
from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

from .base import ConnectorError, ConnectorResponse


class WorkspaceFileConnector:
    name = "filesystem"

    def __init__(
        self,
        root: str | Path,
        max_read_bytes: int = 2_000_000,
        max_write_bytes: int | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_read_bytes = max_read_bytes
        self.max_write_bytes = (
            max_read_bytes if max_write_bytes is None else max_write_bytes
        )

    async def health(self) -> ConnectorResponse:
        return ConnectorResponse(
            connector=self.name,
            operation="health",
            data={"root": str(self.root), "readable": os.access(self.root, os.R_OK)},
        )

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        target = self._resolve(path)
        return await asyncio.to_thread(self._read_text, target, encoding)

    async def write_text(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = False,
    ) -> dict[str, object]:
        target = self._resolve(path)
        return await asyncio.to_thread(
            self._write_text,
            target,
            content,
            encoding,
            overwrite,
        )

    async def list_files(self, path: str = ".", limit: int = 500) -> list[dict[str, object]]:
        target = self._resolve(path)
        return await asyncio.to_thread(self._list_files, target, limit)

    async def sha256(self, path: str) -> str:
        target = self._resolve(path)
        return await asyncio.to_thread(self._sha256, target)

    def _resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ConnectorError(f"Path escapes workspace: {path}") from exc
        return candidate

    def _read_text(self, target: Path, encoding: str) -> str:
        if not target.is_file():
            raise ConnectorError(f"File not found: {target.relative_to(self.root)}")
        size = target.stat().st_size
        if size > self.max_read_bytes:
            raise ConnectorError(f"File exceeds {self.max_read_bytes} byte read limit")
        return target.read_text(encoding=encoding)

    def _write_text(
        self,
        target: Path,
        content: str,
        encoding: str,
        overwrite: bool,
    ) -> dict[str, object]:
        if target.exists() and not overwrite:
            raise ConnectorError(f"Refusing to overwrite existing file: {target.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = content.encode(encoding)
        if len(encoded) > self.max_write_bytes:
            raise ConnectorError(
                f"Content exceeds {self.max_write_bytes} byte write limit"
            )
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", dir=target.parent
        )
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
        return {
            "path": str(target.relative_to(self.root)),
            "bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }

    def _list_files(self, target: Path, limit: int) -> list[dict[str, object]]:
        if not target.exists():
            raise ConnectorError(f"Path not found: {target.relative_to(self.root)}")
        if limit < 1 or limit > 10_000:
            raise ConnectorError("limit must be between 1 and 10000")
        items: list[dict[str, object]] = []
        iterator = target.rglob("*") if target.is_dir() else iter((target,))
        for item in iterator:
            if len(items) >= limit:
                break
            items.append(
                {
                    "path": str(item.relative_to(self.root)),
                    "type": "directory" if item.is_dir() else "file",
                    "bytes": item.stat().st_size if item.is_file() else None,
                }
            )
        return items

    @staticmethod
    def _sha256(target: Path) -> str:
        if not target.is_file():
            raise ConnectorError(f"File not found: {target}")
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
