"""Offline regressions for Auto Heal's pre-run failure evidence."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "auto_heal_annotations_test", ROOT / ".github/auto-heal/auto_heal.py"
)
assert SPEC and SPEC.loader
auto_heal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auto_heal)

BILLING_MESSAGE = (
    "The job was not started because your account is locked due to a billing issue."
)
REPO = "example/repository"
RUN_PATH = f"/repos/{REPO}/actions/runs/42/jobs?per_page=100"
LOG_PATH = f"/repos/{REPO}/actions/jobs/123/logs"
ANNOTATIONS_PATH = f"/repos/{REPO}/check-runs/456/annotations?per_page=100"


class AnnotationDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.job = {
            "id": 123,
            "name": "verify",
            "conclusion": "failure",
            "runner_id": 0,
            "steps": [],
            "check_run_url": "https://api.github.com/repos/example/repository/check-runs/456",
        }
        self.patterns = auto_heal.compile_patterns(
            json.loads((ROOT / ".github/auto-heal/error-patterns.json").read_text())
        )
        self.calls: list[tuple[str, str]] = []

    def diagnose(self, annotations: object, log: str | None = None):
        def fake_api(method, path, payload=None):
            self.calls.append((method, path))
            if method != "GET":
                raise AssertionError(f"Unexpected mutation: {method} {path}")
            if path == RUN_PATH:
                return {"jobs": [self.job]}
            if path == LOG_PATH:
                return log
            if path == ANNOTATIONS_PATH:
                return annotations
            raise AssertionError(f"Unexpected request: {method} {path}")

        with (
            patch.object(auto_heal, "REPOSITORY", REPO),
            patch.object(auto_heal, "API_URL", "https://api.github.com"),
            patch.object(auto_heal, "try_api", side_effect=fake_api),
        ):
            return auto_heal.job_diagnostics(42, self.patterns)

    def test_missing_logs_preserve_explicit_billing_annotation(self) -> None:
        category, strategy, diagnostics = self.diagnose(
            [{"annotation_level": "failure", "message": BILLING_MESSAGE}]
        )
        self.assertEqual(category, "BILLING_BLOCKED")
        self.assertIn("human", strategy.lower())
        self.assertEqual(diagnostics[0]["signature"], BILLING_MESSAGE)
        self.assertEqual(diagnostics[0]["evidence_source"], "check_run_annotations")

    def test_annotation_evidence_is_redacted(self) -> None:
        secret = "ghp_" + "x" * 36
        _, _, diagnostics = self.diagnose(
            [{"annotation_level": "failure", "message": f"{BILLING_MESSAGE} token={secret}"}]
        )
        self.assertNotIn(secret, json.dumps(diagnostics))
        self.assertIn("[REDACTED]", diagnostics[0]["signature"])

    def test_unavailable_or_malformed_annotations_do_not_imply_billing(self) -> None:
        for annotations in (None, [], {}, [None, "invalid", {"message": None}]):
            with self.subTest(annotations=annotations):
                category, _, diagnostics = self.diagnose(annotations)
                self.assertEqual(category, "UNKNOWN_FAILURE")
                self.assertEqual(diagnostics[0]["signature"], "unknown failure")

    def test_notices_do_not_establish_billing_or_enable_retry_classification(self) -> None:
        category, _, _ = self.diagnose([
            {"annotation_level": "notice", "message": BILLING_MESSAGE},
            {"annotation_level": "failure", "message": "503 Service Unavailable"},
        ])
        self.assertEqual(category, "UNKNOWN_FAILURE")

    def test_valid_logs_keep_existing_classification_without_annotation_read(self) -> None:
        category, _, diagnostics = self.diagnose(None, "ModuleNotFoundError: example")
        self.assertEqual(category, "DEPENDENCY_ERROR")
        self.assertNotIn(("GET", ANNOTATIONS_PATH), self.calls)
        self.assertEqual(diagnostics[0]["signature"], "ModuleNotFoundError: example")

    def test_billing_blocker_prevents_aggregate_retry_classification(self) -> None:
        def fake_api(method, path, payload=None):
            self.assertEqual(method, "GET")
            if path == RUN_PATH:
                return {"jobs": [{"id": 124, "name": "build", "conclusion": "failure"}, self.job]}
            if path.endswith("/actions/jobs/124/logs"):
                return "503 Service Unavailable"
            if path == LOG_PATH:
                return None
            if path == ANNOTATIONS_PATH:
                return [{"annotation_level": "failure", "message": BILLING_MESSAGE}]
            raise AssertionError(path)

        with (
            patch.object(auto_heal, "REPOSITORY", REPO),
            patch.object(auto_heal, "API_URL", "https://api.github.com"),
            patch.object(auto_heal, "try_api", side_effect=fake_api),
        ):
            category, _, diagnostics = auto_heal.job_diagnostics(42, self.patterns)
        self.assertEqual(diagnostics[0]["category"], "INFRASTRUCTURE_ERROR")
        self.assertEqual(category, "BILLING_BLOCKED")

    def test_untrusted_check_urls_are_not_followed(self) -> None:
        for url in (
            "https://untrusted.invalid/repos/example/repository/check-runs/456",
            "https://api.github.com/repos/other/repository/check-runs/456",
            "https://api.github.com/repos/example/repository/check-runs/456?next=other",
            "",
            None,
        ):
            with self.subTest(url=url):
                self.job["check_run_url"] = url
                category, _, _ = self.diagnose(None)
                self.assertEqual(category, "UNKNOWN_FAILURE")
        self.assertNotIn(("GET", ANNOTATIONS_PATH), self.calls)

    def test_billing_is_not_recorded_as_flaky_or_sent_to_rerun_or_doctor(self) -> None:
        calls = []

        def fake_api(method, path, payload=None):
            calls.append((method, path))
            if method == "GET" and path.endswith("/actions/runs/42"):
                return {"id": 42, "run_attempt": 1, "name": "CI", "head_sha": "a" * 40}
            if method == "GET" and path == RUN_PATH:
                return {"jobs": [self.job]}
            if method == "GET" and path == LOG_PATH:
                return None
            if method == "GET" and path == ANNOTATIONS_PATH:
                return [{"annotation_level": "failure", "message": BILLING_MESSAGE}]
            if method == "GET" and path.endswith("/issues?state=all&per_page=100"):
                return []
            if method == "POST" and path.endswith("/labels"):
                return {}
            if method == "POST" and path.endswith("/issues"):
                return {"number": 7}
            raise AssertionError(f"Unexpected request: {method} {path}")

        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)
            for name in ("error-patterns.json", "healing-strategies.json"):
                (control / name).write_text((ROOT / ".github/auto-heal" / name).read_text())
            (control / "run-history.json").write_text(json.dumps({"entries": [{
                "run_id": 41, "run_attempt": 1, "workflow": "CI",
                "classification": "UNKNOWN_FAILURE", "diagnostics": [{"job": "verify"}],
            }]}))
            with (
                patch.object(auto_heal, "REPOSITORY", REPO),
                patch.object(auto_heal, "API_URL", "https://api.github.com"),
                patch.object(auto_heal, "TARGET_RUN_ID", "42"),
                patch.object(auto_heal, "PATTERNS_PATH", control / "error-patterns.json"),
                patch.object(auto_heal, "STRATEGIES_PATH", control / "healing-strategies.json"),
                patch.object(auto_heal, "HISTORY_PATH", control / "run-history.json"),
                patch.object(auto_heal, "FLAKY_PATH", control / "flaky-tests.json"),
                patch.object(auto_heal, "api", side_effect=fake_api),
                patch.dict(auto_heal.os.environ, {"GITHUB_OUTPUT": str(control / "outputs")}),
            ):
                self.assertEqual(auto_heal.main(), 0)
            history = json.loads((control / "run-history.json").read_text())
            self.assertEqual(history["entries"][-1]["classification"], "BILLING_BLOCKED")
            self.assertEqual(history["entries"][-1]["action"], "escalated_issue")
            self.assertEqual(json.loads((control / "flaky-tests.json").read_text())["tests"], [])
            self.assertIn("needs_workflow_doctor=false", (control / "outputs").read_text())
        self.assertFalse(any("rerun" in path for _, path in calls))


if __name__ == "__main__":
    unittest.main()
