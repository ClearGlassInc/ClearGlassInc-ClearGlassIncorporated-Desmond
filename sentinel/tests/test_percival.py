"""PERCIVAL — governed website-percival agent tests."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.capability import Tier
from sentinel.identity import AgentIdentity
from sentinel.mission_memory import MissionMemory
from sentinel.percival import (
    Action,
    Finding,
    InboundLead,
    Severity,
    Percival,
    audit_brand,
    audit_links,
    audit_page,
    audit_sitemap,
    draft_booking,
    govern,
    qualify_lead,
    rank,
)


def _ops_identity(default_tier: Tier) -> AgentIdentity:
    return AgentIdentity(
        instance_id="percival-live",
        sponsor="Desmond",
        purpose="governed website operations",
        allowed_scopes={"operations"},
        default_tier=default_tier,
    )

GOOD = ("<html lang='en'><head><title>T</title>"
        "<meta name='description' content='d'>"
        "<link rel='canonical' href='x'>"
        "<meta property='og:title' content='T'>"
        "<meta property='og:description' content='d'></head>"
        "<body><img src='a.png' alt='a'></body></html>")
BARE = "<html><head></head><body><img src='a.png'></body></html>"


# ── audits ──────────────────────────────────────────────────────────────────

def test_audit_page_clean_on_good_html() -> None:
    assert audit_page("p.html", GOOD) == []


def test_audit_page_flags_seo_and_a11y_gaps() -> None:
    kinds = {f.kind for f in audit_page("p.html", BARE)}
    assert {"missing_title", "missing_meta_description", "missing_canonical",
            "missing_lang", "missing_img_alt", "missing_og_tags"} <= kinds


def test_audit_page_flags_partial_og_tags() -> None:
    html = GOOD.replace("<meta property='og:description' content='d'>", "")
    kinds = {f.kind for f in audit_page("p.html", html)}
    assert "missing_og_tags" in kinds


def test_missing_og_tags_is_safe_autofix() -> None:
    f = Finding("missing_og_tags", "seo", "p.html", "", Severity.LOW, technical_risk=1)
    assert govern(f).action is Action.AUTO_FIX


def test_audit_sitemap_detects_drift_both_ways() -> None:
    sm = "<urlset><url><loc>https://x/dead.html</loc></url></urlset>"
    kinds = {(f.kind, f.page) for f in audit_sitemap(sm, {"live.html"})}
    assert ("sitemap_dead_url", "dead.html") in kinds
    assert ("sitemap_missing_page", "live.html") in kinds


def test_audit_links_finds_broken_internal() -> None:
    pages = {"a.html": '<a href="missing.html">x</a>', "b.html": '<a href="a.html">ok</a>'}
    found = audit_links(pages)
    assert [f.kind for f in found] == ["broken_link"]
    assert found[0].page == "a.html"


def test_audit_links_normalizes_dot_slash_and_skips_subdirs() -> None:
    pages = {"a.html": '<a href="./b.html">x</a><a href="legal/terms.html">y</a>',
             "b.html": "<p>ok</p>"}
    assert audit_links(pages) == []   # ./b.html resolves; subdir is out of scope


def test_audit_sitemap_skips_subdirectory_locs() -> None:
    sm = ("<urlset><url><loc>https://x/legal/terms.html</loc></url>"
          "<url><loc>https://x/gone.html</loc></url></urlset>")
    kinds = {(f.kind, f.page) for f in audit_sitemap(sm, {"live.html"})}
    assert ("sitemap_dead_url", "gone.html") in kinds
    assert all(p != "terms.html" for k, p in kinds if k == "sitemap_dead_url")


def test_audit_brand_flags_warm_drift_but_keeps_alert_pink() -> None:
    assert audit_brand("p.html", "<i style='color:#ff8800'>")[0].kind == "brand_color_drift"
    assert audit_brand("p.html", "<i style='color:#f472b6'>") == []


# ── governance ──────────────────────────────────────────────────────────────

def test_govern_autofix_only_for_safelisted_low_risk() -> None:
    f = Finding("missing_canonical", "seo", "p.html", "", Severity.LOW,
                technical_risk=1)
    assert govern(f).action is Action.AUTO_FIX


def test_govern_escalates_security_and_high_severity() -> None:
    sec = Finding("exposed_token", "security", "p.html", "", Severity.LOW)
    assert govern(sec).action is Action.ESCALATE
    high = Finding("missing_canonical", "seo", "p.html", "", Severity.HIGH)
    assert govern(high).action is Action.ESCALATE


def test_govern_fails_closed_on_risky_unknowns() -> None:
    risky = Finding("mystery", "content", "p.html", "", Severity.LOW,
                    technical_risk=5)
    assert govern(risky).action is Action.ESCALATE


def test_rank_orders_by_value_and_impact() -> None:
    low = Finding("a", "ux", "p", "", business_value=1, user_impact=1, technical_risk=1)
    big = Finding("b", "ux", "p", "", business_value=5, user_impact=5, technical_risk=1)
    assert rank([low, big])[0] is big


# ── revenue (inbound-only, governed) ────────────────────────────────────────

def test_lead_without_consent_scores_zero() -> None:
    lead = InboundLead("Acme", "ops@acme.com", "security-audit", "25k+", consent=False)
    score, tier = qualify_lead(lead)
    assert score == 0 and tier.startswith("NO_CONSENT")


def test_lead_qualification_tiers() -> None:
    hot = InboundLead("Acme", "ops@acme.com", "security-audit", "25k+", consent=True)
    assert qualify_lead(hot) == (10, "HOT")
    nurture = InboundLead("Solo", "a@b.c", "other", "<5k", consent=True)
    assert qualify_lead(nurture)[1] == "NURTURE"


def test_booking_is_a_draft_requiring_human_send() -> None:
    lead = InboundLead("Acme", "ops@acme.com", "web-design", "5-25k", consent=True)
    art = draft_booking(lead, slot_utc="2026-06-15T15:00")
    assert art["requires_human_send"] == "true"
    assert art["mailto"].startswith("mailto:ops@acme.com")


# ── the agent end-to-end ────────────────────────────────────────────────────

def test_percival_scan_and_dry_run_apply(tmp_path: pathlib.Path) -> None:
    (tmp_path / "good.html").write_text(GOOD)
    (tmp_path / "bare.html").write_text(BARE)
    (tmp_path / "sitemap.xml").write_text(
        "<urlset><url><loc>https://x/good.html</loc></url>"
        "<url><loc>https://x/ghost.html</loc></url></urlset>")
    s = Percival(tmp_path, clock=lambda: "2026-06-10T00:00:00Z")
    report = s.scan()

    kinds = {f.kind for f in report.findings}
    assert "sitemap_dead_url" in kinds and "missing_title" in kinds
    # sitrep brief is human-readable and locates the surface
    brief = report.brief()
    assert "PERCIVAL SITREP" in brief and "www.clearglassinc.com" in brief

    # default apply is a DRY RUN — no silent writes
    applied = s.apply(report)
    assert applied and all(a.startswith("DRY-RUN") for a in applied)
    # every action is on the tamper-evident audit chain
    assert s.audit.verify()
    assert any(e.action == "percival.scan" for e in s.audit.entries)


def test_percival_never_autofixes_escalated_items(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    s = Percival(tmp_path)
    report = s.scan()
    auto = {d.finding.kind for d in report.decisions if d.action is Action.AUTO_FIX}
    assert auto <= {"missing_meta_description", "missing_canonical",
                    "missing_img_alt", "sitemap_missing_page", "sitemap_dead_url",
                    "trailing_whitespace", "missing_og_tags"}


def test_audit_page_ignores_tags_inside_script() -> None:
    # an inline engine whose source contains an <img ...> regex literal must NOT
    # be read as a real image lacking alt text
    html = ("<html lang='en'><head><title>T</title>"
            "<meta name='description' content='d'>"
            "<link rel='canonical' href='x'>"
            "<meta property='og:title' content='T'>"
            "<meta property='og:description' content='d'></head><body>"
            "<script>var re=/<img\\b[^>]*>/gi;</script></body></html>")
    assert audit_page("p.html", html) == []


# ── control-plane wiring (identity -> governor -> capability -> audit) ───────

def test_governor_wired_change_identity_permits_writes(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    # A CHANGE-scoped, sponsored identity may perform internal writes.
    s = Percival(tmp_path, identity=_ops_identity(Tier.CHANGE))
    report = s.scan()
    applied = s.apply(report, allow_writes=True)
    assert applied and not any(a.startswith("BLOCKED") for a in applied)
    assert s.audit.verify()


def test_governor_wired_readonly_identity_blocks_writes(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    # A READ_ONLY identity cannot execute internal writes — every fix is blocked
    # by the sovereign governor, and nothing is applied.
    s = Percival(tmp_path, identity=_ops_identity(Tier.READ_ONLY))
    report = s.scan()
    applied = s.apply(report, allow_writes=True)
    assert applied and all(a.startswith("BLOCKED") for a in applied)
    assert s.audit.verify()


def test_stopped_identity_blocks_all_writes(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    ident = _ops_identity(Tier.CHANGE)
    ident.stop()  # halted instance may touch nothing
    s = Percival(tmp_path, identity=ident)
    report = s.scan()
    applied = s.apply(report, allow_writes=True)
    assert applied and all(a.startswith("BLOCKED") for a in applied)


def test_scan_records_one_summary_to_memory(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    mem = MissionMemory()
    s = Percival(tmp_path, clock=lambda: "2026-06-10T00:00:00Z", memory=mem)
    s.scan()
    hist = mem.items("decision_history")
    assert len(hist) == 1                                  # one summary, not per-finding
    assert hist[0].source == "percival.scan"
    assert "findings" in hist[0].content


def test_recent_scans_gives_cross_run_continuity(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    mem = MissionMemory()
    clock = iter(["2026-06-10T00:00:00Z", "2026-06-11T00:00:00Z", "2026-06-12T00:00:00Z"])
    s = Percival(tmp_path, clock=lambda: next(clock), memory=mem)
    for _ in range(3):
        s.scan()
    recent = s.recent_scans(limit=2)
    assert len(recent) == 2                                # newest window
    assert "2026-06-12" in recent[-1]                      # most recent last


def test_memory_persists_across_agent_instances(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    path = tmp_path / "mission.json"
    Percival(tmp_path, clock=lambda: "2026-06-10T00:00:00Z",
             memory=MissionMemory(path)).scan()
    # A fresh agent over the same store recalls the prior run — no fabrication.
    revived = Percival(tmp_path, memory=MissionMemory(path))
    assert len(revived.recent_scans()) == 1


def test_no_memory_means_no_history(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    s = Percival(tmp_path)
    s.scan()
    assert s.recent_scans() == []                          # stateless, does not fabricate


def test_no_identity_preserves_legacy_write_behavior(tmp_path: pathlib.Path) -> None:
    (tmp_path / "bare.html").write_text(BARE)
    # Without an identity, real writes proceed under the legacy AUTO_FIX policy
    # (no governor gating, no BLOCKED entries).
    s = Percival(tmp_path)
    report = s.scan()
    applied = s.apply(report, allow_writes=True)
    assert applied and not any(a.startswith("BLOCKED") for a in applied)


def test_index_is_exempt_from_sitemap_drift() -> None:
    # index.html is represented by "/" in the sitemap; must not be flagged missing
    found = audit_sitemap("<urlset></urlset>", {"index.html", "real.html"})
    pages = {f.page for f in found if f.kind == "sitemap_missing_page"}
    assert "index.html" not in pages and "real.html" in pages
