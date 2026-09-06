# ClearGlassInc Artemis Operations Finance Bot

## 1. Executive summary
- Inventory operating cost is **$90,160.00 / month** with fully loaded unit cost of **$75.13**.
- Automated retention flows are expected to save **0.19** customers/month, worth **$778.64** in protected monthly revenue.
- Recommended standard management fee is **$3,104.31** per account/month (min break-even **$2,017.80**).

## 2. Assumptions
| Variable | Value |
|---|---:|
| Product/service type | Managed security hardware bundle |
| Units sold / month | 1200 |
| Unit purchase cost | $62.50 |
| Shipping + handling / unit | $7.80 |
| Storage cost / month | $2,800.00 |
| Shrinkage rate | 2.50% |
| Reorder threshold | 350 units |
| Customer count | 480 |
| Monthly churn rate | 3.80% |
| Open / click / conversion | 42.00% / 11.00% / 22.00% |
| Labor cost per hour | $95.00 |
| Account management hours | 18 |
| Target margin | 35.00% |

## 3. Inventory cost model
- **Total inventory cost** = (Unit Purchase × Units) + (Shipping × Units) + Shrinkage Cost + Carrying Cost
- **Cost per unit sold** = Total Inventory Cost / Units Sold
- **Carrying cost** = Storage + (Purchase Total × 1.5% capital carrying proxy)
- **Reorder cost** = Reorder Threshold × (Unit Purchase + Shipping)
- **Dead stock risk** = Purchase Total × (Shrinkage Rate / 2)
- **Gross margin after inventory expense** = (Revenue - Total Inventory Cost) / Revenue

| Output | Value |
|---|---:|
| Total inventory cost | $90,160.00 |
| Cost per unit sold | $75.13 |
| Carrying cost | $3,925.00 |
| Reorder cost | $24,605.00 |
| Dead stock risk | $937.50 |
| Gross margin after inventory expense | 30.53% |

## 4. Customer retention automation model
| Flow | Trigger | Timing | Purpose | Expected conversion impact | KPI |
|---|---|---|---|---:|---|
| Welcome | New customer created | Immediately + D+2 | Activate first value moment | 8-12% lower 30-day churn | Activation rate |
| Follow-up | No usage event | D+7 | Drive second purchase/use | +4-7% repeat activity | 7-day repeat rate |
| Inactive customer | No activity 30 days | D+30 + D+37 | Reactivation | 3-6% recovered accounts | Reactivation rate |
| Renewal reminder | 45 days before renewal | D-45, D-21, D-7 | Prevent passive churn | 10-18% better renewal | Renewal conversion |
| Win-back | Churn event recorded | D+3 + D+14 | Recover churned account | 6-10% win-back | Win-back rate |
| Upsell/cross-sell | Usage threshold met | Real-time | Expand account value | +5-9% ARPA | Expansion MRR |

Retention value model:
- Customers lost = Customer Count × Churn
- Customers saved = Lost × Open × Click × Retention Conversion
- Protected value = Customers saved × Revenue/account

## 5. Management fee model
| Tier | Monthly fee | Scope | Time requirement | Margin target | Included | Excluded |
|---|---:|---|---:|---:|---|---|
| Basic | $1,916.91 | Reporting + monthly review | 8h | 20% | KPI pack, monthly call | 24/7 support, custom analytics |
| Standard | $3,104.31 | Weekly optimization + retention ops | 18h | 35.00% | All basic + workflows + quarterly planning | Custom model training |
| Premium | $5,122.11 | Full-service command center | 35h | 42% | Standard + priority SLA + custom intelligence packs | Dedicated on-site staff |

Fee formulas:
- **Minimum fee** = (Labor Cost/hour × Hours) + Overhead
- **Recommended fee** = Minimum Fee / (1 - Target Margin)
- **Percentage fee** = Managed Revenue × Fee % (default 12%)

## 6. Example calculation using sample numbers
- Monthly churned customers = 18.24
- Monthly customers saved by automation = 0.19
- Monthly retention value protected = $778.64
- Recommended fee method: **max(flat recommended, % revenue fee)** => max($3,104.31, $504.00)

## 7. KPIs to monitor weekly
1. Fully loaded cost per unit
2. Inventory days on hand and reorder breach count
3. Shrinkage % and dead-stock exposure
4. Churn %, save rate, and win-back rate
5. Email open/click/conversion by segment
6. Gross margin after inventory
7. Fee realization vs target margin

## 8. Risks and adjustments
- If shrinkage > 3.5%, increase cycle counts, adjust reorder threshold upward, and tighten supplier QA.
- If open rates < 30%, refresh subject lines and segment cadence; test sender identity.
- If standard fee realization < target margin for 2 consecutive months, move accounts to percentage floor pricing.

## 9. Recommended next steps
1. Deploy this bot via GitHub Actions workflow dispatch with account-specific inputs.
2. Feed outputs into a spreadsheet/dashboard and compare planned vs actual each week.
3. Add CRM and billing data hooks to auto-recompute fees and retention forecasts nightly.
