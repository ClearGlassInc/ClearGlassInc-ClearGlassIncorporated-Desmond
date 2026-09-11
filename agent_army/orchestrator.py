#!/usr/bin/env python3
"""Deterministic role routing and approval gating for the Agent Army.

``AGENT_POLICY.md`` defines the divisions, the nine-step execution sequence,
and the four actions that may never happen without explicit human approval.
This module turns a free-text objective into the plan that policy implies:
which specialists are engaged, which steps run, and which approval gates the
plan is stopped at.

Three properties matter more than sophistication here:

* **It decides, it never executes.** No network, no filesystem writes outside
  an explicitly requested ``--output``, no side effects. The plan is an
  artifact for a human to approve.
* **It is deterministic.** The same request against the same config yields a
  byte-identical plan, including ``plan_id``. ``agent-army.yml`` asserts on the
  generated plan, so a routing change has to show up as a diff rather than as
  an intermittent CI failure.
* **It fails closed on approvals.** A gate is added when the request mentions
  the gated action; gates are never removed by a later rule. Over-gating costs
  a human a moment. Under-gating publishes, spends, or deploys without one.

Matching is word-anchored, not naive substring: a trigger matches at a word
boundary and may carry a suffix. That is what lets ``preserv`` catch
"preserving" while ``ads`` does not catch "downloads" and ``dm`` does not catch
"admin" — the class of false positive that would silently attach a paid-spend
gate to an unrelated plan, or worse, look like the gating works when it is
firing at random.

Usage::

    python -m agent_army.orchestrator --request "..." --format json --output plan.json
    python -m agent_army.orchestrator --request "..."          # human-readable
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.json"


class ConfigurationError(ValueError):
    """The agent-army configuration is unusable and must not be run."""


@dataclass(frozen=True)
class Plan:
    """A governed execution plan. Reproducible from its request and config."""

    plan_id: str
    system: str
    request: str
    selected_agents: tuple[str, ...] = ()
    divisions: tuple[str, ...] = ()
    steps: tuple[dict[str, str], ...] = ()
    approvals_required: tuple[str, ...] = ()
    approval_detail: tuple[dict[str, str], ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matcher(trigger: str) -> re.Pattern[str]:
    """Word-anchored pattern for one trigger, tolerant of internal whitespace.

    Anchored at the start only, so a trigger doubles as a stem: ``distribut``
    matches "distribution" and "distributed".
    """
    return re.compile(r"\b" + r"\s+".join(re.escape(word) for word in trigger.split()))


def _matches(text: str, triggers: list[str]) -> bool:
    return any(_matcher(trigger).search(text) for trigger in triggers)


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load and validate the agent-army configuration.

    Raises :class:`ConfigurationError` rather than returning a config the
    router would silently misbehave on — a duplicate role key would make role
    selection depend on dict ordering, which is exactly the kind of
    non-determinism ``agent-army.yml`` exists to catch.
    """
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"cannot read agent-army config at {path}: {exc}") from exc

    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigurationError(f"{path} must contain a JSON object")

    for key in ("system", "roles", "approval_gates", "execution_sequence"):
        if key not in config:
            raise ConfigurationError(f"{path} is missing required key {key!r}")

    roles = config["roles"]
    if not isinstance(roles, list) or not roles:
        raise ConfigurationError(f"{path}: 'roles' must be a non-empty list")

    seen: set[str] = set()
    for role in roles:
        if not isinstance(role, dict):
            raise ConfigurationError(f"{path}: every role must be an object")
        for key in ("key", "division"):
            if not role.get(key):
                raise ConfigurationError(f"{path}: role is missing {key!r}: {role}")
        if role["key"] in seen:
            raise ConfigurationError(f"{path}: duplicate role key {role['key']!r}")
        seen.add(role["key"])

    gate_keys: set[str] = set()
    for gate in config["approval_gates"]:
        if not isinstance(gate, dict) or not gate.get("key"):
            raise ConfigurationError(f"{path}: every approval gate needs a 'key'")
        if gate["key"] in gate_keys:
            raise ConfigurationError(f"{path}: duplicate approval gate {gate['key']!r}")
        gate_keys.add(gate["key"])

    for step in config["execution_sequence"]:
        if not isinstance(step, dict) or not step.get("step") or not step.get("owner"):
            raise ConfigurationError(f"{path}: every step needs 'step' and 'owner'")
        if step["owner"] not in seen:
            raise ConfigurationError(
                f"{path}: step {step['step']!r} is owned by unknown role {step['owner']!r}"
            )

    return config


class AgentArmy:
    """Routes an objective to specialists, steps and approval gates."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.system: str = config["system"]
        self._roles: list[dict[str, Any]] = config["roles"]
        self._gates: list[dict[str, Any]] = config["approval_gates"]
        self._sequence: list[dict[str, Any]] = config["execution_sequence"]

    @staticmethod
    def _normalize(request: str) -> str:
        return " ".join(request.lower().split())

    def select_roles(self, request: str) -> list[str]:
        """Role keys engaged by this request, in configuration order.

        Roles marked ``always`` are engaged unconditionally: command has to be
        present to hold the approval gates even on a request that names no
        specialist at all.
        """
        text = self._normalize(request)
        return [
            role["key"]
            for role in self._roles
            if role.get("always") or _matches(text, role.get("triggers", []))
        ]

    def required_approvals(self, request: str) -> list[str]:
        """Approval gates this request trips, in configuration order."""
        text = self._normalize(request)
        return [
            gate["key"]
            for gate in self._gates
            if _matches(text, gate.get("triggers", []))
        ]

    def plan(self, request: str) -> Plan:
        """Build the governed plan for ``request``."""
        selected = self.select_roles(request)
        engaged = set(selected)
        approvals = self.required_approvals(request)

        steps = tuple(
            {
                "step": step["step"],
                "owner": step["owner"],
                "division": step.get("division", ""),
                "description": step.get("description", ""),
            }
            for step in self._sequence
            if step["owner"] in engaged
        )

        divisions = tuple(
            dict.fromkeys(
                role["division"] for role in self._roles if role["key"] in engaged
            )
        )

        detail = tuple(
            {"gate": gate["key"], "description": gate.get("description", "")}
            for gate in self._gates
            if gate["key"] in set(approvals)
        )

        return Plan(
            plan_id=self._plan_id(request, selected, approvals),
            system=self.system,
            request=request.strip(),
            selected_agents=tuple(selected),
            divisions=divisions,
            steps=steps,
            approvals_required=tuple(approvals),
            approval_detail=detail,
        )

    def _plan_id(self, request: str, roles: list[str], approvals: list[str]) -> str:
        """Stable identity for a plan.

        Derived from the normalized request and the routing it produced, so an
        identical request yields an identical id, and a config change that
        alters routing yields a different one.
        """
        material = json.dumps(
            {
                "system": self.system,
                "request": self._normalize(request),
                "roles": roles,
                "approvals": approvals,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def render_text(plan: Plan) -> str:
    lines = [
        f"{plan.system}",
        f"plan {plan.plan_id}",
        f"request: {plan.request}",
        "",
        f"divisions ({len(plan.divisions)}): {', '.join(plan.divisions) or 'none'}",
        f"agents ({len(plan.selected_agents)}): {', '.join(plan.selected_agents) or 'none'}",
        "",
        "steps:",
    ]
    lines.extend(
        f"  {index}. {step['step']} — {step['owner']}"
        for index, step in enumerate(plan.steps, start=1)
    )
    lines.append("")
    if plan.approvals_required:
        lines.append("HUMAN APPROVAL REQUIRED BEFORE EXECUTION:")
        lines.extend(f"  - {item['gate']}: {item['description']}" for item in plan.approval_detail)
    else:
        lines.append("no external approval gate is tripped by this request")
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, payload: str) -> None:
    """Write ``payload`` to ``path`` atomically.

    A consumer of the plan file never sees a partial document: the temporary
    file is fsynced and then renamed over the target in one step, and is
    removed if anything fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="The objective to route.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="Path to the agent-army configuration.")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="Output format.")
    parser.add_argument("--output", help="Write to this path instead of stdout.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigurationError as exc:
        print(f"agent-army configuration error: {exc}", file=sys.stderr)
        return 2

    plan = AgentArmy(config).plan(args.request)

    if args.format == "json":
        payload = json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"
    else:
        payload = render_text(plan)

    if args.output:
        write_atomic(Path(args.output), payload)
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
