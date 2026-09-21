"""ClearGlass Revenue Command System — public qualification + authenticated revenue cockpit."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import payments, pricebook
from ..audit import log_event
from ..config import get_settings
from ..db import get_session
from ..models import Event, Lead, LeadActivity, Order, RevenueControlLog, ServiceOrder
from ..revenue_service import STAGES, confirm_delivery, create_lead
from ..schemas import (
    RevenueActivityOut,
    RevenueCheckoutRequest,
    RevenueCockpitOut,
    RevenueControlLogRequest,
    RevenueLeadOut,
    RevenueLeadRequest,
    RevenueLeadStageUpdate,
    RevenueOfferOut,
    RevenueServiceOrderOut,
)
from ..security import rate_limit, require_admin

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


@router.post("/leads", response_model=RevenueLeadOut, dependencies=[Depends(_lead_throttle)])
def submit_lead(req: RevenueLeadRequest, session: Session = Depends(get_session)) -> Lead:
    try:
        return create_lead(session, req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    lead = session.get(Lead, req.lead_id) if req.lead_id else None
    if req.lead_id and lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    if lead and lead.email != email:
        raise HTTPException(status_code=403, detail="checkout email does not match lead")

    if settings.crcs_rapid_diagnostic_payment_link.strip():
        log_event(
            session,
            actor="revenue_system",
            action="checkout_started",
            target=str(lead.id) if lead else email,
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
        client_reference_id=f"crcs-{lead.id if lead else 'public'}-{email}",
        extra_metadata={
            "crcs_sku": offer.sku,
            "crcs_lead_id": str(lead.id) if lead else "",
            "crcs_revenue_system": "v1",
        },
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


@router.get("/health")
def public_health(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    try:
        session.execute(select(func.count(Lead.id))).scalar_one()
        db_ok = True
    except Exception:
        db_ok = False

    recent_stripe = session.scalar(
        select(Event).where(Event.actor == "stripe").order_by(Event.ts.desc()).limit(1)
    )
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

    live_paid = [o for o in orders if o.status == "paid" and o.environment == "live"]
    test_paid = [o for o in orders if o.status == "paid" and o.environment == "test"]
    confirmed_revenue = sum((Decimal(o.total) for o in live_paid), Decimal(0))
    test_revenue = sum((Decimal(o.total) for o in test_paid), Decimal(0))

    pipeline = sum(
        (Decimal(l.expected_value_cad or 0) for l in leads
         if l.stage not in {"WON", "LOST", "CLOSED", "CUSTOMER_ACTIVE", "RETENTION_RISK"}),
        Decimal(0),
    )
    mrr = sum(
        (Decimal(l.monthly_recurring_value_cad or 0) for l in leads
         if l.stage in {"WON", "CUSTOMER_ACTIVE", "RETENTION_RISK", "EXPANSION_OPPORTUNITY"}),
        Decimal(0),
    )

    live_order_ids = {o.id for o in live_paid}
    cost_rows = [s for s in services if s.order_id in live_order_ids and s.delivery_cost_cad is not None]
    known_costs = sum((Decimal(s.delivery_cost_cad or 0) for s in cost_rows), Decimal(0))
    gross_margin = confirmed_revenue - known_costs if cost_rows else None

    won = sum(1 for l in leads if l.stage == "WON")
    lost = sum(1 for l in leads if l.stage == "LOST")
    close_rate = won / (won + lost) if won + lost else None
    due_actions = sum(
        1 for l in leads
        if l.next_action_at and l.next_action_at <= now and l.stage not in {"LOST", "CLOSED"}
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
        test_revenue_cad=float(test_revenue),
        pipeline_estimate_cad=float(pipeline),
        mrr_cad=float(mrr),
        gross_margin_cad=float(gross_margin) if gross_margin is not None else None,
        qualified_leads=sum(1 for l in leads if l.stage == "QUALIFIED"),
        new_leads=sum(1 for l in leads if l.created_at >= week),
        meetings_booked=sum(1 for a in activities if a.activity_type == "meeting_booked"),
        proposals=sum(
            1 for l in leads
            if l.stage in {"PROPOSAL_PENDING", "PROPOSAL_SENT", "NEGOTIATION", "WON"}
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
