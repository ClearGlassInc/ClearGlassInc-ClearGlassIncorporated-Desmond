"""Tiered model router.

Mirrors the 2026 "orchestrator-first" tiering from the strategy doc: a Pro tier
for complex reasoning (legal/financial), a Flash tier for routine reasoning, and
a Flash-Lite tier for cheap templating. The default backend is a deterministic
offline mock so the system runs with zero external dependencies or API keys.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class ModelTier(str, Enum):
    """Model capability tiers, cheapest last."""

    PRO = "pro"  # complex reasoning: legal / financial / critique
    FLASH = "flash"  # routine reasoning: task decomposition
    FLASH_LITE = "flash-lite"  # cheap templating / research scaffolding


@dataclass(frozen=True)
class ModelResponse:
    tier: ModelTier
    prompt: str
    text: str
    tokens: int


def _mock_backend(tier: ModelTier, prompt: str) -> str:
    """Deterministic offline completion.

    Hashing the (tier, prompt) pair makes runs reproducible — the same input
    always yields the same draft, which keeps CI and tests stable.
    """
    digest = hashlib.sha256(f"{tier.value}:{prompt}".encode()).hexdigest()[:10]
    return f"[{tier.value}] draft:{digest} :: {prompt.strip()[:160]}"


# A backend maps (tier, prompt) -> completion text. Provide your own to plug in
# a real provider; the signature is intentionally minimal.
Backend = Callable[[ModelTier, str], str]


class ModelRouter:
    """Routes prompts to a tier-appropriate backend and records every call."""

    def __init__(self, backend: Backend | None = None) -> None:
        self._backend = backend or _mock_backend
        self.calls: list[ModelResponse] = []

    def complete(self, tier: ModelTier, prompt: str) -> ModelResponse:
        text = self._backend(tier, prompt)
        response = ModelResponse(
            tier=tier,
            prompt=prompt,
            text=text,
            tokens=len(prompt.split()) + len(text.split()),
        )
        self.calls.append(response)
        return response

    @property
    def total_tokens(self) -> int:
        return sum(call.tokens for call in self.calls)
