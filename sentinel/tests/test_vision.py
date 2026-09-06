"""Tests for SENTINEL privacy-preserving vision ops.

Asserts the capabilities deliver operational value WITHOUT identity:
presence/safety analytics are anonymous, and consented access control runs
behind the policy gate and never identifies non-consenting people.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.policy import RequestContext
from sentinel.vision import (
    ConsentedAccessControl,
    Enrollment,
    Observation,
    PresenceEvent,
    PresenceMonitor,
)


# ---- anonymous presence analytics: no identity fields anywhere ----

def test_presence_event_carries_no_identity():
    fields = set(PresenceEvent.__dataclass_fields__)
    assert not (fields & {"name", "identity", "person_id", "subject", "encoding", "face"})
    ofields = set(Observation.__dataclass_fields__)
    assert not (ofields & {"name", "identity", "person_id", "encoding", "face"})


def test_occupancy_event():
    mon = PresenceMonitor(occupancy_limit=3)
    obs = [Observation(f"b{i}", "lobby", 10.0) for i in range(5)]
    kinds = {e.kind for e in mon.analyze("lobby", obs)}
    assert "occupancy" in kinds


def test_tailgating_in_access_zone():
    mon = PresenceMonitor()
    obs = [Observation("b1", "dock", 1.0), Observation("b2", "dock", 2.0)]
    events = mon.analyze("dock", obs)
    assert any(e.kind == "tailgating" for e in events)


def test_no_tailgating_in_open_zone():
    mon = PresenceMonitor()
    obs = [Observation("b1", "yard", 1.0), Observation("b2", "yard", 2.0)]
    assert not any(e.kind == "tailgating" for e in mon.analyze("yard", obs))


def test_abandoned_object():
    mon = PresenceMonitor(abandoned_s=30)
    obs = [Observation("bag1", "lobby", 90.0, is_object=True)]
    assert any(e.kind == "abandoned_object" for e in mon.analyze("lobby", obs))


def test_clear_when_nominal():
    mon = PresenceMonitor()
    obs = [Observation("b1", "yard", 5.0)]
    assert [e.kind for e in mon.analyze("yard", obs)] == ["clear"]


# ---- consented access control ----

def _ctx(**kw):
    base = dict(
        actor_role="security_lead", purpose="consented access control at owned turnstile",
        data_source="consented_watchlist", intent="access_control",
        targets_private_individual=True, subject_consenting=True,
        authorization_ref="POLICY-AC-1", jurisdiction="US-CA",
    )
    base.update(kw)
    return RequestContext(**base)


ROSTER = [
    Enrollment("badge-hash-abc", consent=True, jurisdiction="US-CA"),
    Enrollment("badge-hash-xyz", consent=True, jurisdiction="US-CA"),
    Enrollment("badge-hash-nope", consent=False, jurisdiction="US-CA"),  # not opted in
]


def test_enrolled_consented_credential_grants_pending_review():
    acc = ConsentedAccessControl(ROSTER)
    r = acc.verify(presented_ref="badge-hash-abc", ctx=_ctx())
    assert r.access == "GRANT_PENDING_REVIEW"
    assert r.requires_human_review is True
    assert r.audit_ref.startswith("SENT-")


def test_unknown_credential_denied_without_identifying():
    acc = ConsentedAccessControl(ROSTER)
    r = acc.verify(presented_ref="badge-hash-unknown", ctx=_ctx())
    assert r.access == "DENY"
    assert any("no consented enrollment" in x for x in r.reasons)
    assert r.subject_ref is None              # never tries to identify who


def test_non_consenting_enrollment_not_retained():
    acc = ConsentedAccessControl(ROSTER)
    r = acc.verify(presented_ref="badge-hash-nope", ctx=_ctx())
    assert r.access == "DENY"                  # consent=False -> not in roster


def test_missing_authorization_denied_by_gate():
    acc = ConsentedAccessControl(ROSTER)
    r = acc.verify(presented_ref="badge-hash-abc", ctx=_ctx(authorization_ref=None))
    assert r.access == "DENY"


def test_missing_jurisdiction_denied_by_gate():
    acc = ConsentedAccessControl(ROSTER)
    r = acc.verify(presented_ref="badge-hash-abc", ctx=_ctx(jurisdiction=None))
    assert r.access == "DENY"
