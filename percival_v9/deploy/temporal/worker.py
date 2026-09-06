# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Durable workflow worker for Percival v9 (Temporal). AUTHORED, NOT DEPLOYED.

``temporalio`` is an optional, heavyweight dependency that is **not** installed
in the minimal CI env. This module is import-safe regardless: the activity/
workflow logic is plain and testable, and the Temporal wiring is only imported
inside ``run_worker()``. If the SDK is absent, ``temporal_available()`` returns
False and ``run_worker()`` raises a clear, actionable error instead of an
ImportError at module load.

The single governed activity routes every proposed action through the same
Policy Governor used everywhere else — Temporal never becomes a bypass path.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

from percival_v9.cmd.governor import load_governor
from percival_v9.internal.policy.engine import PolicyGovernor

TASK_QUEUE = "percival-v9"


def temporal_available() -> bool:
    """True iff the Temporal SDK can be imported (without importing it)."""
    return importlib.util.find_spec("temporalio") is not None


@dataclass(frozen=True)
class ActionRequest:
    identity: str
    capability: str


@dataclass(frozen=True)
class ActionResult:
    allowed: bool
    reason: str


def governed_action(request: ActionRequest, governor: PolicyGovernor | None = None) -> ActionResult:
    """Evaluate an action through the governor before it could ever run.

    Pure and dependency-free so it is unit-testable without Temporal. The real
    activity wraps this; the decision (and its audit entry) happen here.
    """
    gov = governor or load_governor()
    decision = gov.evaluate(request.identity, request.capability)
    return ActionResult(allowed=decision.allow, reason=decision.reason)


def run_worker(host: str = "temporal-frontend.temporal.svc.cluster.local:7233") -> int:
    """Start the Temporal worker. Requires the optional ``temporalio`` SDK.

    Deliberately not covered by CI (no SDK, no live Temporal). Kept thin so the
    governed logic above carries the testable weight.
    """
    if not temporal_available():
        raise RuntimeError(
            "temporalio is not installed. `pip install temporalio` and provide a "
            "reachable Temporal frontend before running the worker."
        )
    # Imported lazily so this module stays import-safe in minimal environments.
    import asyncio

    from temporalio.client import Client  # type: ignore[import-not-found]
    from temporalio.worker import Worker  # type: ignore[import-not-found]

    async def _main() -> None:
        client = await Client.connect(host)
        worker = Worker(client, task_queue=TASK_QUEUE, activities=[])
        await worker.run()

    asyncio.run(_main())
    return 0
