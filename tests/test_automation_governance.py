# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The policy that decides what the repository's own automation may merge.

These tests are adversarial on purpose. A policy module is the kind of code that
keeps passing its tests while quietly ceasing to refuse anything — a glob that
stops matching, a default that flips to the convenient value — so most of what is
asserted here is what must be *refused*, not what is allowed.
"""
from __future__ import annotations

import json

import pytest

from scripts.automation_governance import (
    HALT_ALL_SIGNALS,
    HALT_REVENUE_SIGNALS,
    MAX_AUTO_MERGES_PER_DAY,
    MAX_CONSECUTIVE_DEPLOY_FAILURES,
    MAX_OPEN_BOT_PRS,
    ChangeRisk,
    classify_change,
    evaluate_breakers,
    main,
    may_auto_merge,
    protected_reason,
    run_self_check,
)

HEALTHY = {
    **{signal: True for signal in HALT_ALL_SIGNALS},
    **{signal: True for signal in HALT_REVENUE_SIGNALS},
    "consecutive_deploy_failures": 0,
    "open_bot_prs": 0,
    "auto_merges_today": 0,
}


def test_the_policy_self_check_passes() -> None:
    ok, failures = run_self_check()
    assert ok, f"policy invariants violated: {failures}"


# ── What must never auto-merge ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        ".github/workflows/commerce-deploy.yml",
        ".github/dependabot.yml",
        "CODEOWNERS",
        "control-plane/app/payments.py",
        "control-plane/app/paypal.py",
        "control-plane/app/pricebook.py",
        "control-plane/app/order_ledger.py",
        "control-plane/app/security.py",
        "control-plane/app/governance.py",
        "control-plane/app/audit.py",
        "control-plane/app/routers/paypal.py",
        "control-plane/app/data/pricebook.json",
        "control-plane/migrations/004_webhook_idempotency.sql",
        "control-plane/requirements.txt",
        "storefront/package-lock.json",
        "storefront/package.json",
        "admin/pnpm-lock.yaml",
        "data/store/catalog.json",
        "data/side-store/catalog.json",
        "render.yaml",
        "docker-compose.yml",
        "CNAME",
        "_headers",
        ".env.example",
        "LICENSE",
        "SECURITY.md",
        "infra/main.tf",
    ],
)
def test_protected_paths_are_never_auto_mergeable(path: str) -> None:
    assessment = classify_change([path])
    assert assessment.risk is ChangeRisk.HIGH, f"{path} classified {assessment.risk}"
    assert assessment.may_auto_merge is False
    assert assessment.protected, f"{path} produced no protection reason"


def test_a_new_payment_module_is_protected_the_day_it_is_added() -> None:
    """The table cannot list files that do not exist yet; the name markers can."""
    for path in (
        "services/new_checkout_handler.py",
        "api/square_webhook.py",
        "lib/refund_processor.ts",
        "app/auth_middleware.py",
        "db/migration_0099.sql",
    ):
        assert protected_reason(path), f"{path} was not recognised as protected"


def test_documentation_about_payments_is_not_payment_code() -> None:
    """The marker check reads the filename, so docs are not swept up by topic."""
    assessment = classify_change(["docs/REVENUE_OPERATIONS.md"])
    assert assessment.may_auto_merge is True


def test_one_protected_file_poisons_an_otherwise_trivial_change() -> None:
    """A change merges as a unit, so it is only as safe as its riskiest file."""
    assessment = classify_change(
        ["docs/RUNBOOK.md", "README.md", "control-plane/app/payments.py"]
    )
    assert assessment.risk is ChangeRisk.HIGH
    assert assessment.may_auto_merge is False


def test_an_unrecognised_path_needs_a_human() -> None:
    assessment = classify_change(["some/brand/new/module.py"])
    assert assessment.risk is ChangeRisk.MEDIUM
    assert assessment.may_auto_merge is False


def test_an_empty_change_is_refused_rather_than_treated_as_harmless() -> None:
    for paths in ([], [""], ["   "]):
        assessment = classify_change(paths)
        assert assessment.may_auto_merge is False, f"{paths!r} was treated as safe"
        assert assessment.risk is ChangeRisk.MEDIUM


@pytest.mark.parametrize(
    "path",
    ["docs/RUNBOOK.md", "README.md", "tests/test_x.py", "control-plane/tests/test_y.py"],
)
def test_documentation_and_tests_are_auto_mergeable(path: str) -> None:
    assessment = classify_change([path])
    assert assessment.risk is ChangeRisk.LOW
    assert assessment.may_auto_merge is True


# ── Circuit breakers ───────────────────────────────────────────────────────


def test_a_healthy_repository_allows_automation() -> None:
    decision = evaluate_breakers(HEALTHY)
    assert decision.mutation_allowed is True
    assert decision.revenue_automation_allowed is True
    assert decision.auto_merge_allowed is True
    assert decision.blocked_by == []


def test_absent_health_signals_are_treated_as_failing() -> None:
    """The breaker's usual failure mode is its input quietly disappearing."""
    decision = evaluate_breakers({})
    assert decision.mutation_allowed is False
    assert decision.auto_merge_allowed is False
    assert decision.revenue_automation_allowed is False
    assert any("not reported" in reason for reason in decision.blocked_by)


@pytest.mark.parametrize("signal", sorted(HALT_ALL_SIGNALS))
def test_any_failing_safety_gate_halts_all_mutation(signal: str) -> None:
    decision = evaluate_breakers({**HEALTHY, signal: False})
    assert decision.mutation_allowed is False, f"{signal} failing did not halt mutation"
    assert decision.auto_merge_allowed is False


@pytest.mark.parametrize("signal", sorted(HALT_REVENUE_SIGNALS))
def test_a_failing_revenue_gate_halts_revenue_automation_only(signal: str) -> None:
    decision = evaluate_breakers({**HEALTHY, signal: False})
    assert decision.revenue_automation_allowed is False
    # The repository can still be maintained; only the money-side automation stops.
    assert decision.mutation_allowed is True


def test_two_consecutive_failed_deployments_stop_everything() -> None:
    decision = evaluate_breakers(
        {**HEALTHY, "consecutive_deploy_failures": MAX_CONSECUTIVE_DEPLOY_FAILURES}
    )
    assert decision.mutation_allowed is False
    assert any("roll back" in reason for reason in decision.blocked_by)


def test_one_failed_deployment_does_not_stop_everything() -> None:
    """The breaker fires on a pattern, not on a single bad run."""
    decision = evaluate_breakers({**HEALTHY, "consecutive_deploy_failures": 1})
    assert decision.mutation_allowed is True


def test_the_daily_auto_merge_budget_is_enforced() -> None:
    spent = evaluate_breakers({**HEALTHY, "auto_merges_today": MAX_AUTO_MERGES_PER_DAY})
    assert spent.auto_merge_allowed is False
    # Spending the budget stops merging, not every other kind of work.
    assert spent.mutation_allowed is True


def test_the_open_bot_pr_ceiling_is_enforced() -> None:
    decision = evaluate_breakers({**HEALTHY, "open_bot_prs": MAX_OPEN_BOT_PRS})
    assert decision.auto_merge_allowed is False


def test_a_truthy_string_is_not_a_passing_gate() -> None:
    """Shell-assembled state arrives as strings; "false" must not read as pass."""
    for value in ("false", "true", "", 1, 0, None):
        decision = evaluate_breakers({**HEALTHY, "secret_scan_passing": value})
        assert decision.mutation_allowed is False, f"{value!r} was accepted as a pass"


# ── The combined decision ──────────────────────────────────────────────────


def test_a_safe_change_is_still_refused_while_a_gate_is_red() -> None:
    allowed, reasons = may_auto_merge(
        ["docs/RUNBOOK.md"], {**HEALTHY, "secret_scan_passing": False}
    )
    assert allowed is False
    assert any("secret" in reason for reason in reasons)


def test_a_healthy_repository_does_not_license_a_payment_change() -> None:
    allowed, reasons = may_auto_merge(["control-plane/app/payments.py"], HEALTHY)
    assert allowed is False
    assert any("payment processing" in reason for reason in reasons)


def test_both_gates_green_permits_the_merge() -> None:
    allowed, reasons = may_auto_merge(["docs/RUNBOOK.md"], HEALTHY)
    assert allowed is True
    assert reasons == []


# ── CLI contract (workflows read the exit code) ────────────────────────────


def test_self_check_exits_zero(capsys) -> None:
    assert main(["--self-check"]) == 0


def test_classifying_a_protected_path_exits_non_zero(capsys) -> None:
    assert main(["--paths", "control-plane/app/payments.py"]) == 1


def test_missing_state_exits_non_zero(capsys) -> None:
    """No state file means no evidence of health, which is not permission."""
    assert main([]) == 1


def test_unreadable_state_exits_non_zero(tmp_path, capsys) -> None:
    broken = tmp_path / "state.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main(["--state", str(broken)]) == 2


def test_healthy_state_and_safe_paths_exit_zero(tmp_path, capsys) -> None:
    state = tmp_path / "state.json"
    state.write_text(json.dumps(HEALTHY), encoding="utf-8")
    assert main(["--paths", "docs/RUNBOOK.md", "--state", str(state), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["auto_merge_allowed"] is True
