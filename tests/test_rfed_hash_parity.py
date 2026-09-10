# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Hash parity between the n8n Code node and the Python RFED core.

The whole value of the RFED ledger is that a record sealed by the n8n workflow
can be re-verified later by `python -m bots.rfed_audit_bot --verify`. That only
holds if both canonicalisers emit byte-identical JSON.

The subtle failure this guards against: Python renders floats via `repr()`
(`0.0`), while `JSON.stringify(0.0)` gives `0`. The Code node wraps float-typed
fields in `PyFloat` to compensate — if someone removes that, every hash the
workflow writes becomes unverifiable, silently.

Skipped when node is unavailable; the CI image has it.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from bots.rfed_audit_bot import (
    Evidence,
    Fact,
    Request,
    build_record,
    canonical_json,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "deployment" / "rfed" / "workflow_rfed_audit_trail.json"
NODE = shutil.which("node")

PREV_HASH = "e" * 64


def extract_canonicaliser() -> str:
    """Pull the canonicalisation helpers out of the Build RFED Record node."""
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    node = next(n for n in workflow["nodes"] if n["id"] == "build-rfed")
    js = node["parameters"]["jsCode"]
    start = js.index("class PyFloat")
    end = js.index("// --- governor")
    return js[start:end]


def sample_record():
    return build_record(
        Request(
            actor="n8n:rfed-audit-trail",
            workflow="client_zero_trust",
            action="read_telemetry",
            target="endpoint/BRL-014",
            intent="check RMM agent patch level",
            correlation_id="run-1",
            input_digest="a" * 64,
        ),
        [
            Fact(
                source="pg:endpoints",
                reference="endpoint/BRL-014",
                content_digest="b" * 64,
                retrieved_at="2026-08-05T00:00:00Z",
                trusted=True,
            ),
            Fact(
                source="web:vendor-advisory",
                reference="advisory/CVE-2026-18577",
                content_digest="f" * 64,
                retrieved_at="2026-08-05T00:00:00Z",
                trusted=False,
            ),
        ],
        Evidence(
            model_id="claude-opus-5",
            temperature=0.0,
            max_tokens=1024,
            prompt_digest="c" * 64,
            output_digest="d" * 64,
            # Non-ASCII exercises ensure_ascii parity; the excerpt is redacted on build.
            output_excerpt="BRL-014 runs 2026.3.1 without Hotfix 1. Naive café ünïcode — ok.",
            confidence=0.94,
            citations=["endpoint/BRL-014"],
            input_tokens=100,
            output_tokens=50,
        ),
        prev_hash=PREV_HASH,
    )


@unittest.skipIf(NODE is None, "node is not installed")
class TestHashParity(unittest.TestCase):
    def _run_js(self, body: dict) -> dict:
        script = f"""
const crypto = require('crypto');
{extract_canonicaliser()}
const body = {json.dumps(body)};
body.evidence.temperature = new PyFloat(body.evidence.temperature);
body.evidence.confidence  = new PyFloat(body.evidence.confidence);
const c = asciiEscape(canonical(body));
console.log(JSON.stringify({{canonical: c, hash: sha256({json.dumps(PREV_HASH)} + c)}}));
"""
        result = subprocess.run(
            [NODE, "-e", script], capture_output=True, text=True, check=True, timeout=60
        )
        return json.loads(result.stdout)

    def test_canonical_form_is_byte_identical(self):
        record = sample_record()
        js = self._run_js(record.body())
        self.assertEqual(canonical_json(record.body()), js["canonical"])

    def test_chain_hash_is_identical(self):
        record = sample_record()
        js = self._run_js(record.body())
        self.assertEqual(record.chain_hash, js["hash"])

    def test_float_fields_render_python_style(self):
        # The specific regression: temperature 0.0 must not canonicalise to `0`.
        record = sample_record()
        canonical = canonical_json(record.body())
        self.assertIn('"temperature":0.0', canonical)
        self.assertEqual(canonical, self._run_js(record.body())["canonical"])

    def test_non_ascii_is_escaped_identically(self):
        record = sample_record()
        canonical = canonical_json(record.body())
        self.assertNotIn("café", canonical)
        self.assertIn("\\u00e9", canonical)
        self.assertEqual(canonical, self._run_js(record.body())["canonical"])


class TestWorkflowShape(unittest.TestCase):
    """Structural guarantees the deployed workflow must keep."""

    def setUp(self):
        self.workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
        self.nodes = {n["id"]: n for n in self.workflow["nodes"]}

    def test_signature_verification_precedes_the_model_call(self):
        conns = self.workflow["connections"]
        self.assertEqual(
            conns["Proposed Action Webhook"]["main"][0][0]["node"], "Verify Caller (HMAC)"
        )

    def test_ledger_write_precedes_any_execution(self):
        # The record must be durable before the action runs, so a crash mid-run
        # leaves evidence rather than an untracked side effect.
        conns = self.workflow["connections"]
        self.assertEqual(
            conns["Append to RFED Ledger"]["main"][0][0]["node"], "Route by Decision"
        )
        self.assertEqual(
            conns["Build RFED Record"]["main"][0][0]["node"], "Append to RFED Ledger"
        )

    def test_switch_fallback_routes_to_blocked(self):
        routes = self.workflow["connections"]["Route by Decision"]["main"]
        self.assertEqual(len(routes), 4, "expected auto/queued/blocked + fallback")
        self.assertEqual(routes[3][0]["node"], "Alert Security (Blocked)")

    def test_execute_branch_is_only_reachable_from_auto_route(self):
        routes = self.workflow["connections"]["Route by Decision"]["main"]
        targets = [branch[0]["node"] for branch in routes]
        self.assertEqual(targets.count("Execute (Low Risk Only)"), 1)
        self.assertEqual(targets[0], "Execute (Low Risk Only)")

    def test_webhook_secret_is_mandatory(self):
        js = self.nodes["verify-signature"]["parameters"]["jsCode"]
        self.assertIn("RFED_WEBHOOK_SECRET", js)
        self.assertIn("fail closed", js)
        self.assertIn("timingSafeEqual", js)

    def test_governor_tables_match_the_python_core(self):
        from bots.rfed_audit_bot import ACTION_RISK, ALWAYS_ESCALATE, NEVER_AUTOMATE

        js = self.nodes["build-rfed"]["parameters"]["jsCode"]
        for action, score in ACTION_RISK.items():
            with self.subTest(action=action):
                self.assertIn(f"{action}: {score}", js, f"{action} missing/mismatched in n8n node")
        for action in ALWAYS_ESCALATE:
            with self.subTest(escalate=action):
                self.assertIn(f"'{action}'", js)
        for action in NEVER_AUTOMATE:
            with self.subTest(never=action):
                self.assertIn(f"NEVER_AUTOMATE = new Set(['{action}'])", js)

    def test_policy_version_matches_the_python_core(self):
        from bots.rfed_audit_bot import POLICY_VERSION

        js = self.nodes["build-rfed"]["parameters"]["jsCode"]
        self.assertIn(f"POLICY_VERSION = '{POLICY_VERSION}'", js)
        self.assertEqual(self.workflow["meta"]["clearglass"]["policy_version"], POLICY_VERSION)

    def test_dry_run_defaults_to_true(self):
        js = self.nodes["execute-action"]["parameters"]["jsonBody"]
        self.assertIn("RFED_DRY_RUN !== 'false'", js)


if __name__ == "__main__":
    unittest.main()
