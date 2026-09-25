import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHIELD = ROOT / "shield.html"

def read_shield():
    return SHIELD.read_text(encoding="utf-8")

def test_shield_commercial_state_is_locked():
    html = read_shield()
    assert 'data-shield-cta="private-beta"' in html
    assert "COMMERCIAL STATUS: LOCKED" in html
    assert "Target pricing — not currently available for purchase." in html
    assert "Checkout, subscriptions, billing, service-level commitments, and product availability remain disabled" in html

def test_shield_has_no_live_checkout_or_payment_links():
    html = re.sub(r"<!--.*?-->", "", read_shield(), flags=re.S)
    forbidden = [
        r"https?://(?:buy|book|checkout)\.stripe\.com/",
        r"(?i)stripe\.(?:com|js)",
        r"(?i)\b(?:plink|price|prod|cs)_",
        r"(?i)checkout\.sessions",
        r"(?i)payment[_ -]?link",
    ]
    for pattern in forbidden:
        assert not re.search(pattern, html), f"Forbidden Shield commercial pattern: {pattern}"

def test_shield_has_no_client_side_stripe_secrets():
    html = read_shield()
    for pattern in [
        r"(?i)sk_(?:live|test)_[A-Za-z0-9]+",
        r"(?i)rk_(?:live|test)_[A-Za-z0-9]+",
        r"(?i)whsec_[A-Za-z0-9]+",
        r"(?i)STRIPE_SECRET_KEY",
        r"(?i)STRIPE_WEBHOOK_SECRET",
    ]:
        assert not re.search(pattern, html), f"Possible Stripe secret exposure: {pattern}"

def test_shield_purchase_ctas_are_non_payment_actions():
    html = read_shield()
    ctas = re.findall(r'<a\b[^>]*data-shield-cta="[^"]+"[^>]*href="([^"]+)"', html, flags=re.I)
    assert ctas
    assert all(href.startswith("#") or href.lower().startswith("mailto:") for href in ctas), ctas

def test_no_shield_payment_configuration_in_static_runtime_assets():
    candidates = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.name == "package-lock.json":
            continue
        # Scan only static runtime assets; tests/docs/workflows may legitimately
        # contain the very patterns this guard is designed to detect.
        if path.suffix.lower() not in {".html", ".js", ".css", ".json"}:
            continue
        if path.parts[0] in {"tests", "docs", ".github"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"(?i)shield.{0,160}(?:payment[_ -]?link|checkout\.sessions|\b(?:plink|price|prod)_)", content, re.S):
            candidates.append(str(path.relative_to(ROOT)))
    assert not candidates, candidates
