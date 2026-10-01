#!/usr/bin/env python3
"""Fetch IESO public reports into the GridShield-Ontario data feed.

Writes data/grid/ieso-public.json, which GridShield-Ontario-V6-0-ULTRA-FINAL.html
reads. Two public reports are wired:

  PUB_Demand                 hourly Market Demand and Ontario Demand (MW)
  PUB_GenOutputbyFuelHourly  hourly output by fuel, generators of 20 MW or more

Every file is recorded as the page's IESO data-source policy asks: report id,
source URL, retrieval time (UTC), the file's own "created at" stamp, the HTTP
Last-Modified header, SHA-256 of the exact bytes received, byte count and the
parser version that read it.

Fail-closed rules:
  - a header or structure that does not match what the parser expects is an
    error, never a best guess; the source publishes nothing new
  - a failed source keeps its last good data and says so (status "error",
    last_success_utc), so a bad fetch never erases a good snapshot and never
    hides itself
  - values outside a sanity range are rejected, not clamped

Price is not wired. HOEP ended when the Ontario Electricity Market Price
replaced it on 2025-05-01, and the replacement report's URL has not been
verified, so the feed says "not_wired" instead of guessing one.

PUBLIC IESO REPORT DATA — NOT A CONTROL SIGNAL. Nothing here may trigger OT
commands, containment, load-shedding, protection or dispatch.

    python3 scripts/ieso_public_feed.py              # fetch and write
    python3 scripts/ieso_public_feed.py --strict     # exit 1 if any source failed
    python3 scripts/ieso_public_feed.py --offline DIR   # read DIR/PUB_Demand.csv etc.

stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "grid" / "ieso-public.json"

SCHEMA = "clearglass.gridshield.ieso-public/1"
LABEL = "PUBLIC IESO REPORT DATA — NOT A CONTROL SIGNAL"
NOTICE = (
    "Informational public reports, published with delay and subject to revision. "
    "Never used to trigger OT commands, automated containment, load-shedding, "
    "protection or dispatch."
)
USER_AGENT = "clearglass-gridshield-feed/1 (+https://www.clearglassinc.com)"
MAX_BYTES = 40 * 1024 * 1024
SERIES_HOURS = 24

DEMAND = {
    "id": "PUB_Demand",
    "title": "Hourly Demand Report",
    "url": "https://reports-public.ieso.ca/public/Demand/PUB_Demand.csv",
    "file": "PUB_Demand.csv",
    "parser": "ieso-demand-csv/1",
}
FUEL = {
    "id": "PUB_GenOutputbyFuelHourly",
    "title": "Generator Output by Fuel Type Hourly Report",
    "url": "https://reports-public.ieso.ca/public/GenOutputbyFuelHourly/PUB_GenOutputbyFuelHourly.xml",
    "file": "PUB_GenOutputbyFuelHourly.xml",
    "parser": "ieso-fuel-xml/1",
}
SOURCES = (DEMAND, FUEL)

PRICE = {
    "status": "not_wired",
    "reason": (
        "HOEP ended on 2025-05-01 when the Ontario Electricity Market Price replaced it. "
        "The replacement public report's URL has not been verified, so no price is shown."
    ),
}

DEMAND_HEADER = ["Date", "Hour", "Market Demand", "Ontario Demand"]
DATE_RE = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$")

# Sanity bounds, not physics: a value outside them means the file is not what
# the parser thinks it is, so the source fails closed instead of publishing it.
DEMAND_MW = (5_000, 40_000)
FUEL_MW = (-1_000, 25_000)
FUEL_TOTAL_MW = (3_000, 45_000)


class FeedError(Exception):
    """The upstream file is unreachable or not in the expected shape."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── transport ─────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 60) -> tuple[bytes, str, str | None]:
    """Return (body, final_url, last_modified). HTTPS only, size-capped."""
    if not url.startswith("https://"):
        raise FeedError(f"refusing non-HTTPS URL {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final = resp.geturl()
            if not final.startswith("https://"):
                raise FeedError(f"redirected off HTTPS to {final}")
            body = resp.read(MAX_BYTES + 1)
            last_modified = resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as exc:
        raise FeedError(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise FeedError(f"could not reach {url}: {reason}") from exc
    if len(body) > MAX_BYTES:
        raise FeedError(f"{url} is larger than {MAX_BYTES} bytes")
    if not body:
        raise FeedError(f"{url} returned an empty body")
    return body, final, last_modified


# ── parsers ───────────────────────────────────────────────────────────────────

def _int_in(value: str, bounds: tuple[int, int], what: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise FeedError(f"{what} is not an integer: {value!r}") from exc
    if not bounds[0] <= number <= bounds[1]:
        raise FeedError(f"{what} {number} is outside the sanity range {bounds}")
    return number


def _norm_date(value: str, what: str) -> str:
    if not DATE_RE.match(value):
        raise FeedError(f"{what} date is not YYYY-MM-DD: {value!r}")
    return value.replace("/", "-")


def _hour(value: str, what: str) -> int:
    return _int_in(value, (1, 24), f"{what} hour")


def parse_demand(raw: bytes) -> dict[str, Any]:
    """Parse PUB_Demand.csv. Header must be exactly DEMAND_HEADER."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FeedError("PUB_Demand is not UTF-8 text") from exc
    created_at = None
    header: list[str] | None = None
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if line.startswith("\\"):
            note = line.lstrip("\\").rstrip(",").strip()
            if note.lower().startswith("created at"):
                created_at = note[len("created at"):].strip()
            continue
        cells = [c.strip() for c in line.split(",")]
        if header is None:
            if cells != DEMAND_HEADER:
                raise FeedError(f"PUB_Demand header is {cells}, expected {DEMAND_HEADER}")
            header = cells
            continue
        if len(cells) != len(DEMAND_HEADER):
            raise FeedError(f"PUB_Demand line {lineno} has {len(cells)} cells")
        date, hour, market, ontario = cells
        if not market and not ontario:
            continue  # hour not yet published
        where = f"PUB_Demand line {lineno}"
        rows.append({
            "date": _norm_date(date, where),
            "hour": _hour(hour, where),
            "market_mw": _int_in(market, DEMAND_MW, f"{where} Market Demand"),
            "ontario_mw": _int_in(ontario, DEMAND_MW, f"{where} Ontario Demand"),
        })
    if header is None:
        raise FeedError("PUB_Demand has no header row")
    if not rows:
        raise FeedError("PUB_Demand has no published hours")
    rows.sort(key=lambda r: (r["date"], r["hour"]))
    latest = rows[-1]
    return {
        "created_at": created_at,
        "section": {
            "date": latest["date"],
            "hour_ending": latest["hour"],
            "ontario_mw": latest["ontario_mw"],
            "market_mw": latest["market_mw"],
            "series": rows[-SERIES_HOURS:],
        },
    }


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(elem: ET.Element, name: str) -> ET.Element | None:
    for sub in elem:
        if _local(sub.tag) == name:
            return sub
    return None


def _children(elem: ET.Element, name: str) -> list[ET.Element]:
    return [sub for sub in elem if _local(sub.tag) == name]


def _find(elem: ET.Element, name: str) -> ET.Element | None:
    for sub in elem.iter():
        if sub is not elem and _local(sub.tag) == name:
            return sub
    return None


def parse_fuel(raw: bytes) -> dict[str, Any]:
    """Parse PUB_GenOutputbyFuelHourly.xml.

    Expected path: DailyData/Day, DailyData/HourlyData/Hour,
    HourlyData/FuelTotal/Fuel and FuelTotal/.../Output (+ OutputQuality).
    The latest hour in which every fuel carries a numeric Output is published.
    """
    if b"<!DOCTYPE" in raw[:4096] or b"<!ENTITY" in raw:
        raise FeedError("fuel report declares a DOCTYPE/ENTITY; refusing to parse")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise FeedError(f"fuel report is not well-formed XML: {exc}") from exc
    created = _find(root, "CreatedAt")
    created_at = created.text.strip() if created is not None and created.text else None
    days = [e for e in root.iter() if _local(e.tag) == "DailyData"]
    if not days:
        raise FeedError("fuel report has no DailyData elements")
    complete: list[tuple[str, int, list[dict[str, Any]]]] = []
    for day in days:
        day_el = _child(day, "Day")
        if day_el is None or not day_el.text:
            raise FeedError("fuel report DailyData has no Day")
        date = _norm_date(day_el.text.strip(), "fuel report")
        for hourly in _children(day, "HourlyData"):
            hour_el = _child(hourly, "Hour")
            if hour_el is None or not hour_el.text:
                raise FeedError(f"fuel report {date} HourlyData has no Hour")
            hour = _hour(hour_el.text.strip(), f"fuel report {date}")
            fuels: list[dict[str, Any]] = []
            usable = True
            for total in _children(hourly, "FuelTotal"):
                fuel_el = _child(total, "Fuel")
                if fuel_el is None or not fuel_el.text:
                    raise FeedError(f"fuel report {date} HE{hour} FuelTotal has no Fuel")
                output = _find(total, "Output")
                if output is None or not (output.text or "").strip():
                    usable = False
                    break
                quality = _find(total, "OutputQuality")
                fuels.append({
                    "fuel": fuel_el.text.strip().upper(),
                    "mw": _int_in(output.text.strip(), FUEL_MW,
                                  f"fuel report {date} HE{hour} {fuel_el.text.strip()}"),
                    "quality": quality.text.strip() if quality is not None and quality.text else None,
                })
            if usable and fuels:
                complete.append((date, hour, fuels))
    if not complete:
        raise FeedError("fuel report has no hour with a numeric Output for every fuel")
    complete.sort(key=lambda item: (item[0], item[1]))
    date, hour, fuels = complete[-1]
    total = sum(f["mw"] for f in fuels)
    if not FUEL_TOTAL_MW[0] <= total <= FUEL_TOTAL_MW[1]:
        raise FeedError(f"fuel report {date} HE{hour} total {total} MW is outside {FUEL_TOTAL_MW}")
    for f in fuels:
        f["pct"] = round(f["mw"] / total * 100, 1)
    fuels.sort(key=lambda f: f["mw"], reverse=True)
    return {
        "created_at": created_at,
        "section": {"date": date, "hour_ending": hour, "total_mw": total, "fuels": fuels},
    }


PARSERS = {DEMAND["id"]: (parse_demand, "demand"), FUEL["id"]: (parse_fuel, "supply_mix")}


# ── feed assembly ─────────────────────────────────────────────────────────────

def blank_source(spec: dict[str, str]) -> dict[str, Any]:
    return {
        "id": spec["id"], "title": spec["title"], "url": spec["url"], "parser": spec["parser"],
        "status": "never_fetched", "method": None, "attempted_utc": None,
        "retrieved_utc": None, "last_success_utc": None, "created_at": None,
        "last_modified": None, "sha256": None, "bytes": None, "error": None,
    }


def load_previous(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None


def build(
    previous: dict[str, Any] | None,
    read: Any,
    now: str,
) -> dict[str, Any]:
    """Assemble the feed. ``read(spec)`` returns (raw, url, last_modified, method)."""
    prev_sources = {s.get("id"): s for s in (previous or {}).get("sources", [])}
    feed: dict[str, Any] = {
        "schema": SCHEMA, "label": LABEL, "notice": NOTICE, "generated_utc": now,
        "status": "no_data", "sources": [], "demand": None, "supply_mix": None,
        "price": dict(PRICE),
    }
    for spec in SOURCES:
        parse, key = PARSERS[spec["id"]]
        source = blank_source(spec)
        prev = prev_sources.get(spec["id"])
        source["attempted_utc"] = now
        try:
            raw, final_url, last_modified, method = read(spec)
            parsed = parse(raw)
        except FeedError as exc:
            source["status"] = "error"
            source["error"] = str(exc)
            if prev and previous and previous.get(key):
                # Preserve the last good snapshot and its provenance, marked stale.
                for field in ("method", "retrieved_utc", "last_success_utc", "created_at",
                              "last_modified", "sha256", "bytes", "url"):
                    source[field] = prev.get(field)
                feed[key] = previous[key]
            feed["sources"].append(source)
            continue
        source.update({
            "status": "ok", "method": method, "url": final_url, "retrieved_utc": now,
            "last_success_utc": now, "created_at": parsed["created_at"],
            "last_modified": last_modified, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
        feed[key] = parsed["section"]
        feed["sources"].append(source)
    statuses = {s["status"] for s in feed["sources"]}
    has_data = feed["demand"] is not None or feed["supply_mix"] is not None
    if statuses == {"ok"}:
        feed["status"] = "ok"
    elif has_data:
        feed["status"] = "degraded"
    return feed


def network_reader(spec: dict[str, str]) -> tuple[bytes, str, str | None, str]:
    raw, final_url, last_modified = fetch(spec["url"])
    return raw, final_url, last_modified, "https"


def offline_reader(directory: Path):
    def read(spec: dict[str, str]) -> tuple[bytes, str, str | None, str]:
        path = directory / spec["file"]
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise FeedError(f"cannot read {path}: {exc}") from exc
        return raw, spec["url"], None, "local-file"
    return read


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--offline", type=Path, metavar="DIR",
                    help="read the report files from DIR instead of the network")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any source failed")
    args = ap.parse_args(argv)

    reader = offline_reader(args.offline) if args.offline else network_reader
    feed = build(load_previous(args.out), reader, utc_now())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for s in feed["sources"]:
        detail = s["sha256"][:16] if s["status"] == "ok" else s["error"]
        print(f"{s['id']:<28} {s['status']:<6} {detail}")
    print(f"feed status: {feed['status']} -> {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    failed = [s for s in feed["sources"] if s["status"] != "ok"]
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    sys.exit(main())
