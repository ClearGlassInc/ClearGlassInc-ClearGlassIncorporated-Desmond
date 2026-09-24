"""The public Revenue Command page must not hold credentials or strand leads.

CRCS Phase 0 (docs/crcs/IMPLEMENTATION_SEQUENCE.md 0.2, 0.6, 0.7):

* The page asked the owner to type the master admin key into a public page and
  sent it as a bearer token from the browser. The cockpit now lives in the
  authenticated admin app, which calls the control plane from its server
  (ADR 0002 rule 2: the browser never holds a control-plane credential).
* First-touch UTM data sat in ``localStorage`` with no expiry, which the
  privacy notice does not disclose. It is now session-scoped.
* With ``cg-revenue-api`` empty, as shipped, the form posted into nothing. The
  form now stays hidden until an API host is configured, and a contact route
  is shown instead.

These read the committed markup, so they need no browser.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "revenue-command.html"
EXCLUDED_PARTS = {".git", ".next", "node_modules", "vendor"}


def _markup() -> str:
    return PAGE.read_text(encoding="utf-8")


def _public_pages() -> list[Path]:
    return [
        path for path in ROOT.rglob("*.html")
        if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    ]


def test_no_public_page_sends_an_admin_credential() -> None:
    offenders = []
    for path in _public_pages():
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"""Authorization['"]?\s*:\s*['"]Bearer""", text) or 'id="admin-key"' in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"public pages holding an admin credential: {offenders}"


def test_the_page_uses_no_persistent_browser_storage() -> None:
    assert "localStorage" not in _markup()
    assert "sessionStorage" in _markup()


def test_the_form_stays_hidden_until_an_api_host_is_configured() -> None:
    markup = _markup()
    assert '<meta name="cg-revenue-api" content="">' in markup, "the committed page ships without a host"
    assert '<div id="lead-capture" hidden>' in markup
    assert 'id="lead-fallback"' in markup
    fallback = re.search(r'<meta name="cg-revenue-fallback" content="([^"]+)">', markup)
    assert fallback, "the fallback contact route must be configured"
    assert fallback.group(1) in markup, "the no-JavaScript link must match the configured route"


def test_the_honeypot_is_invisible_to_people_and_assistive_technology() -> None:
    """The honeypot now fails silently, so a person who fills it loses their
    request without being told. It must be unreachable for people."""
    markup = _markup()
    trap = re.search(r'<div class="trap" aria-hidden="true">(.*?)</div>', markup, re.S)
    assert trap, "the honeypot must sit in an aria-hidden container"
    assert 'name="website_honeypot"' in trap.group(1)
    assert 'tabindex="-1"' in trap.group(1)
    assert 'class="visually-hidden"' not in markup, "visually-hidden stays readable by screen readers"


def test_checkout_sends_the_opaque_reference_not_the_lead_id() -> None:
    markup = _markup()
    assert "reference:f.dataset.reference" in markup
    assert "lead_id" not in markup
