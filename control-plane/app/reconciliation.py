"""Reconcile Stripe, PayPal and the ClearGlass ledger. Flags; never fixes.

Three records of the same money can disagree: the processor's, the ledger's
(``orders``, one row per settlement) and the ClearGlass order's
(``commercial_orders``). This module finds where they do and reports it. It
writes nothing: a discrepancy "fixed" by software is a discrepancy nobody
looked at, and the usual fix (refund the duplicate, re-send a lost webhook)
happens at the processor anyway.

Two levels of evidence, reported separately so neither is mistaken for the
other:

* **Ledger-internal checks** always run. They need only the database.
* **Processor comparison** runs only when processor records are supplied
  (an export or an API pull, normalized by :func:`normalize_provider_record`).
  Without them the report says ``NOT VERIFIED``; it never infers that the
  processor agrees.

The core (:func:`reconcile`) is stdlib-only and works on plain dicts, so it can
run on an export without a database. :func:`snapshot` builds those dicts from a
SQLAlchemy session.

    python -m app.reconciliation                         # ledger-internal checks
    python -m app.reconciliation --provider-export x.json  # plus processor comparison
    python -m app.reconciliation --json

Exit status is 2 when any critical or high finding exists, so it can gate a job.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SEVERITY_ORDER = ("critical", "high", "medium", "info")
SETTLED = frozenset({"paid", "refunded"})
MONEY_RECEIVED = frozenset({"PAID", "PARTIALLY_REFUNDED", "REFUNDED", "DISPUTED", "CHARGEBACK"})
OPEN_CHECKOUT = frozenset({"CHECKOUT_STARTED", "PAYMENT_PENDING"})
#: Audit actions that mean processor evidence could not be matched or trusted.
UNMATCHED_ACTIONS = frozenset({"refund_unmatched", "dispute_unmatched", "payment_for_unknown_order"})
REJECTED_ACTIONS = frozenset({"paypal_webhook_rejected"})
#: How long a checkout may sit open before it is worth a look.
STALE_CHECKOUT = timedelta(hours=24)
#: Cap on ids listed per informational finding, so a report stays readable.
LIST_CAP = 25


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def provider_for_source(source: str | None) -> str:
    value = (source or "").lower()
    if value.startswith("stripe"):
        return "stripe"
    if value.startswith("paypal"):
        return "paypal"
    return "other"


def _finding(code: str, severity: str, subject: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "subject": subject, "detail": detail, **extra}


# --- processor records ------------------------------------------------------------


def normalize_provider_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    """One processor payment in the shape :func:`reconcile` compares.

    Accepts the normalized shape directly::

        {"provider": "stripe" | "paypal", "reference": "pi_... | cs_... | <capture id>",
         "amount": "125.00", "currency": "CAD", "status": "paid" | "refunded" | ...,
         "amount_refunded": "0.00", "livemode": true, "order_ref": "CG-ORD-..."}

    or a raw Stripe Charge object (``"object": "charge"``), which it maps.
    """
    if raw.get("object") == "charge":
        refunded = _dec(raw.get("amount_refunded")) / 100
        amount = _dec(raw.get("amount")) / 100
        if raw.get("status") != "succeeded":
            status = "failed" if raw.get("status") == "failed" else "pending"
        elif raw.get("refunded"):
            status = "refunded"
        else:
            status = "paid"
        return {
            "provider": "stripe",
            "reference": str(raw.get("payment_intent") or raw.get("id") or ""),
            "amount": amount,
            "currency": str(raw.get("currency") or "").upper(),
            "status": status,
            "amount_refunded": refunded,
            "livemode": bool(raw.get("livemode")),
            "order_ref": (raw.get("metadata") or {}).get("cg_order_ref"),
            "disputed": bool(raw.get("disputed")),
        }
    return {
        "provider": str(raw.get("provider") or "").lower(),
        "reference": str(raw.get("reference") or ""),
        "amount": _dec(raw.get("amount")),
        "currency": str(raw.get("currency") or "").upper(),
        "status": str(raw.get("status") or "").lower(),
        "amount_refunded": _dec(raw.get("amount_refunded")),
        "livemode": bool(raw.get("livemode", True)),
        "order_ref": raw.get("order_ref"),
        "disputed": bool(raw.get("disputed")),
    }


def _ledger_keys(payment: Mapping[str, Any]) -> set[str]:
    """Every identifier a processor might use for this ledger row."""
    keys = set()
    ref = str(payment.get("external_ref") or "")
    if ref:
        keys.add(ref)
        if ref.startswith("paypal_capture_"):
            keys.add(ref[len("paypal_capture_"):])
    if payment.get("payment_intent"):
        keys.add(str(payment["payment_intent"]))
    return keys


def _compare_providers(
    payments: list[Mapping[str, Any]], records: list[dict[str, Any]], *, providers_covered: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    index: dict[str, Mapping[str, Any]] = {}
    for payment in payments:
        for key in _ledger_keys(payment):
            index[key] = payment
    matched: set[int] = set()

    for record in records:
        payment = index.get(record["reference"])
        subject = f"{record['provider']}:{record['reference']}"
        if payment is None:
            if record["status"] in {"paid", "refunded", "partially_refunded"}:
                findings.append(_finding(
                    "PROVIDER_PAYMENT_MISSING_FROM_LEDGER", "critical", subject,
                    f"{record['provider']} reports {record['amount']} {record['currency']} "
                    f"({record['status']}) that the ledger never booked. Check webhook delivery.",
                ))
            continue
        matched.add(int(payment["id"]))
        ledger_env = payment.get("environment")
        if ledger_env in {"live", "test"} and (ledger_env == "live") != record["livemode"]:
            findings.append(_finding(
                "PROVIDER_ENVIRONMENT_MISMATCH", "high", subject,
                f"processor livemode={record['livemode']}, ledger environment={ledger_env}",
            ))
        if record["currency"] and record["currency"] != str(payment.get("currency") or "").upper():
            findings.append(_finding(
                "PROVIDER_CURRENCY_MISMATCH", "high", subject,
                f"processor {record['currency']}, ledger {payment.get('currency')}",
            ))
        if record["amount"] != _dec(payment.get("total")):
            findings.append(_finding(
                "PROVIDER_AMOUNT_MISMATCH", "high", subject,
                f"processor {record['amount']}, ledger {payment.get('total')}",
            ))
        if record["amount_refunded"] != _dec(payment.get("amount_refunded")):
            findings.append(_finding(
                "PROVIDER_REFUND_MISMATCH", "high", subject,
                f"processor refunded {record['amount_refunded']}, ledger {payment.get('amount_refunded')}",
            ))
        ledger_settled = payment.get("status") in SETTLED
        provider_settled = record["status"] in {"paid", "refunded", "partially_refunded"}
        if ledger_settled != provider_settled:
            findings.append(_finding(
                "PROVIDER_STATUS_MISMATCH", "high", subject,
                f"processor status {record['status']}, ledger status {payment.get('status')}",
            ))
        if record["disputed"] and not payment.get("dispute_status"):
            findings.append(_finding(
                "PROVIDER_DISPUTE_MISSING_FROM_LEDGER", "high", subject,
                "processor shows a dispute the ledger has not recorded",
            ))

    for payment in payments:
        provider = provider_for_source(payment.get("source"))
        if (
            provider in providers_covered
            and payment.get("environment") == "live"
            and payment.get("status") in SETTLED
            and int(payment["id"]) not in matched
        ):
            findings.append(_finding(
                "LEDGER_PAYMENT_MISSING_AT_PROVIDER", "critical", f"payment:{payment['id']}",
                f"ledger books {payment.get('total')} {payment.get('currency')} as {payment.get('status')} "
                f"from {provider}, which the {provider} records supplied do not contain",
            ))
    return findings


# --- core -------------------------------------------------------------------------


def reconcile(
    snap: Mapping[str, Any],
    provider_records: Iterable[Mapping[str, Any]] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Every discrepancy between the ledger, ClearGlass orders and the processors."""
    now = now or datetime.now(UTC)
    payments: list[Mapping[str, Any]] = list(snap.get("payments", []))
    orders: list[Mapping[str, Any]] = list(snap.get("commercial_orders", []))
    services: list[Mapping[str, Any]] = list(snap.get("service_orders", []))
    events: list[Mapping[str, Any]] = list(snap.get("events", []))
    findings: list[dict[str, Any]] = []

    by_ref: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for payment in payments:
        if payment.get("order_ref"):
            by_ref[str(payment["order_ref"])].append(payment)
    payments_by_id = {int(p["id"]): p for p in payments}
    known_refs = {str(o["order_ref"]) for o in orders}

    for order in orders:
        ref = str(order["order_ref"])
        linked = by_ref.get(ref, [])
        settled = [p for p in linked if p.get("status") in SETTLED]
        state = order.get("payment_state")

        if len(settled) > 1:
            providers = sorted({provider_for_source(p.get("source")) for p in settled})
            findings.append(_finding(
                "DUPLICATE_PAYMENT", "critical" if any(p.get("environment") == "live" for p in settled) else "medium",
                ref,
                f"{len(settled)} settled payments ({', '.join(providers)}): "
                + ", ".join(f"#{p['id']} {p.get('total')} {p.get('currency')}" for p in settled)
                + ". Refund the duplicate at the processor; do not delete either row.",
                providers=providers,
            ))
        if state in MONEY_RECEIVED and not settled:
            findings.append(_finding(
                "ORDER_PAID_WITHOUT_PAYMENT", "critical", ref,
                f"order is {state} but no settled payment names it",
            ))
        if settled and state not in MONEY_RECEIVED:
            findings.append(_finding(
                "PAYMENT_NOT_APPLIED_TO_ORDER", "high", ref,
                f"a settled payment names this order but its state is {state}",
            ))
        primary = payments_by_id.get(int(order["payment_order_id"])) if order.get("payment_order_id") else None
        if primary is not None:
            if str(primary.get("currency") or "").upper() != str(order.get("currency") or "").upper():
                findings.append(_finding(
                    "CURRENCY_MISMATCH", "high", ref,
                    f"paid in {primary.get('currency')}, priced in {order.get('currency')}",
                ))
            elif _dec(primary.get("total")) < _dec(order.get("amount")):
                findings.append(_finding(
                    "AMOUNT_MISMATCH", "high", ref,
                    f"paid {primary.get('total')}, priced {order.get('amount')}",
                ))
            if order.get("environment") != primary.get("environment"):
                findings.append(_finding(
                    "ENVIRONMENT_MISMATCH", "medium", ref,
                    f"order environment {order.get('environment')}, payment {primary.get('environment')}",
                ))
        if order.get("reconciliation_required"):
            findings.append(_finding(
                "OPEN_RECONCILIATION_FLAG", "high", ref,
                str(order.get("reconciliation_reason") or "flagged without a recorded reason"),
            ))
        if (
            state == "PAID"
            and order.get("environment") == "live"
            and not order.get("reconciliation_required")
            and order.get("fulfillment_state") == "NOT_STARTED"
        ):
            findings.append(_finding(
                "PAID_WITHOUT_FULFILLMENT", "high", ref,
                "verified live payment with no fulfillment task",
            ))
        created = _ts(order.get("updated_at") or order.get("created_at"))
        if state in OPEN_CHECKOUT and created and now - created > STALE_CHECKOUT:
            findings.append(_finding(
                "STALE_CHECKOUT", "info", ref,
                f"{state} for {int((now - created).total_seconds() // 3600)}h with no processor settlement",
            ))

    for ref, linked in by_ref.items():
        if ref not in known_refs:
            findings.append(_finding(
                "UNKNOWN_ORDER_REF", "high", ref,
                f"payments {[p['id'] for p in linked]} name an order that does not exist",
            ))

    for service in services:
        payment = payments_by_id.get(int(service["order_id"])) if service.get("order_id") else None
        if payment is None or payment.get("status") not in SETTLED:
            findings.append(_finding(
                "FULFILLMENT_WITHOUT_PAYMENT", "critical", f"service_order:{service['id']}",
                f"delivery work exists for payment #{service.get('order_id')} "
                f"which is {payment.get('status') if payment else 'missing'}",
            ))

    unlinked = [
        p for p in payments
        if not p.get("order_ref") and p.get("status") in SETTLED and p.get("environment") == "live"
    ]
    if unlinked:
        findings.append(_finding(
            "UNLINKED_PAYMENT", "info", "ledger",
            f"{len(unlinked)} live payment(s) carry no ClearGlass order id (legacy checkout, "
            "Payment Link or Side Store); they count in revenue but cannot be traced to an offer order",
            payment_ids=[p["id"] for p in unlinked][:LIST_CAP],
        ))

    unmatched = [e for e in events if e.get("action") in UNMATCHED_ACTIONS]
    if unmatched:
        findings.append(_finding(
            "UNMATCHED_PROCESSOR_EVENT", "high", "events",
            f"{len(unmatched)} refund, dispute or payment event(s) matched no order",
            event_ids=[e["id"] for e in unmatched][:LIST_CAP],
        ))
    rejected = [e for e in events if e.get("action") in REJECTED_ACTIONS]
    if rejected:
        findings.append(_finding(
            "WEBHOOK_REJECTED", "medium", "events",
            f"{len(rejected)} webhook(s) failed signature verification: a misconfigured "
            "webhook id or forged posts",
            event_ids=[e["id"] for e in rejected][:LIST_CAP],
        ))

    records = [normalize_provider_record(r) for r in (provider_records or [])]
    if records:
        covered = {r["provider"] for r in records}
        findings.extend(_compare_providers(payments, records, providers_covered=covered))
        comparison: dict[str, Any] = {
            "status": "COMPARED",
            "providers": sorted(covered),
            "records": len(records),
        }
    else:
        comparison = {
            "status": "NOT VERIFIED",
            "reason": "no Stripe or PayPal records were supplied; the ledger was checked "
            "against itself only",
        }

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["code"], f["subject"]))
    summary = {level: sum(1 for f in findings if f["severity"] == level) for level in SEVERITY_ORDER}
    return {
        "generated_at": now.isoformat(),
        "ledger": {
            "payments": len(payments),
            "live_settled": sum(1 for p in payments if p.get("environment") == "live" and p.get("status") in SETTLED),
            "commercial_orders": len(orders),
            "service_orders": len(services),
        },
        "provider_comparison": comparison,
        "findings": findings,
        "summary": summary,
        "clean": summary["critical"] == 0 and summary["high"] == 0,
    }


# --- database adapter -----------------------------------------------------------


def snapshot(session: Any) -> dict[str, Any]:
    """Plain-dict copy of what :func:`reconcile` reads. Imports SQLAlchemy lazily."""
    from sqlalchemy import select

    from .commerce_orders import fulfillment_of
    from .models import CommercialOrder, Event, Order, ServiceOrder

    payments = [
        {
            "id": o.id, "source": o.source, "status": o.status, "total": o.total,
            "currency": o.currency, "environment": o.environment, "external_ref": o.external_ref,
            "payment_intent": o.payment_intent, "amount_refunded": o.amount_refunded,
            "dispute_status": o.dispute_status, "order_ref": o.order_ref,
            "created_at": o.created_at,
        }
        for o in session.scalars(select(Order)).all()
    ]
    orders = [
        {
            "order_ref": c.order_ref, "payment_state": c.payment_state, "amount": c.amount,
            "currency": c.currency, "environment": c.environment,
            "payment_order_id": c.payment_order_id,
            "reconciliation_required": c.reconciliation_required,
            "reconciliation_reason": c.reconciliation_reason,
            "fulfillment_state": fulfillment_of(session, c),
            "created_at": c.created_at, "updated_at": c.updated_at,
        }
        for c in session.scalars(select(CommercialOrder)).all()
    ]
    services = [
        {"id": s.id, "order_id": s.order_id, "status": s.status}
        for s in session.scalars(select(ServiceOrder)).all()
    ]
    events = [
        {"id": e.id, "action": e.action, "target": e.target, "ts": e.ts}
        for e in session.scalars(
            select(Event).where(Event.action.in_(sorted(UNMATCHED_ACTIONS | REJECTED_ACTIONS)))
        ).all()
    ]
    return {"payments": payments, "commercial_orders": orders, "service_orders": services, "events": events}


def _load_export(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, dict):
        # A Stripe list response ({"object": "list", "data": [...]}) or {"records": [...]}.
        document = document.get("data") or document.get("records") or []
    if not isinstance(document, list):
        raise ValueError("a provider export must be a list of records")
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.reconciliation", description=__doc__.split("\n")[0])
    parser.add_argument("--provider-export", type=Path, action="append", default=[],
                        help="JSON export of Stripe charges or normalized records; repeatable")
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = parser.parse_args(argv)

    from .db import SessionLocal

    records: list[dict[str, Any]] = []
    for path in args.provider_export:
        records.extend(_load_export(path))
    with SessionLocal() as session:
        report = reconcile(snapshot(session), records)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"# ClearGlass reconciliation ({report['generated_at']})\n")
        print(f"Processor comparison: {report['provider_comparison']['status']}")
        for key, value in report["ledger"].items():
            print(f"- {key}: {value}")
        print()
        for finding in report["findings"]:
            print(f"[{finding['severity'].upper()}] {finding['code']} {finding['subject']}: {finding['detail']}")
        if not report["findings"]:
            print("No discrepancies found in the records checked.")
    return 0 if report["clean"] else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
