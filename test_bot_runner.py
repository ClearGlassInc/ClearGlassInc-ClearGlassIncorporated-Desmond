# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for scripts/bot_runner.py."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bot_runner import BOT_REGISTRY, build_matrix, run_bot  # noqa: E402


class TestBotRegistry:
    def test_all_bots_have_required_fields(self) -> None:
        for bot_id, meta in BOT_REGISTRY.items():
            assert "module" in meta, f"{bot_id}: missing 'module'"
            assert "group" in meta, f"{bot_id}: missing 'group'"
            assert "schedule" in meta, f"{bot_id}: missing 'schedule'"

    def test_all_schedules_are_valid(self) -> None:
        valid = {"daily", "weekly"}
        for bot_id, meta in BOT_REGISTRY.items():
            assert meta["schedule"] in valid, f"{bot_id}: invalid schedule '{meta['schedule']}'"

    def test_master_orchestrator_registered(self) -> None:
        assert "master_orchestrator" in BOT_REGISTRY

    def test_new_bots_registered(self) -> None:
        for bot_id in ("site_health", "seo_optimizer", "release_notes", "alert_dispatcher"):
            assert bot_id in BOT_REGISTRY, f"'{bot_id}' missing from registry"


class TestBuildMatrix:
    def test_matrix_has_include_key(self) -> None:
        matrix = build_matrix()
        assert "include" in matrix
        assert isinstance(matrix["include"], list)

    def test_master_orchestrator_excluded_from_matrix(self) -> None:
        matrix = build_matrix()
        ids = [item["bot"] for item in matrix["include"]]
        assert "master_orchestrator" not in ids

    def test_daily_schedule_filter(self) -> None:
        matrix = build_matrix(schedule="daily")
        for item in matrix["include"]:
            assert BOT_REGISTRY[item["bot"]]["schedule"] == "daily"

    def test_weekly_schedule_filter(self) -> None:
        matrix = build_matrix(schedule="weekly")
        for item in matrix["include"]:
            assert BOT_REGISTRY[item["bot"]]["schedule"] == "weekly"

    def test_matrix_items_have_bot_key(self) -> None:
        matrix = build_matrix()
        for item in matrix["include"]:
            assert "bot" in item


class TestRunBot:
    def test_unknown_bot_returns_error(self) -> None:
        result = run_bot("this_bot_does_not_exist_xyz")
        assert result["status"] == "error"
        assert "Unknown bot" in (result["error"] or "")

    def test_result_has_required_keys(self) -> None:
        result = run_bot("nonexistent_abc")
        for key in ("bot", "status", "duration_s", "error", "started_utc"):
            assert key in result, f"Missing key: {key}"

    def test_duration_is_numeric(self) -> None:
        result = run_bot("nonexistent_abc")
        assert isinstance(result["duration_s"], (int, float))

    def test_bot_field_matches_input(self) -> None:
        result = run_bot("nonexistent_abc")
        assert result["bot"] == "nonexistent_abc"
