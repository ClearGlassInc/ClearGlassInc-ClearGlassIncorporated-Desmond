"""analytics.js reports funnel steps once a provider is on, and nothing before.

Until the owner sets ``CONFIG.provider`` the file must stay inert: no
listener, no script, no event. Once on, the steps between landing and payment
(offer view, CTA, booking, checkout, contact, form) reach the provider tagged
with the tab's campaign code, and never carry an email address, even when the
link itself does (a ``mailto:`` body, a Stripe ``prefilled_email``).

Runs the real file in Node against a stubbed DOM.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analytics.js"
ORIGIN = "https://www.clearglassinc.com"
CODE = "CG-GOOGLE-PROSERV-HARDENING-2026-Q4"

HARNESS = r"""
const [src, provider, scenario] = [process.argv[1], process.argv[2], JSON.parse(process.argv[3])];
const source = src
  .replace('provider: "",', `provider: ${JSON.stringify(provider)},`)
  .replace('measurementId: "",', 'measurementId: "G-TEST000000",');
const listeners = {};
const appended = [];
const url = new URL(scenario.page);
globalThis.location = {href: url.href, pathname: url.pathname, hostname: url.hostname};
const stored = scenario.storage || {};
globalThis.window = {sessionStorage: {getItem: (k) => (k in stored ? stored[k] : null)}};
globalThis.document = {
  addEventListener: (type, fn) => (listeners[type] = listeners[type] || []).push(fn),
  createElement: () => ({setAttribute() {}}),
  head: {appendChild: (el) => appended.push(el)},
};
new Function(source)();
const form = {id: "lead-form", tagName: "FORM", getAttribute: () => null};
const fire = (type, event) => (listeners[type] || []).forEach((fn) => fn(event));
for (const [kind, value] of scenario.actions || []) {
  if (kind === "click") fire("click", {target: {closest: () => ({getAttribute: () => value})}});
  if (kind === "focus") fire("focusin", {target: {form}});
  if (kind === "submit") fire("submit", {target: form});
  if (kind === "funnel") fire("cg:funnel", {detail: {name: value}});
}
let events;
if (provider === "plausible") {
  events = ((globalThis.window.plausible && globalThis.window.plausible.q) || [])
    .map((args) => [args[0], args[1].props]);
} else {
  events = (globalThis.window.dataLayer || [])
    .map((args) => Array.from(args)).filter((a) => a[0] === "event").map((a) => [a[1], a[2]]);
}
console.log(JSON.stringify({events, listeners: Object.keys(listeners), scripts: appended.length}));
"""

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def run(provider: str, page: str, actions=(), campaign: str | None = CODE) -> dict:
    storage = {"cg-utm-last": json.dumps({"campaign": campaign})} if campaign else {}
    scenario = {"page": f"{ORIGIN}{page}", "storage": storage, "actions": list(actions)}
    out = subprocess.run(
        ["node", "-e", HARNESS, SCRIPT.read_text(encoding="utf-8"), provider, json.dumps(scenario)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(out.stdout)


def test_with_no_provider_nothing_listens_loads_or_sends() -> None:
    result = run("", "/offers/hardening-sprint.html", [["click", "https://calendly.com/x/30min"]])
    assert result == {"events": [], "listeners": [], "scripts": 0}


def test_an_offer_page_view_is_tagged_with_the_campaign() -> None:
    events = run("plausible", "/offers/hardening-sprint.html")["events"]
    assert events == [["offer_view", {"page": "/offers/hardening-sprint.html", "campaign": CODE}]]


def test_each_conversion_link_is_its_own_step() -> None:
    events = run("plausible", "/store.html", [
        ["click", "https://calendly.com/desmondodhiambo/30min"],
        ["click", "https://buy.stripe.com/8x2eVe7ZG0mFam00LG4Ni03?prefilled_email=jane%40example.com"],
        ["click", "mailto:desmondotieno@icloud.com?subject=Quick-Audit&body=Organization%3A%20Acme%20jane%40acme.ca"],
        ["click", "/offers/hardening-sprint.html"],
        ["click", "https://www.linkedin.com/company/x"],
        ["click", "/downloads/checklist.pdf"],
        ["click", "/blog/index.html"],
        ["click", "#pricing"],
    ], campaign=None)["events"]
    page = {"page": "/store.html"}
    assert events == [
        ["booking_start", {**page, "target": "calendly.com/desmondodhiambo/30min"}],
        ["checkout_start", {**page, "target": "buy.stripe.com"}],
        ["contact_request", page],
        ["cta_click", {**page, "target": "/offers/hardening-sprint.html"}],
        ["outbound_click", {**page, "target": "www.linkedin.com"}],
        ["download", {**page, "target": "/downloads/checklist.pdf"}],
    ], "plain navigation and in-page anchors are not funnel steps"


def test_no_email_address_reaches_the_provider() -> None:
    result = run("plausible", "/offers/security-quick-audit.html", [
        ["click", "mailto:desmondotieno@icloud.com?body=jane%40acme.ca"],
        ["click", "https://buy.stripe.com/abc?prefilled_email=jane%40acme.ca"],
        ["focus", None], ["submit", None],
    ])
    dumped = json.dumps(result["events"])
    assert "@" not in dumped and "jane" not in dumped and "icloud" not in dumped


def test_a_form_starts_once_and_its_submission_is_counted() -> None:
    events = run("plausible", "/revenue-command.html", [["focus", None], ["focus", None], ["submit", None]])["events"]
    assert [e[0] for e in events] == ["form_start", "form_submit"]
    assert events[0][1] == {"form": "lead-form", "page": "/revenue-command.html", "campaign": CODE}


def test_pages_may_report_only_known_stages() -> None:
    events = run("plausible", "/revenue-command.html", [
        ["funnel", "lead_recorded"], ["funnel", "jane@example.com"], ["funnel", "purchase"],
    ])["events"]
    assert events == [["lead_recorded", {"page": "/revenue-command.html", "campaign": CODE}]]


def test_ga4_receives_the_same_events() -> None:
    events = run("ga4", "/offers/hardening-sprint.html", [["click", "https://calendly.com/x/30min"]])["events"]
    assert [e[0] for e in events] == ["offer_view", "booking_start"]


def test_the_lead_form_reports_an_accepted_lead_only_after_the_api_answers() -> None:
    html = (ROOT / "revenue-command.html").read_text(encoding="utf-8")
    success = html.index("f.dataset.reference=out.reference")
    dispatch = html.index("new CustomEvent('cg:funnel',{detail:{name:'lead_recorded'}})")
    assert success < dispatch < html.index(".catch(function(err){setStatus(st,err.message,'error')})")
