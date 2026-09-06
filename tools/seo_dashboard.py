#!/usr/bin/env python3
"""ClearGlass SEO performance dashboard feed builder.

Pulls live search performance from Google Search Console and Bing Webmaster
Tools, joins it with the local technical audit (`tools/seo_audit.py`), and
writes the feeds that `seo-dashboard.html` renders:

    data/seo/performance.json   current + previous period, per query and page
    data/seo/alerts.json        threshold breaches worth a human's attention
    data/seo/history.jsonl      one append-only row per run, for trend lines

Credentials come from the environment and are never written to the feeds:

    GSC_PROPERTY            overrides config.gsc_property
    GSC_ACCESS_TOKEN        a ready OAuth access token, or …
    GSC_CLIENT_ID           … a refresh-token triple, exchanged at run time
    GSC_CLIENT_SECRET
    GSC_REFRESH_TOKEN
    BING_API_KEY            Bing Webmaster Tools API key
    BING_SITE_URL           defaults to config.site

Design rule: this tool never invents a number. Every connector reports its own
state — `live`, `unconfigured`, or `error` — and a metric with no source is
emitted as null so the dashboard can say "not connected" instead of showing a
plausible-looking zero.

    python3 tools/seo_dashboard.py            # fetch what is configured, write feeds
    python3 tools/seo_dashboard.py --dry-run  # print, write nothing
    python3 tools/seo_dashboard.py --days 28

stdlib only (urllib) — no SDK install needed in CI.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEO_DIR = ROOT / "data" / "seo"
CONFIG = SEO_DIR / "config.json"
PERF = SEO_DIR / "performance.json"
ALERTS = SEO_DIR / "alerts.json"
HISTORY = SEO_DIR / "history.jsonl"
AUDIT = SEO_DIR / "audit.json"

GSC_API = "https://searchconsole.googleapis.com/webmasters/v3"
GSC_TOKEN_URL = "https://oauth2.googleapis.com/token"
BING_API = "https://ssl.bing.com/webmaster/api.svc/json"
TIMEOUT = 30


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _post(url: str, payload: dict, headers: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Google Search Console
# ---------------------------------------------------------------------------
def gsc_token() -> str | None:
    """Return an access token, exchanging a refresh token when needed."""
    token = os.environ.get("GSC_ACCESS_TOKEN", "").strip()
    if token:
        return token

    cid = os.environ.get("GSC_CLIENT_ID", "").strip()
    secret = os.environ.get("GSC_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("GSC_REFRESH_TOKEN", "").strip()
    if not (cid and secret and refresh):
        return None

    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": secret,
        "refresh_token": refresh, "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(GSC_TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode()).get("access_token")


def gsc_query(prop: str, token: str, start: str, end: str,
              dimensions: list[str], limit: int = 500) -> list[dict]:
    url = f"{GSC_API}/sites/{urllib.parse.quote(prop, safe='')}/searchAnalytics/query"
    payload = {
        "startDate": start, "endDate": end,
        "dimensions": dimensions, "rowLimit": limit,
        "dataState": "final",
    }
    rows = _post(url, payload, {"Authorization": f"Bearer {token}"}).get("rows", [])
    out = []
    for r in rows:
        keys = r.get("keys", [])
        out.append({
            **{d: keys[i] for i, d in enumerate(dimensions) if i < len(keys)},
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": round(r.get("ctr", 0.0), 5),
            "position": round(r.get("position", 0.0), 2),
        })
    return out


def collect_gsc(cfg: dict, days: int) -> dict:
    prop = os.environ.get("GSC_PROPERTY", "").strip() or cfg.get("gsc_property", "")
    result = {"source": "google_search_console", "property": prop,
              "state": "unconfigured", "detail": "", "current": {}, "previous": {},
              "queries": [], "pages": [], "countries": [], "devices": []}
    if not prop:
        result["detail"] = "No GSC property configured (config.gsc_property or GSC_PROPERTY)."
        return result

    try:
        token = gsc_token()
    except Exception as exc:  # noqa: BLE001 — surface any auth failure verbatim
        result.update(state="error", detail=f"Token exchange failed: {exc}")
        return result
    if not token:
        result["detail"] = ("No credentials. Set GSC_ACCESS_TOKEN, or "
                            "GSC_CLIENT_ID + GSC_CLIENT_SECRET + GSC_REFRESH_TOKEN.")
        return result

    # GSC finalises data on a ~2 day lag; compare equal-length adjacent windows.
    end = _dt.date.today() - _dt.timedelta(days=2)
    start = end - _dt.timedelta(days=days - 1)
    prev_end = start - _dt.timedelta(days=1)
    prev_start = prev_end - _dt.timedelta(days=days - 1)

    def totals(rows: list[dict]) -> dict:
        clicks = sum(r["clicks"] for r in rows)
        impressions = sum(r["impressions"] for r in rows)
        weighted = sum(r["position"] * r["impressions"] for r in rows)
        return {
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round(clicks / impressions, 5) if impressions else 0.0,
            "position": round(weighted / impressions, 2) if impressions else None,
        }

    try:
        cur_q = gsc_query(prop, token, start.isoformat(), end.isoformat(), ["query"])
        prev_q = gsc_query(prop, token, prev_start.isoformat(), prev_end.isoformat(), ["query"])
        result["queries"] = cur_q
        result["pages"] = gsc_query(prop, token, start.isoformat(), end.isoformat(), ["page"])
        result["countries"] = gsc_query(prop, token, start.isoformat(), end.isoformat(), ["country"], 25)
        result["devices"] = gsc_query(prop, token, start.isoformat(), end.isoformat(), ["device"], 10)
        result["current"] = {"start": start.isoformat(), "end": end.isoformat(), **totals(cur_q)}
        result["previous"] = {"start": prev_start.isoformat(), "end": prev_end.isoformat(), **totals(prev_q)}
        result["state"] = "live"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")[:300]
        result.update(state="error", detail=f"HTTP {exc.code}: {detail}")
    except Exception as exc:  # noqa: BLE001
        result.update(state="error", detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Bing Webmaster Tools
# ---------------------------------------------------------------------------
def collect_bing(cfg: dict) -> dict:
    key = os.environ.get("BING_API_KEY", "").strip()
    site = os.environ.get("BING_SITE_URL", "").strip() or cfg.get("site", "")
    result = {"source": "bing_webmaster_tools", "site": site,
              "state": "unconfigured", "detail": "",
              "current": {}, "queries": [], "crawl": {}}
    if not key:
        result["detail"] = "No BING_API_KEY set."
        return result
    if not site:
        result["detail"] = "No site URL configured."
        return result

    def call(method: str, **params) -> dict:
        qs = urllib.parse.urlencode({"apikey": key, "siteUrl": site, **params})
        return _get(f"{BING_API}/{method}?{qs}")

    try:
        stats = call("GetRankAndTrafficStats").get("d", []) or []
        clicks = sum(r.get("Clicks", 0) for r in stats)
        impressions = sum(r.get("Impressions", 0) for r in stats)
        result["current"] = {
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round(clicks / impressions, 5) if impressions else 0.0,
            "days": len(stats),
        }

        queries = call("GetQueryStats").get("d", []) or []
        result["queries"] = [{
            "query": q.get("Query"),
            "clicks": q.get("Clicks", 0),
            "impressions": q.get("Impressions", 0),
            "position": q.get("AvgClickPosition"),
        } for q in queries[:500]]

        crawl = call("GetCrawlStats").get("d", []) or []
        result["crawl"] = {
            "crawled": sum(c.get("CrawledPages", 0) for c in crawl),
            "in_index": sum(c.get("InIndex", 0) for c in crawl),
            "errors": sum(c.get("CrawlErrors", 0) for c in crawl),
            "blocked_by_robots": sum(c.get("BlockedByRobotsTxt", 0) for c in crawl),
            "http_4xx": sum(c.get("HttpCode4xx", 0) for c in crawl),
            "http_5xx": sum(c.get("HttpCode5xx", 0) for c in crawl),
        }
        result["state"] = "live"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")[:300]
        result.update(state="error", detail=f"HTTP {exc.code}: {detail}")
    except Exception as exc:  # noqa: BLE001
        result.update(state="error", detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Keyword tracking
# ---------------------------------------------------------------------------
def track_keywords(cfg: dict, gsc: dict) -> dict:
    """Match configured target terms against live GSC query rows."""
    groups = cfg.get("keyword_groups", {})
    rows = {r["query"].lower(): r for r in gsc.get("queries", []) if r.get("query")}
    connected = gsc.get("state") == "live"

    out: dict[str, list] = {}
    for group, terms in groups.items():
        if group.startswith("_"):
            continue
        entries = []
        for term in terms:
            hit = rows.get(term.lower())
            entries.append({
                "keyword": term,
                "tracked": bool(hit),
                "clicks": hit["clicks"] if hit else (0 if connected else None),
                "impressions": hit["impressions"] if hit else (0 if connected else None),
                "position": hit["position"] if hit else None,
                # Partial matches show the term is earning impressions in a
                # longer query even when the exact phrase has no row.
                "related_impressions": sum(
                    r["impressions"] for q, r in rows.items()
                    if term.lower() in q and q != term.lower()
                ) if connected else None,
            })
        out[group] = entries
    return out


# ---------------------------------------------------------------------------
# Competitor comparison
# ---------------------------------------------------------------------------
def compare_competitors(cfg: dict, gsc: dict) -> dict:
    """Benchmark visibility against configured rivals.

    Neither GSC nor Bing WMT expose a competitor's data — a property only ever
    reports on itself. So this module scores ClearGlass from live data and
    carries rival rows only where an operator has supplied a measurement.
    Unverified rows stay flagged and are excluded from the gap calculation.
    """
    comp = cfg.get("competitors", {})
    domains = [d for d in comp.get("domains", []) if isinstance(d, dict)]

    own = None
    if gsc.get("state") == "live":
        cur = gsc.get("current", {})
        own = {
            "domain": "clearglassinc.com",
            "impressions": cur.get("impressions"),
            "clicks": cur.get("clicks"),
            "avg_position": cur.get("position"),
            "ranking_keywords": sum(
                1 for r in gsc.get("queries", []) if r.get("position", 99) <= 20
            ),
            "source": "google_search_console",
            "verified": True,
        }

    rivals = []
    for d in domains:
        rivals.append({
            "domain": d.get("domain"),
            "impressions": d.get("impressions"),
            "clicks": d.get("clicks"),
            "avg_position": d.get("avg_position"),
            "ranking_keywords": d.get("ranking_keywords"),
            "source": d.get("source", "manual"),
            "verified": bool(d.get("verified")),
            "measured": d.get("measured"),
        })

    scored = [r for r in rivals if r["verified"] and r.get("ranking_keywords") is not None]
    gap = None
    if own and scored:
        best = max(r["ranking_keywords"] for r in scored)
        gap = best - own["ranking_keywords"]

    return {
        "state": "live" if own else "unconfigured",
        "note": ("Search Console reports only on your own property. Rival rows must come "
                 "from a rank-tracking source and are marked unverified until they do."),
        "own": own,
        "competitors": rivals,
        "unverified_count": sum(1 for r in rivals if not r["verified"]),
        "keyword_gap_vs_best": gap,
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def build_alerts(cfg: dict, gsc: dict, bing: dict, audit: dict) -> list[dict]:
    th = cfg.get("alerts", {})
    alerts: list[dict] = []

    def add(level: str, kind: str, message: str, **extra) -> None:
        alerts.append({"level": level, "kind": kind, "message": message,
                       "detected": _now(), **extra})

    # --- connector health --------------------------------------------------
    for feed in (gsc, bing):
        if feed["state"] == "error":
            add("critical", "connector",
                f"{feed['source']} failed: {feed['detail']}", source=feed["source"])
        elif feed["state"] == "unconfigured":
            add("info", "connector",
                f"{feed['source']} not connected — {feed['detail']}", source=feed["source"])

    # --- traffic movement (GSC) -------------------------------------------
    cur, prev = gsc.get("current", {}), gsc.get("previous", {})
    floor = th.get("min_clicks_for_alert", 10)
    if cur and prev and prev.get("clicks", 0) >= floor:
        for metric, limit in (("clicks", th.get("clicks_drop_pct", 30)),
                              ("impressions", th.get("impressions_drop_pct", 35))):
            before, after = prev.get(metric, 0), cur.get(metric, 0)
            if before:
                delta = (after - before) / before * 100
                if delta <= -limit:
                    add("critical", "traffic_drop",
                        f"{metric.title()} fell {abs(delta):.0f}% "
                        f"({before:,} → {after:,}) versus the previous period.",
                        metric=metric, change_pct=round(delta, 1))

        pos_before, pos_after = prev.get("position"), cur.get("position")
        if pos_before and pos_after:
            slip = pos_after - pos_before  # larger position number = worse
            if slip >= th.get("position_drop_places", 5):
                add("warning", "position_drop",
                    f"Average position slipped {slip:.1f} places "
                    f"({pos_before:.1f} → {pos_after:.1f}).",
                    change=round(slip, 1))

    # --- index coverage ----------------------------------------------------
    if audit:
        totals = audit.get("totals", {})
        indexable, listed = totals.get("indexable", 0), totals.get("in_sitemap", 0)
        if indexable and listed < indexable:
            missing = indexable - listed
            pct = missing / indexable * 100
            add("warning" if pct >= th.get("indexed_drop_pct", 10) else "info",
                "index_coverage",
                f"{missing} indexable page(s) are absent from sitemap.xml "
                f"({pct:.0f}% of the indexable set).", missing=missing)

        if totals.get("errors"):
            add("critical", "technical",
                f"{totals['errors']} blocking technical error(s) in the local audit "
                f"— run `python3 tools/seo_audit.py` for detail.",
                count=totals["errors"])

        schema_errs = sum(n for c, n in audit.get("by_check", {}).items()
                          if c.startswith("schema."))
        if schema_errs:
            add("warning", "schema",
                f"{schema_errs} structured-data issue(s) detected — rich results at risk.",
                count=schema_errs)

    if bing.get("state") == "live":
        crawl = bing.get("crawl", {})
        if crawl.get("http_5xx"):
            add("critical", "crawl",
                f"Bing recorded {crawl['http_5xx']} 5xx response(s) while crawling.",
                count=crawl["http_5xx"])
        if crawl.get("blocked_by_robots"):
            add("warning", "crawl",
                f"Bing found {crawl['blocked_by_robots']} URL(s) blocked by robots.txt.",
                count=crawl["blocked_by_robots"])

    return alerts


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the ClearGlass SEO dashboard feeds")
    ap.add_argument("--days", type=int, default=28, help="comparison window length (default 28)")
    ap.add_argument("--dry-run", action="store_true", help="print the feed, write nothing")
    args = ap.parse_args(argv)

    cfg = load_json(CONFIG, {})
    if not cfg:
        print(f"error: {CONFIG.relative_to(ROOT)} is missing or invalid", file=sys.stderr)
        return 2

    audit = load_json(AUDIT, {})
    gsc = collect_gsc(cfg, args.days)
    bing = collect_bing(cfg)

    performance = {
        "generated": _now(),
        "site": cfg.get("site"),
        "window_days": args.days,
        "connectors": {
            "google_search_console": {"state": gsc["state"], "detail": gsc["detail"]},
            "bing_webmaster_tools": {"state": bing["state"], "detail": bing["detail"]},
            "local_audit": {
                "state": "live" if audit else "unconfigured",
                "detail": "" if audit else "Run `python3 tools/seo_audit.py --write` first.",
            },
        },
        "google": gsc,
        "bing": bing,
        "keywords": track_keywords(cfg, gsc),
        "competitors": compare_competitors(cfg, gsc),
        "indexation": {
            "pages_total": audit.get("totals", {}).get("pages"),
            "indexable": audit.get("totals", {}).get("indexable"),
            "in_sitemap": audit.get("totals", {}).get("in_sitemap"),
            "noindex": audit.get("totals", {}).get("noindex"),
            "with_schema": audit.get("totals", {}).get("with_schema"),
            "health_score": audit.get("score"),
            "bing_in_index": bing.get("crawl", {}).get("in_index"),
        },
    }
    alerts = build_alerts(cfg, gsc, bing, audit)
    alert_feed = {
        "generated": _now(),
        "counts": {
            "critical": sum(1 for a in alerts if a["level"] == "critical"),
            "warning": sum(1 for a in alerts if a["level"] == "warning"),
            "info": sum(1 for a in alerts if a["level"] == "info"),
        },
        "alerts": alerts,
    }

    if args.dry_run:
        print(json.dumps({"performance": performance, "alerts": alert_feed}, indent=2))
        return 0

    SEO_DIR.mkdir(parents=True, exist_ok=True)
    PERF.write_text(json.dumps(performance, indent=2) + "\n", encoding="utf-8")
    ALERTS.write_text(json.dumps(alert_feed, indent=2) + "\n", encoding="utf-8")

    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "at": performance["generated"],
            "gsc_state": gsc["state"],
            "clicks": gsc.get("current", {}).get("clicks"),
            "impressions": gsc.get("current", {}).get("impressions"),
            "position": gsc.get("current", {}).get("position"),
            "bing_clicks": bing.get("current", {}).get("clicks"),
            "indexable": performance["indexation"]["indexable"],
            "in_sitemap": performance["indexation"]["in_sitemap"],
            "health_score": performance["indexation"]["health_score"],
        }) + "\n")

    c = alert_feed["counts"]
    print(f"seo dashboard · GSC={gsc['state']} · Bing={bing['state']} · "
          f"alerts {c['critical']} critical / {c['warning']} warning / {c['info']} info")
    for a in alerts:
        if a["level"] in ("critical", "warning"):
            print(f"  [{a['level']}] {a['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
