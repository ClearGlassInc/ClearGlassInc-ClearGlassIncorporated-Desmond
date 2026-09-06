#!/usr/bin/env python3
"""Validate Burlington exposure contracts and render evidence-safe summaries.

This stdlib-only tool never calls external services or publishes content. It
fails closed when contracts are malformed and treats unavailable values as
``None`` rather than as observed zeros.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = (
    "MISSION_OBJECTIVES.json",
    "baseline_metrics.json",
    "competitor_intel.json",
    "local_opportunity_map.json",
    "geo_grid_baseline.json",
    "priority_levers.json",
)


class ContractError(ValueError):
    """Raised when an exposure artifact violates a deterministic invariant."""


@dataclass(frozen=True)
class ValidationResult:
    path: str
    status: str
    findings: tuple[str, ...]


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object while rejecting duplicate keys."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def priority_score(lever: dict[str, Any]) -> float:
    """Reproduce the documented priority score with bounded 1–5 inputs."""

    names = ("expected_impact", "confidence", "urgency", "effort", "risk")
    values: dict[str, float] = {}
    for name in names:
        # Version 1 producers used ``impact``; retain read compatibility while
        # keeping ``expected_impact`` as the canonical scoring term.
        value = (
            lever.get("impact")
            if name == "expected_impact" and name not in lever
            else lever.get(name)
        )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContractError(f"{lever.get('id', '<unknown>')}.{name} must be numeric")
        values[name] = float(value)
        if not 1 <= values[name] <= 5:
            raise ContractError(f"{lever.get('id', '<unknown>')}.{name} must be in [1, 5]")
    return (
        values["expected_impact"]
        * values["confidence"]
        * values["urgency"]
        / (values["effort"] * values["risk"])
    )


def validate_priority(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    levers = data.get("levers")
    if not isinstance(levers, list) or not levers:
        return ["levers must be a non-empty array"]
    identifiers: set[str] = set()
    for lever in levers:
        if not isinstance(lever, dict):
            findings.append("lever must be an object")
            continue
        identifier = lever.get("id")
        if not isinstance(identifier, str) or not identifier:
            findings.append("lever id is required")
        elif identifier in identifiers:
            findings.append(f"duplicate lever id: {identifier}")
        else:
            identifiers.add(identifier)
        try:
            calculated = priority_score(lever)
        except ContractError as exc:
            findings.append(str(exc))
            continue
        recorded = lever.get("score")
        if isinstance(recorded, bool) or not isinstance(recorded, (int, float)):
            findings.append(f"{identifier}.score must be numeric")
        elif not math.isclose(calculated, float(recorded), rel_tol=0, abs_tol=0.0001):
            findings.append(f"{identifier}.score is {recorded}; expected {calculated:.4f}")
    return findings


def validate_baseline(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    quality = data.get("quality")
    if not isinstance(quality, dict):
        return ["quality must be an object"]
    # Both representations are lossless: newer collectors expose a ratio and
    # blocking gaps, while the original contract exposed a boolean and sources.
    complete = quality.get("complete", quality.get("completeness_ratio") == 1.0)
    missing = quality.get("missing_required_sources", quality.get("blocking_gaps", []))
    if not isinstance(complete, bool):
        findings.append("quality.complete must be boolean")
    if not isinstance(missing, list) or any(not isinstance(item, str) for item in missing):
        findings.append("quality.missing_required_sources must be an array of strings")
    elif complete and missing:
        findings.append("complete baseline cannot list missing required sources")
    return findings


def validate_grid(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    cells = data.get("cells")
    summary = data.get("summary")
    threshold = data.get("green_rank_threshold")
    if threshold is None and isinstance(data.get("rank_semantics"), dict):
        threshold = data["rank_semantics"].get("green_max_position")
    if not isinstance(cells, list) or not isinstance(summary, dict):
        return ["cells must be an array and summary must be an object"]
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        findings.append("green_rank_threshold must be a positive integer")
        return findings
    successful = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("status") == "success"
    ]
    green = [
        cell
        for cell in successful
        if isinstance(cell.get("position"), int) and 1 <= cell["position"] <= threshold
    ]
    failed = [cell for cell in cells if isinstance(cell, dict) and cell.get("status") == "failed"]
    expected = {
        "successful_cells": len(successful),
        "failed_cells": len(failed),
        "green_cells": len(green),
    }
    if data.get("status") == "not_collected" and not cells:
        # Null summary values truthfully mean unavailable, not observed zero.
        return findings
    for key, value in expected.items():
        if summary.get(key) != value:
            findings.append(f"summary.{key} is {summary.get(key)!r}; expected {value}")
    expected_rate = round(100 * len(green) / len(successful), 4) if successful else None
    if summary.get("green_cell_rate") != expected_rate:
        findings.append(
            f"summary.green_cell_rate is {summary.get('green_cell_rate')!r}; expected {expected_rate!r}"
        )
    return findings


def validate_contract(path: Path) -> ValidationResult:
    try:
        data = load_json(path)
    except ContractError as exc:
        return ValidationResult(path.name, "fail", (str(exc),))
    findings: list[str] = []
    if not isinstance(data.get("schema_version", data.get("version")), str):
        findings.append("schema_version or version string is required")
    if path.name == "priority_levers.json":
        findings.extend(validate_priority(data))
    elif path.name == "baseline_metrics.json":
        findings.extend(validate_baseline(data))
    elif path.name == "geo_grid_baseline.json":
        findings.extend(validate_grid(data))
    return ValidationResult(path.name, "fail" if findings else "pass", tuple(findings))


def validate_all(root: Path = ROOT) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for name in CONTRACTS:
        path = root / name
        if not path.is_file():
            results.append(ValidationResult(name, "fail", ("required contract is missing",)))
        else:
            results.append(validate_contract(path))
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",), help="operation to perform")
    parser.add_argument("--root", type=Path, default=ROOT, help="directory containing contracts")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = validate_all(args.root)
    if args.json:
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        for result in results:
            print(f"{result.status.upper():4} {result.path}")
            for finding in result.findings:
                print(f"     - {finding}")
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
