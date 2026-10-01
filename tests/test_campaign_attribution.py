"""A campaign tag survives the click from the offer page to the lead form.

Campaign links land on offer pages (``tools/campaign_registry.py`` builds
them), but only ``revenue-command.html`` read the UTM tags, and only from its
own URL. A visitor who arrived on ``/offers/hardening-sprint.html`` from an ad
and then clicked through to the form was recorded as ``direct``, so the revenue
cockpit could never credit the campaign. ``assets/js/cg-attribution.js`` now
keeps the first and last tagged touch for the tab, and the form sends those.

These run the real script in Node against a stubbed browser, one "page load"
per call, sharing one sessionStorage the way a tab does.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "assets" / "js" / "cg-attribution.js"
CODE = "CG-LINKEDIN-PROSERV-HARDENING-2026-Q4"
TAGGED = f"?utm_source=linkedin&utm_medium=social&utm_campaign={CODE}"
ORIGIN = "https://www.clearglassinc.com"

HARNESS = r"""
const [src, visits] = [process.argv[1], JSON.parse(process.argv[2])];
const backing = new Map();
const storage = {
  getItem: (k) => (backing.has(k) ? backing.get(k) : null),
  setItem: (k, v) => backing.set(k, String(v)),
};
let fields = null;
for (const visit of visits) {
  const url = new URL(visit.url);
  globalThis.location = {
    origin: url.origin, hostname: url.hostname, pathname: url.pathname, search: url.search,
  };
  globalThis.document = {referrer: visit.referrer || ""};
  globalThis.window = {};
  if (visit.storageThrows) {
    Object.defineProperty(globalThis.window, "sessionStorage", {get() { throw new Error("blocked"); }});
  } else {
    globalThis.window.sessionStorage = storage;
  }
  new Function(src)();
  fields = globalThis.window.CGAttribution.leadFields();
}
console.log(JSON.stringify({fields, stored: Object.fromEntries(backing)}));
"""

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def run(*visits: dict) -> dict:
    out = subprocess.run(
        ["node", "-e", HARNESS, SCRIPT.read_text(encoding="utf-8"), json.dumps(list(visits))],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(out.stdout)


def test_a_tag_on_the_offer_page_reaches_the_lead_form() -> None:
    fields = run(
        {"url": f"{ORIGIN}/offers/hardening-sprint.html{TAGGED}", "referrer": "https://www.linkedin.com/feed/"},
        {"url": f"{ORIGIN}/offers/index.html", "referrer": f"{ORIGIN}/offers/hardening-sprint.html"},
        {"url": f"{ORIGIN}/revenue-command.html", "referrer": f"{ORIGIN}/offers/index.html"},
    )["fields"]
    assert fields == {
        "source": "linkedin",
        "landing_page": f"{ORIGIN}/offers/hardening-sprint.html",
        "referrer": "www.linkedin.com",
        "utm_first_source": "linkedin",
        "utm_first_medium": "social",
        "utm_first_campaign": CODE,
        "utm_last_source": "linkedin",
        "utm_last_medium": "social",
        "utm_last_campaign": CODE,
    }


def test_first_touch_is_kept_and_a_later_tagged_arrival_is_the_last_touch() -> None:
    fields = run(
        {"url": f"{ORIGIN}/blog/index.html", "referrer": "https://www.google.com/"},
        {"url": f"{ORIGIN}/offers/security-quick-audit.html?utm_source=email&utm_medium=email"
                f"&utm_campaign=CG-EMAIL-SMB-QUICKAUDIT-2026-Q4"},
        {"url": f"{ORIGIN}/revenue-command.html"},
    )["fields"]
    assert fields["utm_first_campaign"] is None, "the tab's first page was untagged"
    assert fields["landing_page"] == f"{ORIGIN}/blog/index.html"
    assert fields["referrer"] == "www.google.com"
    assert (fields["utm_last_source"], fields["utm_last_campaign"]) == ("email", "CG-EMAIL-SMB-QUICKAUDIT-2026-Q4")
    assert fields["source"] == "email"


def test_an_untagged_visit_is_direct_or_referral_never_a_guessed_campaign() -> None:
    assert run({"url": f"{ORIGIN}/store.html"})["fields"]["source"] == "direct"
    referral = run({"url": f"{ORIGIN}/store.html", "referrer": "https://news.example.org/a?q=1"})["fields"]
    assert (referral["source"], referral["referrer"]) == ("referral", "news.example.org")
    assert referral["utm_last_campaign"] is None and referral["utm_first_campaign"] is None


def test_values_that_are_not_campaign_tags_are_dropped_not_stored() -> None:
    result = run({
        "url": f"{ORIGIN}/store.html?utm_source=jane%40example.com&utm_medium=%3Cscript%3E"
               f"&utm_campaign={'A' * 121}",
    })
    assert result["fields"]["utm_first_source"] is None
    assert result["fields"]["utm_first_medium"] is None
    assert result["fields"]["utm_first_campaign"] is None
    assert "cg-utm-last" not in result["stored"], "nothing valid arrived, so there is no tagged touch"
    assert "example.com" not in json.dumps(result["stored"])


def test_only_the_path_and_the_referrer_host_are_stored() -> None:
    stored = run({
        "url": f"{ORIGIN}/pricing.html{TAGGED}&email=jane%40example.com",
        "referrer": "https://mail.example.com/inbox?id=123&user=jane",
    })["stored"]
    first = json.loads(stored["cg-utm-first"])
    assert first == {
        "source": "linkedin", "medium": "social", "campaign": CODE,
        "landing_page": "/pricing.html", "referrer": "mail.example.com",
    }
    assert "jane" not in json.dumps(stored)


def test_an_internal_referrer_is_not_a_referral() -> None:
    for referrer in (f"{ORIGIN}/index.html", "https://clearglassinc.com/index.html"):
        fields = run({"url": f"{ORIGIN}/store.html", "referrer": referrer})["fields"]
        assert (fields["source"], fields["referrer"]) == ("direct", None), referrer


def test_blocked_storage_degrades_to_unattributed_without_throwing() -> None:
    fields = run({"url": f"{ORIGIN}/store.html{TAGGED}", "storageThrows": True})["fields"]
    assert fields["source"] == "direct" and fields["utm_last_campaign"] is None


def test_the_tag_rule_matches_the_control_planes_filter() -> None:
    """The browser must not keep a value the server would drop, or vice versa."""
    spec = importlib.util.spec_from_file_location("cg_attr", ROOT / "control-plane" / "app" / "attribution.py")
    attribution = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(attribution)  # type: ignore[union-attr]
    js_rule = re.search(r"var TAG = /(.+)/;", SCRIPT.read_text(encoding="utf-8")).group(1)
    assert js_rule == attribution._VALUE.pattern


def test_the_lead_form_sends_the_stored_touches() -> None:
    html = (ROOT / "revenue-command.html").read_text(encoding="utf-8")
    assert '<script defer src="/assets/js/cg-attribution.js"></script>' in html
    assert "window.CGAttribution.leadFields()" in html
    assert "Object.assign(data,captureAttribution())" in html
