#!/usr/bin/env python3
"""Check campaign packages against the playbook, and build their tracked links.

``growth-system/campaign-playbook.md`` says every campaign must define its
audience, offer, CTA, landing page, channel assets, measurement plan, approval
status and shutdown thresholds before it may launch. Nothing checked that, and
of the five packages in ``data/campaigns/burlington-campaign-packages.json``
only one names a landing page, and that page has no element with the id its
anchor names.

This adds the two things attribution needs from a campaign:

* a **campaign code**, ``CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n>``, which
  is what ``utm_campaign`` carries. The control plane copies it from the lead
  onto the Stripe metadata and the paid order (``app/attribution.py``), so the
  revenue cockpit can report confirmed revenue per campaign;
* a **tracked destination** per channel, built from that code, so every ad
  link carries the same tags.

Two more conditions keep a campaign honest about what it can sell and measure:

* its ``offer`` is a SKU ClearGlass sells: one in the control-plane price
  book or the service catalogue, never an offer that exists only in ad copy;
* its landing page loads ``/assets/js/cg-attribution.js``. Campaign traffic
  lands on offer pages, and the lead form is a click away; without that script
  the tags are gone by the time the visitor submits, and the lead is "direct".

The advertising controls in ``data/compliance/advertising-sources.json`` (each
tied to the Canadian law, platform policy or standard it rests on) are checked
here too, and the message for each names its control:

* always: no unsubstantiated absolute, performance or urgency claim in the
  copy (AD-CLAIMS); no audience built on a sensitive personal trait
  (AD-TARGETING); no remarketing, customer list or pixel while the published
  privacy policy says there are none (AD-TRACKING); a landing page links the
  privacy policy and meets basic WCAG 2.2 checks (AD-DESTINATION);
* at approval, recorded by the owner under ``governance``: the date each ad
  platform's policies were read and its verification state (AD-PLATFORM),
  MFA on the ad account (AD-ACCOUNT), the CASL consent basis for email
  (AD-CASL), and a dated legal review where the copy or targeting needs one
  (AD-LEGAL).

It never publishes, spends, or contacts anyone, and it records no performance:
a campaign's results come only from the revenue cockpit's verified data.

    python3 tools/campaign_registry.py            # readiness report
    python3 tools/campaign_registry.py --check    # exit 1 if an approved campaign is incomplete
    python3 tools/campaign_registry.py --links    # tracked destination URLs

Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_DIR = ROOT / "data" / "campaigns"
SITE = "https://www.clearglassinc.com"
PRICEBOOK = ROOT / "control-plane" / "app" / "data" / "pricebook.json"
SERVICE_CATALOG = ROOT / "data" / "store" / "catalog.json"
#: The script that carries a landing page's campaign tags to the lead form.
ATTRIBUTION_SCRIPT = "/assets/js/cg-attribution.js"

#: utm_source per channel. Adding a channel is a reviewed change, so reports
#: never split one channel across two spellings.
CHANNELS = {
    "LINKEDIN": ("linkedin", "social"),
    "GOOGLE": ("google", "cpc"),
    "EMAIL": ("email", "email"),
    "ORGANIC": ("clearglass", "organic"),
    "REFERRAL": ("referral", "referral"),
    "EVENT": ("event", "offline"),
    "PARTNER": ("partner", "referral"),
}

CODE = re.compile(
    r"^CG-(?P<channel>[A-Z]+)-(?P<audience>[A-Z0-9]{2,20})-(?P<offer>[A-Z0-9]{2,24})"
    r"-(?P<year>20\d\d)-Q(?P<quarter>[1-4])$"
)

#: Fields a campaign needs before it may be approved: the playbook's list plus
#: the objective and success criteria an approver has to judge it against.
REQUIRED = (
    "campaign_code",
    "objective",
    "audience",
    "offer",
    "cta",
    "landing_page",
    "measurement_plan",
    "success_criteria",
    "shutdown_thresholds",
    "approval_status",
)
#: Statuses that let a campaign run. A campaign in one of these must be complete.
LIVE_STATUSES = {"approved", "active"}

#: Google Ads responsive search ad text limits, in characters. Copy over the
#: limit is rejected at upload, after approval, so it is caught here instead.
GOOGLE_AD_LIMITS = {"headline": 30, "description": 90}

#: The published privacy policy. Every landing page links it (PIPEDA openness),
#: and while it says ClearGlass runs no advertising cookies or pixels, no
#: campaign may target in a way that needs them.
PRIVACY_POLICY = ROOT / "legal" / "privacy.html"
PRIVACY_POLICY_PATH = "legal/privacy.html"
NO_AD_TRACKING = "do not deploy advertising cookies or third-party tracking pixels"

#: Package fields holding copy that is published as written. Keyword lists in
#: them are not copy.
COPY_FIELDS = (
    "cta", "core_message", "google_search_ads", "linkedin_ads", "linkedin_posts",
    "microsoft_ads", "outreach_emails",
)
NOT_COPY = {"negative_keywords"}

#: Ad assets per platform. A package carrying one is uploaded to that platform.
PLATFORM_ASSETS = {
    "google_search_ads": "google_ads",
    "linkedin_ads": "linkedin_ads",
    "microsoft_ads": "microsoft_ads",
}
VERIFICATION_STATES = {"verified", "not_required"}
CASL_CONSENT = {"express", "implied"}

#: Absolute, performance and urgency claims (AD-CLAIMS). A performance claim
#: must rest on an adequate and proper test made before it is published
#: (Competition Act s. 74.01(1)(b)), and the repository's own rule bars
#: fabricated urgency. The match is broad on purpose: a false hit costs one
#: substantiation entry; a missed claim costs a complaint.
CLAIM_TERMS = re.compile(
    r"(?<![\w-])("
    r"guarantee[ds]?|unhackable|hack-?proof|bullet-?proof|risk-free|zero[- ]risk|100\s?%"
    r"|fully (?:compliant|secure|protected)|certified|proven|(?:industry|market)-leading"
    r"|best(?!\s+practices?\b)|number one|#1|never (?:be )?(?:breached|hacked)"
    r"|eliminates? (?:all )?risks?|military-grade|bank-grade"
    r"|limited time|act now|last chance|only \d+ (?:spots?|places?|seats?) left"
    r")(?!\w)",
    re.IGNORECASE,
)

#: Personal traits no ClearGlass audience is built on (AD-TARGETING). Ad
#: platforms restrict these and PIPEDA treats them as sensitive; this list is
#: ClearGlass's own, and an industry ("healthcare clinics") is not a trait.
SENSITIVE_TRAITS = re.compile(
    r"(?<![\w-])("
    r"(?:health|medical) conditions?|diagnos\w*|disabilit\w*|pregnan\w*|religio\w*|ethnic\w*"
    r"|racial|sexual orientation|gender identity|political (?:affiliation|views?)|trade unions?"
    r"|immigration status|criminal records?|bankrupt\w*|debts?|financial hardship|credit scores?"
    r")(?!\w)",
    re.IGNORECASE,
)

#: Targeting that follows a visitor across sites or uploads a contact list.
TRACKING_TARGETING = ("remarketing", "customer_list", "conversion_pixel")

#: Copy topics that need a dated review by counsel before approval (AD-LEGAL).
LEGAL_TOPICS = re.compile(
    r"(?<![\w-])(complian\w*|PHIPA|PIPEDA|CASL|legal\w*|law|lawful\w*|insur\w*|regulat\w*"
    r"|OSINT|cross-border)(?!\w)",
    re.IGNORECASE,
)


def sellable_offers() -> set[str]:
    """SKUs in the control-plane price book plus the service catalogue ids."""
    offers: set[str] = set()
    if PRICEBOOK.is_file():
        offers |= {o["sku"] for o in json.loads(PRICEBOOK.read_text(encoding="utf-8")).get("offers", [])}
    if SERVICE_CATALOG.is_file():
        catalog = json.loads(SERVICE_CATALOG.read_text(encoding="utf-8"))
        items = catalog.get("items") or catalog.get("products") or catalog.get("offers") or []
        offers |= {str(i.get("id") or i.get("sku")) for i in items if i.get("id") or i.get("sku")}
    return offers


def parse_code(code: str) -> dict[str, str] | None:
    """Split a campaign code into its parts, or ``None`` if it is not one."""
    match = CODE.match(code or "")
    if not match or match["channel"] not in CHANNELS:
        return None
    return match.groupdict()


#: Input types with no label of their own: buttons name themselves, hidden
#: fields are never shown.
UNLABELLED_INPUTS = {"hidden", "submit", "button", "reset", "image"}


class _Page(HTMLParser):
    """What a landing page gives a visitor: ids, links, language, images, fields."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.lang = ""
        self.images_without_alt = 0
        self._fields: list[tuple[str, str, bool]] = []
        self._label_for: set[str] = set()
        self._in_label = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001 - HTMLParser signature
        a = {name: value or "" for name, value in attrs}
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        elif tag == "img" and "alt" not in a:
            self.images_without_alt += 1
        elif tag == "label":
            self._in_label += 1
            if a.get("for"):
                self._label_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            kind = a.get("type", "text").lower() if tag == "input" else tag
            if kind in UNLABELLED_INPUTS or a.get("aria-hidden") == "true":
                return
            named = bool(self._in_label or a.get("aria-label") or a.get("aria-labelledby") or a.get("title"))
            self._fields.append((a.get("id", ""), a.get("name") or a.get("id") or tag, named))

    def handle_endtag(self, tag):  # noqa: ANN001 - HTMLParser signature
        if tag == "label" and self._in_label:
            self._in_label -= 1

    def unlabelled(self) -> list[str]:
        return [name for id_, name, named in self._fields if not named and id_ not in self._label_for]


def _is_same_site_privacy_link(href: str, landing_path: str) -> bool:
    """Whether href resolves to this site's canonical privacy-policy path."""
    site = urlsplit(SITE)
    resolved = urlsplit(urljoin(f"{SITE}{landing_path}", href))
    return (
        resolved.scheme == site.scheme
        and resolved.netloc == site.netloc
        and resolved.path == f"/{PRIVACY_POLICY_PATH}"
    )


def destination_problem(landing_page: str) -> str | None:
    """Why a landing page cannot receive traffic, or ``None`` if it can."""
    parts = urlsplit(landing_page or "")
    if parts.scheme or parts.netloc:
        return "landing_page must be a path on this site"
    path = ROOT / parts.path.lstrip("/")
    if path.is_dir():
        path = path / "index.html"
    if not path.is_file():
        return f"landing page {parts.path} does not exist"
    html = path.read_text(encoding="utf-8", errors="replace")
    page = _Page()
    page.feed(html)
    if parts.fragment and parts.fragment not in page.ids:
        return f"{parts.path} has no element with id '{parts.fragment}'"
    if ATTRIBUTION_SCRIPT not in html:
        return f"{parts.path} does not load {ATTRIBUTION_SCRIPT}, so its campaign tags never reach the lead"
    if not any(_is_same_site_privacy_link(href, parts.path) for href in page.hrefs):
        return f"{parts.path} has no link to the privacy policy (/{PRIVACY_POLICY_PATH}) [AD-DESTINATION]"
    if not page.lang:
        return f"{parts.path} does not declare its language (<html lang>, WCAG 2.2 SC 3.1.1) [AD-DESTINATION]"
    if page.images_without_alt:
        return (f"{parts.path} has {page.images_without_alt} image(s) without alt text "
                "(WCAG 2.2 SC 1.1.1) [AD-DESTINATION]")
    unlabelled = page.unlabelled()
    if unlabelled:
        return (f"{parts.path} has form fields without a label: {', '.join(unlabelled)} "
                "(WCAG 2.2 SC 1.3.1, 3.3.2) [AD-DESTINATION]")
    return None


def _strings(value, key: str = ""):  # noqa: ANN001, ANN202 - walks any JSON value
    """Every string in a JSON value, skipping keyword lists."""
    if key in NOT_COPY:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for name, item in value.items():
            yield from _strings(item, name)


def copy_text(campaign: dict) -> list[str]:
    """The copy a campaign would publish, string by string."""
    return [text for field in COPY_FIELDS for text in _strings(campaign.get(field))]


def _evidence_exists(path: str) -> bool:
    if not path:
        return False
    target = (ROOT / path).resolve()
    return target.is_relative_to(ROOT) and target.is_file()


def claim_problems(campaign: dict) -> list[str]:
    """Absolute, performance or urgency claims nothing in the repository proves (AD-CLAIMS)."""
    backed = [
        str(entry.get("claim") or "").lower()
        for entry in campaign.get("substantiation") or []
        if isinstance(entry, dict) and _evidence_exists(str(entry.get("evidence") or ""))
    ]
    found = []
    for text in copy_text(campaign):
        for match in CLAIM_TERMS.finditer(text):
            term = match.group(0)
            if not any(term.lower() in claim for claim in backed):
                found.append(f"claim {term!r} in {text!r} has no substantiation entry with evidence "
                              "in this repository [AD-CLAIMS]")
    return found


def privacy_policy_refuses_ad_tracking() -> bool:
    """True while the published privacy policy says there are no ad cookies or pixels."""
    return PRIVACY_POLICY.is_file() and NO_AD_TRACKING in PRIVACY_POLICY.read_text(encoding="utf-8").lower()


def tracking(campaign: dict) -> list[str]:
    """The cross-site or list-based targeting a campaign switches on."""
    targeting = campaign.get("targeting") or {}
    return [key for key in TRACKING_TARGETING if targeting.get(key)]


def targeting_problems(campaign: dict) -> list[str]:
    """Sensitive-trait audiences (AD-TARGETING) and tracking the privacy policy rules out (AD-TRACKING)."""
    found = []
    texts = [str(campaign.get("audience") or ""), *_strings(campaign.get("targeting") or {})]
    for text in texts:
        for match in SENSITIVE_TRAITS.finditer(text):
            found.append(f"audience or targeting uses a sensitive personal trait ({match.group(0)!r}) "
                         "[AD-TARGETING]")
    keys = tracking(campaign)
    if keys and privacy_policy_refuses_ad_tracking():
        found.append(f"targeting {', '.join(keys)} contradicts {PRIVACY_POLICY_PATH} section 10 (\"we "
                     f"{NO_AD_TRACKING}\"): the policy changes first, with counsel [AD-TRACKING]")
    return found


def platforms(campaign: dict) -> list[str]:
    """The ad platforms a package carries assets for."""
    return [platform for field, platform in PLATFORM_ASSETS.items() if campaign.get(field)]


def _recorded_date(value) -> bool:  # noqa: ANN001 - any JSON value
    """A YYYY-MM-DD date that is not in the future."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return dt.date.fromisoformat(value) <= dt.date.today()
    except ValueError:
        return False


def needs_legal_review(campaign: dict) -> bool:
    return bool(tracking(campaign)) or any(LEGAL_TOPICS.search(text) for text in copy_text(campaign))


def sends_email(campaign: dict) -> bool:
    parsed = parse_code(campaign.get("campaign_code", ""))
    return bool(campaign.get("outreach_emails")) or (parsed is not None and parsed["channel"] == "EMAIL")


def attestations_missing(campaign: dict) -> list[str]:
    """What the owner records under ``governance`` before the campaign may be approved."""
    governance = campaign.get("governance") or {}
    reviewed = governance.get("policy_reviewed_on") or {}
    verification = governance.get("advertiser_verification") or {}
    missing = []
    for platform in platforms(campaign):
        if not _recorded_date(reviewed.get(platform)):
            missing.append(f"governance.policy_reviewed_on.{platform}: the date the owner read this "
                           "platform's current ad policies [AD-PLATFORM]")
        if verification.get(platform) not in VERIFICATION_STATES:
            missing.append(f"governance.advertiser_verification.{platform}: 'verified' or 'not_required', "
                           "as the platform shows it [AD-PLATFORM]")
    if platforms(campaign) and governance.get("account_mfa") is not True:
        missing.append("governance.account_mfa: true once every login to the ad account uses "
                       "multi-factor authentication [AD-ACCOUNT]")
    if sends_email(campaign) and governance.get("casl_consent_basis") not in CASL_CONSENT:
        missing.append("governance.casl_consent_basis: 'express' or 'implied' for the recipient list; "
                       "each message still passes python -m bots.outreach_preflight [AD-CASL]")
    if needs_legal_review(campaign) and not _recorded_date(governance.get("legal_review_on")):
        missing.append("governance.legal_review_on: the date qualified counsel reviewed the copy and "
                       "targeting [AD-LEGAL]")
    return missing


def problems(campaign: dict, offers: set[str] | None = None) -> list[str]:
    """Everything that stops a campaign being approvable."""
    found = [f"missing {field}" for field in REQUIRED if not campaign.get(field)]
    ceiling = campaign.get("spend_ceiling_cad")
    live = str(campaign.get("approval_status") or "").lower() in LIVE_STATUSES
    if live and (
        isinstance(ceiling, bool) or not isinstance(ceiling, int | float) or ceiling < 0
    ):
        found.append("an approved campaign needs spend_ceiling_cad, set by the owner (0 for organic)")
    offer = campaign.get("offer")
    if offer and offer not in (sellable_offers() if offers is None else offers):
        found.append(f"offer {offer!r} is not a SKU ClearGlass sells (price book or service catalogue)")
    code = campaign.get("campaign_code")
    if code and parse_code(code) is None:
        found.append(f"campaign_code {code!r} does not match CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n>")
    if campaign.get("landing_page"):
        issue = destination_problem(campaign["landing_page"])
        if issue:
            found.append(issue)
    for n, ad in enumerate(campaign.get("google_search_ads") or [], 1):
        for field, limit in GOOGLE_AD_LIMITS.items():
            if len(str(ad.get(field) or "")) > limit:
                found.append(f"google_search_ads[{n}].{field} is over Google's {limit}-character limit")
    found += claim_problems(campaign)
    found += targeting_problems(campaign)
    if live:
        found += [f"missing {item}" for item in attestations_missing(campaign)]
    return found


def tracked_url(campaign: dict) -> str | None:
    """The landing page with the campaign's UTM tags, or ``None`` if it has no valid code."""
    parsed = parse_code(campaign.get("campaign_code", ""))
    if parsed is None or not campaign.get("landing_page"):
        return None
    source, medium = CHANNELS[parsed["channel"]]
    parts = urlsplit(campaign["landing_page"])
    query = urlencode({"utm_source": source, "utm_medium": medium, "utm_campaign": campaign["campaign_code"]})
    fragment = f"#{parts.fragment}" if parts.fragment else ""
    return f"{SITE}{parts.path}?{query}{fragment}"


def load(directory: Path = CAMPAIGN_DIR) -> list[tuple[Path, dict]]:
    campaigns = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for campaign in data.get("campaigns", []):
            campaigns.append((path, campaign))
    return campaigns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if an approved or active campaign is incomplete")
    parser.add_argument("--links", action="store_true", help="print tracked destination URLs")
    args = parser.parse_args(argv)

    failures = 0
    offers = sellable_offers()
    for path, campaign in load(CAMPAIGN_DIR):
        name = campaign.get("id", "?")
        status = str(campaign.get("approval_status") or "draft").lower()
        issues = problems(campaign, offers)
        if args.links:
            print(f"{name}: {tracked_url(campaign) or 'NO TRACKED LINK (needs campaign_code and landing_page)'}")
            continue
        verdict = "READY FOR APPROVAL" if not issues else "INCOMPLETE"
        print(f"{name} [{status}] {verdict}")
        for issue in issues:
            print(f"    - {issue}")
        if status not in LIVE_STATUSES:
            for item in attestations_missing(campaign):
                print(f"    · at approval, record {item}")
        if args.check and status in LIVE_STATUSES and issues:
            failures += 1
            print(f"    ! {status} campaign is incomplete ({path.name})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
