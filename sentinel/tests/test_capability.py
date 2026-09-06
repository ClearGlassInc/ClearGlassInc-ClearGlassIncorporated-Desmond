# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for sentinel/sentinel/capability.py — deny-by-default object-capability
gating with approval tiers."""
from __future__ import annotations

import pytest

from sentinel.capability import CapabilityBroker, Grant, Tier, required_tier


# --------------------------------------------------------------------------- #
# tier ordering / required_tier
# --------------------------------------------------------------------------- #
def test_tiers_are_ordered():
    assert Tier.READ_ONLY < Tier.DRAFT < Tier.CHANGE < Tier.DEPLOY


@pytest.mark.parametrize(
    "kind,tier",
    [
        ("read", Tier.READ_ONLY),
        ("summarize", Tier.READ_ONLY),
        ("draft", Tier.DRAFT),
        ("catalog_edit", Tier.CHANGE),
        ("pricing_change", Tier.DEPLOY),
        ("payment", Tier.DEPLOY),
        ("credential_access", Tier.DEPLOY),
    ],
)
def test_required_tier_mapping(kind, tier):
    assert required_tier(kind) == tier


def test_unknown_action_fails_closed_to_deploy():
    assert required_tier("frobnicate") == Tier.DEPLOY


# --------------------------------------------------------------------------- #
# deny-by-default
# --------------------------------------------------------------------------- #
def test_no_grant_is_denied():
    broker = CapabilityBroker()
    d = broker.check("catalog", Tier.READ_ONLY)
    assert d.allowed is False
    assert "deny-by-default" in d.reason


def test_grant_allows_up_to_tier():
    broker = CapabilityBroker()
    g = broker.grant("catalog", Tier.CHANGE, reason="content ops")
    assert isinstance(g, Grant)
    assert broker.check("catalog", Tier.READ_ONLY).allowed is True
    assert broker.check("catalog", Tier.DRAFT).allowed is True
    assert broker.check("catalog", Tier.CHANGE).allowed is True


def test_request_above_granted_tier_is_denied():
    broker = CapabilityBroker()
    broker.grant("catalog", Tier.CHANGE)
    d = broker.check("catalog", Tier.DEPLOY)
    assert d.allowed is False
    assert "exceeds granted" in d.reason


def test_revoke_returns_to_deny_by_default():
    broker = CapabilityBroker()
    broker.grant("catalog", Tier.CHANGE)
    assert broker.revoke("catalog") is True
    assert broker.revoke("catalog") is False
    assert broker.check("catalog", Tier.READ_ONLY).allowed is False


def test_grant_requires_name():
    broker = CapabilityBroker()
    with pytest.raises(ValueError):
        broker.grant("   ", Tier.READ_ONLY)


# --------------------------------------------------------------------------- #
# authorize_action end-to-end
# --------------------------------------------------------------------------- #
def test_authorize_action_respects_action_tier():
    broker = CapabilityBroker()
    broker.grant("store", Tier.CHANGE)
    # A CHANGE-tier action on a CHANGE-granted capability is allowed...
    assert broker.authorize_action("store", "catalog_edit").allowed is True
    # ...but a DEPLOY-tier action (pricing) on the same grant is denied.
    assert broker.authorize_action("store", "pricing_change").allowed is False


def test_read_only_grant_blocks_drafting():
    broker = CapabilityBroker()
    broker.grant("metrics", Tier.READ_ONLY)
    assert broker.authorize_action("metrics", "read").allowed is True
    assert broker.authorize_action("metrics", "draft").allowed is False
