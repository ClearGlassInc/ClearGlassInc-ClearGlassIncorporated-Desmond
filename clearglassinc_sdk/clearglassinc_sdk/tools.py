"""Tool abstractions: wrap plain Python callables as schema-described,
provider-agnostic function-calling tools."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, get_type_hints

_TYPE_TO_JSON_SCHEMA: dict[type, dict[str, Any]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}


def _schema_for_annotation(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty:
        return {"type": "string"}
    return _TYPE_TO_JSON_SCHEMA.get(annotation, {"type": "string"})


def _build_parameters_schema(func: Callable[..., Any]) -> dict[str, Any]:
    """Derive a JSON Schema `parameters` object from a function's signature."""
    signature = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:  # noqa: BLE001 - unresolvable forward refs fall back to permissive schemas
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue
        annotation = hints.get(param_name, param.annotation)
        properties[param_name] = _schema_for_annotation(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {"type": "object", "properties": properties, "required": required}


@dataclass
class Tool:
    """A callable exposed to an agent, with a name/description/JSON schema
    that can be handed to any LLM provider's function-calling API."""

    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.parameters:
            self.parameters = _build_parameters_schema(self.func)

    def to_schema(self) -> dict[str, Any]:
        """OpenAI/Anthropic-compatible function-calling schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def run(self, **kwargs: Any) -> Any:
        """Invoke the tool synchronously (runs async funcs via a fresh loop)."""
        if inspect.iscoroutinefunction(self.func):
            return asyncio.run(self.func(**kwargs))
        return self.func(**kwargs)

    async def arun(self, **kwargs: Any) -> Any:
        """Invoke the tool asynchronously."""
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return await asyncio.to_thread(self.func, **kwargs)


def tool(name: str | None = None, description: str | None = None) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator that turns a plain function into a `Tool`.

    Example:
        @tool(description="Adds two numbers")
        def add(a: int, b: int) -> int:
            return a + b
    """

    def decorator(func: Callable[..., Any]) -> Tool:
        tool_name = name or func.__name__
        tool_description = description or (inspect.getdoc(func) or "").strip() or tool_name
        return Tool(name=tool_name, description=tool_description, func=func)

    return decorator
