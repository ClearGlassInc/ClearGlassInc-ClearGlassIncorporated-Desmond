# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Typed function registration and invocation."""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from pydantic import BaseModel, ConfigDict, create_model

from .models import CapabilitySpec, RiskLevel

CapabilityCallable = Callable[..., Any] | Callable[..., Awaitable[Any]]


class CapabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


@dataclass(slots=True)
class RegisteredCapability:
    spec: CapabilitySpec
    function: CapabilityCallable
    input_model: type[BaseModel]

    async def invoke(self, arguments: dict[str, Any]) -> Any:
        validated = self.input_model.model_validate(arguments)
        value = self.function(**validated.model_dump())
        if inspect.isawaitable(value):
            return await value
        return value


class CapabilityRegistry:
    """In-process capability registry with strict schema validation."""

    def __init__(self) -> None:
        self._capabilities: dict[str, RegisteredCapability] = {}

    def register(
        self,
        function: CapabilityCallable,
        *,
        name: str | None = None,
        description: str | None = None,
        risk: RiskLevel = RiskLevel.SAFE,
        tags: set[str] | None = None,
        timeout_seconds: float = 30.0,
        idempotent: bool = False,
        replace: bool = False,
    ) -> RegisteredCapability:
        capability_name = name or function.__name__
        if capability_name in self._capabilities and not replace:
            raise ValueError(f"Capability already registered: {capability_name}")

        input_model = self._build_input_model(capability_name, function)
        spec = CapabilitySpec(
            name=capability_name,
            description=description or inspect.getdoc(function) or capability_name,
            risk=risk,
            input_schema=input_model.model_json_schema(),
            tags=tags or set(),
            timeout_seconds=timeout_seconds,
            idempotent=idempotent,
        )
        registered = RegisteredCapability(spec=spec, function=function, input_model=input_model)
        self._capabilities[capability_name] = registered
        return registered

    def register_decorated(
        self, function: CapabilityCallable, *, replace: bool = False
    ) -> RegisteredCapability:
        metadata = getattr(function, "__artemis_capability__", None)
        if metadata is None:
            raise ValueError(f"Function {function.__name__} is not decorated with @capability")
        return self.register(function, replace=replace, **metadata)

    def get(self, name: str) -> RegisteredCapability:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise KeyError(f"Unknown capability: {name}") from exc

    def list(self) -> list[CapabilitySpec]:
        return [
            item.spec
            for item in sorted(self._capabilities.values(), key=lambda item: item.spec.name)
        ]

    @staticmethod
    def _build_input_model(name: str, function: CapabilityCallable) -> type[BaseModel]:
        fields: dict[str, tuple[Any, Any]] = {}
        try:
            type_hints = get_type_hints(function)
        except (NameError, TypeError) as exc:
            raise TypeError(f"Capability {name} contains unresolved type annotations") from exc

        for parameter in inspect.signature(function).parameters.values():
            if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
                raise TypeError(f"Capability {name} may not use *args or **kwargs")
            annotation = type_hints.get(parameter.name, Any)
            default = ... if parameter.default is inspect.Parameter.empty else parameter.default
            fields[parameter.name] = (annotation, default)

        model_name = "".join(
            part.title()
            for part in name.replace("-", "_").replace(".", "_").split("_")
        )
        return create_model(f"{model_name}Input", __base__=CapabilityInput, **fields)


def capability(
    name: str | None = None,
    *,
    description: str | None = None,
    risk: RiskLevel = RiskLevel.SAFE,
    tags: set[str] | None = None,
    timeout_seconds: float = 30.0,
    idempotent: bool = False,
) -> Callable[[CapabilityCallable], CapabilityCallable]:
    """Mark a function for explicit registration without global side effects."""

    def decorator(function: CapabilityCallable) -> CapabilityCallable:
        function.__dict__["__artemis_capability__"] = {
            "name": name,
            "description": description,
            "risk": risk,
            "tags": tags,
            "timeout_seconds": timeout_seconds,
            "idempotent": idempotent,
        }
        return function

    return decorator
