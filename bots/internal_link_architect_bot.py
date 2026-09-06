#!/usr/bin/env python3
"""Validate and report on the ClearGlass internal-link authority graph."""
from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKER_PATH = ROOT / "tools" / "internal_links.py"
OUT = ROOT / "operations" / "output" / "internal_link_architect_report.json"


@dataclass
class ClusterReport:
    cluster_id: str
    name: str
    pillar: str
    member_count: int
    cta_count: int


def load_linker():
    spec = importlib.util.spec_from_file_location("internal_links", LINKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {LINKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_report() -> dict:
    linker = load_linker()
    errors = linker.validate()
    clusters = [
        ClusterReport(cid, cfg["name"], cfg["pillar"], len(cfg["members"]), len(cfg.get("cta", [])))
        for cid, cfg in linker.CLUSTERS.items()
    ]
    pages_without_extra = sorted(set(linker.PAGES) - set(linker.EXTRA_LINKS))
    return {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "page_count": len(linker.PAGES),
        "cluster_count": len(linker.CLUSTERS),
        "clusters": [asdict(c) for c in clusters],
        "errors": errors,
        "pages_without_curated_cross_cluster_links": pages_without_extra,
        "execution_order": [
            "Update tools/internal_links.py as the canonical graph.",
            "Run python3 tools/internal_links.py to regenerate blocks.",
            "Run python3 tools/internal_links.py --check.",
            "Run this bot in --check mode before commit."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if graph validation fails")
    args = parser.parse_args()
    report = build_report()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "page_count", "cluster_count")}, indent=2))
    return 1 if args.check and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
