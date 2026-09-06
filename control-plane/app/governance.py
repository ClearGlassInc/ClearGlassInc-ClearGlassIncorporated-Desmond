"""Governance core — risk scoring and approval gating.

This module is intentionally dependency-free (stdlib only) so it can be unit-tested
and reused by automation jobs without a database or web framework. It is the single
place that decides whether an action may auto-execute or must be escalated to a human.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskTier(str, Enum):
    """Coarse risk classification that maps to an execution policy."""

    LOW = "low"        # auto-execute + log
    MEDIUM = "medium"  # queue for review
    HIGH = "high"      # approval required
    CRITICAL = "critical"  # approval required, highest scrutiny


# Action types the operator can propose, mapped to a base risk score (0-100).
# Anything touching money, payment config, fulfillment, or mass outbound is gated.
ACTION_RISK: dict[str, int] = {
    # low — analysis / drafting, fully reversible
    "generate_copy": 5,
    "read_metrics": 0,
    "reconcile_orders": 10,
    "inventory_check": 10,
    "draft_message": 15,
    "draft_campaign": 20,
    # low — Etsy connection introspection is read-only (detect creds / read shop identity)
    "etsy_connection_check": 0,
    "etsy_verify_connection": 5,
    # low — Printful reads: credential detection, store identity, catalogue and
    # order/tracking lookups. None of these change anything at the supplier.
    "printful_connection_check": 0,
    "printful_verify_connection": 5,
    "printful_catalog_snapshot": 10,
    "printful_order_status": 10,
    "printful_shipping_estimate": 15,
    # medium — content/catalog changes that are reversible but customer-visible
    "refresh_products": 35,
    "publish_content": 45,
    "update_catalog": 40,
    # medium — importing the supplier catalogue writes our own database only.
    "printful_import_catalog": 40,
    # medium — a Printful DRAFT order costs nothing, prints nothing, and can be
    # deleted. It auto-executes on purpose: it is booked when a customer has
    # already paid, and gating it would strand a paid order behind a queue while
    # the reversible half of the work waits on a human. Confirmation, which is
    # what actually spends money, stays escalated below.
    "printful_draft_order": 45,
    # high — financial / fulfillment / outbound, hard to reverse
    "update_pricing": 80,
    "inventory_reorder": 75,
    "send_outbound": 78,
    "launch_campaign": 70,
    # high — writes to a live external marketplace (customer-visible listings, prices, orders)
    "etsy_publish_listing": 82,
    "etsy_update_listing": 80,
    "etsy_sync_inventory": 72,
    "etsy_manage_order": 80,
    # high — confirming a Printful order debits the wallet and starts production;
    # cancelling one abandons a parcel a customer is waiting for.
    "printful_confirm_order": 88,
    "printful_cancel_order": 85,
    # critical — irreversible or platform-level exposure
    "update_payment_settings": 100,
    "update_tax_settings": 95,
    "trigger_refund": 95,
    "update_fulfillment_rules": 90,
}

# Always-escalate triggers (from the operator's escalation rules), independent of score.
ALWAYS_ESCALATE = {
    "update_pricing",
    "update_payment_settings",
    "update_tax_settings",
    "trigger_refund",
    "update_fulfillment_rules",
    "inventory_reorder",
    # Every write to the live Etsy shop is human-gated: listings, prices, inventory, orders.
    "etsy_publish_listing",
    "etsy_update_listing",
    "etsy_sync_inventory",
    "etsy_manage_order",
    # Printful order confirmation spends real money and starts an irreversible
    # print run; cancellation strands a paid customer. Both need a human, even
    # when `printful_auto_confirm` is set — that flag records intent, it does not
    # open the gate.
    "printful_confirm_order",
    "printful_cancel_order",
}


@dataclass
class RiskAssessment:
    """Result of scoring a proposed action."""

    action: str
    score: int
    tier: RiskTier
    requires_approval: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "score": self.score,
            "tier": self.tier.value,
            "requires_approval": self.requires_approval,
            "reasons": self.reasons,
        }


def _tier_for_score(score: int) -> RiskTier:
    if score >= 90:
        return RiskTier.CRITICAL
    if score >= 60:
        return RiskTier.HIGH
    if score >= 30:
        return RiskTier.MEDIUM
    return RiskTier.LOW


def score_action(
    action: str,
    payload: dict[str, object] | None = None,
    *,
    require_approval_for_high_risk: bool = True,
    low_confidence: bool = False,
) -> RiskAssessment:
    """Score an action 0-100 and decide whether it needs human approval.

    Unknown actions default to HIGH and are gated — fail closed, never fail open.
    """
    payload = payload or {}
    reasons: list[str] = []

    base = ACTION_RISK.get(action)
    if base is None:
        reasons.append(f"unknown action '{action}' — defaulting to high risk (fail closed)")
        base = 85

    score = base

    # Payload signals that raise risk.
    if _money_delta(payload) >= 0.20:
        score = min(100, score + 10)
        reasons.append("price/amount change exceeds 20%")
    if payload.get("audience") == "all" or payload.get("bulk") is True:
        score = min(100, score + 8)
        reasons.append("affects all customers / bulk operation")
    if low_confidence:
        score = min(100, score + 12)
        reasons.append("low confidence / missing data — escalate per operating rule 8")

    tier = _tier_for_score(score)

    # Operating rule 8: stop and escalate when data is missing or confidence is
    # low. A low-confidence signal must hard-gate on its own — a score bump alone
    # can leave a low/medium-base action below the HIGH threshold and let it
    # auto-execute, which would contradict the escalation the reason claims.
    requires_approval = (
        tier in (RiskTier.HIGH, RiskTier.CRITICAL)
        or action in ALWAYS_ESCALATE
        or low_confidence
    )
    if action in ALWAYS_ESCALATE:
        reasons.append("action is in the always-escalate set (financial / fulfillment / outbound)")
    if requires_approval and require_approval_for_high_risk:
        reasons.append("hard gate enabled — cannot auto-execute")
    elif requires_approval:
        reasons.append("approval required by policy")
    else:
        reasons.append("auto-executable: reversible, low risk")

    return RiskAssessment(
        action=action,
        score=score,
        tier=tier,
        requires_approval=requires_approval,
        reasons=reasons,
    )


def _money_delta(payload: dict[str, object]) -> float:
    """Relative magnitude of a price change, if both old and new prices are present."""
    old = payload.get("old_price")
    new = payload.get("new_price")
    try:
        old_f = float(old)  # type: ignore[arg-type]
        new_f = float(new)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if old_f <= 0:
        return 1.0
    return abs(new_f - old_f) / old_f
