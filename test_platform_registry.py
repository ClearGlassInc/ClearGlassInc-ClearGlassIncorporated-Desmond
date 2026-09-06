# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import copy

import pytest

from tools.validate_platform_registry import (
    EXPECTED_DOMAINS,
    REGISTRY_PATH,
    load_registry,
    main,
    validate,
)


@pytest.fixture(scope="module")
def registry() -> dict:
    return load_registry()


# ── committed registry is valid ──────────────────────────────────────────────

def test_registry_file_exists():
    assert REGISTRY_PATH.is_file()


def test_committed_registry_has_no_violations(registry):
    assert validate(registry) == []


def test_cli_exits_zero_on_committed_registry(capsys):
    assert main([]) == 0
    assert "registry OK" in capsys.readouterr().out


def test_expected_shape(registry):
    assert registry["hierarchy"]["root"] == "ClearGlass Nexus"
    assert len(registry["executive_layer"]) == 5
    assert len(registry["hierarchy"]["nodes"]) == 15
    assert len(registry["products"]) == 12
    for domain in EXPECTED_DOMAINS:
        expected = 5 if domain == "executive_ai" else 10
        assert len(registry["agent_framework"][domain]) == expected


def test_every_product_has_a_hierarchy_node(registry):
    nodes = {n["name"] for n in registry["hierarchy"]["nodes"]}
    for product in registry["products"]:
        assert product["anchor"] in nodes


# ── validator fails closed on violations ─────────────────────────────────────

def test_rejects_missing_top_level_key(registry):
    broken = copy.deepcopy(registry)
    del broken["products"]
    assert any("missing top-level key" in e for e in validate(broken))


def test_rejects_agent_id_off_standard(registry):
    broken = copy.deepcopy(registry)
    broken["hierarchy"]["nodes"][0]["agent_id"] = "sentinel_1"
    assert any("violates the agent tier pattern" in e for e in validate(broken))


def test_rejects_product_without_nexus_node(registry):
    broken = copy.deepcopy(registry)
    broken["products"].append(
        {"name": "ClearGlass Phantom", "domain": "Testing", "anchor": "Phantom"}
    )
    assert any("has no hierarchy node" in e for e in validate(broken))


def test_rejects_duplicate_codename_within_domain(registry):
    broken = copy.deepcopy(registry)
    broken["agent_framework"]["intelligence"].append("Oracle")
    assert any("duplicate names within domain" in e for e in validate(broken))


def test_rejects_hierarchy_node_that_resolves_nowhere(registry):
    broken = copy.deepcopy(registry)
    broken["hierarchy"]["nodes"].append(
        {"name": "Wraith", "role": "Testing", "agent_id": "CGA-Wraith-01"}
    )
    assert any("does not resolve" in e for e in validate(broken))


def test_rejects_example_that_breaks_its_own_pattern(registry):
    broken = copy.deepcopy(registry)
    broken["naming_standard"]["tiers"][1]["example"] = "Cortex-One"
    assert any("does not match its own pattern" in e for e in validate(broken))
