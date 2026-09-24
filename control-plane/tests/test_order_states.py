"""The ClearGlass payment state machine and order ids (stdlib only).

The rule these hold: a state that says something about money can only be
entered on verified processor evidence, and only along an allowed edge.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import order_states as s


def test_order_refs_have_the_published_shape_and_do_not_repeat() -> None:
    refs = {s.new_order_ref(datetime(2026, 9, 24, tzinfo=UTC)) for _ in range(500)}
    assert len(refs) == 500
    for ref in refs:
        assert s.is_order_ref(ref), ref
        assert ref.startswith("CG-ORD-2026-")
        # Crockford base32: nothing that reads as another character.
        assert not set(ref[len("CG-ORD-2026-"):]) & set("ILOU")


@pytest.mark.parametrize(
    "value",
    ["", "CG-ORD-2026-1234567", "CG-ORD-2026-123456789", "CG-ORD-2026-ABCDEFGI",
     "cg-ord-2026-ABCDEFGH", "CG-ORD-1999-ABCDEFGH", "CG-ORD-2026-ABCD EFG", None, 7],
)
def test_anything_else_is_not_an_order_ref(value) -> None:
    assert not s.is_order_ref(value)


@pytest.mark.parametrize("target", sorted(s.PROVIDER_STATES))
def test_money_states_need_verified_evidence(target) -> None:
    """A browser redirect or request body is never enough to say money moved."""
    sources = [state for state, allowed in s.TRANSITIONS.items() if target in allowed]
    assert sources, f"{target} is unreachable"
    for source in sources:
        assert s.check_transition(source, target, verified=False) is not None
        assert s.check_transition(source, target, verified=True) is None


def test_the_happy_path_is_allowed() -> None:
    path = [s.CREATED, s.CHECKOUT_STARTED, s.PAYMENT_PROCESSING, s.PAID]
    for current, target in zip(path, path[1:]):
        assert s.check_transition(current, target, verified=True) is None


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (s.CREATED, s.PAID),              # no checkout ever started
        (s.PAID, s.CHECKOUT_STARTED),     # a paid order cannot be paid again
        (s.PAID, s.CANCELED),             # money received is never "canceled"
        (s.REFUNDED, s.PAID),             # a refund is final
        (s.CHARGEBACK, s.PAID),           # so is a lost dispute
        (s.PAYMENT_PROCESSING, s.CANCELED),
    ],
)
def test_forbidden_edges_are_refused_even_with_evidence(current, target) -> None:
    assert s.check_transition(current, target, verified=True) is not None


def test_unknown_states_are_refused() -> None:
    assert s.check_transition("SHIPPED", s.PAID, verified=True) is not None
    assert s.check_transition(s.PAID, "SETTLED", verified=True) is not None


def test_every_state_is_in_the_table() -> None:
    assert set(s.TRANSITIONS) == set(s.PAYMENT_STATES)
    for allowed in s.TRANSITIONS.values():
        assert allowed <= set(s.PAYMENT_STATES)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"status": "paid", "amount_refunded": 0, "total": 125, "dispute_status": None}, s.PAID),
        ({"status": "paid", "amount_refunded": 25, "total": 125, "dispute_status": None}, s.PARTIALLY_REFUNDED),
        ({"status": "refunded", "amount_refunded": 125, "total": 125, "dispute_status": None}, s.REFUNDED),
        ({"status": "paid", "amount_refunded": 0, "total": 125, "dispute_status": "needs_response"}, s.DISPUTED),
        ({"status": "paid", "amount_refunded": 0, "total": 125, "dispute_status": "lost"}, s.CHARGEBACK),
        ({"status": "paid", "amount_refunded": 0, "total": 125, "dispute_status": "won"}, s.PAID),
    ],
)
def test_adjustments_map_to_states(kwargs, expected) -> None:
    assert s.state_for_adjustment(
        **kwargs,
        open_disputes=frozenset({"needs_response", "under_review"}),
        lost_disputes=frozenset({"lost"}),
    ) == expected


@pytest.mark.parametrize(
    ("payment_state", "flagged", "service", "expected"),
    [
        (s.CHECKOUT_STARTED, False, None, s.NOT_STARTED),
        (s.PAID, False, None, s.NOT_STARTED),              # paid, no task: reconciliation flags this
        (s.PAID, False, "INTAKE_REQUIRED", s.FULFILLMENT_PENDING),
        (s.PAID, False, "IN_PROGRESS", s.FULFILLING),
        (s.PAID, False, "DELIVERED", s.COMPLETED),
        (s.PAID, True, "INTAKE_REQUIRED", s.HELD),          # money in question: stop work
        (s.DISPUTED, False, "INTAKE_REQUIRED", s.HELD),
        (s.REFUNDED, False, "DELIVERED", s.COMPLETED),     # delivered work stays delivered
    ],
)
def test_fulfillment_is_derived_from_what_exists(payment_state, flagged, service, expected) -> None:
    assert s.fulfillment_state(
        payment_state=payment_state,
        reconciliation_required=flagged,
        service_status=service,
        shipment_status=None,
    ) == expected


def test_display_state_shows_fulfillment_only_once_paid() -> None:
    assert s.display_state(s.PAID, s.FULFILLING) == s.FULFILLING
    assert s.display_state(s.PAID, s.HELD) == s.PAID
    assert s.display_state(s.CHECKOUT_STARTED, s.NOT_STARTED) == s.CHECKOUT_STARTED
    assert s.display_state(s.REFUNDED, s.COMPLETED) == s.REFUNDED
