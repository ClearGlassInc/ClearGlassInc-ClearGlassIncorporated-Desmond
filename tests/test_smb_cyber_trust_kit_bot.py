# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import json
import unittest

from bots.smb_cyber_trust_kit_bot import (
    DEFAULT_RISK_REGISTER,
    INCIDENT_PHASES,
    INCIDENT_SCRIPTS,
    JARGON_GLOSSARY,
    POLICIES,
    RISK_BANDS,
    band_for_score,
    build_heat_map,
    build_kit,
    incident_script,
    kit_payload,
    rank_risks,
    render_markdown,
    render_policy,
    score_risk,
)


class RiskScoringTests(unittest.TestCase):
    def test_score_is_product_of_likelihood_and_impact(self) -> None:
        self.assertEqual(score_risk(4, 5).score, 20)
        self.assertEqual(score_risk(1, 1).score, 1)

    def test_bands_map_to_expected_labels(self) -> None:
        self.assertEqual(score_risk(1, 1).band, "Low")        # 1
        self.assertEqual(score_risk(2, 3).band, "Moderate")   # 6
        self.assertEqual(score_risk(3, 4).band, "High")       # 12
        self.assertEqual(score_risk(5, 5).band, "Critical")   # 25

    def test_bands_tile_the_full_1_to_25_range(self) -> None:
        for score in range(1, 26):
            band = band_for_score(score)
            self.assertTrue(band.min_score <= score <= band.max_score)

    def test_invalid_inputs_rejected(self) -> None:
        with self.assertRaises(ValueError):
            score_risk(0, 3)
        with self.assertRaises(ValueError):
            score_risk(3, 6)
        with self.assertRaises(TypeError):
            score_risk("4", 3)  # type: ignore[arg-type]

    def test_every_band_has_a_colour_and_action(self) -> None:
        for band in RISK_BANDS:
            self.assertTrue(band.color.startswith("#"))
            self.assertTrue(band.action)


class HeatMapTests(unittest.TestCase):
    def test_grid_has_25_cells(self) -> None:
        self.assertEqual(len(build_heat_map()), 25)

    def test_first_cell_is_top_left_worst_impact_lowest_likelihood(self) -> None:
        cells = build_heat_map()
        # Rows run impact 5 -> 1; first row, first column = L1 x I5.
        self.assertEqual((cells[0].likelihood, cells[0].impact), (1, 5))
        self.assertEqual(cells[0].score, 5)

    def test_registered_risks_are_placed_in_cells(self) -> None:
        placed = {rid for cell in build_heat_map() for rid in cell.risk_ids}
        expected = {r.id for r in DEFAULT_RISK_REGISTER}
        self.assertEqual(placed, expected)

    def test_ranking_is_worst_first(self) -> None:
        ranked = rank_risks()
        scores = [r.score for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreaterEqual(ranked[0].score, ranked[-1].score)


class PolicyTests(unittest.TestCase):
    def test_every_policy_has_rules_and_owner(self) -> None:
        for policy in POLICIES:
            self.assertTrue(policy.rules)
            self.assertTrue(policy.owner_role)
            self.assertTrue(policy.review_cadence)

    def test_render_fills_org_name(self) -> None:
        rendered = render_policy(POLICIES[0], org="Acme Co")
        self.assertIn("Acme Co", rendered)
        self.assertNotIn("{org}", rendered)

    def test_incident_policy_exposes_contact_placeholder(self) -> None:
        incident = next(p for p in POLICIES if p.id == "incident-response")
        rendered = render_policy(incident, org="Acme", incident_contact="Pat 555-1234")
        self.assertIn("Pat 555-1234", rendered)
        self.assertNotIn("{incident_contact}", rendered)


class IncidentCommsTests(unittest.TestCase):
    def test_every_script_phase_is_known(self) -> None:
        for script in INCIDENT_SCRIPTS:
            self.assertIn(script.phase, INCIDENT_PHASES)

    def test_lookup_by_audience(self) -> None:
        scripts = incident_script("Customers")
        self.assertTrue(scripts)
        self.assertTrue(all(s.audience == "Customers" for s in scripts))

    def test_lookup_by_audience_and_phase(self) -> None:
        scripts = incident_script("Internal staff", phase="recover")
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].id, "staff-allclear")

    def test_unknown_audience_returns_empty(self) -> None:
        self.assertEqual(incident_script("nobody"), [])

    def test_scripts_keep_placeholders_for_go_time(self) -> None:
        staff = incident_script("Internal staff", phase="contain")[0]
        self.assertIn("{", staff.template)
        self.assertIn("}", staff.template)


class GuideTests(unittest.TestCase):
    def test_glossary_terms_have_plain_and_analogy(self) -> None:
        for term in JARGON_GLOSSARY:
            self.assertTrue(term.plain)
            self.assertTrue(term.analogy)


class KitAssemblyTests(unittest.TestCase):
    def test_build_kit_has_all_four_deliverables(self) -> None:
        kit = build_kit(org="Acme Co")
        self.assertEqual(kit["org"], "Acme Co")
        self.assertIn("risk_model", kit)
        self.assertIn("policies", kit)
        self.assertIn("incident_comms", kit)
        self.assertIn("plain_language_guide", kit)
        self.assertEqual(len(kit["risk_model"]["heat_map"]), 25)

    def test_kit_payload_is_valid_json(self) -> None:
        parsed = json.loads(kit_payload("Acme Co"))
        self.assertEqual(parsed["name"], "ClearGlass SMB Cyber Trust Kit")

    def test_markdown_renders_every_section(self) -> None:
        md = render_markdown(org="Acme Co")
        self.assertIn("Simple Policy Templates", md)
        self.assertIn("Risk Heat-Map Template", md)
        self.assertIn("Communication During Incidents", md)
        self.assertIn("How to Talk to Non-Technical People", md)
        # Policies are personalised; the org placeholder is filled there.
        self.assertIn("Everyone who uses Acme Co systems", md)
        # Incident scripts intentionally keep {placeholders} for go-time.
        self.assertIn("Organization: {org}", md)


if __name__ == "__main__":
    unittest.main()
