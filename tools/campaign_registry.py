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

It never publishes, spends, or contacts anyone, and it records no performance:
a campaign's results come only from the revenue cockpit's verified data.

    python3 tools/campaign_registry.py            # readiness report
    python3 tools/campaign_registry.py --check    # exit 1 if an approved campaign is incomplete
    python3 tools/campaign_registry.py --links    # tracked destination URLs

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_DIR = ROOT / "data" / "campaigns"
SITE = "https://www.clearglassinc.com"

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


def parse_code(code: str) -> dict[str, str] | None:
    """Split a campaign code into its parts, or ``None`` if it is not one."""
    match = CODE.match(code or "")
    if not match or match["channel"] not in CHANNELS:
        return None
    return match.groupdict()


class _Ids(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):  # noqa: ANN001 - HTMLParser signature
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)


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
    if parts.fragment:
        ids = _Ids()
        ids.feed(path.read_text(encoding="utf-8", errors="replace"))
        if parts.fragment not in ids.ids:
            return f"{parts.path} has no element with id '{parts.fragment}'"
    return None


def problems(campaign: dict) -> list[str]:
    """Everything that stops a campaign being approvable."""
    found = [f"missing {field}" for field in REQUIRED if not campaign.get(field)]
    code = campaign.get("campaign_code")
    if code and parse_code(code) is None:
        found.append(f"campaign_code {code!r} does not match CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n>")
    if campaign.get("landing_page"):
        issue = destination_problem(campaign["landing_page"])
        if issue:
            found.append(issue)
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
    for path, campaign in load(CAMPAIGN_DIR):
        name = campaign.get("id", "?")
        status = str(campaign.get("approval_status") or "draft").lower()
        issues = problems(campaign)
        if args.links:
            print(f"{name}: {tracked_url(campaign) or 'NO TRACKED LINK (needs campaign_code and landing_page)'}")
            continue
        verdict = "READY FOR APPROVAL" if not issues else "INCOMPLETE"
        print(f"{name} [{status}] {verdict}")
        for issue in issues:
            print(f"    - {issue}")
        if args.check and status in LIVE_STATUSES and issues:
            failures += 1
            print(f"    ! {status} campaign is incomplete ({path.name})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
