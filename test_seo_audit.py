"""Tests for the SEO audit engine and dashboard feed builder.

The audit gates CI, so its severity grading has to be exact: an `error` must
mean "this genuinely blocks discovery or serving", because anything else turns
the gate into noise people learn to ignore.

The dashboard's contract is narrower and stricter — it must never invent a
number. A metric with no source is `null`, never a plausible-looking zero.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


seo_audit = _load("seo_audit")
seo_dashboard = _load("seo_dashboard")


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://www.clearglassinc.com/{name}">
{robots}
{schema}
</head>
<body>{body}</body>
</html>"""


def write_page(tmp: Path, name: str, *, title="A Reasonable Page Title About Things",
               desc="A" * 120, robots="", schema="", body="<h1>Heading</h1>") -> Path:
    p = tmp / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(PAGE.format(title=title, desc=desc, name=name, robots=robots,
                             schema=schema, body=body), encoding="utf-8")
    return p


def audit_one(tmp: Path, path: Path, *, in_sitemap=True, disallow=()) -> list[dict]:
    findings: list[dict] = []
    listed = {path.relative_to(tmp).as_posix()} if in_sitemap else set()
    monkey_root = seo_audit.ROOT
    seo_audit.ROOT = tmp
    try:
        seo_audit.audit_page(path, listed, list(disallow), findings)
    finally:
        seo_audit.ROOT = monkey_root
    return findings


def checks(findings: list[dict]) -> set[str]:
    return {f["check"] for f in findings}


class TestSeverityGrading:
    """Errors are reserved for conditions that actually break indexing."""

    def test_clean_page_produces_no_findings(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "clean.html")
        assert not audit_one(tmp_path, page)

    def test_missing_title_is_an_error(self, tmp_path: Path) -> None:
        page = tmp_path / "x.html"
        page.write_text("<html lang='en'><head><meta name='viewport' content='w'>"
                        "<meta name='description' content='" + "d" * 120 + "'>"
                        "<link rel='canonical' href='u'></head><body><h1>H</h1></body></html>",
                        encoding="utf-8")
        found = audit_one(tmp_path, page)
        assert any(f["check"] == "title.missing" and f["level"] == "error" for f in found)

    def test_noindex_page_in_sitemap_is_a_warning_not_an_error(self, tmp_path: Path) -> None:
        # noindex wins regardless, so the page never enters the index. The cost
        # is wasted crawl budget — worth flagging, but it breaks nothing.
        page = write_page(tmp_path, "internal.html",
                          robots='<meta name="robots" content="noindex">')
        found = audit_one(tmp_path, page, in_sitemap=True)
        conflict = [f for f in found if f["check"] == "index.conflict"]
        assert conflict, "expected the noindex/sitemap conflict to be reported"
        assert conflict[0]["level"] == "warn"

    def test_robots_blocked_page_in_sitemap_is_an_error(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "blocked.html")
        found = audit_one(tmp_path, page, in_sitemap=True, disallow=["/blocked.html"])
        conflict = [f for f in found if f["check"] == "index.conflict"]
        assert conflict and conflict[0]["level"] == "error"

    def test_noindex_page_is_exempt_from_content_scoring(self, tmp_path: Path) -> None:
        # A deliberately internal page must not be judged on title or description
        # length — it is not competing for a snippet.
        page = write_page(tmp_path, "app.html", title="Hi", desc="short",
                          robots='<meta name="robots" content="noindex">', body="")
        found = audit_one(tmp_path, page, in_sitemap=False)
        assert not (checks(found) & {"title.length", "description.length", "h1.missing"})

    def test_indexable_page_absent_from_sitemap_warns(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "lonely.html")
        assert "sitemap.missing" in checks(audit_one(tmp_path, page, in_sitemap=False))


class TestOnPageSignals:
    def test_overlong_title_and_description_are_flagged(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "long.html", title="T" * 90, desc="D" * 300)
        assert {"title.length", "description.length"} <= checks(audit_one(tmp_path, page))

    def test_missing_h1_is_flagged(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "noh1.html", body="<h2>Only a subheading</h2>")
        assert "h1.missing" in checks(audit_one(tmp_path, page))

    def test_h1_rendered_only_by_javascript_does_not_count(self, tmp_path: Path) -> None:
        # Crawlers reading raw HTML see no heading here, which is the whole point.
        page = write_page(tmp_path, "jsh1.html",
                          body="<script>document.write('<h1>Hi</h1>')</script>")
        assert "h1.missing" in checks(audit_one(tmp_path, page))

    def test_multiple_h1_is_flagged(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "two.html", body="<h1>One</h1><h1>Two</h1>")
        assert "h1.multiple" in checks(audit_one(tmp_path, page))

    def test_duplicate_metadata_is_flagged_across_routes(self) -> None:
        records = {
            "a.html": {"indexable": True, "title": "Same", "description": "A", "canonical": "u1"},
            "b.html": {"indexable": True, "title": "Same", "description": "B", "canonical": "u2"},
        }
        found: list[dict] = []
        seo_audit.audit_uniqueness(records, found)
        assert any(item["check"] == "title.duplicate" for item in found)


class TestStructuredData:
    def test_unparseable_json_ld_is_an_error(self, tmp_path: Path) -> None:
        page = write_page(tmp_path, "bad.html",
                          schema='<script type="application/ld+json">{oops,}</script>')
        found = audit_one(tmp_path, page)
        assert any(f["check"] == "schema.parse" and f["level"] == "error" for f in found)

    def test_missing_required_property_is_flagged(self, tmp_path: Path) -> None:
        blob = json.dumps({"@context": "https://schema.org", "@type": "Organization",
                           "name": "ClearGlass Inc"})  # no url
        page = write_page(tmp_path, "org.html",
                          schema=f'<script type="application/ld+json">{blob}</script>')
        found = audit_one(tmp_path, page)
        assert any(f["check"] == "schema.required" and "url" in f["message"] for f in found)

    def test_complete_organization_passes(self, tmp_path: Path) -> None:
        blob = json.dumps({"@context": "https://schema.org", "@type": "Organization",
                           "name": "ClearGlass Inc", "url": "https://www.clearglassinc.com"})
        page = write_page(tmp_path, "org2.html",
                          schema=f'<script type="application/ld+json">{blob}</script>')
        assert "schema.required" not in checks(audit_one(tmp_path, page))

    def test_nested_nodes_inside_a_graph_are_reached(self, tmp_path: Path) -> None:
        blob = json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "name": "P",
             "publisher": {"@type": "Organization", "name": "Nested"}}]})
        page = write_page(tmp_path, "graph.html",
                          schema=f'<script type="application/ld+json">{blob}</script>')
        found = audit_one(tmp_path, page)
        assert any("Organization" in f["message"] for f in found)


class TestLiveSite:
    """The committed site must stay free of blocking errors."""

    def test_repository_audit_has_no_errors(self) -> None:
        report = seo_audit.build_report()
        errors = [f for f in report["findings"] if f["level"] == "error"]
        assert not errors, f"blocking SEO errors: {errors}"

    def test_every_indexable_page_is_in_the_sitemap(self) -> None:
        report = seo_audit.build_report()
        missing = [f["page"] for f in report["findings"] if f["check"] == "sitemap.missing"]
        assert not missing, f"indexable pages absent from sitemap.xml: {missing}"

    def test_every_json_ld_block_on_the_site_parses(self) -> None:
        report = seo_audit.build_report()
        assert not [f for f in report["findings"] if f["check"] == "schema.parse"]

    def test_no_broken_internal_links(self) -> None:
        report = seo_audit.build_report()
        broken = [f"{f['page']}: {f['message']}" for f in report["findings"]
                  if f["check"] == "link.broken"]
        assert not broken, f"broken internal links: {broken}"


class TestDashboardHonesty:
    """The dashboard must never present an unsourced number as data."""

    def test_connectors_report_unconfigured_without_credentials(self, monkeypatch) -> None:
        for var in ("GSC_ACCESS_TOKEN", "GSC_CLIENT_ID", "GSC_CLIENT_SECRET",
                    "GSC_REFRESH_TOKEN", "GSC_PROPERTY", "BING_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        cfg = {"site": "https://www.clearglassinc.com/", "gsc_property": "sc-domain:example.com"}
        assert seo_dashboard.collect_gsc(cfg, 28)["state"] == "unconfigured"
        assert seo_dashboard.collect_bing(cfg)["state"] == "unconfigured"

    def test_untracked_keywords_are_null_not_zero_when_disconnected(self) -> None:
        cfg = {"keyword_groups": {"g": ["some term"]}}
        gsc = {"state": "unconfigured", "queries": []}
        row = seo_dashboard.track_keywords(cfg, gsc)["g"][0]
        assert row["clicks"] is None and row["impressions"] is None
        assert row["position"] is None and row["tracked"] is False

    def test_untracked_keywords_are_zero_when_connected(self) -> None:
        # Connected but with no row for the term genuinely means zero.
        cfg = {"keyword_groups": {"g": ["some term"]}}
        gsc = {"state": "live", "queries": [{"query": "other", "clicks": 1,
                                             "impressions": 2, "position": 3.0}]}
        row = seo_dashboard.track_keywords(cfg, gsc)["g"][0]
        assert row["clicks"] == 0 and row["tracked"] is False

    def test_partial_matches_surface_as_related_impressions(self) -> None:
        cfg = {"keyword_groups": {"g": ["phipa readiness"]}}
        gsc = {"state": "live", "queries": [
            {"query": "phipa readiness checklist ontario", "clicks": 2,
             "impressions": 40, "position": 12.0}]}
        row = seo_dashboard.track_keywords(cfg, gsc)["g"][0]
        assert row["tracked"] is False and row["related_impressions"] == 40

    def test_competitor_rows_stay_unverified_until_measured(self) -> None:
        cfg = {"competitors": {"domains": [{"domain": "rival.com", "ranking_keywords": 500}]}}
        gsc = {"state": "live", "current": {"clicks": 1, "impressions": 2, "position": 3.0},
               "queries": []}
        out = seo_dashboard.compare_competitors(cfg, gsc)
        assert out["competitors"][0]["verified"] is False
        assert out["unverified_count"] == 1
        # An unverified rival must not drive the gap number.
        assert out["keyword_gap_vs_best"] is None


class TestAlerting:
    def _cfg(self) -> dict:
        return {"alerts": {"clicks_drop_pct": 30, "impressions_drop_pct": 35,
                           "position_drop_places": 5, "min_clicks_for_alert": 10}}

    def _gsc(self, cur: dict, prev: dict) -> dict:
        return {"source": "gsc", "state": "live", "detail": "",
                "current": cur, "previous": prev, "queries": []}

    def test_traffic_collapse_raises_critical(self) -> None:
        gsc = self._gsc({"clicks": 40, "impressions": 900, "position": 12.0},
                        {"clicks": 100, "impressions": 2000, "position": 11.0})
        bing = {"source": "bing", "state": "unconfigured", "detail": "", "crawl": {}}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        drops = [a for a in alerts if a["kind"] == "traffic_drop"]
        assert drops and all(a["level"] == "critical" for a in drops)

    def test_stable_traffic_raises_no_traffic_alert(self) -> None:
        gsc = self._gsc({"clicks": 102, "impressions": 2010, "position": 11.0},
                        {"clicks": 100, "impressions": 2000, "position": 11.0})
        bing = {"source": "bing", "state": "unconfigured", "detail": "", "crawl": {}}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        assert not [a for a in alerts if a["kind"] in ("traffic_drop", "position_drop")]

    def test_low_traffic_sites_do_not_trip_percentage_alarms(self) -> None:
        # 5 -> 2 clicks is a 60% drop but statistically meaningless.
        gsc = self._gsc({"clicks": 2, "impressions": 30, "position": 12.0},
                        {"clicks": 5, "impressions": 60, "position": 11.0})
        bing = {"source": "bing", "state": "unconfigured", "detail": "", "crawl": {}}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        assert not [a for a in alerts if a["kind"] == "traffic_drop"]

    def test_position_slip_raises_warning(self) -> None:
        gsc = self._gsc({"clicks": 95, "impressions": 2000, "position": 18.0},
                        {"clicks": 100, "impressions": 2000, "position": 11.0})
        bing = {"source": "bing", "state": "unconfigured", "detail": "", "crawl": {}}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        slip = [a for a in alerts if a["kind"] == "position_drop"]
        assert slip and slip[0]["level"] == "warning"

    def test_bing_server_errors_raise_critical(self) -> None:
        bing = {"source": "bing", "state": "live", "detail": "",
                "crawl": {"http_5xx": 3, "blocked_by_robots": 2}}
        gsc = {"source": "gsc", "state": "unconfigured", "detail": "",
               "current": {}, "previous": {}, "queries": []}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        assert any(a["kind"] == "crawl" and a["level"] == "critical" for a in alerts)

    def test_missing_connectors_are_info_not_failures(self) -> None:
        # An unwired connector is a setup task, not a visibility regression.
        gsc = {"source": "gsc", "state": "unconfigured", "detail": "no creds",
               "current": {}, "previous": {}, "queries": []}
        bing = {"source": "bing", "state": "unconfigured", "detail": "no key", "crawl": {}}
        alerts = seo_dashboard.build_alerts(self._cfg(), gsc, bing, {})
        assert alerts and all(a["level"] == "info" for a in alerts)


class TestConfig:
    def test_shipped_config_is_valid(self) -> None:
        cfg = json.loads((ROOT / "data" / "seo" / "config.json").read_text(encoding="utf-8"))
        assert cfg["site"].startswith("https://")
        groups = {k: v for k, v in cfg["keyword_groups"].items() if not k.startswith("_")}
        assert groups, "expected at least one keyword group"
        for name, terms in groups.items():
            assert terms, f"keyword group {name} is empty"
            assert all(isinstance(t, str) and t == t.lower() for t in terms), \
                f"keyword group {name} must be lowercase for case-insensitive matching"

    def test_dashboard_page_is_noindex(self) -> None:
        # The internal dashboard must never be indexed.
        html = (ROOT / "seo-dashboard.html").read_text(encoding="utf-8")
        assert "noindex" in html

    def test_dashboard_page_is_not_in_the_sitemap(self) -> None:
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        assert "seo-dashboard.html" not in sitemap


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
