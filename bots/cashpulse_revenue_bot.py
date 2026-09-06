# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""CashPulse — Revenue Recovery & Follow-Up Bot.

Deterministic core for the CashPulse automation product:
- Lead scoring (A/B/C tiering with reason codes)
- Invoice dunning schedule + tone escalation
- Booking/no-show recovery cadence
- Retention nudge cadence
- Expense leakage flagging
- KPI rollup for the weekly Monday report

The orchestration layer (n8n / Make.com) calls into these pure functions and
records every action in an append-only audit log. No network calls live here;
side-effectful adapters belong in the deployment layer.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output" / "cashpulse"

TWOPLACES = Decimal("0.01")


def d(value: str | float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> str:
    return f"${value.quantize(TWOPLACES, rounding=ROUND_HALF_UP):,.2f}"


# ---------------------------------------------------------------------------
# Lead scoring
# ---------------------------------------------------------------------------

A_TIER_THRESHOLD = 75
B_TIER_THRESHOLD = 50

ROLE_WEIGHTS = {
    "owner": 25, "ceo": 25, "founder": 25,
    "vp": 20, "director": 18, "head": 18,
    "manager": 12, "lead": 10,
    "analyst": 5, "intern": 0, "student": 0,
}

BUDGET_SIGNAL_WEIGHTS = {
    "explicit_budget": 30,
    "rfp_mentioned": 20,
    "competitor_named": 15,
    "timeline_under_30d": 20,
    "timeline_under_90d": 10,
}

DISQUALIFIERS = ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com")


@dataclass(frozen=True)
class Lead:
    email: str
    full_name: str
    company: str
    role: str
    company_size: int
    source: str
    message: str = ""
    deal_size_estimate: Decimal = field(default_factory=lambda: d(0))
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class LeadScore:
    lead_email: str
    score: int
    tier: str
    reasons: tuple[str, ...]
    requires_owner_alert: bool


def score_lead(lead: Lead) -> LeadScore:
    """Score 0-100. A: hot (owner alert if deal>$10k). B: warm. C: nurture."""
    score = 0
    reasons: list[str] = []

    role_key = (lead.role or "").lower().strip()
    role_points = 0
    for key, weight in ROLE_WEIGHTS.items():
        if key in role_key:
            role_points = max(role_points, weight)
    score += role_points
    if role_points:
        reasons.append(f"role:{role_key}:+{role_points}")

    if lead.company_size >= 200:
        score += 20
        reasons.append("size:200+:+20")
    elif lead.company_size >= 50:
        score += 12
        reasons.append("size:50-199:+12")
    elif lead.company_size >= 10:
        score += 6
        reasons.append("size:10-49:+6")

    domain = lead.email.split("@")[-1].lower() if "@" in lead.email else ""
    if domain and domain not in DISQUALIFIERS:
        score += 10
        reasons.append("business_email:+10")
    elif domain in DISQUALIFIERS:
        score -= 10
        reasons.append("freemail:-10")

    for signal in lead.signals:
        weight = BUDGET_SIGNAL_WEIGHTS.get(signal, 0)
        if weight:
            score += weight
            reasons.append(f"signal:{signal}:+{weight}")

    if lead.deal_size_estimate >= d(10000):
        score += 15
        reasons.append("deal>=10k:+15")
    elif lead.deal_size_estimate >= d(2500):
        score += 8
        reasons.append("deal>=2.5k:+8")

    score = max(0, min(100, score))

    if score >= A_TIER_THRESHOLD:
        tier = "A"
    elif score >= B_TIER_THRESHOLD:
        tier = "B"
    else:
        tier = "C"

    requires_owner_alert = tier == "A" and lead.deal_size_estimate >= d(10000)

    return LeadScore(
        lead_email=lead.email,
        score=score,
        tier=tier,
        reasons=tuple(reasons),
        requires_owner_alert=requires_owner_alert,
    )


# ---------------------------------------------------------------------------
# Invoice dunning
# ---------------------------------------------------------------------------

# Stage offsets in days from invoice due_date and the tone for each step.
DUNNING_SCHEDULE: tuple[tuple[int, str, str, bool], ...] = (
    # (offset_days, stage, tone, requires_approval)
    (-3, "pre_due_friendly", "friendly_heads_up", False),
    (0, "due_today", "polite_reminder", False),
    (3, "soft_followup", "polite_reminder", False),
    (7, "firm_followup", "firm_but_friendly", False),
    (14, "escalation_owner_cc", "firm_with_owner_cc", True),
    (30, "payment_plan_offer", "payment_plan_offer", True),
    (45, "collections_handoff", "final_notice", True),
)


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_email: str
    amount: Decimal
    issued_on: date
    due_on: date
    paid: bool = False
    paid_on: date | None = None
    last_response_on: date | None = None
    unsubscribed: bool = False


@dataclass(frozen=True)
class DunningStep:
    invoice_id: str
    send_on: date
    stage: str
    tone: str
    requires_approval: bool


def build_dunning_plan(invoice: Invoice, today: date | None = None) -> tuple[DunningStep, ...]:
    """Return the dunning steps still to execute for a single invoice."""
    if invoice.paid or invoice.unsubscribed:
        return ()
    today = today or date.today()
    plan: list[DunningStep] = []
    for offset, stage, tone, requires_approval in DUNNING_SCHEDULE:
        send_on = invoice.due_on + timedelta(days=offset)
        if send_on < today:
            continue
        plan.append(DunningStep(
            invoice_id=invoice.invoice_id,
            send_on=send_on,
            stage=stage,
            tone=tone,
            requires_approval=requires_approval,
        ))
    return tuple(plan)


def next_dunning_action(invoice: Invoice, today: date | None = None) -> DunningStep | None:
    """The single next step to fire today, or None."""
    today = today or date.today()
    for step in build_dunning_plan(invoice, today):
        if step.send_on == today:
            return step
        if step.send_on > today:
            return None
    return None


# ---------------------------------------------------------------------------
# Booking / no-show
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Meeting:
    meeting_id: str
    customer_email: str
    starts_at: datetime
    confirmed: bool = False
    attended: bool | None = None  # None until after the meeting


@dataclass(frozen=True)
class MeetingStep:
    meeting_id: str
    fire_at: datetime
    kind: str  # confirm | reminder_24h | reminder_1h | no_show_recovery | post_meeting


def booking_cadence(meeting: Meeting, now: datetime | None = None) -> tuple[MeetingStep, ...]:
    now = now or datetime.now(timezone.utc)
    plan: list[MeetingStep] = []
    starts = meeting.starts_at

    if not meeting.confirmed and starts > now:
        plan.append(MeetingStep(meeting.meeting_id, now, "confirm"))

    plan.append(MeetingStep(meeting.meeting_id, starts - timedelta(hours=24), "reminder_24h"))
    plan.append(MeetingStep(meeting.meeting_id, starts - timedelta(hours=1), "reminder_1h"))

    if meeting.attended is False:
        plan.append(MeetingStep(meeting.meeting_id, starts + timedelta(minutes=15), "no_show_recovery"))
    elif meeting.attended is True:
        plan.append(MeetingStep(meeting.meeting_id, starts + timedelta(hours=2), "post_meeting"))

    return tuple(step for step in plan if step.fire_at >= now - timedelta(minutes=5))


# ---------------------------------------------------------------------------
# Expense watchdog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Charge:
    charge_id: str
    vendor: str
    amount: Decimal
    posted_on: date
    category: str = ""


@dataclass(frozen=True)
class ExpenseFlag:
    kind: str
    vendor: str
    amount: Decimal
    note: str
    requires_approval: bool = True


def detect_expense_leakage(charges: Sequence[Charge]) -> tuple[ExpenseFlag, ...]:
    """Find duplicates, price spikes, and likely-unused subscriptions."""
    flags: list[ExpenseFlag] = []
    by_vendor: dict[str, list[Charge]] = {}
    for charge in charges:
        by_vendor.setdefault(charge.vendor.lower(), []).append(charge)

    for vendor, items in by_vendor.items():
        items_sorted = sorted(items, key=lambda c: c.posted_on)

        seen: dict[tuple[date, str], Charge] = {}
        for c in items_sorted:
            key = (c.posted_on, str(c.amount))
            if key in seen:
                flags.append(ExpenseFlag(
                    kind="duplicate_charge",
                    vendor=vendor,
                    amount=c.amount,
                    note=f"Duplicate charge of {money(c.amount)} on {c.posted_on}",
                ))
            else:
                seen[key] = c

        amounts = [c.amount for c in items_sorted]
        if len(amounts) >= 3:
            prior = sum(amounts[:-1], Decimal("0")) / d(len(amounts) - 1)
            latest = amounts[-1]
            if prior > 0 and latest >= prior * d("1.5"):
                flags.append(ExpenseFlag(
                    kind="price_spike",
                    vendor=vendor,
                    amount=latest,
                    note=f"Latest charge {money(latest)} > 1.5x prior avg {money(prior)}",
                ))

        if len(items_sorted) >= 2:
            gaps = [
                (items_sorted[i + 1].posted_on - items_sorted[i].posted_on).days
                for i in range(len(items_sorted) - 1)
            ]
            if gaps and all(25 <= g <= 35 for g in gaps):
                flags.append(ExpenseFlag(
                    kind="recurring_subscription",
                    vendor=vendor,
                    amount=amounts[-1],
                    note="Monthly recurring — confirm still in use",
                    requires_approval=True,
                ))

    return tuple(flags)


# ---------------------------------------------------------------------------
# KPI rollup
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KPISnapshot:
    period_start: date
    period_end: date
    cash_collected: Decimal
    invoices_open_count: int
    ar_total_open: Decimal
    ar_over_30_days: Decimal
    ar_aging_pct_over_30: Decimal
    leads_in: int
    leads_replied_under_5min: int
    speed_to_lead_pct: Decimal
    meetings_booked: int
    no_show_count: int
    no_show_rate: Decimal
    expense_flags_count: int
    estimated_leakage_flagged: Decimal


def kpi_snapshot(
    *,
    period_start: date,
    period_end: date,
    invoices: Sequence[Invoice],
    leads: Sequence[Lead],
    leads_replied_under_5min: int,
    meetings: Sequence[Meeting],
    expense_flags: Sequence[ExpenseFlag],
) -> KPISnapshot:
    cash_collected = sum(
        (inv.amount for inv in invoices
         if inv.paid and inv.paid_on and period_start <= inv.paid_on <= period_end),
        Decimal("0"),
    )
    open_invoices = [inv for inv in invoices if not inv.paid]
    ar_total_open = sum((inv.amount for inv in open_invoices), Decimal("0"))
    ar_over_30 = sum(
        (inv.amount for inv in open_invoices
         if (period_end - inv.due_on).days > 30),
        Decimal("0"),
    )
    ar_pct = (ar_over_30 / ar_total_open) if ar_total_open > 0 else d(0)

    leads_in = len(leads)
    speed_pct = (d(leads_replied_under_5min) / d(leads_in)) if leads_in else d(0)

    meetings_booked = len(meetings)
    no_shows = sum(1 for m in meetings if m.attended is False)
    no_show_rate = (d(no_shows) / d(meetings_booked)) if meetings_booked else d(0)

    leakage = sum((f.amount for f in expense_flags), Decimal("0"))

    return KPISnapshot(
        period_start=period_start,
        period_end=period_end,
        cash_collected=cash_collected,
        invoices_open_count=len(open_invoices),
        ar_total_open=ar_total_open,
        ar_over_30_days=ar_over_30,
        ar_aging_pct_over_30=ar_pct,
        leads_in=leads_in,
        leads_replied_under_5min=leads_replied_under_5min,
        speed_to_lead_pct=speed_pct,
        meetings_booked=meetings_booked,
        no_show_count=no_shows,
        no_show_rate=no_show_rate,
        expense_flags_count=len(expense_flags),
        estimated_leakage_flagged=leakage,
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuditEntry:
    id: str
    occurred_at: str
    actor: str
    workflow: str
    action: str
    target: str
    payload_hash: str
    requires_approval: bool
    approved_by: str | None = None


def make_audit_entry(
    *,
    workflow: str,
    action: str,
    target: str,
    payload: dict,
    actor: str = "cashpulse-bot",
    requires_approval: bool = False,
    approved_by: str | None = None,
) -> AuditEntry:
    import hashlib
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    payload_hash = hashlib.sha256(blob).hexdigest()
    return AuditEntry(
        id=str(uuid.uuid4()),
        occurred_at=datetime.now(timezone.utc).isoformat(),
        actor=actor,
        workflow=workflow,
        action=action,
        target=target,
        payload_hash=payload_hash,
        requires_approval=requires_approval,
        approved_by=approved_by,
    )


# ---------------------------------------------------------------------------
# CLI / report writer
# ---------------------------------------------------------------------------

def _serialize(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if hasattr(obj, "__dict__") or hasattr(obj, "_asdict"):
        return asdict(obj) if hasattr(obj, "__dataclass_fields__") else str(obj)
    return str(obj)


def write_report(snapshot: KPISnapshot, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = snapshot.period_end.isoformat()
    path = out_dir / f"cashpulse_kpi_{stamp}.json"
    path.write_text(json.dumps(asdict(snapshot), default=_serialize, indent=2))
    return path


def main() -> None:
    today = date.today()
    period_start = today - timedelta(days=7)
    sample_invoices = (
        Invoice("INV-1001", "ar@acme.test", d("4500"), today - timedelta(days=20),
                today - timedelta(days=5), paid=False),
        Invoice("INV-1002", "ar@globex.test", d("12500"), today - timedelta(days=60),
                today - timedelta(days=40), paid=False),
        Invoice("INV-1003", "ar@initech.test", d("3200"), today - timedelta(days=15),
                today - timedelta(days=1), paid=True, paid_on=today - timedelta(days=2)),
    )
    snapshot = kpi_snapshot(
        period_start=period_start,
        period_end=today,
        invoices=sample_invoices,
        leads=(),
        leads_replied_under_5min=0,
        meetings=(),
        expense_flags=(),
    )
    path = write_report(snapshot)
    print(f"CashPulse KPI snapshot written: {path}")


if __name__ == "__main__":
    main()
