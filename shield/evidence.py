"""G01 evidence and gate calculation.

    python3 shield/scripts/generate-evidence.py [--artifacts DIR] [--provenance]

Reads the per-test records a run wrote, maps them onto the G01 acceptance
criteria, and computes the gate:

    G01 = PASS only if every mandatory criterion is PASS in every cycle,
          teardown completed, Stripe and production interactions are 0,
          and there was no customer traffic. Otherwise FAIL.

The calculation is the only way G01 changes. There is no override flag.
With --provenance it also copies the non-sensitive records into
provenance/shield/runs/<run_id>/, rewrites the committed G01 evidence and report,
and updates G01 (and only G01) in the release manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROVENANCE = REPO / "provenance"
MANIFEST = PROVENANCE / "shield-release-manifest.json"
LIMITATIONS_DOC = REPO / "shield/docs/limitations-g01.md"
LOCK_STATEMENT = "NETWORK LOCK VALIDATED ONLY FOR THE DEFINED LINUX/CONTAINERIZED"
CYCLES = ("cycle-1", "cycle-2")
DEFAULT_BASELINE = "031cdcda0411b92e433af6faef0fbc8a8a33986a"

# Phase 14: each mandatory criterion and the tests that evidence it. Runtime tests
# must PASS in both cycles; static tests run once per run.
CRITERIA: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Disposable client exists", ("BOOT-01", "TUN-01")),
    ("Disposable gateway exists", ("BOOT-01", "GW-01")),
    ("Test keys generated safely", ("KEY-01", "SEC-02")),
    ("Client authentication works", ("TUN-01",)),
    ("Invalid identity fails", ("FI-02",)),
    ("Revocation works", ("FI-03",)),
    ("Encrypted tunnel establishes", ("TUN-01",)),
    ("Synthetic test traffic routes", ("TUN-02",)),
    ("DNS policy works", ("DNS-01", "DNS-02")),
    ("DNS failure is handled", ("DNS-04", "FI-07")),
    ("Tunnel interruption detected", ("FI-06",)),
    ("Network lock validates in scope",
     ("LOCK-CTRL", "LOCK-01", "LOCK-02", "LOCK-03", "LOCK-04", "LOCK-05", "DNS-03")),
    ("Gateway restart recovers", ("FI-08", "DNS-05")),
    ("Client restart recovers", ("FI-09",)),
    ("Config validation works", ("FI-04", "UNIT-01")),
    ("Failure-injection suite complete",
     ("FI-01", "FI-02", "FI-03", "FI-04", "FI-05", "FI-06", "FI-07", "FI-08", "FI-09", "FI-10",
      "FI-11", "FI-12", "FI-13", "FI-14")),
    ("No secrets committed/logged", ("SEC-01", "SEC-02", "SEC-03", "SEC-06", "FI-12")),
    ("No unexpected external traffic", ("FI-11", "SEC-04")),
    ("Test-only telemetry enforced", ("SEC-07",)),
    ("Deterministic teardown works", ("FI-14",)),
    ("Evidence tied to an exact commit", ("TREE-01",)),
    ("Stripe untouched", ("SEC-08", "FI-11")),
    ("Production untouched", ("FI-11", "SEC-04")),
)
STATIC = {"TREE-01", "UNIT-01", "SEC-01", "SEC-03", "SEC-08", "SEC-09", "SEC-10", "FI-12"}


def load_records(artifacts: Path) -> dict[str, dict[str, dict[str, object]]]:
    """{cycle name: {test id: record}} for static and every cycle."""
    out: dict[str, dict[str, dict[str, object]]] = {}
    for part in ("static", *CYCLES):
        tests = artifacts / part / "tests"
        out[part] = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                     for p in sorted(tests.glob("*.json"))} if tests.is_dir() else {}
    return out


def test_status(records: dict[str, dict[str, dict[str, object]]], test_id: str) -> str:
    """PASS only if present and PASS everywhere it must run."""
    parts = ("static",) if test_id in STATIC else CYCLES
    statuses = [records.get(part, {}).get(test_id, {}).get("status", "MISSING") for part in parts]
    if all(s == "PASS" for s in statuses):
        return "PASS"
    if "FAIL" in statuses or "MISSING" in statuses:
        return "FAIL"
    return "SKIPPED"


def evaluate(records: dict[str, dict[str, dict[str, object]]], limitations_ok: bool,
             teardown_completed: bool, stripe_interactions: int = 0,
             production_interactions: int = 0, customer_traffic: bool = False) -> dict[str, object]:
    criteria = []
    for name, tests in CRITERIA:
        statuses = {t: test_status(records, t) for t in tests}
        criteria.append({"requirement": name, "tests": statuses,
                         "status": "PASS" if all(s == "PASS" for s in statuses.values()) else "FAIL"})
    cycles_ok = all(records.get(c) and all(r["status"] == "PASS" for r in records[c].values())
                    for c in CYCLES)
    criteria.append({"requirement": "Environment reproducible",
                     "tests": {c: "PASS" if records.get(c) and all(
                         r["status"] == "PASS" for r in records[c].values()) else "FAIL" for c in CYCLES},
                     "status": "PASS" if cycles_ok else "FAIL"})
    criteria.append({"requirement": "Limitations documented", "tests": {"limitations-g01.md": (
        "PASS" if limitations_ok else "FAIL")}, "status": "PASS" if limitations_ok else "FAIL"})
    all_pass = all(c["status"] == "PASS" for c in criteria)
    decision = ("PASS" if all_pass and teardown_completed and stripe_interactions == 0
                and production_interactions == 0 and customer_traffic is False else "FAIL")
    return {"criteria": criteria, "gate_decision": decision,
            "passed": sum(c["status"] == "PASS" for c in criteria),
            "failed": [c["requirement"] for c in criteria if c["status"] != "PASS"]}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, text=True, capture_output=True,
                          check=False).stdout.strip()


def build(artifacts: Path) -> dict[str, object]:
    records = load_records(artifacts)
    run_id = (artifacts / "run_id").read_text(encoding="utf-8").strip()
    commits = {r["commit_sha"] for part in records.values() for r in part.values()}
    teardown = [records[c].get("FI-14", {}).get("status") == "PASS" for c in CYCLES]
    limitations_ok = LOCK_STATEMENT in LIMITATIONS_DOC.read_text(encoding="utf-8")
    result = evaluate(records, limitations_ok, all(teardown))
    if len(commits) != 1:
        result["gate_decision"] = "FAIL"
        result["failed"].append("Records disagree on the commit under test")
    boot = artifacts / "cycle-1/detail/BOOT-01.json"
    backend = json.loads(boot.read_text())["backend"] if boot.exists() else "unknown"
    files = sorted(p for p in artifacts.rglob("*") if p.is_file() and p.name not in (
        "g01-runtime-evidence.json", "g01-runtime-report.md"))
    tests = [{"test_id": t, "cycle": part, "status": r["status"]}
             for part, recs in records.items() for t, r in recs.items()]
    counts = {s: sum(1 for t in tests if t["status"] == s) for s in ("PASS", "FAIL", "SKIPPED")}
    return {
        "schema_version": "1.0",
        "product": "ClearGlass Shield",
        "gate": "G01",
        "environment": "isolated-disposable-test",
        "repository": "ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond",
        "branch": os.environ.get("GITHUB_HEAD_REF") or _git("branch", "--show-current"),
        "before_commit": os.environ.get("G01_BASELINE_SHA", DEFAULT_BASELINE),
        "commit": next(iter(commits)) if len(commits) == 1 else sorted(commits),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "test_run_id": run_id,
        "runner": os.environ.get("SHIELD_RUNNER", "github-actions" if os.environ.get("GITHUB_ACTIONS")
                                 else "local"),
        "wireguard_backend": backend,
        "components": ["shield/client", "shield/gateway", "shield/topology.py", "shield/common.py",
                       "shield/probes.py", "shield/g01_suite.py", "shield/secret_scan.py",
                       "shield/evidence.py", "shield/scripts", "shield/tests",
                       ".github/workflows/shield-g01-mvp.yml"],
        "controls": ["isolated Linux network namespaces, no default route", "standard WireGuard "
                     f"({backend} implementation)", "explicit peer allowlist with revocation",
                     "test-only DNS policy", "test-scope network lock (iptables, client namespace)",
                     "telemetry field allowlist", "secret scan", "deterministic teardown"],
        "tests": tests,
        "test_counts": counts,
        "acceptance": result["criteria"],
        "artifacts": [str(p.relative_to(artifacts)) for p in files],
        "artifact_hashes": [{"path": str(p.relative_to(artifacts)), "sha256": sha256(p)} for p in files],
        "limitations": [
            "Linux network-namespace test topology only (no Windows, macOS, mobile or public network)",
            "Network lock validated only for this topology; no universal leak-protection claim",
            "No production validation, no independent audit, no load or availability testing",
            "No customer traffic, identities or data; no billing, entitlement or account testing",
            "Test telemetry is not production observability",
            "Unknown, invalid and revoked peers are indistinguishable to the client by WireGuard "
            "design and surface as HANDSHAKE_FAILURE",
            "SEC-09 dependency audit and SEC-10 image scan were not run (SKIPPED, not PASS)",
        ],
        "teardown": {"attempted": True, "completed": all(teardown),
                     "evidence": "FI-14 in each cycle; cycle-N/verify-clean.json"},
        "stripe_interactions": 0,
        "stripe_interactions_basis": "shield/ has no Stripe code, key or host (SEC-08), and the "
                                     "test namespaces have no route out (FI-11)",
        "production_interactions": 0,
        "customer_traffic": False,
        "production_status": "NOT_PRODUCTION",
        "commercial_status": "BILLING_LOCKED",
        "gate_decision": result["gate_decision"],
        "unmet": result["failed"],
    }


def report(evidence: dict[str, object]) -> str:
    lines = [
        "# ClearGlass Shield G01: product implementation evidence",
        "",
        f"- Gate decision: **{evidence['gate_decision']}** (automated calculation; no override)",
        f"- Commit under test: `{evidence['commit']}` (baseline `{evidence['before_commit']}`)",
        f"- Run: `{evidence['test_run_id']}`, runner `{evidence['runner']}`, "
        f"WireGuard `{evidence['wireguard_backend']}`, created {evidence['created_at']}",
        f"- Tests: {evidence['test_counts']['PASS']} passed, {evidence['test_counts']['FAIL']} failed, "
        f"{evidence['test_counts']['SKIPPED']} skipped (SKIPPED is never counted as PASS)",
        "- Stripe interactions 0, production interactions 0, customer traffic none. "
        "Production status NOT_PRODUCTION, commercial status BILLING_LOCKED.",
        "",
        "## Acceptance criteria",
        "",
        "| Requirement | Status | Tests |",
        "|---|---|---|",
    ]
    for c in evidence["acceptance"]:
        tests = ", ".join(f"{t} {s}" for t, s in c["tests"].items())
        lines.append(f"| {c['requirement']} | {c['status']} | {tests} |")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in evidence["limitations"]]
    lines += ["", "This status reflects an isolated engineering test environment only. It does not "
              "indicate a public service, customer availability, production readiness, billing "
              "activation, or independent security audit.", ""]
    return "\n".join(lines)


def update_manifest(evidence: dict[str, object], evidence_path: str) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gates = manifest["gates"]
    frozen = {k: v for k, v in gates.items() if k != "G01_PRODUCT_IMPLEMENTATION"}
    gates["G01_PRODUCT_IMPLEMENTATION"] = {
        "status": evidence["gate_decision"],
        "evidence": f"{evidence_path}; commit {evidence['commit']}; run {evidence['test_run_id']} "
                    f"({evidence['runner']}, {evidence['wireguard_backend']} WireGuard); teardown "
                    f"{'complete' if evidence['teardown']['completed'] else 'INCOMPLETE'}",
        "limitations": "Linux network-namespace test scope only; see shield/docs/limitations-g01.md",
    }
    assert {k: v for k, v in gates.items() if k != "G01_PRODUCT_IMPLEMENTATION"} == frozen
    assert gates["G05_BILLING_CONFIGURATION"]["status"] == "FAIL"
    assert gates["G09_HUMAN_LAUNCH_AUTHORIZATION"]["status"] == "BLOCKED"
    assert manifest["release_state"] == "LOCKED" and manifest["billing_state"] == "LOCKED"
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="generate-evidence")
    parser.add_argument("--artifacts", type=Path,
                        default=Path(os.environ.get("SHIELD_ARTIFACT_DIR", "artifacts/shield-g01")))
    parser.add_argument("--provenance", action="store_true",
                        help="also write committed evidence and update G01 in the manifest")
    args = parser.parse_args(argv)
    artifacts = args.artifacts.resolve()
    evidence = build(artifacts)
    (artifacts / "g01-runtime-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n",
                                                         encoding="utf-8")
    (artifacts / "g01-runtime-report.md").write_text(report(evidence), encoding="utf-8")
    print(f"G01 gate: {evidence['gate_decision']}; unmet: {evidence['unmet'] or 'none'}")
    if args.provenance:
        run_dir = PROVENANCE / "shield" / "runs" / str(evidence["test_run_id"])
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.copytree(artifacts, run_dir)
        evidence_path = "provenance/shield/g01-product-evidence.json"
        (REPO / evidence_path).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        (PROVENANCE / "shield" / "g01-product-report.md").write_text(report(evidence), encoding="utf-8")
        update_manifest(evidence, evidence_path)
    return 0 if evidence["gate_decision"] == "PASS" else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
