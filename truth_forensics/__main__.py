# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Command line for ClearGlass Truth Forensics.

    python -m truth_forensics hash FILE...              acquire + SHA-256 + type
    python -m truth_forensics analyze FILE [--json]     single-item analysis
    python -m truth_forensics case CASE.json [--json|--report] [--review-demo]
    python -m truth_forensics verify-ledger LEDGER.jsonl
    python -m truth_forensics check-url URL
    python -m truth_forensics demo --write | --check

Files are opened read-only through the intake rules (no symlinks, no path
escape from the case directory, size limits). Nothing is sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import case as case_mod
from . import demo, intake, report, vocab
from .provenance import verify_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def cmd_hash(args) -> int:
    rc = 0
    for name in args.files:
        try:
            rec, _ = intake.acquire_file(name, acquired_at=_now(), acquired_by=args.actor)
        except intake.IntakeError as exc:
            print(f"REFUSED {intake.display_name(name)}: {exc}", file=sys.stderr)
            rc = 1
            continue
        print(f"{rec.content_sha256}  {rec.size_bytes:>10}  {rec.mime_sniffed:<26} "
              f"{rec.processing_boundary:<10} {rec.declared_name}")
    return rc


def cmd_analyze(args) -> int:
    try:
        rec, data = intake.acquire_file(args.file, acquired_at=_now(), acquired_by=args.actor,
                                        declared_mime=args.declared_mime or "")
    except intake.IntakeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    result = case_mod.analyze_item(rec, data)
    if args.json:
        _print({"evidence": rec.to_dict(), "analysis": result, "disclaimer": vocab.DISCLAIMER})
        return 0
    print(f"{rec.evidence_id}  {rec.mime_sniffed}  sha256 {rec.content_sha256}")
    for ind in result["indicators"]:
        print(f"  [{ind['state']}/{ind['confidence']}] {ind['title']}")
        print(f"      evidence:   {ind['evidence']}")
        print(f"      limitation: {ind['limitation']}")
    print(vocab.INDICATORS_FOUND if any(i["state"] != vocab.NORMAL for i in result["indicators"])
          else vocab.NO_INDICATORS)
    for item in result.get("not_performed", []):
        print(f"  not performed: {item}")
    return 0


def cmd_case(args) -> int:
    path = Path(args.case)
    try:
        spec = json.loads(intake.safe_open_path(path).read_text(encoding="utf-8"))
        files = demo.load_files(spec, path.resolve().parent)
        reviews = spec.get("suggested_reviews", []) if args.review_demo else None
        result = case_mod.run_case(spec, files, reviews=reviews)
    except (intake.IntakeError, case_mod.CaseError, ValueError, KeyError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2
    if args.report:
        print(report.render_markdown(report.build_report(result)))
    elif args.json:
        _print(result)
    else:
        print(f"{result['case_id']}  job {result['job']['state']}  "
              f"{result['label'] or ''}".rstrip())
        for e in result["evidence"]:
            print(f"  {e['evidence_id']:<6} {e['final_status']:<13} {e['integrity']:<9} "
                  f"{e['group']:<4} open={e['open_findings']} {e['label']}")
        if result["claim"]:
            print(f"  claim: {result['claim']['verdict']} (final: "
                  f"{result['claim']['final_verdict']})")
        print(f"  {result['summary']['statement']}")
        print(f"  ledger verified: {result['provenance']['verified']}")
    return 0


def cmd_verify(args) -> int:
    ok, bad = verify_jsonl(intake.safe_open_path(args.ledger).read_text(encoding="utf-8"))
    print("chain intact" if ok else f"chain broken at record {bad}")
    return 0 if ok else 1


def cmd_url(args) -> int:
    ok, reasons = intake.validate_url(args.url, resolve=args.resolve)
    print("fetchable by a future adapter" if ok else "not fetchable:")
    for r in reasons:
        print(f"  - {r}")
    print("Note: this engine never fetches URLs; it records them as references.")
    return 0 if ok else 1


def cmd_demo(args) -> int:
    if args.write:
        changed = demo.write()
        print("\n".join(changed) if changed else "demo files already current")
        return 0
    stale = demo.check()
    if stale:
        print("stale demo files: " + ", ".join(stale), file=sys.stderr)
        return 1
    print("demo files current")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m truth_forensics",
                                description="ClearGlass Truth Forensics. " + vocab.DISCLAIMER)
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hash", help="acquire files and print SHA-256, size and sniffed type")
    h.add_argument("files", nargs="+")
    h.add_argument("--actor", default="cli")
    h.set_defaults(fn=cmd_hash)
    a = sub.add_parser("analyze", help="analyse one file")
    a.add_argument("file")
    a.add_argument("--declared-mime")
    a.add_argument("--actor", default="cli")
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_analyze)
    c = sub.add_parser("case", help="run a case manifest")
    c.add_argument("case")
    g = c.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true")
    g.add_argument("--report", action="store_true", help="Markdown forensic report")
    c.add_argument("--review-demo", action="store_true",
                   help="apply the manifest's suggested_reviews (demonstration only)")
    c.set_defaults(fn=cmd_case)
    v = sub.add_parser("verify-ledger", help="replay a provenance ledger's hash chain")
    v.add_argument("ledger")
    v.set_defaults(fn=cmd_verify)
    u = sub.add_parser("check-url", help="SSRF-safety check for a URL reference")
    u.add_argument("url")
    u.add_argument("--resolve", action="store_true")
    u.set_defaults(fn=cmd_url)
    d = sub.add_parser("demo", help="regenerate or check the demonstration case")
    dg = d.add_mutually_exclusive_group(required=True)
    dg.add_argument("--write", action="store_true")
    dg.add_argument("--check", action="store_true")
    d.set_defaults(fn=cmd_demo)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
