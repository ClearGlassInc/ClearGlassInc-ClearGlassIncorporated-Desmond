"""ClearGlassInc Agent SDK — a modular, provider-agnostic framework for building
tool-using LLM agents with memory, guardrails, and streaming execution."""

from clearglassinc_sdk.agent import Agent
from clearglassinc_sdk.exceptions import (
    ClearGlassSDKError,
    GuardrailViolation,
    MaxStepsExceeded,
    ToolExecutionError,
)
from clearglassinc_sdk.guardrails import Guardrail, GuardrailResult
from clearglassinc_sdk.memory import Memory
from clearglassinc_sdk.runner import Runner, RunResult
from clearglassinc_sdk.tools import Tool, tool

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "ClearGlassSDKError",
    "Guardrail",
    "GuardrailResult",
    "GuardrailViolation",
    "MaxStepsExceeded",
    "Memory",
    "RunResult",
    "Runner",
    "Tool",
    "ToolExecutionError",
    "__version__",
    "tool",
]
