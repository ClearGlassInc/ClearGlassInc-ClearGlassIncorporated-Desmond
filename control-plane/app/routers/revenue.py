"""ClearGlass Revenue Command System — public qualification + authenticated revenue cockpit."""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from .. import attribution, payments, pricebook
from ..audit import log_event
from ..config import get_settings
from ..db import get_session
from ..models import Event, Lead, LeadActivity, Order, RevenueControlLog, ServiceOrder
from ..order_ledger import SETTLED_STATUSES, revenue_breakdown
from ..revenue_service import STAGES, confirm_delivery, create_lead, is_spam_trap
from ..schemas import (
    RevenueActivityOut,
    RevenueByCampaign,
    RevenueCheckoutRequest,
    RevenueCockpitOut,
    RevenueControlLogRequest,
    RevenueLeadOut,
    RevenueLeadReceipt,
    RevenueLeadRequest,
    RevenueLeadStageUpdate,
    RevenueOfferOut,
    RevenueServiceOrderOut,
)
from ..security import rate_limit, require_admin

logger = logging.getLogger("clearglass.revenue")
router = APIRouter(prefix="/revenue", tags=["revenue"])
_lead_throttle = rate_limit("revenue_lead", "revenue_lead_rate_limit_per_minute")
_checkout_throttle = rate_limit("revenue_checkout", "rate_limit_checkout_per_minute")

RAPID_SCOPE = [
    "intake review",
    "issue triage",
    "root-cause findings",
    "prioritized repair plan",
    "next-step recommendations",
]
RAPID_EXCLUSIONS = [
    "no guaranteed repair",
    "no full penetration test",
    "no legal or compliance advice",
    "no emergency response unless separately agreed",
    "no promise of rankings, revenue, uptime, or business outcomes",
]


@router.get("/public-offer", response_model=RevenueOfferOut)
def public_offer() -> RevenueOfferOut:
    settings = get_settings()
    try:
        offer = pricebook.get_offer(settings.crcs_first_offer_sku)
    except pricebook.PricebookError as exc:
        raise HTTPException(status_code=503, detail="first offer is not configured") from exc

    link = settings.crcs_rapid_diagnostic_payment_link.strip() or None
    payment_ready = settings.crcs_rapid_diagnostic_enabled and (
        bool(link) or bool(settings.stripe_secret_key.strip())
    )
    payment_mode = (
        "payment_link" if link and payment_ready
        else "server_checkout" if payment_ready
        else "manual_review"
    )
    return RevenueOfferOut(
        sku=offer.sku,
        name=offer.name,
        description=offer.description,
        amount_cad=float(Decimal(offer.amount) / Decimal(100)),
        currency=offer.currency.upper(),
        scope=RAPID_SCOPE,
        exclusions=RAPID_EXCLUSIONS,
        enabled=settings.crcs_rapid_diagnostic_enabled,
        payment_ready=payment_ready,
        payment_mode=payment_mode,
        payment_url=link if link and payment_ready else None,
        calendar_url=settings.crcs_calendar_booking_url.strip() or None,
    )


def _receipt(reference: uuid.UUID) -> RevenueLeadReceipt:
    # Every submitter is offered the same next step. The fit score orders the
    # owner's review queue; it never decides who may book a call.
    booking_url = get_settings().crcs_calendar_booking_url.strip() or None
    return RevenueLeadReceipt(
        reference=reference,
        next_step="book_discovery_call" if booking_url else "owner_review",
        booking_url=booking_url,
    )


@router.post(
    "/leads",
    response_model=RevenueLeadReceipt,
    status_code=201,
    dependencies=[Depends(_lead_throttle)],
)
def submit_lead(req: RevenueLeadRequest, session: Session = Depends(get_session)) -> RevenueLeadReceipt:
    data = req.model_dump()
    if is_spam_trap(data):
        # Same status and shape as a real receipt, and nothing stored. A bot that
        # can see it was caught learns which field to leave empty.
        logger.info("crcs honeypot submission discarded")
        return _receipt(uuid.uuid4())
    lead = create_lead(session, data)
    return _receipt(lead.public_ref)


def _lead_attribution(lead: Lead | None) -> dict[str, str | None]:
    """Last touch when the lead has one, else first touch."""
    if lead is None:
        return {}
    if lead.utm_last_campaign or lead.utm_last_source:
        return {
            "utm_source": lead.utm_last_source,
            "utm_medium": lead.utm_last_medium,
            "utm_campaign": lead.utm_last_campaign,
        }
    return {
        "utm_source": lead.utm_first_source,
        "utm_medium": lead.utm_first_medium,
        "utm_campaign": lead.utm_first_campaign,
    }


def _buyer_ref(email: str) -> str:
    """A stable pseudonym for a buyer with no lead.

    The audit ledger is kept for years and cannot be edited, so it holds IDs,
    never email addresses (docs/crcs/DATA_MODEL.md rule 1). A keyed hash still
    lets the owner see repeated attempts by the same buyer.
    """
    key = (get_settings().crcs_audit_hash_key or "clearglass-dev-audit-key").encode()
    return "buyer:" + hmac.new(key, email.encode(), hashlib.sha256).hexdigest()[:24]


@router.post("/checkout", dependencies=[Depends(_checkout_throttle)])
def start_checkout(req: RevenueCheckoutRequest, session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    try:
        offer = pricebook.get_offer(settings.crcs_first_offer_sku)
    except pricebook.PricebookError as exc:
        raise HTTPException(status_code=503, detail="first offer is not configured") from exc

    if not settings.crcs_rapid_diagnostic_enabled:
        raise HTTPException(
            status_code=409,
            detail="payment activation requires owner confirmation of price, refund policy, and delivery promise",
        )

    email = req.customer_email.strip().lower()
    lead = (
        session.scalar(select(Lead).where(Lead.public_ref == req.reference))
        if req.reference else None
    )
    # One answer for "no such lead" and "not your lead", so a reference cannot
    # be used to confirm that a given address submitted the qualification form.
    if req.reference and (lead is None or lead.email != email):
        raise HTTPException(status_code=403, detail="checkout email does not match lead")
    audit_target = str(lead.id) if lead else _buyer_ref(email)

    if settings.crcs_rapid_diagnostic_payment_link.strip():
        log_event(
            session,
            actor="revenue_system",
            action="checkout_started",
            target=audit_target,
            payload={"sku": offer.sku, "mode": "payment_link"},
            result="executed",
        )
        return {
            "status": "ready",
            "mode": "payment_link",
            "url": settings.crcs_rapid_diagnostic_payment_link.strip(),
            "sku": offer.sku,
            "amount_cad": float(Decimal(offer.amount) / Decimal(100)),
        }

    line_items, checkout_mode = pricebook.resolve_line_items([{"sku": offer.sku, "quantity": 1}])
    result = payments.create_checkout_session(
        line_items,
        customer_email=email,
        checkout_mode=checkout_mode,
        # No email here: Stripe already has it as customer_email, and this id
        # is echoed into dashboards and exports.
        client_reference_id=f"crcs-{lead.public_ref if lead else 'public'}",
        extra_metadata={
            "crcs_sku": offer.sku,
            "crcs_lead_id": str(lead.id) if lead else "",
            "crcs_revenue_system": "v1",
            # Copied from the lead server-side, so the paid order carries the
            # campaign that produced the lead without trusting the browser.
            **attribution.to_metadata(_lead_attribution(lead)),
        },
    )
    # The payment-link branch logged this and the server-checkout branch did
    # not, so checkout_started undercounted whenever Stripe Checkout was used.
    log_event(
        session,
        actor="revenue_system",
        action="checkout_started",
        target=audit_target,
        payload={"sku": offer.sku, "mode": result["mode"]},
        result="executed",
    )
    return {
        "status": "ready",
        "mode": result["mode"],
        "url": result["url"],
        "checkout_mode": result["checkout_mode"],
        "id": result["id"],
        "sku": offer.sku,
        "amount_cad": result["amount_total"] / 100,
        "currency": result["currency"],
    }


def _utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; Postgres TIMESTAMPTZ hands back aware ones.

    Comparing a naive value with ``now`` raised TypeError, so the cockpit
    answered 500 on SQLite as soon as one lead existed.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _latest_stripe_event(session: Session) -> Event | None:
    """The newest audit event Stripe itself produced: the webhook-health evidence."""
    return session.scalar(
        select(Event).where(Event.actor == "stripe").order_by(Event.ts.desc()).limit(1)
    )


@router.get("/health")
def public_health(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    try:
        session.execute(select(func.count(Lead.id))).scalar_one()
        db_ok = True
    except Exception:
        db_ok = False

    recent_stripe = _latest_stripe_event(session)
    return {
        "service": "clearglass-revenue-command",
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "first_offer": settings.crcs_first_offer_sku,
        "payment_activation": "enabled" if settings.crcs_rapid_diagnostic_enabled else "blocked",
        "payment_route": (
            "payment_link" if settings.crcs_rapid_diagnostic_payment_link.strip()
            else "server_checkout" if settings.stripe_secret_key.strip()
            else "not_configured"
        ),
        "last_stripe_event_at": recent_stripe.ts.isoformat() if recent_stripe else None,
        "booking_configured": bool(settings.crcs_calendar_booking_url.strip()),
        "internal_crm": "ready",
    }


def _verified_mrr(session: Session) -> tuple[Decimal | None, int | None, int | None, int | None]:
    """MRR from the subscriptions Stripe's verified webhook wrote, not from leads.

    Returns ``(mrr, active, past_due, unpriced)``, all ``None`` when the
    subscriptions table does not exist (migration 006 not applied): no data is
    reported as no data, never as zero.

    A subscription counts only when its Stripe Price is one of the price book's
    live Prices. The table records no livemode, so this is also what keeps
    test-mode subscriptions (test Price ids) out of MRR; they are reported as
    ``unpriced`` instead.
    """
    if not inspect(session.get_bind()).has_table("subscriptions"):
        return None, None, None, None
    offers = {o.stripe_price_id: o for o in pricebook.all_offers(include_inactive=True) if o.stripe_price_id}
    rows = session.execute(text("SELECT stripe_price_id, status FROM subscriptions")).all()
    mrr = Decimal(0)
    active = past_due = unpriced = 0
    for price_id, status in rows:
        if status == "past_due":
            past_due += 1
        if status not in {"active", "trialing"}:
            continue
        offer = offers.get(price_id)
        if offer is None or offer.interval not in {"month", "year"}:
            unpriced += 1
            continue
        active += 1
        monthly = Decimal(offer.amount) / Decimal(100)
        mrr += monthly if offer.interval == "month" else (monthly / Decimal(12)).quantize(Decimal("0.01"))
    return mrr, active, past_due, unpriced


def _revenue_by_campaign(orders: list[Order]) -> list[RevenueByCampaign]:
    """Confirmed live revenue per utm_campaign; untagged orders are 'unattributed'."""
    groups: dict[str, list[Order]] = {}
    for order in orders:
        groups.setdefault(order.utm_campaign or "unattributed", []).append(order)
    rows = [
        RevenueByCampaign(
            campaign=campaign,
            orders=len(members),
            confirmed_revenue_cad=float(revenue_breakdown(members)["confirmed"]),
        )
        for campaign, members in groups.items()
    ]
    return sorted(rows, key=lambda r: r.confirmed_revenue_cad, reverse=True)[:20]


@router.get("/cockpit", response_model=RevenueCockpitOut, dependencies=[Depends(require_admin)])
def cockpit(session: Session = Depends(get_session)) -> RevenueCockpitOut:
    now = datetime.now(UTC)
    window = now - timedelta(days=30)
    week = now - timedelta(days=7)

    leads = list(session.scalars(select(Lead)).all())
    orders = list(session.scalars(select(Order)).all())
    services = list(session.scalars(select(ServiceOrder)).all())
    activities = list(session.scalars(
        select(LeadActivity).where(LeadActivity.created_at >= window)
    ).all())
    recent_stripe = _latest_stripe_event(session)

    # Orders that received money in live mode; revenue_breakdown then takes out
    # refunds and disputes, so a refunded or charged-back sale is not revenue.
    live_settled = [o for o in orders if o.status in SETTLED_STATUSES and o.environment == "live"]
    test_settled = [o for o in orders if o.status in SETTLED_STATUSES and o.environment == "test"]
    live = revenue_breakdown(live_settled)
    confirmed_revenue = live["confirmed"]
    test_revenue = revenue_breakdown(test_settled)["confirmed"]
    verified_mrr, active_subs, past_due_subs, unpriced_subs = _verified_mrr(session)

    pipeline = sum(
        (Decimal(lead.expected_value_cad or 0) for lead in leads
         if lead.stage not in {"WON", "LOST", "CLOSED", "CUSTOMER_ACTIVE", "RETENTION_RISK"}),
        Decimal(0),
    )
    mrr = sum(
        (Decimal(lead.monthly_recurring_value_cad or 0) for lead in leads
         if lead.stage in {"WON", "CUSTOMER_ACTIVE", "RETENTION_RISK", "EXPANSION_OPPORTUNITY"}),
        Decimal(0),
    )

    live_order_ids = {o.id for o in live_settled}
    cost_rows = [s for s in services if s.order_id in live_order_ids and s.delivery_cost_cad is not None]
    known_costs = sum((Decimal(s.delivery_cost_cad or 0) for s in cost_rows), Decimal(0))
    gross_margin = confirmed_revenue - known_costs if cost_rows else None

    won = sum(1 for lead in leads if lead.stage == "WON")
    lost = sum(1 for lead in leads if lead.stage == "LOST")
    close_rate = won / (won + lost) if won + lost else None
    due_actions = sum(
        1 for lead in leads
        if lead.next_action_at and _utc(lead.next_action_at) <= now and lead.stage not in {"LOST", "CLOSED"}
    )
    today = now.date().isoformat()
    today_logs = list(session.scalars(
        select(RevenueControlLog).where(RevenueControlLog.action_date == today)
    ).all())
    revenue_action_required = not any(
        x.status in {"IN_PROGRESS", "COMPLETED"} for x in today_logs
    )

    return RevenueCockpitOut(
        generated_at=now,
        confirmed_revenue_cad=float(confirmed_revenue),
        gross_revenue_cad=float(live["gross"]),
        refunded_cad=float(live["refunded"]),
        disputed_open_cad=float(live["disputed_open"]),
        dispute_lost_cad=float(live["dispute_lost"]),
        verified_mrr_cad=float(verified_mrr) if verified_mrr is not None else None,
        active_subscriptions=active_subs,
        past_due_subscriptions=past_due_subs,
        unpriced_subscriptions=unpriced_subs,
        revenue_by_campaign=_revenue_by_campaign(live_settled),
        test_revenue_cad=float(test_revenue),
        pipeline_estimate_cad=float(pipeline),
        mrr_cad=float(mrr),
        gross_margin_cad=float(gross_margin) if gross_margin is not None else None,
        qualified_leads=sum(1 for lead in leads if lead.stage == "QUALIFIED"),
        new_leads=sum(1 for lead in leads if _utc(lead.created_at) >= week),
        meetings_booked=sum(1 for a in activities if a.activity_type == "meeting_booked"),
        proposals=sum(
            1 for lead in leads
            if lead.stage in {"PROPOSAL_PENDING", "PROPOSAL_SENT", "NEGOTIATION", "WON"}
        ),
        won=won,
        lost=lost,
        close_rate=close_rate,
        open_service_orders=sum(1 for s in services if s.status not in {"DELIVERED", "CLOSED"}),
        due_actions=due_actions,
        webhook_health="EVIDENCE_PRESENT" if recent_stripe else "NO_RECENT_EVIDENCE",
        booking_health="CONFIGURED" if get_settings().crcs_calendar_booking_url.strip() else "MANUAL_FALLBACK",
        crm_health="READY",
        revenue_action_required=revenue_action_required,
    )


@router.get("/leads", response_model=list[RevenueLeadOut], dependencies=[Depends(require_admin)])
def list_leads(
    stage: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(max(1, min(limit, 500)))
    if stage:
        if stage not in STAGES:
            raise HTTPException(status_code=400, detail="unknown stage")
        stmt = stmt.where(Lead.stage == stage)
    return list(session.scalars(stmt).all())


@router.get("/leads/{lead_id}/activities", response_model=list[RevenueActivityOut], dependencies=[Depends(require_admin)])
def list_activities(lead_id: int, session: Session = Depends(get_session)) -> list[LeadActivity]:
    if session.get(Lead, lead_id) is None:
        raise HTTPException(status_code=404, detail="lead not found")
    stmt = (
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.created_at.desc())
        .limit(200)
    )
    return list(session.scalars(stmt).all())


@router.post("/leads/{lead_id}/stage", response_model=RevenueLeadOut, dependencies=[Depends(require_admin)])
def update_stage(
    lead_id: int,
    req: RevenueLeadStageUpdate,
    session: Session = Depends(get_session),
) -> Lead:
    if req.stage not in STAGES:
        raise HTTPException(status_code=400, detail="unknown stage")
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    previous = lead.stage
    lead.stage = req.stage
    if req.owner:
        lead.owner = req.owner.strip()
    lead.next_action = req.next_action.strip()
    lead.next_action_at = req.next_action_at
    lead.expected_value_cad = req.expected_value_cad
    lead.monthly_recurring_value_cad = req.monthly_recurring_value_cad
    session.add(LeadActivity(
        lead_id=lead.id,
        activity_type="stage_changed",
        actor="admin",
        detail=f"{previous} -> {lead.stage}; next_action={lead.next_action}",
    ))
    log_event(
        session,
        actor="admin",
        action="lead_stage_changed",
        target=str(lead.id),
        payload={"from": previous, "to": lead.stage},
        result="executed",
    )
    return lead


@router.post("/control-log", dependencies=[Depends(require_admin)])
def create_control_log(req: RevenueControlLogRequest, session: Session = Depends(get_session)) -> dict:
    allowed = {
        "NOT_STARTED",
        "IN_PROGRESS",
        "BLOCKED",
        "WAITING_ON_PROSPECT",
        "COMPLETED",
        "LOST",
        "DEFERRED_WITH_REASON",
    }
    if req.status not in allowed:
        raise HTTPException(status_code=400, detail="invalid control-log status")
    row = RevenueControlLog(**req.model_dump())
    session.add(row)
    session.flush()
    log_event(
        session,
        actor="admin",
        action="revenue_control_log_created",
        target=str(row.id),
        payload={"status": row.status, "action_date": row.action_date},
        result="executed",
    )
    return {
        "id": row.id,
        "status": row.status,
        "action_date": row.action_date,
        "next_action": row.next_action,
        "due_date": row.due_date,
    }


@router.get("/control-log", dependencies=[Depends(require_admin)])
def list_control_log(limit: int = 100, session: Session = Depends(get_session)) -> list[dict]:
    rows = list(session.scalars(
        select(RevenueControlLog)
        .order_by(RevenueControlLog.action_date.desc(), RevenueControlLog.id.desc())
        .limit(max(1, min(limit, 500)))
    ).all())
    return [
        {
            "id": r.id,
            "action_date": r.action_date,
            "action": r.action,
            "target": r.target,
            "expected_outcome": r.expected_outcome,
            "action_taken": r.action_taken,
            "evidence": r.evidence,
            "result": r.result,
            "next_action": r.next_action,
            "due_date": r.due_date,
            "owner": r.owner,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/service-orders", response_model=list[RevenueServiceOrderOut], dependencies=[Depends(require_admin)])
def list_service_orders(limit: int = 100, session: Session = Depends(get_session)) -> list[ServiceOrder]:
    stmt = select(ServiceOrder).order_by(ServiceOrder.created_at.desc()).limit(max(1, min(limit, 500)))
    return list(session.scalars(stmt).all())


@router.post("/service-orders/{service_order_id}/confirm-delivery", dependencies=[Depends(require_admin)])
def confirm_service_delivery(service_order_id: int, session: Session = Depends(get_session)) -> dict:
    service = session.get(ServiceOrder, service_order_id)
    if service is None:
        raise HTTPException(status_code=404, detail="service order not found")
    confirm_delivery(session, service)
    return {
        "status": "DELIVERED",
        "service_order_id": service.id,
        "testimonial_request": "DRAFT_ONLY_AFTER_CUSTOMER_CONFIRMED_DELIVERY",
    }
