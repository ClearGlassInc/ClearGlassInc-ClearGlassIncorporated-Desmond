# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive"

TWOPLACES = Decimal("0.01")


def d(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> str:
    return f"${value.quantize(TWOPLACES, rounding=ROUND_HALF_UP):,.2f}"


def pct(value: Decimal) -> str:
    return f"{(value * d(100)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)}%"


@dataclass(frozen=True)
class ModelInputs:
    product_type: str
    units_sold_per_month: int
    unit_purchase_cost: Decimal
    shipping_handling_per_unit: Decimal
    storage_cost_per_month: Decimal
    shrinkage_rate: Decimal
    reorder_threshold_units: int
    customer_count: int
    monthly_churn_rate: Decimal
    email_open_rate: Decimal
    email_click_rate: Decimal
    retention_conversion_rate: Decimal
    labor_cost_per_hour: Decimal
    account_mgmt_hours_per_month: Decimal
    target_profit_margin: Decimal
    fee_preference: str
    service_revenue_per_account: Decimal
    overhead_rate: Decimal


@dataclass(frozen=True)
class ModelOutputs:
    run_utc: str
    inventory_cost_total_month: Decimal
    cost_per_unit_sold: Decimal
    carrying_cost_month: Decimal
    reorder_cost: Decimal
    dead_stock_risk_cost: Decimal
    gross_margin_after_inventory: Decimal
    customers_lost_month: Decimal
    customers_saved_month: Decimal
    retention_value_month: Decimal
    min_monthly_fee: Decimal
    recommended_monthly_fee: Decimal
    fee_by_revenue_percentage: Decimal


def load_inputs() -> ModelInputs:
    return ModelInputs(
        product_type=os.getenv("PRODUCT_TYPE", "Managed security hardware bundle"),
        units_sold_per_month=int(os.getenv("UNITS_SOLD_PER_MONTH", "1200")),
        unit_purchase_cost=d(os.getenv("UNIT_PURCHASE_COST", "62.5")),
        shipping_handling_per_unit=d(os.getenv("SHIPPING_HANDLING_PER_UNIT", "7.8")),
        storage_cost_per_month=d(os.getenv("STORAGE_COST_PER_MONTH", "2800")),
        shrinkage_rate=d(os.getenv("SHRINKAGE_RATE", "0.025")),
        reorder_threshold_units=int(os.getenv("REORDER_THRESHOLD_UNITS", "350")),
        customer_count=int(os.getenv("CUSTOMER_COUNT", "480")),
        monthly_churn_rate=d(os.getenv("MONTHLY_CHURN_RATE", "0.038")),
        email_open_rate=d(os.getenv("EMAIL_OPEN_RATE", "0.42")),
        email_click_rate=d(os.getenv("EMAIL_CLICK_RATE", "0.11")),
        retention_conversion_rate=d(os.getenv("RETENTION_CONVERSION_RATE", "0.22")),
        labor_cost_per_hour=d(os.getenv("LABOR_COST_PER_HOUR", "95")),
        account_mgmt_hours_per_month=d(os.getenv("ACCOUNT_MGMT_HOURS_PER_MONTH", "18")),
        target_profit_margin=d(os.getenv("TARGET_PROFIT_MARGIN", "0.35")),
        fee_preference=os.getenv("FEE_PREFERENCE", "hybrid"),
        service_revenue_per_account=d(os.getenv("SERVICE_REVENUE_PER_ACCOUNT", "4200")),
        overhead_rate=d(os.getenv("OVERHEAD_RATE", "0.18")),
    )


def calculate_outputs(inputs: ModelInputs) -> ModelOutputs:
    purchase_total = inputs.unit_purchase_cost * inputs.units_sold_per_month
    shipping_total = inputs.shipping_handling_per_unit * inputs.units_sold_per_month
    shrinkage_cost = purchase_total * inputs.shrinkage_rate
    carrying_cost = inputs.storage_cost_per_month + (purchase_total * d("0.015"))
    inventory_total = purchase_total + shipping_total + shrinkage_cost + carrying_cost

    reorder_cost = inputs.reorder_threshold_units * (inputs.unit_purchase_cost + inputs.shipping_handling_per_unit)
    dead_stock_risk = purchase_total * (inputs.shrinkage_rate / d(2))

    sales_price_per_unit = (inputs.unit_purchase_cost + inputs.shipping_handling_per_unit) / (d(1) - inputs.target_profit_margin)
    revenue_month = sales_price_per_unit * inputs.units_sold_per_month
    gross_margin_after_inventory = (revenue_month - inventory_total) / revenue_month

    customers_lost = d(inputs.customer_count) * inputs.monthly_churn_rate
    customers_saved = customers_lost * inputs.email_open_rate * inputs.email_click_rate * inputs.retention_conversion_rate
    retention_value = customers_saved * inputs.service_revenue_per_account

    labor_cost_month = inputs.labor_cost_per_hour * inputs.account_mgmt_hours_per_month
    overhead_month = labor_cost_month * inputs.overhead_rate
    min_fee = labor_cost_month + overhead_month
    recommended_fee = min_fee / (d(1) - inputs.target_profit_margin)
    fee_by_revenue_pct = inputs.service_revenue_per_account * d("0.12")

    return ModelOutputs(
        run_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        inventory_cost_total_month=inventory_total,
        cost_per_unit_sold=inventory_total / inputs.units_sold_per_month,
        carrying_cost_month=carrying_cost,
        reorder_cost=reorder_cost,
        dead_stock_risk_cost=dead_stock_risk,
        gross_margin_after_inventory=gross_margin_after_inventory,
        customers_lost_month=customers_lost,
        customers_saved_month=customers_saved,
        retention_value_month=retention_value,
        min_monthly_fee=min_fee,
        recommended_monthly_fee=recommended_fee,
        fee_by_revenue_percentage=fee_by_revenue_pct,
    )


def build_markdown(inputs: ModelInputs, outputs: ModelOutputs) -> str:
    return f"""# ClearGlassInc Artemis Operations Finance Bot\n\n## 1. Executive summary\n- Inventory operating cost is **{money(outputs.inventory_cost_total_month)} / month** with fully loaded unit cost of **{money(outputs.cost_per_unit_sold)}**.\n- Automated retention flows are expected to save **{outputs.customers_saved_month.quantize(TWOPLACES)}** customers/month, worth **{money(outputs.retention_value_month)}** in protected monthly revenue.\n- Recommended standard management fee is **{money(outputs.recommended_monthly_fee)}** per account/month (min break-even **{money(outputs.min_monthly_fee)}**).\n\n## 2. Assumptions\n| Variable | Value |\n|---|---:|\n| Product/service type | {inputs.product_type} |\n| Units sold / month | {inputs.units_sold_per_month} |\n| Unit purchase cost | {money(inputs.unit_purchase_cost)} |\n| Shipping + handling / unit | {money(inputs.shipping_handling_per_unit)} |\n| Storage cost / month | {money(inputs.storage_cost_per_month)} |\n| Shrinkage rate | {pct(inputs.shrinkage_rate)} |\n| Reorder threshold | {inputs.reorder_threshold_units} units |\n| Customer count | {inputs.customer_count} |\n| Monthly churn rate | {pct(inputs.monthly_churn_rate)} |\n| Open / click / conversion | {pct(inputs.email_open_rate)} / {pct(inputs.email_click_rate)} / {pct(inputs.retention_conversion_rate)} |\n| Labor cost per hour | {money(inputs.labor_cost_per_hour)} |\n| Account management hours | {inputs.account_mgmt_hours_per_month} |\n| Target margin | {pct(inputs.target_profit_margin)} |\n\n## 3. Inventory cost model\n- **Total inventory cost** = (Unit Purchase × Units) + (Shipping × Units) + Shrinkage Cost + Carrying Cost\n- **Cost per unit sold** = Total Inventory Cost / Units Sold\n- **Carrying cost** = Storage + (Purchase Total × 1.5% capital carrying proxy)\n- **Reorder cost** = Reorder Threshold × (Unit Purchase + Shipping)\n- **Dead stock risk** = Purchase Total × (Shrinkage Rate / 2)\n- **Gross margin after inventory expense** = (Revenue - Total Inventory Cost) / Revenue\n\n| Output | Value |\n|---|---:|\n| Total inventory cost | {money(outputs.inventory_cost_total_month)} |\n| Cost per unit sold | {money(outputs.cost_per_unit_sold)} |\n| Carrying cost | {money(outputs.carrying_cost_month)} |\n| Reorder cost | {money(outputs.reorder_cost)} |\n| Dead stock risk | {money(outputs.dead_stock_risk_cost)} |\n| Gross margin after inventory expense | {pct(outputs.gross_margin_after_inventory)} |\n\n## 4. Customer retention automation model\n| Flow | Trigger | Timing | Purpose | Expected conversion impact | KPI |\n|---|---|---|---|---:|---|\n| Welcome | New customer created | Immediately + D+2 | Activate first value moment | 8-12% lower 30-day churn | Activation rate |\n| Follow-up | No usage event | D+7 | Drive second purchase/use | +4-7% repeat activity | 7-day repeat rate |\n| Inactive customer | No activity 30 days | D+30 + D+37 | Reactivation | 3-6% recovered accounts | Reactivation rate |\n| Renewal reminder | 45 days before renewal | D-45, D-21, D-7 | Prevent passive churn | 10-18% better renewal | Renewal conversion |\n| Win-back | Churn event recorded | D+3 + D+14 | Recover churned account | 6-10% win-back | Win-back rate |\n| Upsell/cross-sell | Usage threshold met | Real-time | Expand account value | +5-9% ARPA | Expansion MRR |\n\nRetention value model:\n- Customers lost = Customer Count × Churn\n- Customers saved = Lost × Open × Click × Retention Conversion\n- Protected value = Customers saved × Revenue/account\n\n## 5. Management fee model\n| Tier | Monthly fee | Scope | Time requirement | Margin target | Included | Excluded |\n|---|---:|---|---:|---:|---|---|\n| Basic | {money(outputs.min_monthly_fee * d('0.95'))} | Reporting + monthly review | 8h | 20% | KPI pack, monthly call | 24/7 support, custom analytics |\n| Standard | {money(outputs.recommended_monthly_fee)} | Weekly optimization + retention ops | 18h | {pct(inputs.target_profit_margin)} | All basic + workflows + quarterly planning | Custom model training |\n| Premium | {money(outputs.recommended_monthly_fee * d('1.65'))} | Full-service command center | 35h | 42% | Standard + priority SLA + custom intelligence packs | Dedicated on-site staff |\n\nFee formulas:\n- **Minimum fee** = (Labor Cost/hour × Hours) + Overhead\n- **Recommended fee** = Minimum Fee / (1 - Target Margin)\n- **Percentage fee** = Managed Revenue × Fee % (default 12%)\n\n## 6. Example calculation using sample numbers\n- Monthly churned customers = {outputs.customers_lost_month.quantize(TWOPLACES)}\n- Monthly customers saved by automation = {outputs.customers_saved_month.quantize(TWOPLACES)}\n- Monthly retention value protected = {money(outputs.retention_value_month)}\n- Recommended fee method: **max(flat recommended, % revenue fee)** => max({money(outputs.recommended_monthly_fee)}, {money(outputs.fee_by_revenue_percentage)})\n\n## 7. KPIs to monitor weekly\n1. Fully loaded cost per unit\n2. Inventory days on hand and reorder breach count\n3. Shrinkage % and dead-stock exposure\n4. Churn %, save rate, and win-back rate\n5. Email open/click/conversion by segment\n6. Gross margin after inventory\n7. Fee realization vs target margin\n\n## 8. Risks and adjustments\n- If shrinkage > 3.5%, increase cycle counts, adjust reorder threshold upward, and tighten supplier QA.\n- If open rates < 30%, refresh subject lines and segment cadence; test sender identity.\n- If standard fee realization < target margin for 2 consecutive months, move accounts to percentage floor pricing.\n\n## 9. Recommended next steps\n1. Deploy this bot via GitHub Actions workflow dispatch with account-specific inputs.\n2. Feed outputs into a spreadsheet/dashboard and compare planned vs actual each week.\n3. Add CRM and billing data hooks to auto-recompute fees and retention forecasts nightly.\n"""


def write_outputs(inputs: ModelInputs, outputs: ModelOutputs) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    latest_md = OUTPUT_DIR / "latest.md"
    latest_json = OUTPUT_DIR / "latest.json"
    archive_stamp = outputs.run_utc.replace("+00:00", "Z").replace(":", "")
    archive_md = ARCHIVE_DIR / f"{archive_stamp}.md"

    payload = {
        "inputs": {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(inputs).items()},
        "outputs": {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(outputs).items()},
    }

    markdown = build_markdown(inputs, outputs)
    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    archive_md.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    model_inputs = load_inputs()
    model_outputs = calculate_outputs(model_inputs)
    write_outputs(model_inputs, model_outputs)
    print("Operations finance output generated.")
    print(f"Output directory: {OUTPUT_DIR}")
