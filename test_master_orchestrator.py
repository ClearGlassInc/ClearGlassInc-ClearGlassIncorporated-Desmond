# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/master_orchestrator.py."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.master_orchestrator import DEPENDENCY_GRAPH, _topo_sort  # noqa: E402


class TestTopoSort:
    def test_simple_chain(self) -> None:
        graph = {"a": [], "b": ["a"], "c": ["b"]}
        waves = _topo_sort(graph)
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert waves[1] == ["b"]
        assert waves[2] == ["c"]

    def test_parallel_roots(self) -> None:
        graph = {"a": [], "b": [], "c": ["a", "b"]}
        waves = _topo_sort(graph)
        # a and b should be in the first wave
        assert set(waves[0]) == {"a", "b"}
        assert waves[-1] == ["c"]

    def test_single_node(self) -> None:
        waves = _topo_sort({"x": []})
        assert waves == [["x"]]

    def test_all_roots(self) -> None:
        graph = {"a": [], "b": [], "c": []}
        waves = _topo_sort(graph)
        assert len(waves) == 1
        assert set(waves[0]) == {"a", "b", "c"}

    def test_all_nodes_included(self) -> None:
        waves = _topo_sort(DEPENDENCY_GRAPH)
        all_bots = {b for wave in waves for b in wave}
        assert all_bots == set(DEPENDENCY_GRAPH.keys())

    def test_dependency_order_respected(self) -> None:
        waves = _topo_sort(DEPENDENCY_GRAPH)
        completed: set[str] = set()
        for wave in waves:
            for bot in wave:
                deps = DEPENDENCY_GRAPH.get(bot, [])
                for dep in deps:
                    if dep in DEPENDENCY_GRAPH:
                        assert dep in completed, (
                            f"'{bot}' depends on '{dep}' but '{dep}' hasn't run yet"
                        )
            completed.update(wave)

    def test_alert_dispatcher_after_dependencies(self) -> None:
        waves = _topo_sort(DEPENDENCY_GRAPH)
        wave_map = {bot: i for i, wave in enumerate(waves) for bot in wave}
        alert_wave = wave_map.get("alert_dispatcher", -1)
        for dep in DEPENDENCY_GRAPH.get("alert_dispatcher", []):
            if dep in wave_map:
                assert wave_map[dep] < alert_wave, (
                    f"'{dep}' must run before 'alert_dispatcher'"
                )


class TestDependencyGraph:
    def test_all_dependencies_exist(self) -> None:
        for bot, deps in DEPENDENCY_GRAPH.items():
            for dep in deps:
                assert dep in DEPENDENCY_GRAPH, (
                    f"'{bot}' depends on '{dep}' which is not in DEPENDENCY_GRAPH"
                )

    def test_no_self_dependency(self) -> None:
        for bot, deps in DEPENDENCY_GRAPH.items():
            assert bot not in deps, f"'{bot}' depends on itself"

    def test_all_new_bots_present(self) -> None:
        expected = {"site_health", "seo_optimizer", "release_notes", "alert_dispatcher"}
        for bot in expected:
            assert bot in DEPENDENCY_GRAPH, f"'{bot}' missing from DEPENDENCY_GRAPH"
