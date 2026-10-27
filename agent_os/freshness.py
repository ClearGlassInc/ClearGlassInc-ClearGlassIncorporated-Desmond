# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Freshness of the live datasets the site actually publishes.

Two feeds are wired, each with its own fetcher that records provenance:

    data/grid/ieso-public.json     scripts/ieso_public_feed.py   (IESO public reports)
    feeds/minerals/manifest.json   scripts/minerals_data_sync.py (Government of Canada news API)

This module fetches nothing. It reads the provenance those fetchers wrote and
says, per source, whether the data is fresh, ageing, stale, or was never
retrieved at all — so a status panel can show the truth instead of a green
dot. A source with no successful retrieval is ``never_retrieved``, never
"fresh by default".

Thresholds: the minerals manifest carries its own per-feed policy and that is
used as-is. The IESO reports are hourly and published with delay, so a
snapshot older than 3 hours is ``warning`` and older than 6 hours ``stale``.

    python -m agent_os.freshness            # JSON report, exit 0
    python -m agent_os.freshness --strict   # exit 1 unless every source is fresh

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "clearglass.agent_os.freshness/1"
STATES = ("fresh", "warning", "stale", "never_retrieved", "unknown", "missing")

IESO_PATH = Path("data/grid/ieso-public.json")
MINERALS_PATH = Path("feeds/minerals/manifest.json")
IESO_WARNING_HOURS = 3
IESO_STALE_HOURS = 6

_ROOT = Path(__file__).resolve().parents[1]


def _parse(stamp: object) -> datetime | None:
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _classify(last_success: object, warning_hours: float, stale_hours: float,
              now: datetime) -> tuple[str, float | None]:
    if last_success in (None, ""):
        return "never_retrieved", None
    moment = _parse(last_success)
    if moment is None:
        return "unknown", None
    age = round((now - moment).total_seconds() / 3600, 2)
    if age >= stale_hours:
        return "stale", age
    if age >= warning_hours:
        return "warning", age
    return "fresh", age


def _load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{path.name} is missing"
    except (OSError, ValueError) as exc:
        return None, f"{path.name} is unreadable: {exc}"
    if not isinstance(document, dict):
        return None, f"{path.name} is not a JSON object"
    return document, None


def _missing(feed: str, detail: str) -> dict[str, Any]:
    return {"id": feed, "feed": feed, "state": "missing", "detail": detail}


def report(root: Path | str | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _ROOT
    moment = now or datetime.now(UTC)
    sources: list[dict[str, Any]] = []

    ieso, problem = _load(base / IESO_PATH)
    if ieso is None:
        sources.append(_missing("ieso-public", problem or ""))
    else:
        for src in ieso.get("sources") or []:
            state, age = _classify(src.get("last_success_utc"), IESO_WARNING_HOURS,
                                   IESO_STALE_HOURS, moment)
            sources.append({
                "id": src.get("id"),
                "feed": "ieso-public",
                "provider": "IESO public reports",
                "url": src.get("url"),
                "last_success_utc": src.get("last_success_utc"),
                "source_updated_utc": src.get("created_at") or src.get("last_modified"),
                "last_attempt_utc": src.get("attempted_utc"),
                "last_error": src.get("error"),
                "age_hours": age,
                "warning_hours": IESO_WARNING_HOURS,
                "stale_hours": IESO_STALE_HOURS,
                "state": state,
            })

    minerals, problem = _load(base / MINERALS_PATH)
    if minerals is None:
        sources.append(_missing("minerals", problem or ""))
    else:
        for feed in minerals.get("feeds") or []:
            warning = float(feed.get("warning_threshold_hours") or 24)
            stale = float(feed.get("stale_threshold_hours") or 72)
            state, age = _classify(feed.get("retrieved_at"), warning, stale, moment)
            sources.append({
                "id": feed.get("id"),
                "feed": "minerals",
                "provider": feed.get("source"),
                "url": feed.get("source_url"),
                "last_success_utc": feed.get("retrieved_at"),
                "source_updated_utc": feed.get("source_updated_at"),
                "last_attempt_utc": minerals.get("generated_at"),
                "last_error": None if feed.get("status") in (None, "OK", "FRESH")
                else f"feed status {feed.get('status')}",
                "age_hours": age,
                "warning_hours": warning,
                "stale_hours": stale,
                "state": state,
            })

    counts = Counter(s["state"] for s in sources)
    return {
        "schema": SCHEMA,
        "checked_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Read-only: reports the provenance the fetchers recorded; fetches nothing.",
        "sources": sources,
        "summary": {state: counts.get(state, 0) for state in STATES},
        "all_fresh": bool(sources) and counts.get("fresh", 0) == len(sources),
    }


def validate(document: object) -> list[str]:
    """Problems with a freshness report, or ``[]``. Used to accept task output."""
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        return ["not a freshness report"]
    problems = []
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        problems.append("report lists no sources")
    else:
        for src in sources:
            if not isinstance(src, dict) or src.get("state") not in STATES:
                problems.append(f"source {src!r} has no valid state")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent_os.freshness", description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--strict", action="store_true", help="exit 1 unless every source is fresh")
    ns = ap.parse_args(argv)
    result = report(ns.root)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if ns.strict and not result["all_fresh"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
