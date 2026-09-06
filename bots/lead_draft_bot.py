#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Lead-draft bot — turns the outreach lead list into personalized, CASL-compliant
DRAFT emails, ready for a human to review and send manually.

This bot NEVER sends email and has no mail transport. It only assembles drafts and
enforces the outreach playbook's hard rules:
  • published-business-email (CASL) consent basis only,
  • health / clinic sectors excluded (express consent + human review),
  • CASL footer + opt-out on every message,
  • the specific public observation and recipient name are left as placeholders for
    a human to confirm — the bot does not fabricate claims about a business,
  • a "verify the public business email before sending" flag on every draft.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTREACH_DIR = ROOT / "offers" / "outreach"
OUT_DIR = OUTREACH_DIR / "generated"
STORE_URL = "https://www.clearglassinc.com/store.html"
SENDER = "Desmond, ClearGlass Inc."

CASL_FOOTER = (
    "ClearGlass Inc. · Burlington, Ontario, Canada\n"
    "You're receiving this because your business contact is publicly listed and this "
    "relates to your role. Prefer not to hear from us? Reply \"unsubscribe\" and we'll "
    "remove you within 10 business days."
)

# Sectors we never cold-email — require express consent / human review.
EXCLUDED_SECTOR_RE = re.compile(r"health|clinic|medical|dental|hospital|pharma|patient", re.I)
# Consent basis we accept for cold B2B (CASL published-business-email provision).
CASL_CONSENT_RE = re.compile(r"casl|published business email", re.I)


@dataclass
class Draft:
    company: str
    sector: str
    template: str
    subject: str
    body: str
    recommended_offer: str
    consent_basis: str
    verify_contact_at: str
    status: str  # "draft" | "skipped"
    skip_reason: str = ""


def pick_template(offer: str, next_action: str) -> str:
    text = f"{offer} {next_action}".lower()
    if "phipa" in text:
        return "phipa"
    if "template 1" in text or "quick-audit" in text or "quick audit" in text:
        return "quick_audit"
    if "template 4" in text or "automation" in text:
        return "automation"
    if "template 2" in text or "hardening" in text:
        return "hardening"
    return "quick_audit"


def _wrap(subject: str, body: str) -> tuple[str, str]:
    return subject, body.strip() + "\n\n— " + SENDER + "\n\n" + CASL_FOOTER


def render(template: str, company: str, sector: str) -> tuple[str, str]:
    sector_l = sector.lower()
    # The first sentence must reference a *specific public* observation — left as a
    # placeholder (with a hint from the lead's Why_fit) for a human to confirm.
    obs = "{{specific public observation — e.g. from " + company + "'s public site}}"
    if template == "quick_audit":
        return _wrap(
            f"A 3-day read-only security check for {company}",
            f"Hi {{{{First name}}}},\n\n"
            f"I came across {company} — {obs}. I'm Desmond at ClearGlass Inc., a Burlington "
            f"security practice; we help Ontario {sector_l} teams see exactly where they stand "
            f"without a big project.\n\n"
            f"Our Security Quick-Audit (CAD $249) is a read-only review of your email security "
            f"(SPF/DKIM/DMARC), public exposure, and Microsoft 365 baseline. You get a branded "
            f"findings report with the top 10 risk-ranked items within 3 business days. It changes "
            f"nothing and needs only your written authorization for the domain in scope.\n\n"
            f"Worth a look? You can review or book it here: {STORE_URL}",
        )
    if template == "hardening":
        return _wrap(
            f"Fixed-scope Microsoft 365 hardening for {company}",
            f"Hi {{{{First name}}}},\n\n"
            f"{obs}. Many {sector_l} teams in Ontario run Microsoft 365 that's never been formally "
            f"reviewed — usually a few high-impact gaps in MFA, admin roles, or sharing defaults.\n\n"
            f"Our Microsoft 365 + Windows Hardening Sprint is fixed-scope (1–2 weeks): we bring your "
            f"tenant and endpoints to CIS-aligned baselines and hand you a prioritized, plain-language "
            f"remediation report, with quick wins applied on your sign-off. Tiers run $2,500 / $4,500 / "
            f"$7,500 CAD by environment size. All work is under written authorization.\n\n"
            f"Open to a short scoping call to confirm fit and a fixed price? Details: {STORE_URL}",
        )
    if template == "automation":
        return _wrap(
            f"Cutting repetitive ops work at {company}",
            f"Hi {{{{First name}}}},\n\n"
            f"{obs}. Teams managing many user accounts and properties often lose hours to manual "
            f"onboarding/offboarding and reporting — which is also where security gaps creep in.\n\n"
            f"We pair a fixed-scope hardening pass with light workflow automation so the routine work "
            f"runs itself and access stays tidy. Scoped, fixed-fee, under written authorization.\n\n"
            f"Worth a short call to see if it fits? Details: {STORE_URL}",
        )
    # phipa
    return _wrap(
        f"PHIPA readiness checklist for {company}",
        f"Hi {{{{First name}}}},\n\n"
        f"{obs}. We help Ontario teams find privacy & security gaps before they become problems.\n\n"
        f"To start with zero commitment, here's our free PHIPA Readiness Checklist: "
        f"https://www.clearglassinc.com/offers/phipa-readiness-checklist.html . If useful, our "
        f"PHIPA Readiness Assessment (from $3,000 CAD) maps your gaps to PHIPA obligations and delivers "
        f"a risk-ranked roadmap. This is readiness/advisory — not legal advice or a certification.\n\n"
        f"Would the checklist be helpful?",
    )


def load_leads(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            company = (row.get("Company") or "").strip()
            if not company or company.upper().startswith("NOTE"):
                continue  # skip the instructional NOTE row / blanks
            rows.append(row)
    return rows


def build_draft(lead: dict) -> Draft:
    company = lead["Company"].strip()
    sector = (lead.get("Sector") or "").strip()
    offer = (lead.get("Recommended_offer") or "").strip()
    consent = (lead.get("Consent_basis") or "").strip()
    verify = (lead.get("Public_source_URL") or "").strip()
    next_action = (lead.get("Next_action") or "").strip()

    if EXCLUDED_SECTOR_RE.search(sector):
        return Draft(company, sector, "", "", "", offer, consent, verify,
                     "skipped", "excluded sector (express consent / human review required)")
    if not CASL_CONSENT_RE.search(consent):
        return Draft(company, sector, "", "", "", offer, consent, verify,
                     "skipped", "no CASL published-business-email consent basis recorded")

    template = pick_template(offer, next_action)
    subject, body = render(template, company, sector)
    return Draft(company, sector, template, subject, body, offer, consent, verify, "draft")


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(OUTREACH_DIR.glob("lead-list-*.csv"))
    # Prefer real lead lists over the template scaffold.
    csv_files = [p for p in csv_files if "template" not in p.name] or csv_files

    drafts: list[Draft] = []
    for csv_path in csv_files:
        for lead in load_leads(csv_path):
            drafts.append(build_draft(lead))

    ready = [d for d in drafts if d.status == "draft"]
    skipped = [d for d in drafts if d.status == "skipped"]
    now = datetime.now(timezone.utc)

    md = [
        "# ClearGlass — Generated Outreach Drafts",
        "",
        f"_Generated {now.isoformat()} · {len(ready)} draft(s), {len(skipped)} skipped._",
        "",
        (
            "> **These are DRAFTS. Nothing has been sent.** Before sending each one: "
            + "(1) verify the recipient's public business email on the firm's Contact page, "
            + "(2) replace `{{First name}}` and `{{specific public observation}}`, "
            + "(3) **add a complete CASL mailing address** to the footer — a street address or "
            + "PO box + postal code. *\"Burlington, Ontario\" alone is not a deliverable address "
            + "and is not CASL-sufficient.* Max **3 touches** per contact; any reply or opt-out "
            + "ends the sequence. Personalize every send — no bulk blasting."
        ),
        "",
    ]
    for d in ready:
        md += [
            f"## {d.company} — {d.sector}",
            f"- **Offer:** {d.recommended_offer}  ·  **Template:** {d.template}  ·  **Consent:** {d.consent_basis}",
            f"- **⚠ Verify business email at:** {d.verify_contact_at}/contact (or the site's Contact page)",
            "",
            f"**Subject:** {d.subject}",
            "",
            "```",
            d.body,
            "```",
            "",
        ]
    if skipped:
        md += ["## Skipped (need human review / express consent)", ""]
        md += [f"- **{d.company}** ({d.sector}) — {d.skip_reason}" for d in skipped]
        md += [""]

    (OUT_DIR / "drafts-latest.md").write_text("\n".join(md), encoding="utf-8")
    (OUT_DIR / "drafts-latest.json").write_text(
        json.dumps(
            {"generated_utc": now.isoformat(), "ready": len(ready), "skipped": len(skipped),
             "sends": 0, "drafts": [asdict(d) for d in drafts]},
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        out_disp = OUT_DIR.relative_to(ROOT)
    except ValueError:
        out_disp = OUT_DIR
    print(f"lead_draft: generated {len(ready)} CASL-structured draft(s) "
          f"(add a complete mailing address before sending), {len(skipped)} skipped. "
          f"No emails sent. Output: {out_disp}")
    return {"ready": len(ready), "skipped": len(skipped), "sends": 0}


if __name__ == "__main__":
    run()
