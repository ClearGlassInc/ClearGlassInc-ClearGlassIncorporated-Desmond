# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""IESO public feed: parsers fail closed, failures never erase good data.

The fixtures below are hand-written from IESO's published layout (PUB_Demand
columns Date, Hour, Market Demand, Ontario Demand; fuel report elements
DailyData/Day/HourlyData/Hour/FuelTotal/Fuel/Output/OutputQuality). They are
not captured IESO files, so they pin the parser's contract, not IESO's.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.ieso_public_feed import (
    DEMAND,
    FUEL,
    LABEL,
    OUT_PATH,
    SCHEMA,
    FeedError,
    build,
    main,
    parse_demand,
    parse_fuel,
)

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "GridShield-Ontario-V6-0-ULTRA-FINAL.html"
NOW = "2026-09-30T12:00:00Z"

DEMAND_CSV = (
    "\\\\Hourly Demand Report,,,\n"
    "\\\\Created at 2026-09-30 11:00:12,,,\n"
    "\\\\For 2026,,,\n"
    "Date,Hour,Market Demand,Ontario Demand\n"
    "2026/09/30,9,17100,15200\n"
    "2026-09-30,10,17600,15650\n"
    "2026-09-30,11,,\n"
).encode()

FUEL_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
<DocHeader><DocTitle>Output by Fuel Type Hourly Report</DocTitle>
<CreatedAt>2026-09-30T11:00:09</CreatedAt></DocHeader>
<DocBody><Year>2026</Year>
<DailyData><Day>2026-09-30</Day>
<HourlyData><Hour>10</Hour>
<FuelTotal><Fuel>NUCLEAR</Fuel><EnergyValue><OutputQuality>0</OutputQuality><Output>9000</Output></EnergyValue></FuelTotal>
<FuelTotal><Fuel>HYDRO</Fuel><EnergyValue><OutputQuality>0</OutputQuality><Output>4000</Output></EnergyValue></FuelTotal>
<FuelTotal><Fuel>GAS</Fuel><EnergyValue><OutputQuality>0</OutputQuality><Output>1000</Output></EnergyValue></FuelTotal>
</HourlyData>
<HourlyData><Hour>11</Hour>
<FuelTotal><Fuel>NUCLEAR</Fuel><EnergyValue><OutputQuality>0</OutputQuality><Output>9100</Output></EnergyValue></FuelTotal>
<FuelTotal><Fuel>HYDRO</Fuel><EnergyValue><OutputQuality>-1</OutputQuality></EnergyValue></FuelTotal>
</HourlyData>
</DailyData>
</DocBody></Document>
"""


def reader_for(files: dict[str, bytes | Exception]):
    def read(spec):
        item = files[spec["id"]]
        if isinstance(item, Exception):
            raise item
        return item, spec["url"], "Tue, 30 Sep 2026 11:00:15 GMT", "https"
    return read


# ── demand ────────────────────────────────────────────────────────────────────

def test_demand_takes_latest_published_hour():
    parsed = parse_demand(DEMAND_CSV)
    assert parsed["created_at"] == "2026-09-30 11:00:12"
    section = parsed["section"]
    assert (section["date"], section["hour_ending"]) == ("2026-09-30", 10)
    assert section["ontario_mw"] == 15650 and section["market_mw"] == 17600
    assert [r["date"] for r in section["series"]] == ["2026-09-30", "2026-09-30"]


@pytest.mark.parametrize("bad", [
    DEMAND_CSV.replace(b"Ontario Demand", b"Ontario Load"),
    DEMAND_CSV.replace(b"15650", b"156500"),
    DEMAND_CSV.replace(b",10,", b",25,"),
    DEMAND_CSV.replace(b"2026-09-30,10", b"30/09/2026,10"),
    b"\\\\Hourly Demand Report,,,\n",
])
def test_demand_fails_closed(bad):
    with pytest.raises(FeedError):
        parse_demand(bad)


# ── fuel ──────────────────────────────────────────────────────────────────────

def test_fuel_skips_incomplete_hour_and_computes_mix():
    parsed = parse_fuel(FUEL_XML)
    assert parsed["created_at"] == "2026-09-30T11:00:09"
    section = parsed["section"]
    assert section["hour_ending"] == 10  # HE11 lacks HYDRO output
    assert section["total_mw"] == 14000
    assert [f["fuel"] for f in section["fuels"]] == ["NUCLEAR", "HYDRO", "GAS"]
    assert abs(sum(f["pct"] for f in section["fuels"]) - 100) < 0.5


@pytest.mark.parametrize("bad", [
    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "a">]><Document/>',
    b"<Document><DocBody></DocBody></Document>",
    b"<Document><DailyData><Day>2026-09-30</Day>",
    FUEL_XML.replace(b"<Output>9000</Output>", b"<Output>90000</Output>"),
    FUEL_XML.replace(b"<Output>", b"<Output>n/a").replace(b"n/a9", b"9"),
])
def test_fuel_fails_closed(bad):
    with pytest.raises(FeedError):
        parse_fuel(bad)


# ── assembly ──────────────────────────────────────────────────────────────────

def test_build_ok_records_provenance():
    feed = build(None, reader_for({DEMAND["id"]: DEMAND_CSV, FUEL["id"]: FUEL_XML}), NOW)
    assert feed["status"] == "ok"
    demand_src = next(s for s in feed["sources"] if s["id"] == DEMAND["id"])
    assert demand_src["sha256"] == hashlib.sha256(DEMAND_CSV).hexdigest()
    assert demand_src["bytes"] == len(DEMAND_CSV)
    assert demand_src["retrieved_utc"] == NOW
    assert demand_src["last_modified"] == "Tue, 30 Sep 2026 11:00:15 GMT"
    assert feed["price"]["status"] == "not_wired"


def test_failure_preserves_last_good_snapshot_and_says_so():
    good = build(None, reader_for({DEMAND["id"]: DEMAND_CSV, FUEL["id"]: FUEL_XML}), NOW)
    later = "2026-09-30T13:00:00Z"
    feed = build(good, reader_for({
        DEMAND["id"]: FeedError("HTTP 503 from IESO"),
        FUEL["id"]: FUEL_XML,
    }), later)
    assert feed["status"] == "degraded"
    src = next(s for s in feed["sources"] if s["id"] == DEMAND["id"])
    assert src["status"] == "error" and src["error"] == "HTTP 503 from IESO"
    assert src["attempted_utc"] == later
    assert src["retrieved_utc"] == NOW  # the preserved data's real age
    assert feed["demand"] == good["demand"]


def test_no_previous_and_all_failing_publishes_no_numbers():
    feed = build(None, reader_for({
        DEMAND["id"]: FeedError("x"), FUEL["id"]: FeedError("y"),
    }), NOW)
    assert feed["status"] == "no_data"
    assert feed["demand"] is None and feed["supply_mix"] is None


def test_offline_cli_writes_feed(tmp_path):
    (tmp_path / DEMAND["file"]).write_bytes(DEMAND_CSV)
    (tmp_path / FUEL["file"]).write_bytes(FUEL_XML)
    out = tmp_path / "feed.json"
    assert main(["--offline", str(tmp_path), "--out", str(out), "--strict"]) == 0
    feed = json.loads(out.read_text())
    assert feed["status"] == "ok"
    assert {s["method"] for s in feed["sources"]} == {"local-file"}


def test_strict_exits_nonzero_on_failure(tmp_path):
    out = tmp_path / "feed.json"
    assert main(["--offline", str(tmp_path), "--out", str(out), "--strict"]) == 1
    assert json.loads(out.read_text())["status"] == "no_data"


# ── committed feed and the page that reads it ─────────────────────────────────

def test_committed_feed_is_honest():
    feed = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    assert feed["schema"] == SCHEMA and feed["label"] == LABEL
    assert feed["price"]["status"] == "not_wired"
    for src in feed["sources"]:
        if src["retrieved_utc"]:
            assert re.fullmatch(r"[0-9a-f]{64}", src["sha256"])
        else:
            assert src["sha256"] is None
    if feed["status"] == "no_data":
        assert feed["demand"] is None and feed["supply_mix"] is None


def test_page_reads_the_feed_and_invents_no_grid_numbers():
    html = PAGE.read_text(encoding="utf-8")
    assert "data/grid/ieso-public.json" in html
    assert "noindex" not in html
    # Removed fabrications: random demand/price, fake signatures and hashes.
    for phrase in ("18000 + Math.sin", "Manifest signed HSM", "Verified independently",
                   "a3f9c1", "$18/MWh", "Retrieval: 0.3s ago", ">STABLE<"):
        assert phrase not in html, phrase
