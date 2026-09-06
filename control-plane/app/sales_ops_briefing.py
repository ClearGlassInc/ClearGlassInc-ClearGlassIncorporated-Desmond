"""Morning sales-ops briefing — sourced from the commerce control plane (Stripe-backed).

Produces a brief, factual, action-oriented daily briefing from the same database the control
plane writes (orders, payouts, approvals, the audit ledger). It computes only what the commerce
source actually supports and **labels anything it cannot source** rather than inventing numbers.

Source coverage note (read this before trusting a section):
The source of truth is e-commerce/Stripe, not a deal-based CRM. So:
  * revenue / new orders / at-risk / data-quality  → computed directly from the DB.
  * "deals"                                         → mapped to orders (paid = won, pending = open).
  * "rep activity"                                  → no human reps exist in the commerce source;
                                                       mapped to operator/automation ledger activity
                                                       and labelled as such (never fabricated).

Runs stdlib-only apart from SQLAlchemy (already a control-plane dependency), so it executes inside
GitHub Actions. With ``DATABASE_URL`` set it reads live data; with none set it runs in **safe mode**
against an empty in-memory database and emits a clearly-marked "no live source" briefing — it never
prints fake figures. Email send (``--email``) uses Gmail SMTP and is skipped (not failed) when the
credentials are absent, matching the repo's mock-mode convention.

Usage:
    python -m app.sales_ops_briefing            # markdown to stdout
    python -m app.sales_ops_briefing --json     # machine-readable
    python -m app.sales_ops_briefing --email    # also email via Gmail SMTP (needs secrets)
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import smtplib
import ssl
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Approval, Base, Event, Order, Payout

# Order/payout status vocabulary actually written by the control plane (see routers/payments.py,
# routers/orders.py). Keep these in sync with the app if the status set changes.
REVENUE_STATUSES = ("paid",)
STALLED_STATUS = "pending"
ATRISK_ORDER_STATUS = "exception"
FAILED_PAYOUT_STATUS = "failed"
STALLED_AGE_HOURS = 24


# ─────────────────────────────────────────────────────────────────────────────
# Data model for the briefing
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Briefing:
    date: str
    generated_at: str
    live: bool                       # True when a real DATABASE_URL was connected
    currency: str = "CAD"
    yesterday_revenue: float = 0.0
    yesterday_orders: int = 0
    mtd_revenue: float = 0.0
    mtd_orders: int = 0
    days_elapsed: int = 0
    days_in_month: int = 0
    projected_month_end: float = 0.0     # run-rate projection from MTD pace
    last_month_total: float = 0.0        # for forecast movement context
    forecast_movement: float = 0.0       # projected EOM − last month total
    new_deals: list[dict] = field(default_factory=list)      # orders booked yesterday
    stalled_deals: list[dict] = field(default_factory=list)  # pending orders aging > 24h
    at_risk_deals: list[dict] = field(default_factory=list)  # exceptions / failed payouts / refunds
    rep_activity: list[dict] = field(default_factory=list)   # operator/automation ledger activity
    crm_issues: list[str] = field(default_factory=list)      # data-quality / gate backlog
    top_actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Computation (all figures come from the DB; nothing is invented)
# ─────────────────────────────────────────────────────────────────────────────
def _money(value: object) -> float:
    return round(float(value or 0), 2)


def compute_briefing(session: Session, now: datetime, *, live: bool) -> Briefing:
    today = now.date()
    yest_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=1)
    yest_end = yest_start + timedelta(days=1)
    month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day

    b = Briefing(
        date=today.isoformat(),
        generated_at=now.replace(microsecond=0).isoformat(),
        live=live,
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
    )

    def revenue_between(start: datetime, end: datetime | None) -> tuple[float, int]:
        q = select(func.coalesce(func.sum(Order.total), 0), func.count()).where(
            Order.status.in_(REVENUE_STATUSES), Order.created_at >= start
        )
        if end is not None:
            q = q.where(Order.created_at < end)
        total, count = session.execute(q).one()
        return _money(total), int(count or 0)

    # Yesterday + month-to-date revenue
    b.yesterday_revenue, b.yesterday_orders = revenue_between(yest_start, yest_end)
    b.mtd_revenue, b.mtd_orders = revenue_between(month_start, None)

    # Forecast movement: straight-line run-rate from MTD pace vs last month's actual.
    if days_elapsed > 0:
        b.projected_month_end = round(b.mtd_revenue / days_elapsed * days_in_month, 2)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = datetime(prev_month_end.year, prev_month_end.month, 1, tzinfo=timezone.utc)
    b.last_month_total, _ = revenue_between(prev_month_start, month_start)
    b.forecast_movement = round(b.projected_month_end - b.last_month_total, 2)

    # New deals → orders booked yesterday
    rows = session.execute(
        select(Order.id, Order.total, Order.source, Order.customer_id)
        .where(Order.status.in_(REVENUE_STATUSES), Order.created_at >= yest_start,
               Order.created_at < yest_end)
        .order_by(Order.total.desc())
        .limit(10)
    ).all()
    b.new_deals = [
        {"order": f"#{r.id}", "amount": _money(r.total), "source": r.source or "direct"}
        for r in rows
    ]

    # Stalled deals → pending orders older than the stall threshold
    stale_before = now - timedelta(hours=STALLED_AGE_HOURS)
    rows = session.execute(
        select(Order.id, Order.total, Order.created_at)
        .where(Order.status == STALLED_STATUS, Order.created_at < stale_before)
        .order_by(Order.created_at.asc())
        .limit(10)
    ).all()
    b.stalled_deals = [
        {"order": f"#{r.id}", "amount": _money(r.total),
         "age_h": int((now - _aware(r.created_at)).total_seconds() // 3600)}
        for r in rows
    ]

    # At-risk → order exceptions + failed payouts + pending refund approvals
    rows = session.execute(
        select(Order.id, Order.total)
        .where(Order.status == ATRISK_ORDER_STATUS).order_by(Order.total.desc()).limit(10)
    ).all()
    b.at_risk_deals = [{"order": f"#{r.id}", "amount": _money(r.total), "reason": "exception"}
                       for r in rows]
    failed_payouts = session.execute(
        select(Payout.stripe_payout_id, Payout.amount)
        .where(Payout.status == FAILED_PAYOUT_STATUS).limit(10)
    ).all()
    b.at_risk_deals += [
        {"order": p.stripe_payout_id, "amount": _money(p.amount), "reason": "payout failed"}
        for p in failed_payouts
    ]

    # Rep activity → operator/automation ledger activity yesterday (NOT human reps)
    rows = session.execute(
        select(Event.actor, func.count())
        .where(Event.ts >= yest_start, Event.ts < yest_end)
        .group_by(Event.actor).order_by(func.count().desc()).limit(10)
    ).all()
    b.rep_activity = [{"actor": actor, "actions": int(n)} for actor, n in rows]

    # CRM issues → data-quality + approval-gate backlog
    pending_approvals = session.scalar(
        select(func.count()).select_from(Approval).where(Approval.status == "pending")
    ) or 0
    orders_no_customer = session.scalar(
        select(func.count()).select_from(Order)
        .where(Order.status.in_(REVENUE_STATUSES), Order.customer_id.is_(None))
    ) or 0
    if pending_approvals:
        b.crm_issues.append(f"{pending_approvals} approval(s) pending in the governance gate")
    if orders_no_customer:
        b.crm_issues.append(f"{orders_no_customer} paid order(s) with no linked customer record")
    if failed_payouts:
        b.crm_issues.append(f"{len(failed_payouts)} payout(s) in failed state")

    b.top_actions = _derive_actions(b, pending_approvals)
    b.notes = _coverage_notes(b)
    return b


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as UTC for age math."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _derive_actions(b: Briefing, pending_approvals: int) -> list[str]:
    actions: list[str] = []
    if pending_approvals:
        actions.append(f"Clear the approval gate — {pending_approvals} item(s) blocking execution.")
    if b.at_risk_deals:
        amt = _money(sum(d["amount"] for d in b.at_risk_deals))
        actions.append(f"Resolve {len(b.at_risk_deals)} at-risk item(s) (${amt:,.2f} exposed).")
    if b.stalled_deals:
        amt = _money(sum(d["amount"] for d in b.stalled_deals))
        actions.append(f"Recover {len(b.stalled_deals)} stalled order(s) (${amt:,.2f}) — checkout/abandon follow-up.")
    if b.forecast_movement < 0:
        actions.append(
            f"Forecast is tracking ${abs(b.forecast_movement):,.2f} below last month — review demand/pricing levers (pricing changes stay gated).")
    if b.yesterday_orders == 0 and b.live:
        actions.append("No paid orders yesterday — verify checkout + payment webhook are healthy.")
    if not actions:
        actions.append("No exceptions detected — hold course and monitor conversion + AOV.")
    return actions[:5]


def _coverage_notes(b: Briefing) -> list[str]:
    notes = []
    if not b.live:
        notes.append(
            "⚠️ NO LIVE SOURCE: DATABASE_URL is not set, so all figures are zero/empty placeholders. "
            "Set the control-plane DATABASE_URL secret to populate real numbers. Nothing here is fabricated.")
    notes.append(
        "Source = commerce/Stripe (not a deal CRM): 'deals' = orders, and 'rep activity' = "
        "operator/automation ledger activity. Connect a CRM (HubSpot/Salesforce) for true "
        "rep-level pipeline.")
    return notes


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────
def _cur(b: Briefing, value: float) -> str:
    return f"${value:,.2f} {b.currency}"


def render_markdown(b: Briefing) -> str:
    arrow = "▲" if b.forecast_movement >= 0 else "▼"
    lines = [
        f"# Sales-Ops Briefing — {b.date}",
        f"_Generated {b.generated_at} · source: commerce/Stripe · {'LIVE' if b.live else 'NO LIVE SOURCE'}_",
        "",
        f"- **Yesterday revenue:** {_cur(b, b.yesterday_revenue)} across {b.yesterday_orders} order(s)",
        f"- **Month-to-date:** {_cur(b, b.mtd_revenue)} across {b.mtd_orders} order(s) "
        f"(day {b.days_elapsed}/{b.days_in_month})",
        f"- **Forecast movement:** projected month-end {_cur(b, b.projected_month_end)} "
        f"{arrow} {_cur(b, abs(b.forecast_movement))} vs last month ({_cur(b, b.last_month_total)})",
        "",
        f"## New deals (orders booked yesterday) — {len(b.new_deals)}",
        *([f"- {d['order']}: {_cur(b, d['amount'])} ({d['source']})" for d in b.new_deals]
          or ["- none"]),
        "",
        f"## Stalled deals (pending > {STALLED_AGE_HOURS}h) — {len(b.stalled_deals)}",
        *([f"- {d['order']}: {_cur(b, d['amount'])} — {d['age_h']}h old" for d in b.stalled_deals]
          or ["- none"]),
        "",
        f"## At-risk deals — {len(b.at_risk_deals)}",
        *([f"- {d['order']}: {_cur(b, d['amount'])} — {d['reason']}" for d in b.at_risk_deals]
          or ["- none"]),
        "",
        "## Rep activity (operator/automation ledger)",
        *([f"- {a['actor']}: {a['actions']} action(s)" for a in b.rep_activity] or ["- none"]),
        "",
        "## CRM / data-quality issues",
        *([f"- {i}" for i in b.crm_issues] or ["- none"]),
        "",
        "## Top 5 actions for today",
        *[f"{i}. {a}" for i, a in enumerate(b.top_actions, 1)],
        "",
        "---",
        *[f"_{n}_" for n in b.notes],
    ]
    return "\n".join(lines)


def render_text(b: Briefing) -> str:
    # Plain-text email body: strip the markdown bullets/headers lightly.
    return render_markdown(b).replace("**", "").replace("# ", "").replace("## ", "")


# ─────────────────────────────────────────────────────────────────────────────
# Delivery (Gmail SMTP) — skipped, not failed, when credentials are absent
# ─────────────────────────────────────────────────────────────────────────────
def send_email(subject: str, body_text: str, body_md: str) -> bool:
    user = os.environ.get("GMAIL_USER", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipients = os.environ.get("BRIEFING_TO", user)
    if not (user and app_password and recipients):
        print("email: GMAIL_USER / GMAIL_APP_PASSWORD / BRIEFING_TO not set — skipping send (safe mode).")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipients
    msg.set_content(body_text)
    msg.add_alternative(f"<pre style='font:14px/1.5 ui-monospace,monospace'>{body_md}</pre>",
                        subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(user, app_password)
        smtp.send_message(msg)
    print(f"email: sent to {recipients}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def _make_session() -> tuple[Session, bool]:
    """Return (session, live). Live when DATABASE_URL is set; else an empty in-memory DB."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        engine = create_engine(url, pool_pre_ping=True, future=True)
        return sessionmaker(bind=engine, future=True)(), True
    # Safe mode: empty schema, no fabricated data.
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)(), False


def main() -> int:
    parser = argparse.ArgumentParser(description="ClearGlass morning sales-ops briefing")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--email", action="store_true", help="email the briefing via Gmail SMTP")
    args = parser.parse_args()

    session, live = _make_session()
    try:
        briefing = compute_briefing(session, datetime.now(timezone.utc), live=live)
    finally:
        session.close()

    markdown = render_markdown(briefing)
    if args.json:
        print(json.dumps(asdict(briefing), indent=2, default=str))
    else:
        print(markdown)

    if args.email:
        subject = f"Sales-Ops Briefing — {briefing.date}"
        send_email(subject, render_text(briefing), markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
