# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for sentinel/sentinel/identity.py — scoped, sponsor-owned Percival
instances bound to the capability broker."""
from __future__ import annotations

import pytest

from sentinel.capability import Tier
from sentinel.identity import AgentIdentity


def _identity(**kw) -> AgentIdentity:
    base = dict(
        instance_id="percival-1",
        sponsor="Desmond",
        purpose="executive decision support",
        allowed_scopes={"metrics", "catalog"},
    )
    base.update(kw)
    return AgentIdentity(**base)


# --------------------------------------------------------------------------- #
# required fields
# --------------------------------------------------------------------------- #
def test_sponsor_is_required():
    with pytest.raises(ValueError):
        _identity(sponsor="  ")


def test_purpose_is_required():
    with pytest.raises(ValueError):
        _identity(purpose="")


def test_instance_id_is_required():
    with pytest.raises(ValueError):
        _identity(instance_id="")


# --------------------------------------------------------------------------- #
# scope checks (deny-by-default, denial wins)
# --------------------------------------------------------------------------- #
def test_may_touch_only_allowed_scopes():
    ident = _identity()
    assert ident.may_touch("metrics") is True
    assert ident.may_touch("payments") is False  # not allowed → unavailable


def test_denied_scope_wins_over_allowed():
    ident = _identity(allowed_scopes={"metrics", "catalog"}, denied_scopes={"catalog"})
    assert ident.may_touch("catalog") is False


def test_stopped_instance_touches_nothing():
    ident = _identity()
    ident.stop()
    assert ident.active is False
    assert ident.may_touch("metrics") is False


# --------------------------------------------------------------------------- #
# default authority is read-only
# --------------------------------------------------------------------------- #
def test_default_authority_is_read_only():
    ident = _identity()
    assert ident.default_tier == Tier.READ_ONLY
    broker = ident.new_broker()
    assert broker.check("metrics", Tier.READ_ONLY).allowed is True
    # Write/deploy authority is NOT granted by default — must be elevated.
    assert broker.check("metrics", Tier.CHANGE).allowed is False
    assert broker.check("metrics", Tier.DEPLOY).allowed is False


def test_broker_seeds_only_allowed_scopes():
    ident = _identity(allowed_scopes={"metrics"}, denied_scopes=set())
    broker = ident.new_broker()
    assert broker.check("metrics", Tier.READ_ONLY).allowed is True
    assert broker.check("catalog", Tier.READ_ONLY).allowed is False  # never granted


def test_broker_respects_denied_scopes():
    ident = _identity(allowed_scopes={"metrics", "catalog"}, denied_scopes={"catalog"})
    broker = ident.new_broker()
    assert broker.check("catalog", Tier.READ_ONLY).allowed is False


def test_stopped_instance_grants_nothing():
    ident = _identity()
    ident.stop()
    broker = ident.new_broker()
    assert broker.check("metrics", Tier.READ_ONLY).allowed is False


def test_elevated_default_tier_is_honored():
    # An instance can be provisioned with a higher authority floor when its
    # sponsor and purpose warrant it.
    ident = _identity(default_tier=Tier.CHANGE)
    broker = ident.new_broker()
    assert broker.check("catalog", Tier.CHANGE).allowed is True
    assert broker.check("catalog", Tier.DEPLOY).allowed is False


# --------------------------------------------------------------------------- #
# describe (audit-readable)
# --------------------------------------------------------------------------- #
def test_describe_exposes_ownership():
    d = _identity().describe()
    assert d["sponsor"] == "Desmond"
    assert d["default_tier"] == "READ_ONLY"
    assert d["allowed_scopes"] == ["catalog", "metrics"]
