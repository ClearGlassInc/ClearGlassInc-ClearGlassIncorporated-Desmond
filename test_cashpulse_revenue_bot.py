# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from bots.cashpulse_revenue_bot import (
    A_TIER_THRESHOLD,
    AuditEntry,
    Charge,
    DUNNING_SCHEDULE,
    Invoice,
    Lead,
    Meeting,
    booking_cadence,
    build_dunning_plan,
    d,
    detect_expense_leakage,
    kpi_snapshot,
    make_audit_entry,
    next_dunning_action,
    score_lead,
)


class LeadScoringTests(unittest.TestCase):
    def test_owner_with_budget_signal_is_A_tier(self) -> None:
        lead = Lead(
            email="jane@bigco.com",
            full_name="Jane Owner",
            company="BigCo",
            role="Founder / CEO",
            company_size=120,
            source="web_form",
            deal_size_estimate=d("15000"),
            signals=("explicit_budget", "timeline_under_30d"),
        )
        result = score_lead(lead)
        self.assertEqual(result.tier, "A")
        self.assertGreaterEqual(result.score, A_TIER_THRESHOLD)
        self.assertTrue(result.requires_owner_alert)

    def test_freemail_intern_is_C_tier(self) -> None:
        lead = Lead(
            email="kid@gmail.com",
            full_name="Junior",
            company="Self",
            role="Intern",
            company_size=1,
            source="web_form",
        )
        result = score_lead(lead)
        self.assertEqual(result.tier, "C")
        self.assertFalse(result.requires_owner_alert)

    def test_score_clamped_to_0_100(self) -> None:
        lead = Lead(
            email="ceo@enterprise.com",
            full_name="Big Boss",
            company="Enterprise",
            role="CEO Founder Owner",
            company_size=5000,
            source="referral",
            deal_size_estimate=d("250000"),
            signals=tuple(["explicit_budget", "rfp_mentioned",
                          "competitor_named", "timeline_under_30d"]),
        )
        result = score_lead(lead)
        self.assertLessEqual(result.score, 100)
        self.assertGreaterEqual(result.score, 0)


class DunningTests(unittest.TestCase):
    def test_paid_invoice_yields_no_plan(self) -> None:
        inv = Invoice("INV-1", "x@y.com", d("100"), date(2026, 1, 1),
                      date(2026, 1, 15), paid=True, paid_on=date(2026, 1, 14))
        self.assertEqual(build_dunning_plan(inv, today=date(2026, 1, 20)), ())

    def test_unsubscribed_invoice_yields_no_plan(self) -> None:
        inv = Invoice("INV-2", "x@y.com", d("100"), date(2026, 1, 1),
                      date(2026, 1, 15), unsubscribed=True)
        self.assertEqual(build_dunning_plan(inv, today=date(2026, 1, 1)), ())

    def test_plan_filters_past_steps(self) -> None:
        due = date(2026, 1, 15)
        inv = Invoice("INV-3", "x@y.com", d("100"), date(2026, 1, 1), due)
        # Today is 8 days past due; expect only the +14, +30, +45 future steps.
        plan = build_dunning_plan(inv, today=due + timedelta(days=8))
        stages = [step.stage for step in plan]
        self.assertEqual(stages, ["escalation_owner_cc",
                                  "payment_plan_offer", "collections_handoff"])
        self.assertTrue(all(step.send_on >= due + timedelta(days=8) for step in plan))

    def test_escalation_stages_require_approval(self) -> None:
        approval_required = {stage for offset, stage, tone, req in DUNNING_SCHEDULE if req}
        self.assertIn("escalation_owner_cc", approval_required)
        self.assertIn("payment_plan_offer", approval_required)
        self.assertIn("collections_handoff", approval_required)

    def test_next_dunning_action_fires_on_due_date(self) -> None:
        due = date(2026, 2, 1)
        inv = Invoice("INV-4", "x@y.com", d("100"), date(2026, 1, 1), due)
        step = next_dunning_action(inv, today=due)
        self.assertIsNotNone(step)
        assert step is not None  # for type checker
        self.assertEqual(step.stage, "due_today")
        self.assertFalse(step.requires_approval)


class BookingCadenceTests(unittest.TestCase):
    def test_unattended_meeting_schedules_no_show_recovery(self) -> None:
        starts = datetime(2026, 3, 1, 14, 0, tzinfo=timezone.utc)
        meeting = Meeting("M1", "x@y.com", starts, confirmed=True, attended=False)
        now = starts + timedelta(minutes=10)
        steps = booking_cadence(meeting, now=now)
        kinds = [s.kind for s in steps]
        self.assertIn("no_show_recovery", kinds)

    def test_post_meeting_followup_for_attended(self) -> None:
        starts = datetime(2026, 3, 1, 14, 0, tzinfo=timezone.utc)
        meeting = Meeting("M2", "x@y.com", starts, confirmed=True, attended=True)
        now = starts + timedelta(minutes=10)
        steps = booking_cadence(meeting, now=now)
        kinds = [s.kind for s in steps]
        self.assertIn("post_meeting", kinds)
        self.assertNotIn("no_show_recovery", kinds)


class ExpenseWatchdogTests(unittest.TestCase):
    def test_detects_duplicate_charge(self) -> None:
        charges = [
            Charge("c1", "Zoom", d("16.00"), date(2026, 4, 1)),
            Charge("c2", "Zoom", d("16.00"), date(2026, 4, 1)),
        ]
        flags = detect_expense_leakage(charges)
        self.assertTrue(any(f.kind == "duplicate_charge" for f in flags))

    def test_detects_price_spike(self) -> None:
        charges = [
            Charge("c1", "Adobe", d("50"), date(2026, 1, 5)),
            Charge("c2", "Adobe", d("50"), date(2026, 2, 5)),
            Charge("c3", "Adobe", d("50"), date(2026, 3, 5)),
            Charge("c4", "Adobe", d("200"), date(2026, 4, 5)),
        ]
        flags = detect_expense_leakage(charges)
        self.assertTrue(any(f.kind == "price_spike" for f in flags))

    def test_recurring_subscription_flagged(self) -> None:
        charges = [
            Charge("c1", "Notion", d("12"), date(2026, 1, 5)),
            Charge("c2", "Notion", d("12"), date(2026, 2, 5)),
            Charge("c3", "Notion", d("12"), date(2026, 3, 6)),
        ]
        flags = detect_expense_leakage(charges)
        self.assertTrue(any(f.kind == "recurring_subscription" for f in flags))


class KPISnapshotTests(unittest.TestCase):
    def test_kpi_aggregates_correctly(self) -> None:
        today = date(2026, 5, 1)
        start = today - timedelta(days=7)
        invoices = (
            Invoice("INV-A", "a@x.com", d("1000"), today - timedelta(days=20),
                    today - timedelta(days=5), paid=True,
                    paid_on=today - timedelta(days=2)),
            Invoice("INV-B", "b@x.com", d("2500"), today - timedelta(days=60),
                    today - timedelta(days=45), paid=False),
            Invoice("INV-C", "c@x.com", d("500"), today - timedelta(days=10),
                    today + timedelta(days=5), paid=False),
        )
        meetings = (
            Meeting("M1", "a@x.com",
                    datetime(2026, 4, 28, 12, tzinfo=timezone.utc), attended=True),
            Meeting("M2", "b@x.com",
                    datetime(2026, 4, 29, 12, tzinfo=timezone.utc), attended=False),
        )
        snapshot = kpi_snapshot(
            period_start=start, period_end=today,
            invoices=invoices,
            leads=(Lead("a@x.com", "A", "X", "Owner", 50, "form"),) * 5,
            leads_replied_under_5min=4,
            meetings=meetings,
            expense_flags=(),
        )
        self.assertEqual(snapshot.cash_collected, Decimal("1000"))
        self.assertEqual(snapshot.invoices_open_count, 2)
        self.assertEqual(snapshot.ar_over_30_days, Decimal("2500"))
        self.assertEqual(snapshot.no_show_count, 1)
        self.assertEqual(snapshot.meetings_booked, 2)
        self.assertEqual(snapshot.leads_in, 5)
        self.assertEqual(snapshot.speed_to_lead_pct, Decimal("4") / Decimal("5"))


class AuditLogTests(unittest.TestCase):
    def test_audit_entry_is_deterministic_for_same_payload(self) -> None:
        a = make_audit_entry(workflow="dunning", action="send_email",
                             target="INV-1", payload={"x": 1})
        b = make_audit_entry(workflow="dunning", action="send_email",
                             target="INV-1", payload={"x": 1})
        self.assertEqual(a.payload_hash, b.payload_hash)
        self.assertNotEqual(a.id, b.id)
        self.assertIsInstance(a, AuditEntry)


if __name__ == "__main__":
    unittest.main()
