# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Command-line entrypoint for the MLOps deploy agent.

Loads a JSON DeployPlan and runs it through the in-memory adapters by default.
Production use swaps adapters via factory injection.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adapters import InMemoryCI, InMemoryRegistry, InMemoryRuntime, InMemorySecrets
from .schema import DeployPlan, ModelRef, Policy, Target
from .supervisor import StageFailure, Supervisor


def _load_plan(path: Path) -> DeployPlan:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    model = ModelRef(**raw["model"])
    target_raw = dict(raw["target"])
    if "canary_steps" in target_raw:
        target_raw["canary_steps"] = tuple(target_raw["canary_steps"])
    target = Target(**target_raw)
    policy = Policy(**raw["policy"])
    return DeployPlan(
        plan_id=raw["plan_id"],
        model=model,
        target=target,
        policy=policy,
        secrets_ref=raw["secrets_ref"],
        image_digest=raw["image_digest"],
        rollback_on_fail=raw.get("rollback_on_fail", True),
    )


def _bootstrap_in_memory(plan: DeployPlan) -> Supervisor:
    registry = InMemoryRegistry()
    registry.register(plan.model.name, plan.model.version, plan.model.digest, signed=True)
    registry.signed.add(plan.image_digest)
    secrets = InMemorySecrets(store={plan.secrets_ref: {"api_key": "local-dev"}})
    return Supervisor(
        registry=registry,
        runtime=InMemoryRuntime(),
        secrets=secrets,
        ci=InMemoryCI(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mlops-deploy-agent")
    parser.add_argument("--plan", required=True, type=Path, help="path to DeployPlan JSON")
    parser.add_argument("--dry-run", action="store_true", help="use in-memory adapters")
    args = parser.parse_args(argv)

    plan = _load_plan(args.plan)
    if not args.dry_run:
        print("real adapters not configured in this template; pass --dry-run", file=sys.stderr)
        return 2

    supervisor = _bootstrap_in_memory(plan)
    try:
        manifest = supervisor.run(plan)
    except StageFailure as exc:
        print(json.dumps({"status": "FAILED", "stage": exc.stage, "reason": exc.reason}))
        return 1
    print(json.dumps({"status": "OK", "manifest": asdict(manifest)}, indent=2, default=list))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
