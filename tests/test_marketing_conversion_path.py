from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_has_one_prominent_entry_offer_and_retains_existing_paths() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="offers/security-quick-audit.html" class="btn btn-crystal"' in homepage
    assert "Start with Security Quick-Audit · CAD $249" in homepage
    assert 'href="#contact" class="btn btn-glass">Request a Strategic Brief' in homepage
    assert 'href="#services" class="btn btn-glass">View Capabilities' in homepage
    assert 'href="#founder" class="btn btn-glass">Founder Profile' in homepage
    assert 'class="hero-entry-offer"' in homepage
    assert ".hero-entry-offer{" in homepage
    assert "The delivery target starts after scope, written authorization, and required evidence are complete." in homepage


def test_homepage_metadata_matches_a_clearer_commercial_entry_point() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")

    assert '<meta name="description" content="ClearGlass helps Ontario organizations reduce technology risk' in homepage
    assert '<meta property="og:description" content="Reduce technology risk and put governed AI automation to work.' in homepage
    assert '<meta name="twitter:description" content="Reduce technology risk and put governed AI automation to work.' in homepage


def test_quick_audit_destination_is_present_in_sitemap_and_has_truthful_scope() -> None:
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    offer = (ROOT / "offers" / "security-quick-audit.html").read_text(encoding="utf-8")

    assert "https://www.clearglassinc.com/offers/security-quick-audit.html" in sitemap
    assert "Security Quick-Audit" in offer
    assert "CAD $249" in offer
    assert "read-only" in offer.lower()
    assert "written" in offer.lower()
    assert "https://buy.stripe.com/8x2eVe7ZG0mFam00LG4Ni03" in offer
    assert "https://calendly.com/desmondodhiambo/30min" in offer
    assert "penetration test" in offer.lower()
    assert "compliance attestation" in offer.lower()


def test_marketing_assets_disclose_draft_status_and_measurement_limits() -> None:
    scorecard = (ROOT / "marketing" / "weekly-funnel-scorecard.md").read_text(encoding="utf-8")
    scan = (ROOT / "marketing" / "competitive-scan-2026-10-09.md").read_text(encoding="utf-8")
    launch_kit = (ROOT / "marketing" / "content-launch-kit-2026-10-09.md").read_text(encoding="utf-8")
    checklist = (ROOT / "marketing" / "small-business-security-baseline-checklist.md").read_text(encoding="utf-8")

    assert "Unknown" in scorecard
    assert "CAC" in scorecard
    assert "not a market-size study" in scan
    assert "nothing has been posted or sent" in launch_kit.lower()
    assert "not an audit, certification, penetration test, or legal opinion" in checklist
