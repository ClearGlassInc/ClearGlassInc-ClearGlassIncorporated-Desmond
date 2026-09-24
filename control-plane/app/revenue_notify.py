"""Slack revenue events: one short message per real step of the revenue chain.

Every step that matters is already written to the append-only audit ledger by
``log_event``: a lead, a qualification, a booked meeting, a sent proposal, a
verified payment, delivery work opening, a confirmed delivery, a new or cancelled
subscription, and money leaving through a refund or dispute. ``observe`` notes
each ledger row as it is written, in memory only: it runs no SQL, so it cannot
disturb the transaction that is recording a payment. Only **after that
transaction commits** are the rows described, on a separate read-only session,
and posted to the Slack incoming webhook in ``SLACK_WEBHOOK_URL``. Slack never
announces a step the database rolled back. Unset, nothing is noted.

A message carries the step, the offer, the amount, live or test, the lead source
or campaign, and opaque references. Never a name, an email address or a secret.
Test-mode money is labelled TEST DATA and is never called revenue.

Posting cannot fail the request that produced the step: a Slack error is logged by
exception type only (the webhook URL is itself a credential) and dropped. A
redelivered webhook sends nothing, because the ledger skips a duplicate before it
writes the row this module would have seen.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event as sa_event
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import pricebook
from .config import get_settings
from .models import CommercialOrder, Event, Lead, Order, ServiceOrder

log = logging.getLogger(__name__)

SLACK_HOST_PREFIX = "https://hooks.slack.com/"
TIMEOUT_SECONDS = 3
MAX_FIELD_LENGTH = 120
_QUEUE_KEY = "cg_revenue_notifications"

#: Lead stages worth a message, with a fixed next action. Every other stage change
#: stays in the ledger only. The lead's own ``next_action`` is free text an admin
#: types, and can name a person, so it is never sent.
LEAD_STAGE_EVENTS = {
    "QUALIFIED": ("QUALIFIED", "Book a discovery call"),
    "BOOKED": ("MEETING BOOKED", "Prepare the discovery call"),
    "PROPOSAL_SENT": ("PROPOSAL SENT", "Follow up on the proposal"),
}

LIVE = "LIVE"
TEST_DATA = "TEST DATA"

_warned_bad_url = False


def webhook_url() -> str:
    """The configured Slack incoming-webhook URL, or ``""`` when events are off.

    Anything that is not an ``https://hooks.slack.com/`` URL is refused, so a
    mistyped setting cannot turn this into a request to an arbitrary host.
    """
    global _warned_bad_url
    url = (get_settings().slack_webhook_url or "").strip()
    if url and not url.startswith(SLACK_HOST_PREFIX):
        if not _warned_bad_url:
            log.warning(
                "SLACK_WEBHOOK_URL is not a Slack incoming-webhook URL; revenue events are off"
            )
            _warned_bad_url = True
        return ""
    return url


def _post(url: str, text: str) -> None:
    body = json.dumps({"text": text}).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    # The scheme and host were checked by webhook_url().
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        response.read()


#: Replaceable in tests; production posts over HTTPS with a short timeout.
transport: Callable[[str, str], None] = _post


def observe(session: Session, row: Event) -> None:
    """Note ``row`` for announcement after commit. In memory only: no SQL, no I/O."""
    if not webhook_url():
        return
    snapshot = Event(actor=row.actor, action=row.action, target=row.target,
                     payload=dict(row.payload or {}), result=row.result)
    session.info.setdefault(_QUEUE_KEY, []).append((snapshot, datetime.now(UTC)))


def describe(session: Session, row: Event) -> dict[str, Any] | None:
    """The message fields for a ledger row, or ``None`` when it is not a revenue step."""
    action = row.action
    payload = row.payload or {}

    if action == "lead_created":
        lead = _get(session, Lead, row.target)
        return {
            "Stage": "NEW LEAD",
            "Offer": payload.get("service_interest"),
            "Score": payload.get("score"),
            "Source": payload.get("source"),
            "Lead": lead.public_ref if lead else None,
            "Next Action": "Review the lead and choose the next commercial step",
        }

    if action == "lead_stage_changed":
        milestone = LEAD_STAGE_EVENTS.get(str(payload.get("to")))
        lead = _get(session, Lead, row.target) if milestone else None
        if milestone is None or lead is None:
            return None
        stage, next_action = milestone
        return {
            "Stage": stage,
            "Offer": lead.service_interest,
            "Source": lead.utm_last_campaign or lead.source,
            "Lead": lead.public_ref,
            "Next Action": next_action,
        }

    if action == "order_paid":
        order = _get(session, Order, row.target)
        if order is None or not payload.get("verified"):
            return None
        live = order.environment == "live"
        return {
            "Stage": "PAYMENT RECEIVED",
            "Mode": LIVE if live else TEST_DATA,
            "Offer": _order_offer(session, order),
            "Amount": _money(order.total, order.currency),
            "Source": order.utm_campaign or order.source,
            "Payment": order.external_ref,
            "Order": order.order_ref or f"#{order.id}",
            "Next Action": "Begin delivery" if live else "None: test data, not revenue",
        }

    if action in {"order_refunded", "order_partially_refunded"}:
        order = _get(session, Order, row.target)
        if order is None:
            return None
        return {
            "Stage": "REFUNDED" if action == "order_refunded" else "PARTIALLY REFUNDED",
            "Mode": LIVE if order.environment == "live" else TEST_DATA,
            "Offer": _order_offer(session, order),
            "Refunded": _money(order.amount_refunded, order.currency),
            "Order Total": _money(order.total, order.currency),
            "Order": order.order_ref or f"#{order.id}",
            "Next Action": "Confirmed revenue is reduced; check whether delivery should stop",
        }

    if action.startswith("order_dispute_"):
        order = _get(session, Order, row.target)
        if order is None:
            return None
        return {
            "Stage": "DISPUTE",
            "Status": action[len("order_dispute_"):],
            "Mode": LIVE if order.environment == "live" else TEST_DATA,
            "Amount": _money(order.total, order.currency),
            "Order": order.order_ref or f"#{order.id}",
            "Next Action": "Review the dispute in the processor dashboard before its deadline",
        }

    if action == "service_order_provisioned":
        order = _get(session, Order, payload.get("order_id"))
        return {
            "Stage": "DELIVERY STARTED",
            "Mode": LIVE,  # delivery opens only on verified live money
            "Offer": _offer_name(payload.get("sku")),
            "Amount": _money(order.total, order.currency) if order else None,
            "Order": (order.order_ref or f"#{order.id}") if order else None,
            "Next Action": "Start intake and confirm scope",
        }

    if action == "delivery_confirmed":
        service = _get(session, ServiceOrder, row.target)
        order = _get(session, Order, payload.get("order_id"))
        net = Decimal(order.total) - Decimal(order.amount_refunded or 0) if order else None
        return {
            "Stage": "REVENUE CONFIRMED",
            "Meaning": "paid and delivered",
            "Offer": _offer_name(service.sku) if service else None,
            "Amount": _money(net, order.currency) if order else None,
            "Order": (order.order_ref or f"#{order.id}") if order else None,
            "Next Action": "Send the follow-up; ask for a referral only if it was earned",
        }

    if action in {"subscription_active", "subscription_canceled"}:
        created = action == "subscription_active"
        was_active = payload.get("from_status") == "active"
        if created == was_active:
            return None  # an update that neither starts nor ends recurring revenue
        plan = str(payload.get("plan") or "")
        return {
            "Stage": "MRR CREATED" if created else "MRR CANCELLED",
            "Mode": LIVE if payload.get("livemode") else TEST_DATA,
            "Offer": _offer_name(plan),
            "MRR": _monthly(plan),
            "Next Action": (
                "Schedule the first recurring delivery"
                if created
                else "Confirm the reason and stop recurring delivery"
            ),
        }

    return None


def format_message(fields: dict[str, Any], *, when: datetime) -> str:
    """Render the fields as the plain-text block the revenue channel reads."""
    header = "CLEARGLASS REVENUE EVENT"
    if fields.get("Mode") == TEST_DATA:
        header += " (TEST DATA)"
    lines = [header, ""]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        lines.append(f"{key}: {_clean(value)}")
    lines.append(f"Timestamp: {when.astimezone(UTC):%Y-%m-%dT%H:%M:%SZ}")
    return "\n".join(lines)


def _clean(value: Any) -> str:
    """One line, bounded, with Slack's control characters escaped.

    Lead sources and campaigns come from public form fields. Escaping ``<`` and
    ``>`` stops ``<!channel>`` pings and disguised links; collapsing whitespace
    stops a value forging extra ``Stage:`` lines.
    """
    text = re.sub(r"\s+", " ", str(value)).strip()[:MAX_FIELD_LENGTH]
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _get(session: Session, model: type, key: Any) -> Any:
    try:
        return session.get(model, int(key)) if key is not None else None
    except (TypeError, ValueError):
        return None


def _money(amount: Any, currency: str | None) -> str | None:
    if amount is None:
        return None
    return f"{(currency or '').upper()} ${Decimal(amount):,.2f}".strip()


def _order_offer(session: Session, order: Order) -> str | None:
    if not order.order_ref:
        return None
    commercial = session.scalar(
        select(CommercialOrder).where(CommercialOrder.order_ref == order.order_ref)
    )
    return commercial.offer_name if commercial else None


def _offer(sku: str | None) -> pricebook.Offer | None:
    """The price-book offer for ``sku``, retired ones included: a sale outlives its listing."""
    if not sku:
        return None
    return next((o for o in pricebook.all_offers(include_inactive=True) if o.sku == sku), None)


def _offer_name(sku: str | None) -> str | None:
    offer = _offer(sku)
    return offer.name if offer else sku


def _monthly(sku: str) -> str | None:
    """Monthly equivalent of a recurring price-book offer, e.g. ``CAD $83.33``."""
    offer = _offer(sku)
    months = {"month": 1, "year": 12}.get(offer.interval or "") if offer else None
    if not offer or not months:
        return None
    return _money(Decimal(offer.amount) / 100 / months, offer.currency)


def _send_queued(session: Session) -> None:
    noted = session.info.pop(_QUEUE_KEY, None)
    if not noted:
        return
    url = webhook_url()
    if not url:
        return
    # A separate session reads the committed rows. Any error here is contained:
    # the transaction that recorded the step has already committed.
    with Session(bind=session.get_bind()) as reader:
        for row, when in noted:
            try:
                fields = describe(reader, row)
                if fields:
                    transport(url, format_message(fields, when=when))
            except Exception as exc:  # Slack being down must not surface as a failed request
                log.warning(
                    "revenue event for %s not delivered (%s)", row.action, type(exc).__name__
                )


def _discard(session: Session, *_: Any) -> None:
    session.info.pop(_QUEUE_KEY, None)


# The application uses no savepoints, so any rollback ends the transaction the
# queued rows belonged to; dropping the whole queue is exact, not conservative.
sa_event.listen(Session, "after_commit", _send_queued)
sa_event.listen(Session, "after_soft_rollback", _discard)
