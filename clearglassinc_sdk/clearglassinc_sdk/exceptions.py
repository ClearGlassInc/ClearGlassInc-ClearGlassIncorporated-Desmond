"""Exception hierarchy for the ClearGlassInc Agent SDK."""


class ClearGlassSDKError(Exception):
    """Base class for all SDK errors."""


class ToolExecutionError(ClearGlassSDKError):
    """Raised when a tool call fails."""

    def __init__(self, tool_name: str, original: Exception):
        self.tool_name = tool_name
        self.original = original
        super().__init__(f"Tool '{tool_name}' raised {original!r}")


class GuardrailViolation(ClearGlassSDKError):
    """Raised when a guardrail blocks input or output."""

    def __init__(self, guardrail_name: str, reason: str):
        self.guardrail_name = guardrail_name
        self.reason = reason
        super().__init__(f"Guardrail '{guardrail_name}' blocked: {reason}")


class MaxStepsExceeded(ClearGlassSDKError):
    """Raised when an agent run exceeds its configured step budget without finishing."""

    def __init__(self, max_steps: int):
        self.max_steps = max_steps
        super().__init__(f"Run did not complete within {max_steps} steps")
