# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Contracts shared by external-system connectors."""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ConnectorError(RuntimeError):
    pass


class ConnectorResponse(BaseModel):
    connector: str
    operation: str
    status_code: int | None = None
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Connector(Protocol):
    name: str

    async def health(self) -> ConnectorResponse: ...
