"""ClearGlass Engineering and Marketing Agent Army.

Governed role routing and approval gating. ``AGENT_POLICY.md`` is the policy
this package implements; ``orchestrator.py`` is the deterministic runner.

The public names are re-exported lazily (PEP 562) rather than imported at
module scope. ``agent-army.yml`` runs ``python -m agent_army.orchestrator``,
and an eager ``from .orchestrator import ...`` here makes the submodule appear
in ``sys.modules`` before ``runpy`` executes it — which emits a RuntimeWarning
about unpredictable behaviour on every CI run.
"""

from __future__ import annotations

from typing import Any

__all__ = ["AgentArmy", "ConfigurationError", "Plan", "load_config"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import orchestrator

        return getattr(orchestrator, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
