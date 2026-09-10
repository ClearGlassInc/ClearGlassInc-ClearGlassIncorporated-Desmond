# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from bots import operations_finance_bot
from bots.operations_finance_bot import ModelInputs, calculate_outputs, d, money, pct


def _base_inputs(**overrides) -> ModelInputs:
    """Return default inputs with optional field overrides for targeted tests."""
    defaults = dict(
        product_type="Test product",
        units_sold_per_month=1200,
        unit_purchase_cost=d("62.5"),
        shipping_handling_per_unit=d("7.8"),
        storage_cost_per_month=d("2800"),
        shrinkage_rate=d("0.025"),
        reorder_threshold_units=350,
        customer_count=480,
        monthly_churn_rate=d("0.038"),
        email_open_rate=d("0.42"),
        email_click_rate=d("0.11"),
        retention_conversion_rate=d("0.22"),
        labor_cost_per_hour=d("95"),
        account_mgmt_hours_per_month=d("18"),
        target_profit_margin=d("0.35"),
        fee_preference="hybrid",
        service_revenue_per_account=d("4200"),
        overhead_rate=d("0.18"),
    )
    defaults.update(overrides)
    return ModelInputs(**defaults)


class OperationsFinanceBotTests(unittest.TestCase):

    # --- existing tests (preserved) ---

    def test_calculate_outputs_returns_positive_recommended_fee(self) -> None:
        inputs = operations_finance_bot.load_inputs()
        outputs = calculate_outputs(inputs)

        self.assertGreater(outputs.recommended_monthly_fee, outputs.min_monthly_fee)
        self.assertGreater(outputs.inventory_cost_total_month, 0)
        self.assertGreaterEqual(outputs.gross_margin_after_inventory, 0)

    def test_write_outputs_creates_archive_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "operations" / "output"
            archive_dir = output_dir / "archive"

            original_root = operations_finance_bot.ROOT
            original_output = operations_finance_bot.OUTPUT_DIR
            original_archive = operations_finance_bot.ARCHIVE_DIR
            try:
                operations_finance_bot.ROOT = root
                operations_finance_bot.OUTPUT_DIR = output_dir
                operations_finance_bot.ARCHIVE_DIR = archive_dir

                inputs = operations_finance_bot.load_inputs()
                outputs = calculate_outputs(inputs)

                operations_finance_bot.write_outputs(inputs, outputs)
                expected = archive_dir / f"{outputs.run_utc.replace('+00:00', 'Z').replace(':', '')}.md"
                self.assertTrue(expected.exists())
                self.assertTrue((output_dir / "latest.md").exists())
                self.assertTrue((output_dir / "latest.json").exists())
            finally:
                operations_finance_bot.ROOT = original_root
                operations_finance_bot.OUTPUT_DIR = original_output
                operations_finance_bot.ARCHIVE_DIR = original_archive

    # --- new edge-case and financial-integrity tests ---

    def test_inventory_cost_scales_linearly_with_units(self) -> None:
        """Doubling unit volume should roughly double inventory cost."""
        base = calculate_outputs(_base_inputs(units_sold_per_month=600))
        double = calculate_outputs(_base_inputs(units_sold_per_month=1200))
        ratio = double.inventory_cost_total_month / base.inventory_cost_total_month
        # Ratio should be close to 2; storage is fixed so it won't be exact.
        self.assertGreater(ratio, Decimal("1.8"))
        self.assertLess(ratio, Decimal("2.1"))

    def test_cost_per_unit_is_consistent_with_total(self) -> None:
        """cost_per_unit_sold × units_sold should equal inventory_cost_total."""
        inputs = _base_inputs()
        outputs = calculate_outputs(inputs)
        reconstructed = outputs.cost_per_unit_sold * inputs.units_sold_per_month
        diff = abs(reconstructed - outputs.inventory_cost_total_month)
        self.assertLess(diff, Decimal("0.01"))

    def test_recommended_fee_exceeds_min_fee_at_any_positive_margin(self) -> None:
        """Recommended fee must always be greater than the minimum break-even fee."""
        for margin in ("0.10", "0.25", "0.40", "0.50"):
            with self.subTest(margin=margin):
                inputs = _base_inputs(target_profit_margin=d(margin))
                outputs = calculate_outputs(inputs)
                self.assertGreater(
                    outputs.recommended_monthly_fee,
                    outputs.min_monthly_fee,
                    msg=f"recommended_fee <= min_fee at margin={margin}",
                )

    def test_zero_churn_produces_zero_customers_lost(self) -> None:
        inputs = _base_inputs(monthly_churn_rate=d("0"))
        outputs = calculate_outputs(inputs)
        self.assertEqual(outputs.customers_lost_month, Decimal("0"))
        self.assertEqual(outputs.customers_saved_month, Decimal("0"))
        self.assertEqual(outputs.retention_value_month, Decimal("0"))

    def test_full_churn_caps_at_customer_count(self) -> None:
        """At 100% churn all customers are lost; saved is bounded by open/click/conversion."""
        inputs = _base_inputs(monthly_churn_rate=d("1.0"), customer_count=100)
        outputs = calculate_outputs(inputs)
        self.assertEqual(outputs.customers_lost_month, Decimal("100"))
        # saved = 100 × open × click × conversion
        expected_saved = (
            d("100")
            * inputs.email_open_rate
            * inputs.email_click_rate
            * inputs.retention_conversion_rate
        )
        self.assertEqual(outputs.customers_saved_month, expected_saved)

    def test_higher_overhead_raises_min_fee(self) -> None:
        low = calculate_outputs(_base_inputs(overhead_rate=d("0.10")))
        high = calculate_outputs(_base_inputs(overhead_rate=d("0.30")))
        self.assertGreater(high.min_monthly_fee, low.min_monthly_fee)

    def test_fee_by_revenue_percentage_formula(self) -> None:
        """Fee-by-revenue percentage must equal service_revenue × 12%."""
        inputs = _base_inputs(service_revenue_per_account=d("5000"))
        outputs = calculate_outputs(inputs)
        expected = d("5000") * d("0.12")
        self.assertEqual(outputs.fee_by_revenue_percentage, expected)

    def test_json_output_is_valid_and_complete(self) -> None:
        """latest.json must be parseable and contain both inputs and outputs keys."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "operations" / "output"
            archive_dir = output_dir / "archive"

            original_root = operations_finance_bot.ROOT
            original_output = operations_finance_bot.OUTPUT_DIR
            original_archive = operations_finance_bot.ARCHIVE_DIR
            try:
                operations_finance_bot.ROOT = root
                operations_finance_bot.OUTPUT_DIR = output_dir
                operations_finance_bot.ARCHIVE_DIR = archive_dir

                inputs = _base_inputs()
                outputs = calculate_outputs(inputs)
                operations_finance_bot.write_outputs(inputs, outputs)

                payload = json.loads((output_dir / "latest.json").read_text())
                self.assertIn("inputs", payload)
                self.assertIn("outputs", payload)
                self.assertIn("run_utc", payload["outputs"])
                self.assertIn("recommended_monthly_fee", payload["outputs"])
            finally:
                operations_finance_bot.ROOT = original_root
                operations_finance_bot.OUTPUT_DIR = original_output
                operations_finance_bot.ARCHIVE_DIR = original_archive

    def test_markdown_output_contains_executive_summary_section(self) -> None:
        inputs = _base_inputs()
        outputs = calculate_outputs(inputs)
        md = operations_finance_bot.build_markdown(inputs, outputs)
        self.assertIn("## 1. Executive summary", md)
        self.assertIn("## 7. KPIs to monitor weekly", md)

    def test_money_formatter_handles_large_values(self) -> None:
        self.assertEqual(money(d("1000000")), "$1,000,000.00")
        self.assertEqual(money(d("0")), "$0.00")
        self.assertEqual(money(d("0.005")), "$0.01")  # rounds half-up

    def test_pct_formatter_precision(self) -> None:
        self.assertEqual(pct(d("0.035")), "3.50%")
        self.assertEqual(pct(d("1")), "100.00%")
        self.assertEqual(pct(d("0")), "0.00%")


if __name__ == "__main__":
    unittest.main()
