# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for tools/catalog_contract.py — the governed-catalog contract.

The validator's whole value is that it reports the truth about the catalogs
without touching them. These tests pin that: it never mutates an entry, it
never invents a value, an alias only counts where the meaning is unambiguous,
and --strict stays opt-in so it cannot break the build before the owner has
supplied the missing fields.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from tools.catalog_contract import (
    CATALOGS,
    CONTRACT,
    PRODUCT_TYPES,
    audit_all,
    audit_entry,
)

REPO = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# the contract itself
# --------------------------------------------------------------------------- #
def test_contract_field_names_are_unique():
    names = [f.name for f in CONTRACT]
    assert len(names) == len(set(names))


def test_every_contract_field_explains_why_it_is_required():
    """A field nobody can justify is a field nobody will fill in."""
    for f in CONTRACT:
        assert f.why.strip(), f"{f.name} has no rationale"
        assert f.why.strip().endswith("."), f"{f.name} rationale is not a sentence"


def test_the_money_fields_are_required():
    required = {f.name for f in CONTRACT if f.required}
    for essential in ("sku", "approved_price", "currency", "product_type", "active"):
        assert essential in required


def test_shipping_is_optional_because_digital_goods_do_not_ship():
    optional = {f.name for f in CONTRACT if not f.required}
    assert "shipping_policy" in optional
    assert "delivery_entitlement" in optional


def test_product_types_are_the_four_the_policy_names():
    assert set(PRODUCT_TYPES) == {"digital", "physical", "subscription", "service"}


# --------------------------------------------------------------------------- #
# the audit never changes what it measures
# --------------------------------------------------------------------------- #
def test_audit_entry_does_not_mutate_the_entry():
    entry = {"sku": "x", "name": "X", "amount": 100, "currency": "cad"}
    before = copy.deepcopy(entry)
    audit_entry(entry)
    assert entry == before


def test_audit_entry_invents_nothing():
    """A missing field comes back named, never filled."""
    rep = audit_entry({"sku": "x"})
    assert "refund_policy_ref" in rep.missing_required
    assert "product_type" in rep.missing_required


def test_alias_satisfies_a_field_without_rewriting_the_catalog():
    rep = audit_entry({"sku": "x", "amount_cents": 24900})
    assert rep.satisfied_by_alias.get("approved_price") == "amount_cents"
    assert "approved_price" not in rep.missing_required


def test_a_complete_entry_is_reported_complete():
    entry = {f.name: "set" for f in CONTRACT if f.required}
    rep = audit_entry(entry)
    assert rep.complete
    assert rep.missing_required == []


def test_sku_falls_back_to_id_but_is_never_blank():
    assert audit_entry({"id": "cg-1"}).sku == "cg-1"
    assert audit_entry({}).sku == "<no sku>"


# --------------------------------------------------------------------------- #
# the catalogs it points at must stay real
# --------------------------------------------------------------------------- #
def test_every_declared_catalog_exists_and_parses():
    """If a catalog moves, this fails here rather than silently auditing nothing."""
    for rel, key in CATALOGS:
        path = REPO / rel
        assert path.exists(), f"declared catalog missing: {rel}"
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(doc, (dict, list)), rel
        if isinstance(doc, dict):
            assert key in doc, f"{rel} has no '{key}' collection"


def test_audit_all_reports_every_catalog_without_error():
    results = audit_all()
    assert len(results) == len(CATALOGS)
    for rel, reports, err in results:
        assert err is None, f"{rel}: {err}"
        assert reports, f"{rel} audited zero entries"


# --------------------------------------------------------------------------- #
# --strict must stay opt-in
# --------------------------------------------------------------------------- #
def test_default_run_exits_zero_even_though_skus_are_incomplete():
    """Reporting a gap is not the same as failing a build. Today it must not."""
    proc = subprocess.run(
        [sys.executable, "tools/catalog_contract.py"],
        cwd=REPO, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "not contract-complete" in proc.stdout


def test_strict_exits_nonzero_while_any_sku_is_incomplete():
    proc = subprocess.run(
        [sys.executable, "tools/catalog_contract.py", "--strict"],
        cwd=REPO, capture_output=True, text=True, timeout=120,
    )
    incomplete = sum(1 for _, reps, _ in audit_all() for r in reps if not r.complete)
    assert proc.returncode == (1 if incomplete else 0)


def test_json_output_is_parseable():
    proc = subprocess.run(
        [sys.executable, "tools/catalog_contract.py", "--json"],
        cwd=REPO, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0
    doc = json.loads(proc.stdout)
    assert {c["path"] for c in doc["catalogs"]} == {rel for rel, _ in CATALOGS}


def test_strict_is_not_wired_into_the_blocking_gate_yet():
    """Turning it on before the fields exist would only break the build."""
    ci = (REPO / "scripts" / "ci_local.py").read_text(encoding="utf-8")
    assert "catalog_contract.py --strict" not in ci
