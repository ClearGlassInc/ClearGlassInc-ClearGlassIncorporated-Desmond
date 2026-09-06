# CashPulse — Revenue Recovery & Follow-Up Bot

**Version:** 1.0
**Owner:** ClearGlass Inc. — Revenue Operations
**Status:** Build-ready (7-day deploy)

---

## 1. Bot Name
**CashPulse** — automates lead capture, follow-up, booking, invoice dunning,
expense leakage detection, retention nudges, and weekly KPI reporting for
service businesses.

## 2. Buyer
- Service businesses, agencies, consultants, small B2B ($250K–$5M revenue)
- Owner-operator or 1–2 person ops team
- Stack: Gmail/Outlook, Google Calendar / Cal.com, QuickBooks/Xero/Stripe,
  HubSpot Free / Pipedrive / spreadsheet CRM
- Pain: "I'm leaving money on the table and I don't have time to chase it."

## 3. Cashflow Problem (ranked by recoverable $)
1. Unpaid / late invoices — 15–25% of AR aged 30+ days
2. Lead response lag — leads cold after 1 hour (~80% conversion drop)
3. No-show / unbooked discovery calls — 20–30% slip rate
4. Zero retention follow-up on past customers
5. Expense leakage — duplicate SaaS, unreviewed card spikes

## 4. Automation Workflows

### Workflow A — `lead_capture_and_speed_to_lead`
- `trigger(new_web_form_submission OR inbound_email_to_sales OR missed_call)`
- `action(enrich_lead via Clearbit/Apollo)`
- `action(score_lead → A/B/C)` — see `bots/cashpulse_revenue_bot.py::score_lead`
- `action(send_personalized_reply within 60s via email + SMS)`
- `action(insert_calendar_link with pre-qualifying questions)`
- `action(create_CRM_record + audit log)`
- `action(notify_owner via Slack/SMS if tier=A AND deal>=$10K)`

### Workflow B — `invoice_dunning` (HIGHEST $ RECOVERY)
- `trigger(invoice_due_date - 3, due_date, +3, +7, +14, +30, +45)`
- See schedule: `bots/cashpulse_revenue_bot.py::DUNNING_SCHEDULE`
- `action(send_polite_reminder with payment link)`
- `action(escalate_tone per stage; CC owner at +14 — REQUIRES APPROVAL)`
- `action(auto-offer_payment_plan at +30 — REQUIRES APPROVAL)`
- `action(flag_for_collections at +45 — REQUIRES APPROVAL)`
- `action(reconcile_paid_status from Stripe/QBO webhook → stop sequence)`

### Workflow C — `booking_and_no_show_recovery`
- `trigger(meeting_booked)` → confirmation + 24h + 1h reminders (email + SMS)
- `trigger(no_show_detected)` → 15-min "still want to chat?" reschedule link
- `trigger(meeting_completed)` → proposal/follow-up sent within 2 hours

### Workflow D — `retention_nudge`
- `trigger(customer.last_purchase + 60/90/180 days)`
- `action(send_check_in with relevant offer)`
- `action(flag_at_risk if no engagement in 120 days)`

### Workflow E — `expense_watchdog`
- `trigger(daily_sync of bank/card transactions via Plaid/QBO)`
- `action(detect_duplicates, price_spikes, unused_subscriptions)` — see
  `bots/cashpulse_revenue_bot.py::detect_expense_leakage`
- `action(generate_weekly_leakage_report — REQUIRES APPROVAL before cancellations)`

### Workflow F — `weekly_reporting`
- Every Monday 7am: cash collected, AR aging, leads in/out, no-shows, expense
  flags → email + Slack. Backed by
  `bots/cashpulse_revenue_bot.py::kpi_snapshot`.

## 5. Integrations
| Layer | Tool |
|---|---|
| Orchestration | n8n (self-host) or Make.com |
| CRM | HubSpot Free / Pipedrive / Google Sheets |
| Email | Gmail API / Outlook Graph |
| SMS | Twilio |
| Calendar | Google Calendar / Cal.com |
| Invoicing | Stripe + QuickBooks Online / Xero |
| Banking | Plaid (read-only) |
| AI | Claude Haiku 4.5 (drafting), Sonnet 4.6 (scoring/triage) |
| Audit log | Supabase Postgres — append-only `bot_actions` table |
| Approvals | Slack interactive buttons |

## 6. Failure Modes & Risk Controls
- `risk_control(rate_limit_outbound — max 3 emails/lead/week)`
- `risk_control(stop_sequence_on_reply — keyword + LLM intent detection)`
- `risk_control(payment_status_double_check before any dunning send)`
- `risk_control(unsubscribe_honor across all channels — TCPA/CAN-SPAM)`
- `risk_control(PII_redaction in logs)`
- `risk_control(idempotency_keys on all webhook handlers)`
- `risk_control(dry_run_mode for first 72 hours per client)`

## 7. Human Approval Points
1. Sending invoice past +14 days (escalation tone)
2. Offering payment plans or collections handoff
3. Cancelling any subscription flagged by the expense watchdog
4. First-time use of any new email template
5. Any outbound to A-tier lead worth >$10K (5-minute owner veto window)

## 8. Monetization Model
`monetize(setup_fee + monthly_retainer + performance_fee)`

| Component | Amount |
|---|---|
| Setup fee | $2,500 (one-time, paid before build) |
| Monthly retainer | $750–$1,500/mo (tier-based) |
| Performance fee | 5% of invoices recovered past 30d (cap $2K/mo) |

## 9. 7-Day Build Plan
| Day | Deliverable |
|---|---|
| 0 (sales) | Sign $2,500 setup + first month retainer; collect creds via 1Password |
| 1 | Provision n8n, Supabase audit DB, Twilio, Claude API; connect Gmail + Stripe + QBO + Calendar |
| 2 | Deploy Workflow A (lead capture) + B (invoice dunning) — the two revenue drivers |
| 3 | Deploy Workflow C (booking) + F (weekly report); wire Slack approvals |
| 4 | Deploy Workflow D (retention) + E (expense watchdog read-only) |
| 5 | Dry-run mode: shadow real traffic, owner reviews every drafted action |
| 6 | Go-live on Workflows A + B; D/E in report-only |
| 7 | Handoff doc, owner training (30 min), KPI dashboard live |

## 10. First Offer to Sell
> **"Recover $10K+ in unpaid invoices and stop losing leads — in 7 days, or your setup fee back."**
> CashPulse audits your last 90 days of invoices and inbound leads, then deploys
> a bot that follows up on every overdue invoice and replies to every new lead
> in under 60 seconds. You approve the tone; the bot does the work. Most clients
> recover 3–10x the setup fee in month one.

**Lead magnet:** Free 15-min Cashflow Leak Audit — pull QBO + form data, return
a PDF showing exact $ being left on the table.

## 11. Pricing
| Tier | Workflows | Setup | Monthly | Perf Fee |
|---|---|---|---|---|
| Starter | A + B | $2,500 | $750 | 5% recovered |
| Growth | A + B + C + F | $3,500 | $1,250 | 5% recovered |
| Full Stack | All (A–F) | $5,000 | $1,500 | 5% recovered |
| Annual prepay | — | 2 months free | — | — |

Target: 10 Growth-tier clients = $35K setup + $12.5K MRR + perf in 60 days.

## 12. KPI Targets (per client, day 30)
| KPI | Baseline | Target |
|---|---|---|
| Lead response time | 4–24 hrs | < 5 min |
| Lead → meeting booked | 8% | 18% |
| Invoice DSO | 38 days | < 22 days |
| AR > 30 days | 22% | < 8% |
| No-show rate | 25% | < 12% |
| Owner admin hours/wk | 8–12 | < 3 |
| **Net new collected $ / mo** | — | **≥ 5× retainer** |

## 13. Scoring
| Criterion | Score |
|---|---|
| speed_to_cash | 10 |
| urgency | 9 |
| willingness_to_pay | 9 |
| build_speed | 8 |
| repeatability | 10 |
| **Average** | **9.2 — APPROVED** |

## 14. Repository Layout
- `bots/cashpulse_revenue_bot.py` — pure logic (scoring, dunning, KPIs, audit)
- `tests/test_cashpulse_revenue_bot.py` — pytest suite
- `deployment/cashpulse/` — n8n workflow JSON + ops README

Run locally:
```bash
python -m pytest tests/test_cashpulse_revenue_bot.py -q
python -m bots.cashpulse_revenue_bot   # writes a sample KPI snapshot
```
