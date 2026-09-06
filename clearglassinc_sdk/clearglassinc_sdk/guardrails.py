"""Guardrails: pluggable validation/safety checks applied to agent input
and output before/after each model call."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class GuardrailResult:
    passed: bool
    reason: str = ""


class Guardrail(Protocol):
    """A guardrail inspects a piece of text and decides whether it's allowed."""

    name: str

    def check(self, text: str) -> GuardrailResult: ...


@dataclass
class MaxLengthGuardrail:
    """Rejects text longer than `max_chars`."""

    max_chars: int
    name: str = "max_length"

    def check(self, text: str) -> GuardrailResult:
        if len(text) > self.max_chars:
            return GuardrailResult(False, f"text exceeds {self.max_chars} characters")
        return GuardrailResult(True)


@dataclass
class RegexBlocklistGuardrail:
    """Rejects text matching any pattern in `patterns` (e.g. secrets, PII)."""

    patterns: list[str]
    name: str = "regex_blocklist"

    def __post_init__(self) -> None:
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def check(self, text: str) -> GuardrailResult:
        for pattern in self._compiled:
            if pattern.search(text):
                return GuardrailResult(False, f"text matched blocked pattern: {pattern.pattern}")
        return GuardrailResult(True)


@dataclass
class RequiredKeywordsGuardrail:
    """Requires at least one of `keywords` to be present (e.g. topical scoping)."""

    keywords: list[str]
    name: str = "required_keywords"

    def check(self, text: str) -> GuardrailResult:
        lowered = text.lower()
        if not any(keyword.lower() in lowered for keyword in self.keywords):
            return GuardrailResult(False, f"text did not contain any of {self.keywords}")
        return GuardrailResult(True)


def run_guardrails(guardrails: list[Guardrail], text: str) -> GuardrailResult:
    """Runs guardrails in order, short-circuiting on the first failure."""
    for guardrail in guardrails:
        result = guardrail.check(text)
        if not result.passed:
            return result
    return GuardrailResult(True)
