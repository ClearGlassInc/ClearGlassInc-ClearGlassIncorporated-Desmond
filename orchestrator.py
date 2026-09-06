"""Deterministic orchestration for the ClearGlass engineering and marketing agent army.

This module performs local planning only. It does not call external services, publish
content, contact prospects, spend money, deploy production systems, or store secrets.
Those actions remain behind explicit human approval gates defined in config.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ConfigurationError(ValueError):
    """Raised when the agent-army configuration is incomplete or inconsistent."""


@dataclass(frozen=True)
class AgentRole:
    id: str
    division: str
    name: str
    mission: str
    triggers: tuple[str, ...]
    deliverables: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionStep:
    sequence: int
    stage: str
    owner_id: str
    owner_name: str
    objective: str
    deliverables: tuple[str, ...]
    approval_required: bool
    approval_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    generated_at: str
    system: str
    request: str
    assessment: str
    selected_agents: tuple[str, ...]
    approvals_required: tuple[str, ...]
    steps: tuple[ExecutionStep, ...]
    risks: tuple[str, ...]
    validation: tuple[str, ...]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def to_markdown(self) -> str:
        approvals = ", ".join(self.approvals_required) or "None for planning"
        agents = ", ".join(self.selected_agents)
        lines = [
            f"# Execution Plan {self.plan_id}",
            "",
            f"**Generated:** {self.generated_at}",
            f"**System:** {self.system}",
            f"**Request:** {self.request}",
            f"**Assessment:** {self.assessment}",
            f"**Selected agents:** {agents}",
            f"**Approval gates:** {approvals}",
            "",
            "## Steps",
            "",
        ]
        for step in self.steps:
            approval = "yes" if step.approval_required else "no"
            reasons = ", ".join(step.approval_reasons) or "none"
            lines.extend(
                [
                    f"### {step.sequence}. {step.stage}",
                    f"- Owner: **{step.owner_name}** (`{step.owner_id}`)",
                    f"- Objective: {step.objective}",
                    f"- Deliverables: {', '.join(step.deliverables)}",
                    f"- Human approval required: {approval} ({reasons})",
                    "",
                ]
            )
        lines.extend(["## Risks", ""])
        lines.extend(f"- {risk}" for risk in self.risks)
        lines.extend(["", "## Validation", ""])
        lines.extend(f"- {item}" for item in self.validation)
        lines.extend(["", "## Next action", "", self.next_action, ""])
        return "\n".join(lines)


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{name} must be a non-empty array")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_require_string(item, f"{name}[{index}]").lower())
    return tuple(result)


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate an agent-army configuration file."""

    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"invalid JSON in {config_path}: line {exc.lineno}, column {exc.colno}"
        ) from exc

    config = dict(_require_mapping(raw, "config"))
    for key in ("version", "system", "mission"):
        _require_string(config.get(key), key)

    roles_raw = config.get("roles")
    if not isinstance(roles_raw, list) or not roles_raw:
        raise ConfigurationError("roles must be a non-empty array")

    role_ids: set[str] = set()
    divisions: set[str] = set()
    normalized_roles: list[dict[str, Any]] = []
    for index, role_value in enumerate(roles_raw):
        role = _require_mapping(role_value, f"roles[{index}]")
        role_id = _require_string(role.get("id"), f"roles[{index}].id")
        if role_id in role_ids:
            raise ConfigurationError(f"duplicate role id: {role_id}")
        role_ids.add(role_id)
        division = _require_string(role.get("division"), f"roles[{index}].division").lower()
        divisions.add(division)
        normalized_roles.append(
            {
                "id": role_id,
                "division": division,
                "name": _require_string(role.get("name"), f"roles[{index}].name"),
                "mission": _require_string(role.get("mission"), f"roles[{index}].mission"),
                "triggers": _require_string_list(role.get("triggers"), f"roles[{index}].triggers"),
                "deliverables": _require_string_list(
                    role.get("deliverables"), f"roles[{index}].deliverables"
                ),
            }
        )

    missing_divisions = {"command", "engineering", "marketing"} - divisions
    if missing_divisions:
        raise ConfigurationError(
            "roles must cover command, engineering, and marketing divisions; missing: "
            + ", ".join(sorted(missing_divisions))
        )

    workflow_raw = config.get("workflow")
    if not isinstance(workflow_raw, list) or not workflow_raw:
        raise ConfigurationError("workflow must be a non-empty array")
    workflow: list[dict[str, str]] = []
    stages: set[str] = set()
    for index, stage_value in enumerate(workflow_raw):
        stage = _require_mapping(stage_value, f"workflow[{index}]")
        stage_id = _require_string(stage.get("stage"), f"workflow[{index}].stage")
        if stage_id in stages:
            raise ConfigurationError(f"duplicate workflow stage: {stage_id}")
        stages.add(stage_id)
        owner = _require_string(stage.get("owner"), f"workflow[{index}].owner")
        if owner not in role_ids:
            raise ConfigurationError(f"workflow stage {stage_id} references unknown owner {owner}")
        workflow.append(
            {
                "stage": stage_id,
                "owner": owner,
                "output": _require_string(stage.get("output"), f"workflow[{index}].output"),
            }
        )

    guardrails = dict(_require_mapping(config.get("guardrails"), "guardrails"))
    guardrails["forbidden"] = _require_string_list(guardrails.get("forbidden"), "guardrails.forbidden")
    guardrails["approval_required"] = _require_string_list(
        guardrails.get("approval_required"), "guardrails.approval_required"
    )

    config["roles"] = normalized_roles
    config["workflow"] = workflow
    config["guardrails"] = guardrails
    return config


class AgentArmy:
    """Routes a request and produces a governed, deterministic execution plan."""

    _ENGINEERING_SIGNALS = {
        "api",
        "architecture",
        "build",
        "code",
        "deploy",
        "engineering",
        "fix",
        "implement",
        "legacy",
        "migration",
        "modernize",
        "performance",
        "refactor",
        "release",
        "security",
        "software",
        "test",
    }
    _MARKETING_SIGNALS = {
        "audience",
        "campaign",
        "compaign",
        "content",
        "conversion",
        "customer",
        "email",
        "launch",
        "lead",
        "linkedin",
        "market",
        "marketing",
        "multi",
        "offer",
        "outreach",
        "pipeline",
        "positioning",
        "publish",
        "revenue",
        "sales",
        "seo",
        "social",
        "swarm",
    }
    _APPROVAL_SIGNALS = {
        "external_publish": {"publish", "post", "social", "launch", "newsletter"},
        "external_outreach": {"outreach", "email", "dm", "contact", "prospect"},
        "paid_spend": {"ads", "advertising", "budget", "spend", "sponsor"},
        "production_deploy": {"deploy", "production", "release", "merge"},
        "legal_or_regulatory_claim": {"legal", "regulatory", "compliance", "certified"},
        "customer_data_use": {"customer data", "personal data", "crm", "pii"},
    }

    def __init__(self, config: Mapping[str, Any]):
        self.config = dict(config)
        self.roles = {
            role["id"]: AgentRole(
                id=role["id"],
                division=role["division"],
                name=role["name"],
                mission=role["mission"],
                triggers=tuple(role["triggers"]),
                deliverables=tuple(role["deliverables"]),
            )
            for role in self.config["roles"]
        }

    @classmethod
    def from_file(cls, path: str | Path) -> "AgentArmy":
        return cls(load_config(path))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        normalized = "".join(character.lower() if character.isalnum() else " " for character in text)
        return {token for token in normalized.split() if token}

    def _role_scores(self, request: str) -> dict[str, int]:
        text = request.lower()
        tokens = self._tokens(request)
        scores: dict[str, int] = {}
        for role in self.roles.values():
            score = 0
            for trigger in role.triggers:
                if " " in trigger:
                    score += 3 if trigger in text else 0
                elif trigger in tokens:
                    score += 2
            scores[role.id] = score
        return scores

    def select_roles(self, request: str) -> tuple[str, ...]:
        tokens = self._tokens(request)
        engineering = bool(tokens & self._ENGINEERING_SIGNALS)
        marketing = bool(tokens & self._MARKETING_SIGNALS)
        scores = self._role_scores(request)

        selected = {"chief_of_staff", "analytics_controller"}
        if engineering:
            selected.update({"staff_engineer", "quality_security"})
        if marketing:
            selected.update(
                {
                    "market_intelligence",
                    "content_strategist",
                    "distribution_planner",
                    "revenue_operator",
                }
            )
        selected.update(role_id for role_id, score in scores.items() if score > 0)

        if not engineering and not marketing and all(score == 0 for score in scores.values()):
            selected.update(self.roles)

        workflow_order = [stage["owner"] for stage in self.config["workflow"]]
        ordered = [role_id for role_id in workflow_order if role_id in selected]
        ordered.extend(sorted(selected - set(ordered)))
        return tuple(dict.fromkeys(ordered))

    def required_approvals(self, request: str) -> tuple[str, ...]:
        text = request.lower()
        tokens = self._tokens(request)
        configured = set(self.config["guardrails"]["approval_required"])
        approvals: list[str] = []
        for approval, signals in self._APPROVAL_SIGNALS.items():
            if approval not in configured:
                continue
            matched = any((signal in text if " " in signal else signal in tokens) for signal in signals)
            if matched:
                approvals.append(approval)
        return tuple(approvals)

    @staticmethod
    def _approval_for_stage(stage: str, approvals: Sequence[str]) -> tuple[str, ...]:
        stage_rules = {
            "quality_gate": {"production_deploy", "legal_or_regulatory_claim", "customer_data_use"},
            "legacy_assurance": {"production_deploy", "customer_data_use"},
            "distribution": {"external_publish", "external_outreach", "paid_spend"},
            "campaign_bot_operations": {"external_publish", "external_outreach", "paid_spend"},
            "revenue": {"external_outreach", "paid_spend", "customer_data_use"},
        }
        applicable = stage_rules.get(stage, set())
        return tuple(item for item in approvals if item in applicable)

    def plan(self, request: str) -> ExecutionPlan:
        normalized_request = _require_string(request, "request")
        selected = self.select_roles(normalized_request)
        approvals = self.required_approvals(normalized_request)

        steps: list[ExecutionStep] = []
        for stage in self.config["workflow"]:
            owner_id = stage["owner"]
            if owner_id not in selected:
                continue
            role = self.roles[owner_id]
            reasons = self._approval_for_stage(stage["stage"], approvals)
            steps.append(
                ExecutionStep(
                    sequence=len(steps) + 1,
                    stage=stage["stage"],
                    owner_id=owner_id,
                    owner_name=role.name,
                    objective=f"{role.mission} Required output: {stage['output']}.",
                    deliverables=role.deliverables,
                    approval_required=bool(reasons),
                    approval_reasons=reasons,
                )
            )

        digest_source = f"{self.config['version']}\n{normalized_request.strip()}"
        plan_id = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
        divisions = {self.roles[role_id].division for role_id in selected}
        assessment = (
            "Cross-functional engineering and go-to-market execution is required."
            if {"engineering", "marketing"}.issubset(divisions)
            else "Focused execution is required with command and measurement controls."
        )

        risks = (
            "Unverified marketing claims can create legal, reputational, and trust exposure.",
            "Automating external actions without approval can produce spam, platform violations, or production incidents.",
            "Weak acceptance criteria can make activity look productive while producing no business outcome.",
            "Dependencies and secrets must remain outside generated plans and committed artifacts.",
        )
        validation = (
            "Confirm every factual claim against repository evidence or an authoritative source.",
            "Run repository tests, security checks, and rollback validation before deployment.",
            "Require a named human approver for every flagged external side effect.",
            "Measure qualified demand, conversion, revenue, reliability, and risk reduction—not vanity activity.",
        )
        next_action = (
            "Execute step 1, record constraints and acceptance criteria, then advance only when its output is complete."
        )
        return ExecutionPlan(
            plan_id=plan_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            system=self.config["system"],
            request=normalized_request,
            assessment=assessment,
            selected_agents=selected,
            approvals_required=approvals,
            steps=tuple(steps),
            risks=risks,
            validation=validation,
            next_action=next_action,
        )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="Objective to route through the agent army")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.json")),
        help="Path to agent-army JSON configuration",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--output",
        help="Optional output file. When omitted, the plan is printed to standard output.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        army = AgentArmy.from_file(args.config)
        plan = army.plan(args.request)
        rendered = plan.to_json() if args.format == "json" else plan.to_markdown()
        if args.output:
            _atomic_write(Path(args.output), rendered)
        else:
            sys.stdout.write(rendered)
        return 0
    except (ConfigurationError, OSError) as exc:
        print(f"agent-army error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
