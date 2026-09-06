from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.burlington_exposure import (
    ContractError,
    load_json,
    priority_score,
    validate_all,
    validate_baseline,
    validate_grid,
    validate_priority,
)


def test_repository_contracts_validate() -> None:
    results = validate_all()
    assert results
    assert all(result.status == "pass" for result in results), results


def test_priority_formula_rejects_out_of_range_values() -> None:
    with pytest.raises(ContractError, match="must be in"):
        priority_score(
            {
                "id": "unsafe",
                "expected_impact": 6,
                "confidence": 1,
                "urgency": 1,
                "effort": 1,
                "risk": 1,
            }
        )


def test_priority_validation_detects_stale_recorded_score() -> None:
    findings = validate_priority(
        {
            "levers": [
                {
                    "id": "baseline",
                    "expected_impact": 5,
                    "confidence": 5,
                    "urgency": 5,
                    "effort": 2,
                    "risk": 1,
                    "score": 1,
                }
            ]
        }
    )
    assert any("expected 62.5000" in finding for finding in findings)


def test_complete_baseline_cannot_report_missing_sources() -> None:
    findings = validate_baseline(
        {"quality": {"complete": True, "missing_required_sources": ["ga4"]}}
    )
    assert findings == ["complete baseline cannot list missing required sources"]


def test_current_baseline_schema_preserves_unavailable_data() -> None:
    findings = validate_baseline(
        {"quality": {"completeness_ratio": 0.0, "blocking_gaps": ["connector unavailable"]}}
    )
    assert findings == []


def test_priority_accepts_version_one_impact_alias() -> None:
    assert (
        priority_score(
            {
                "id": "compatible",
                "impact": 5,
                "confidence": 5,
                "urgency": 5,
                "effort": 2,
                "risk": 1,
            }
        )
        == 62.5
    )


def test_grid_uses_only_successful_cells_as_rate_denominator() -> None:
    data = {
        "green_rank_threshold": 3,
        "cells": [
            {"status": "success", "position": 2},
            {"status": "success", "position": 8},
            {"status": "failed", "position": None},
        ],
        "summary": {
            "successful_cells": 2,
            "failed_cells": 1,
            "green_cells": 1,
            "green_cell_rate": 50.0,
        },
    }
    assert validate_grid(data) == []


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"status": "draft", "status": "approved"}', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate key"):
        load_json(path)


def test_contract_json_round_trips_without_nan() -> None:
    for result in validate_all():
        data = json.loads((Path(__file__).parents[1] / result.path).read_text(encoding="utf-8"))
        json.dumps(data, allow_nan=False)
