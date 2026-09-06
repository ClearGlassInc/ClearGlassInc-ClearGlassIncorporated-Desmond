#!/usr/bin/env python3
"""Validate ClearGlass edge policy safety invariants without third-party packages."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "policies" / "baseline.json"
DEFAULT_SCHEMA = ROOT / "policy.schema.json"

ALLOWED_ACTIONS = {
    "allow", "log", "managed_challenge", "interactive_challenge",
    "rate_limit", "block", "set_header", "remove_header", "cache", "route",
}
ALLOWED_ROLLOUT = {"observe", "challenge", "enforce", "disabled"}
ALLOWED_LOG_LEVELS = {"none", "metadata", "security_event"}
ALLOWED_CATEGORIES = {
    "ddos", "managed_waf", "custom_waf", "bot", "ip_reputation",
    "rate_limit", "geo_asn", "headers", "origin", "logging", "emergency",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    return data


def parse_expiry(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("expiry must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top = {"version", "environment", "defaults", "rules"}
    missing = required_top - policy.keys()
    if missing:
        errors.append(f"missing top-level keys: {sorted(missing)}")
        return errors

    defaults = policy.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("defaults must be an object")
        defaults = {}

    if defaults.get("geo_enforcement_enabled") is not False:
        errors.append("safe default violated: geo_enforcement_enabled must be false")
    if defaults.get("csp_mode") != "report-only":
        errors.append("safe default violated: baseline CSP must start report-only")
    if defaults.get("log_sensitive_fields") is not False:
        errors.append("privacy invariant violated: log_sensitive_fields must be false")

    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    seen_priorities: set[int] = set()
    now = datetime.now(timezone.utc)

    for index, rule in enumerate(rules):
        where = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{where}: must be an object")
            continue

        required = {
            "id", "description", "category", "scope", "priority", "action",
            "rollout_mode", "log_level", "enabled", "exceptions", "owner", "rationale",
        }
        missing_rule = required - rule.keys()
        if missing_rule:
            errors.append(f"{where}: missing keys {sorted(missing_rule)}")
            continue

        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or len(rule_id) < 3:
            errors.append(f"{where}: invalid id")
        elif rule_id in seen_ids:
            errors.append(f"{where}: duplicate id {rule_id}")
        else:
            seen_ids.add(rule_id)

        priority = rule.get("priority")
        if not isinstance(priority, int) or not 1 <= priority <= 100000:
            errors.append(f"{where}: priority must be integer 1..100000")
        elif priority in seen_priorities:
            errors.append(f"{where}: duplicate priority {priority}")
        else:
            seen_priorities.add(priority)

        action = rule.get("action")
        rollout = rule.get("rollout_mode")
        category = rule.get("category")
        log_level = rule.get("log_level")

        if action not in ALLOWED_ACTIONS:
            errors.append(f"{where}: unsupported action {action!r}")
        if rollout not in ALLOWED_ROLLOUT:
            errors.append(f"{where}: unsupported rollout_mode {rollout!r}")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{where}: unsupported category {category!r}")
        if log_level not in ALLOWED_LOG_LEVELS:
            errors.append(f"{where}: unsupported log_level {log_level!r}")

        enabled = rule.get("enabled")
        if not isinstance(enabled, bool):
            errors.append(f"{where}: enabled must be boolean")

        exceptions = rule.get("exceptions")
        if not isinstance(exceptions, list) or not all(isinstance(x, str) for x in exceptions):
            errors.append(f"{where}: exceptions must be an array of strings")

        # Dangerous broad terminal policies require explicit rationale/exception handling.
        if enabled and rule.get("scope") == "all" and action in {"allow", "block"}:
            errors.append(f"{where}: broad enabled {action} over scope=all is prohibited")

        # Geo/ASN is disabled in the baseline unless the operator explicitly changes it.
        if category == "geo_asn" and enabled:
            errors.append(f"{where}: geo/ASN rule must be disabled in baseline policy")

        # Permanent reputation-only blocks are prohibited.
        if category == "ip_reputation" and action == "block" and not rule.get("expires_at"):
            errors.append(f"{where}: reputation-only block requires expiry and review")

        # Emergency controls must be temporary.
        if category == "emergency" and enabled:
            expiry = rule.get("expires_at")
            if not expiry:
                errors.append(f"{where}: enabled emergency rule requires expires_at")
            else:
                try:
                    if parse_expiry(str(expiry)) <= now:
                        errors.append(f"{where}: emergency rule is already expired")
                except ValueError as exc:
                    errors.append(f"{where}: invalid expires_at: {exc}")

        threshold = rule.get("threshold")
        if category == "rate_limit":
            if not isinstance(threshold, dict):
                errors.append(f"{where}: rate_limit requires threshold object")
            else:
                requests = threshold.get("requests")
                period = threshold.get("period_seconds")
                if not isinstance(requests, int) or requests <= 0:
                    errors.append(f"{where}: threshold.requests must be a positive integer")
                if not isinstance(period, int) or period <= 0:
                    errors.append(f"{where}: threshold.period_seconds must be a positive integer")

        if action == "block" and rollout == "observe":
            errors.append(f"{where}: block action cannot be in observe rollout")

        if not str(rule.get("owner", "")).strip():
            errors.append(f"{where}: owner is required")
        if len(str(rule.get("rationale", "")).strip()) < 5:
            errors.append(f"{where}: rationale is too short")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()

    try:
        policy = load_json(args.policy)
        schema = load_json(args.schema)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # Ensure the committed schema itself is parseable and clearly identifies the expected draft.
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        print("ERROR: policy schema must use JSON Schema draft 2020-12", file=sys.stderr)
        return 2

    errors = validate(policy)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Policy validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Policy OK: {args.policy} ({len(policy['rules'])} rules, version {policy['version']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
