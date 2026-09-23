"""Core CRCS qualification, CRM handoff, and paid-service provisioning logic."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import log_event
from .models import Customer, Lead, LeadActivity, Order, ServiceOrder

STAGES = {
    "NEW", "REVIEW_REQUIRED", "QUALIFIED", "NURTURE", "BOOKED",
    "DISCOVERY_COMPLETE", "PROPOSAL_PENDING", "PROPOSAL_SENT", "NEGOTIATION",
    "WON", "LOST", "CUSTOMER_ACTIVE", "RETENTION_RISK", "EXPANSION_OPPORTUNITY", "CLOSED",
}


def score_qualification(data: dict[str, Any]) -> tuple[int, str]:
    """Explainable fit routing using only explicit commercial inputs.

    This is prioritization, not an eligibility decision. No lead is rejected by the score.
    """
    score = 0
    reasons: list[str] = []
    if data.get("website"):
        score += 15
        reasons.append("digital property supplied")
    if data.get("desired_timeline") in {"0-7 days", "8-30 days"}:
        score += 25
        reasons.append("near-term timeline")
    elif data.get("desired_timeline"):
        score += 10
        reasons.append("timeline supplied")
    if data.get("investment_range") in {"CAD $125-$500", "CAD $500-$2,500", "CAD $2,500+"}:
        score += 20
        reasons.append("investment range supplied")
    if str(data.get("primary_goal", "")).strip():
        score += 15
        reasons.append("goal supplied")
    if str(data.get("current_challenge", "")).strip():
        score += 15
        reasons.append("challenge supplied")
    if data.get("service_interest"):
        score += 10
        reasons.append("service interest supplied")
    score = min(100, score)
    explanation = "; ".join(reasons) if reasons else "insufficient commercial context; manual review"
    return score, explanation


def create_lead(session: Session, data: dict[str, Any]) -> Lead:
    if data.get("website_honeypot"):
        raise ValueError("spam challenge failed")
    email = str(data["work_email"]).strip().lower()
    score, explanation = score_qualification(data)
    stage = "QUALIFIED" if score >= 60 else "REVIEW_REQUIRED"
    lead = Lead(
        full_name=str(data["full_name"]).strip(),
        email=email,
        company=str(data["company"]).strip() if data.get("company") else None,
        website=str(data["website"]).strip() if data.get("website") else None,
        role=str(data["role"]).strip() if data.get("role") else None,
        service_interest=str(data["service_interest"]).strip(),
        primary_goal=str(data.get("primary_goal", "")).strip(),
        current_challenge=str(data.get("current_challenge", "")).strip(),
        business_context=str(data.get("business_context", "")).strip(),
        desired_timeline=data.get("desired_timeline"),
        investment_range=data.get("investment_range"),
        notes=str(data.get("notes", "")).strip(),
        source=str(data.get("source") or "direct").strip()[:120],
        landing_page=data.get("landing_page"),
        referrer=data.get("referrer"),
        utm_first_source=data.get("utm_first_source"),
        utm_first_medium=data.get("utm_first_medium"),
        utm_first_campaign=data.get("utm_first_campaign"),
        utm_last_source=data.get("utm_last_source"),
        utm_last_medium=data.get("utm_last_medium"),
        utm_last_campaign=data.get("utm_last_campaign"),
        consent_marketing=bool(data.get("consent_marketing", False)),
        stage=stage,
        owner="unassigned",
        next_action="Review and choose the next commercial action",
        next_action_at=datetime.now(UTC),
        lead_score=score,
        score_explanation=explanation,
    )
    session.add(lead)
    session.flush()
    session.add(LeadActivity(
        lead_id=lead.id,
        activity_type="qualification_submitted",
        actor="public_form",
        detail=f"Stage={stage}; score={score}; source={lead.source}",
    ))
    log_event(
        session,
        actor="public_form",
        action="lead_created",
        target=str(lead.id),
        payload={"source": lead.source, "service_interest": lead.service_interest, "score": score},
        result="executed",
    )
    return lead


def upsert_customer_for_order(session: Session, order: Order, email: str | None) -> Customer | None:
    if not email:
        return None
    normalized = email.strip().lower()
    customer = session.scalar(select(Customer).where(Customer.email == normalized))
    if customer is None:
        customer = Customer(email=normalized, consent_marketing=False)
        session.add(customer)
        session.flush()
    order.customer_id = customer.id
    session.flush()
    return customer


def provision_paid_service(
    session: Session,
    order: Order,
    *,
    sku: str | None,
    lead_id: int | None,
) -> ServiceOrder | None:
    if not sku:
        log_event(
            session,
            actor="revenue_system",
            action="payment_needs_offer_reconciliation",
            target=str(order.id),
            payload={"external_ref": order.external_ref, "environment": order.environment},
            result="flagged",
        )
        return None

    existing = session.scalar(select(ServiceOrder).where(ServiceOrder.order_id == order.id))
    if existing is not None:
        return existing

    service = ServiceOrder(
        order_id=order.id,
        lead_id=lead_id,
        sku=sku,
        status="INTAKE_REQUIRED",
        scope_status="AWAITING_SCOPE_CONFIRMATION",
        customer_next_step="Complete the secure intake and confirm scope.",
        internal_checklist=[
            "Confirm scope",
            "Review intake",
            "Document findings",
            "Deliver prioritized plan",
            "Confirm delivery",
        ],
    )
    session.add(service)
    if lead_id:
        lead = session.get(Lead, lead_id)
        if lead:
            lead.stage = "CUSTOMER_ACTIVE"
            lead.next_action = "Start paid-service intake"
            session.add(LeadActivity(
                lead_id=lead.id,
                activity_type="payment_verified",
                actor="stripe",
                detail=f"Paid order {order.id} verified for {sku}",
            ))
    session.flush()
    log_event(
        session,
        actor="revenue_system",
        action="service_order_provisioned",
        target=str(service.id),
        payload={"order_id": order.id, "sku": sku},
        result="executed",
    )
    return service


def confirm_delivery(session: Session, service: ServiceOrder) -> None:
    service.status = "DELIVERED"
    service.delivery_confirmed_at = datetime.now(UTC)
    service.testimonial_eligible = True
    service.follow_up_at = datetime.now(UTC)
    if service.lead_id:
        lead = session.get(Lead, service.lead_id)
        if lead:
            lead.stage = "EXPANSION_OPPORTUNITY"
            lead.next_action = "Review follow-up, testimonial, referral, or next scoped service"
            session.add(LeadActivity(
                lead_id=lead.id,
                activity_type="delivery_confirmed",
                actor="admin",
                detail="Customer-confirmed delivery recorded; testimonial/referral request may now be drafted.",
            ))
    log_event(
        session,
        actor="admin",
        action="delivery_confirmed",
        target=str(service.id),
        payload={"order_id": service.order_id},
        result="executed",
    )
