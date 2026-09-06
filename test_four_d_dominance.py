"""Tests for the 4-D Dominance system (four_d_dominance package)."""
from __future__ import annotations

from four_d_dominance import (
    Memory,
    ModelRouter,
    ModelTier,
    Orchestrator,
    RiskLevel,
    score_action,
)
from four_d_dominance.pipeline import DOMAIN_ORDER, load_config, run


# --- governance gate ---------------------------------------------------------


def test_low_risk_analysis_auto_executes():
    decision = score_action("Draft an internal-linking authority improvement report")
    assert decision.level is RiskLevel.LOW
    assert decision.auto_execute is True
    assert decision.requires_approval is False


def test_publish_is_gated_for_approval():
    decision = score_action("Publish the new blog post to the live site")
    assert decision.requires_approval is True
    assert decision.auto_execute is False


def test_money_movement_is_critical_and_blocked():
    decision = score_action("Issue a refund and adjust payment settings")
    assert decision.level is RiskLevel.CRITICAL
    assert decision.auto_execute is False
    assert decision.score >= 90


# --- model router ------------------------------------------------------------


def test_mock_backend_is_deterministic():
    router = ModelRouter()
    first = router.complete(ModelTier.PRO, "hello")
    second = router.complete(ModelTier.PRO, "hello")
    assert first.text == second.text
    assert router.total_tokens > 0


def test_custom_backend_is_used():
    router = ModelRouter(backend=lambda tier, prompt: f"{tier.value}!")
    assert router.complete(ModelTier.FLASH, "x").text == "flash!"


# --- memory ------------------------------------------------------------------


def test_memory_roundtrip(tmp_path):
    mem = Memory()
    mem.remember({"action": "classify"})
    mem.learn("last_score", 88)
    path = tmp_path / "mem.json"
    mem.save(path)
    restored = Memory.load(path)
    assert restored.recall("last_score") == 88
    assert restored.short_term == [{"action": "classify"}]


def test_short_term_buffer_is_bounded():
    mem = Memory(max_short_term=3)
    for i in range(10):
        mem.remember({"i": i})
    assert len(mem.short_term) == 3
    assert mem.short_term[-1] == {"i": 9}


# --- orchestrator ------------------------------------------------------------


def test_orchestrator_runs_full_loop_and_logs():
    orch = Orchestrator()
    outcome = orch.run_task("Draft a thought-leadership article outline")
    assert outcome.plan_steps == 3
    assert 60 <= outcome.critic_score <= 99
    assert outcome.auto_executed is True
    # audit trail records the classify step plus one entry per plan step.
    assert len(outcome.audit) == outcome.plan_steps + 1
    assert outcome.audit[0]["action"] == "classify"


def test_orchestrator_holds_risky_task_for_approval():
    orch = Orchestrator()
    outcome = orch.run_task("Deploy to production and change price on all items")
    assert outcome.auto_executed is False
    assert outcome.governance.requires_approval is True


# --- pipeline ----------------------------------------------------------------


def test_config_has_all_four_domains():
    config = load_config()
    assert set(config["domains"]) == set(DOMAIN_ORDER)


def test_run_produces_report_for_all_domains():
    report = run(list(DOMAIN_ORDER))
    assert report["mode"] == "dry-run"
    assert report["totals"]["domains"] == 4
    assert report["totals"]["tasks"] == 8
    assert report["totals"]["model_tokens"] > 0
    for name in DOMAIN_ORDER:
        assert name in report["domains"]
        assert report["domains"][name]["tasks"]
