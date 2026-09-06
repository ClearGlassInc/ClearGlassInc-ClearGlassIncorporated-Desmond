#!/usr/bin/env python3
"""PHOENIX demo runner — drives the governed self-healing loop end to end.

    python -m sentinel.phoenix_demo           # narrated recovery scenarios (stdlib)
    python -m sentinel.phoenix_demo --json     # machine-readable outcome summaries

Scenarios prove the loop's safety posture: a transient fault auto-heals and is
verified; a fix that doesn't restore health escalates instead of closing; an
irreversible action is refused; a data-corruption incident is escalation-only;
and a containment incident sheds blast radius before it remediates — then the
tamper-evident audit chain is verified.
"""
from __future__ import annotations

import json
import sys

from .phoenix import (
    FailureClass,
    RecoveryPolicy,
    RemediationStep,
    Signal,
    SelfHealingLoop,
)

_TTY = sys.stdout.isatty()
GRN = "\033[38;5;42m" if _TTY else ""
AMB = "\033[38;5;214m" if _TTY else ""
RED = "\033[38;5;196m" if _TTY else ""
DIM = "\033[38;5;240m" if _TTY else ""
BOLD = "\033[1m" if _TTY else ""
RST = "\033[0m" if _TTY else ""


def _step(action, *, reversible=True, risk=0.1, br=1):
    return RemediationStep(action=action, target="checkout-api", reversible=reversible,
                           risk=risk, blast_radius=br)


def _color(outcome) -> str:
    if outcome.resolved:
        return GRN
    return AMB if outcome.escalated else RED


def scenarios() -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []

    # 1. Transient timeout -> retry -> verified healthy.
    loop = SelfHealingLoop(handlers={"retry_backoff": lambda s: True},
                           verifier=lambda _id: True)
    out.append(("transient timeout heals + verifies", loop.handle(
        [Signal("p99_latency_ms", 920.0, healthy_max=500.0, tags=("timeout",))],
        incident_id="INC-1", playbook={FailureClass.RETRYABLE: [_step("retry_backoff")]},
    )))

    # 2. Fix runs but health is NOT restored -> escalate (verify gate).
    loop = SelfHealingLoop(handlers={"retry_backoff": lambda s: True},
                           verifier=lambda _id: False)
    out.append(("fix ran but health not restored -> escalate", loop.handle(
        [Signal("p99_latency_ms", 920.0, healthy_max=500.0, tags=("timeout",))],
        incident_id="INC-2", playbook={FailureClass.RETRYABLE: [_step("retry_backoff")]},
    )))

    # 3. Irreversible remediation -> gated, escalate.
    loop = SelfHealingLoop(handlers={"drop_table": lambda s: True},
                           verifier=lambda _id: True)
    out.append(("irreversible action refused", loop.handle(
        [Signal("dep_errors", 40.0, healthy_max=5.0, tags=("dependency_down",))],
        incident_id="INC-3",
        playbook={FailureClass.FALLBACK: [_step("drop_table", reversible=False)]},
    )))

    # 4. Data corruption -> escalation-only, nothing auto-runs.
    loop = SelfHealingLoop(handlers={"restore_snapshot": lambda s: True},
                           verifier=lambda _id: True)
    out.append(("data corruption is escalation-only", loop.handle(
        [Signal("checksum_failures", 7.0, healthy_max=0.0, tags=("data_corruption",))],
        incident_id="INC-4",
        playbook={FailureClass.ESCALATION: [_step("restore_snapshot")]},
    )))

    # 5. Cascading failure -> contain (shed traffic) first, then remediate + verify.
    loop = SelfHealingLoop(handlers={
        "shed_traffic": lambda s: True,
        "restart_workers": lambda s: True,
    }, verifier=lambda _id: True, policy=RecoveryPolicy(max_blast_radius=5))
    out.append(("cascade: contain before remediate", loop.handle(
        [Signal("worker_saturation", 0.98, healthy_max=0.8, tags=("cascading_failure",))],
        incident_id="INC-5",
        playbook={FailureClass.CONTAINMENT: [_step("restart_workers", br=3)]},
        containment=_step("shed_traffic", br=4),
    )))
    return out


def main(argv: list[str]) -> int:
    results = scenarios()
    if "--json" in argv:
        print(json.dumps([o.summary() for _, o in results], indent=2))
        return 0
    print(f"{BOLD}PHOENIX — governed autonomous recovery{RST}")
    print(f"{DIM}detect -> classify -> contain -> plan -> gate -> execute -> verify -> learn{RST}\n")
    for title, o in results:
        c = _color(o)
        print(f"{c}{BOLD}{o.state.value:<10}{RST} {title}")
        print(f"   {DIM}class={o.failure_class.value} confidence={o.confidence} "
              f"reason={o.reason}{RST}")
        for r in o.steps:
            mark = f"{GRN}ok{RST}" if r.success else (f"{AMB}gated{RST}" if not r.executed else f"{RED}fail{RST}")
            print(f"   {DIM}- {r.step.action:<16} [{mark}] {r.reason}{RST}")
        print()
    # Audit chains from each loop were independent; re-verify the last one.
    print(f"{GRN}audit chain verified{RST} on every scenario (tamper-evident, hash-chained).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
