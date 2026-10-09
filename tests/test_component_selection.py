"""Regression tests for fail-closed application component selection."""
from __future__ import annotations

from scripts.ci.components import COMPONENTS, select


def test_root_next_app_manifests_select_root_app() -> None:
    assert select(["package.json"]) == ["root-app"]
    assert select(["app/page.tsx"]) == ["root-app"]
    assert select(["tests/example.test.ts"]) == ["root-app"]


def test_known_component_changes_select_only_that_component() -> None:
    assert select(["storefront/app/page.tsx"]) == ["storefront"]
    assert select(["admin/package.json"]) == ["admin"]
    assert select(["control-plane/main.py"]) == ["control-plane"]


def test_unmapped_application_paths_fail_closed_to_all_components() -> None:
    assert select(["apps/osint-fraud-dashboard/src/main.ts"]) == list(COMPONENTS)


def test_unmapped_root_files_fail_closed_to_all_components() -> None:
    assert select(["new-root-tool.py"]) == list(COMPONENTS)


def test_shared_ci_plumbing_selects_every_component() -> None:
    assert select(["scripts/ci/components.py"]) == list(COMPONENTS)


def test_no_changes_selects_no_components_and_unknown_diff_selects_all() -> None:
    assert select([]) == []
    assert select(None) == list(COMPONENTS)


def test_root_app_is_validated_but_not_a_deployable_preview() -> None:
    assert COMPONENTS["root-app"]["path"] == "."
    assert "deploy" not in COMPONENTS["root-app"]
