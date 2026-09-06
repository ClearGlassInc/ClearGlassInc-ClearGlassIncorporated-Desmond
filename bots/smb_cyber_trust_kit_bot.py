# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass SMB Cyber Trust Kit — deterministic content engine.

This is the single source of truth for the ClearGlass SMB Cyber Trust Kit, a
plain-language cyber resilience starter pack for small and medium businesses
(Ontario / Canadian context: PIPEDA, PHIPA, CASL aware). It contains four
deliverables and the logic an agent uses to work with them:

  1. Simple policy templates        -> fill-in-the-blank, owner-ready policies
  2. A risk heat-map template        -> 5x5 likelihood x impact register
  3. "Communication during incidents" script -> phase x audience holding lines
  4. "How to talk to non-technical people about cyber risk" mini-guide

Everything here is pure and deterministic: no network calls, no side effects
beyond the explicit ``write_outputs`` step. The web console (the embedded
agent) and the Python agent layer both consume ``build_kit`` / ``kit_payload``
so the browser and the backend never drift apart.

Usage:
    python -m bots.smb_cyber_trust_kit_bot                 # render + write
    python -m bots.smb_cyber_trust_kit_bot --print         # markdown to stdout
    python -m bots.smb_cyber_trust_kit_bot --org "Acme Co" # personalise
    python -m bots.smb_cyber_trust_kit_bot --json          # emit kit JSON
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "smb_cyber_trust_kit"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
WEB_DATA_PATH = ROOT / "assets" / "data" / "smb-cyber-trust-kit.json"

KIT_NAME = "ClearGlass SMB Cyber Trust Kit"
KIT_VERSION = "1.0.0"
DEFAULT_ORG = "[Your Business Name]"

# ---------------------------------------------------------------------------
# 1. Risk heat-map model
# ---------------------------------------------------------------------------

LIKELIHOOD_SCALE: dict[int, str] = {
    1: "Rare — would be surprising (once in many years)",
    2: "Unlikely — possible but not expected this year",
    3: "Possible — could reasonably happen this year",
    4: "Likely — expect it within the year",
    5: "Almost certain — happening now or imminent",
}

IMPACT_SCALE: dict[int, str] = {
    1: "Negligible — a nuisance, no real cost",
    2: "Minor — a few hours lost, small cost",
    3: "Moderate — a day or two down, noticeable cost",
    4: "Major — serious disruption, money + reputation",
    5: "Severe — business-threatening, legal/regulatory exposure",
}


@dataclass(frozen=True)
class RiskBand:
    name: str
    color: str
    min_score: int
    max_score: int
    action: str


# Bands over the 1..25 product space. Colours align to the brand prism so the
# web heat-map and the printed kit show the same language.
RISK_BANDS: tuple[RiskBand, ...] = (
    RiskBand("Low", "#34d399", 1, 4,
             "Accept and monitor. Review at the normal cadence."),
    RiskBand("Moderate", "#fbbf24", 5, 9,
             "Plan a fix. Assign an owner and a target date this quarter."),
    RiskBand("High", "#fb7185", 10, 15,
             "Act soon. Put a control in place within 30 days."),
    RiskBand("Critical", "#ef4444", 16, 25,
             "Act now. Escalate to the owner today; treat as a priority."),
)


@dataclass(frozen=True)
class RiskScore:
    likelihood: int
    impact: int
    score: int
    band: str
    color: str
    action: str


def _clamp_1_5(value: int, label: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{label} must be an int 1-5, got {value!r}")
    if value < 1 or value > 5:
        raise ValueError(f"{label} must be between 1 and 5, got {value}")
    return value


def band_for_score(score: int) -> RiskBand:
    """Return the risk band a 1..25 score falls into."""
    for band in RISK_BANDS:
        if band.min_score <= score <= band.max_score:
            return band
    # Defensive: scores are products of 1..5 so this should be unreachable.
    return RISK_BANDS[-1] if score > RISK_BANDS[-1].max_score else RISK_BANDS[0]


def score_risk(likelihood: int, impact: int) -> RiskScore:
    """Score a single risk. score = likelihood x impact, banded 1..25."""
    likelihood = _clamp_1_5(likelihood, "likelihood")
    impact = _clamp_1_5(impact, "impact")
    score = likelihood * impact
    band = band_for_score(score)
    return RiskScore(likelihood, impact, score, band.name, band.color, band.action)


@dataclass(frozen=True)
class Risk:
    id: str
    title: str
    category: str
    likelihood: int
    impact: int
    note: str = ""


# A starter register of the risks that actually hurt small businesses. Owners
# edit the numbers; the bands recompute automatically.
DEFAULT_RISK_REGISTER: tuple[Risk, ...] = (
    Risk("R1", "Phishing / business email compromise", "People", 4, 4,
         "Most common entry point. Fake invoice or 'CEO' wire request."),
    Risk("R2", "Ransomware locks files / servers", "Systems", 3, 5,
         "Often arrives via phishing or an unpatched remote login."),
    Risk("R3", "Stolen or reused passwords", "Identity", 4, 4,
         "One leaked password unlocks email, banking, and cloud apps."),
    Risk("R4", "No multi-factor authentication (MFA)", "Identity", 4, 5,
         "Without MFA, a stolen password is a full account takeover."),
    Risk("R5", "Lost or stolen laptop / phone", "Devices", 3, 3,
         "Unencrypted device = the data on it is gone with the device."),
    Risk("R6", "No tested backups", "Recovery", 3, 5,
         "A backup you have never restored is a guess, not a safety net."),
    Risk("R7", "Unpatched software / overdue updates", "Systems", 4, 3,
         "Known holes get exploited within days of a patch release."),
    Risk("R8", "Ex-employee access not removed", "Identity", 3, 4,
         "Accounts that outlive the job are a quiet, standing risk."),
    Risk("R9", "Sensitive data emailed in the clear", "Data", 3, 3,
         "Client PII / health info sent unprotected can trigger reporting."),
    Risk("R10", "Vendor / supplier breach reaches you", "Third-party", 2, 4,
         "Their access and their breach become your incident."),
    Risk("R11", "Website / customer portal defaced or down", "Systems", 2, 3,
         "Reputation and revenue both take the hit when it is public."),
    Risk("R12", "Staff unsure who to call in an incident", "People", 4, 3,
         "Minutes lost in confusion are the most expensive minutes."),
)


@dataclass(frozen=True)
class HeatCell:
    likelihood: int
    impact: int
    score: int
    band: str
    color: str
    risk_ids: tuple[str, ...]


def build_heat_map(register: tuple[Risk, ...] = DEFAULT_RISK_REGISTER) -> list[HeatCell]:
    """Place every risk on the 5x5 grid and return populated cells.

    Returns 25 cells ordered impact 5->1 (rows, top = worst) then
    likelihood 1->5 (columns), which is how the printed grid reads.
    """
    placed: dict[tuple[int, int], list[str]] = {}
    for risk in register:
        key = (risk.likelihood, risk.impact)
        placed.setdefault(key, []).append(risk.id)

    cells: list[HeatCell] = []
    for impact in range(5, 0, -1):
        for likelihood in range(1, 6):
            rs = score_risk(likelihood, impact)
            cells.append(HeatCell(
                likelihood=likelihood,
                impact=impact,
                score=rs.score,
                band=rs.band,
                color=rs.color,
                risk_ids=tuple(placed.get((likelihood, impact), [])),
            ))
    return cells


def rank_risks(register: tuple[Risk, ...] = DEFAULT_RISK_REGISTER) -> list[RiskScore]:
    """Risks scored and sorted worst-first — the owner's to-do order."""
    scored = []
    for risk in register:
        rs = score_risk(risk.likelihood, risk.impact)
        scored.append((risk, rs))
    scored.sort(key=lambda pair: (-pair[1].score, pair[0].id))
    return [rs for _, rs in scored]


# ---------------------------------------------------------------------------
# 2. Simple policy templates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Policy:
    id: str
    title: str
    purpose: str
    scope: str
    rules: tuple[str, ...]
    owner_role: str
    review_cadence: str


POLICIES: tuple[Policy, ...] = (
    Policy(
        "acceptable-use", "Acceptable Use Policy",
        "Set clear, fair rules for using company devices, accounts, and data.",
        "Everyone who uses {org} systems: staff, contractors, and volunteers.",
        (
            "Use company accounts and devices for work purposes; keep "
            "reasonable personal use lawful and minimal.",
            "Do not install unapproved software or plug in unknown USB drives.",
            "Do not share your login with anyone, including co-workers.",
            "Lock your screen when you step away.",
            "Report anything that looks suspicious — no blame for a fast report.",
        ),
        "Owner / Office Manager", "Annually, or after a major change",
    ),
    Policy(
        "passwords-mfa", "Password & Multi-Factor Authentication Policy",
        "Keep accounts hard to break into, even if a password leaks.",
        "All {org} accounts: email, banking, cloud apps, and admin logins.",
        (
            "Use a unique passphrase of 12+ characters for every account.",
            "Use the company password manager — never a sticky note or a "
            "shared spreadsheet.",
            "Turn on multi-factor authentication (MFA) on every account that "
            "offers it, especially email and banking.",
            "Never approve an MFA prompt you did not start.",
            "Change a password immediately if you suspect it was exposed.",
        ),
        "Owner / IT Lead", "Annually",
    ),
    Policy(
        "data-protection", "Data Protection & Privacy Policy",
        "Protect customer and staff information and meet privacy obligations.",
        "All personal and sensitive data {org} collects, stores, or shares.",
        (
            "Collect only the information you actually need.",
            "Store sensitive data in approved systems — not personal email or "
            "personal cloud drives.",
            "Encrypt laptops, phones, and backups.",
            "Share sensitive data only over approved, protected channels.",
            "Delete data you no longer need on a defined schedule.",
            "Know your obligations under PIPEDA (and PHIPA for health data).",
        ),
        "Owner / Privacy Lead", "Annually, or after a process change",
    ),
    Policy(
        "incident-response", "Incident Response Policy",
        "Make sure everyone knows what to do in the first hour of an incident.",
        "Any suspected breach, ransomware, lost device, or account takeover.",
        (
            "If you suspect an incident, report it to {incident_contact} "
            "immediately — speed beats certainty.",
            "Do not turn the device off or 'clean it up' — preserve evidence.",
            "The incident lead decides on containment (disconnect, reset "
            "passwords, isolate).",
            "Follow the Communication During Incidents script for who to tell "
            "and when.",
            "Write down what happened and when — a simple timeline is enough.",
            "Hold a short blameless review within a week to fix root causes.",
        ),
        "Owner / Incident Lead", "Annually, plus after every incident",
    ),
    Policy(
        "access-control", "Access Control (Joiners, Movers, Leavers) Policy",
        "Give people the access they need — and remove it the day they leave.",
        "All accounts and physical access across {org}.",
        (
            "Grant the least access needed to do the job.",
            "Set up new-starter access from a checklist on day one.",
            "Review access when someone changes role.",
            "Remove all access the same day someone leaves — accounts, "
            "devices, building keys, and shared passwords.",
            "Review who has admin rights every quarter.",
        ),
        "Owner / Office Manager", "Quarterly access review",
    ),
    Policy(
        "backup-recovery", "Backup & Recovery Policy",
        "Be able to get back to work quickly after loss, theft, or ransomware.",
        "All business-critical data, files, and systems.",
        (
            "Follow 3-2-1: three copies, on two types of media, one off-site.",
            "Automate backups daily for anything you cannot afford to retype.",
            "Keep at least one backup offline or otherwise out of reach of "
            "ransomware.",
            "Test a real restore at least quarterly — an untested backup is a "
            "guess.",
            "Know your target recovery time for the systems that matter most.",
        ),
        "Owner / IT Lead", "Quarterly restore test",
    ),
    Policy(
        "vendor-risk", "Vendor & Third-Party Risk Policy",
        "Make sure the suppliers you trust do not become your weak point.",
        "Any vendor with access to {org} data, systems, or accounts.",
        (
            "Keep a simple list of vendors and what each can access.",
            "Ask new vendors how they protect your data before you sign.",
            "Give vendors the least access they need, and remove it when the "
            "work ends.",
            "Require vendors to tell you promptly if they have a breach.",
            "Review the vendor list once a year.",
        ),
        "Owner", "Annually",
    ),
    Policy(
        "device-byod", "Device & Bring-Your-Own-Device (BYOD) Policy",
        "Keep work data safe on the phones and laptops people actually use.",
        "Company and personal devices used for {org} work.",
        (
            "Protect every device with a passcode or biometric lock.",
            "Keep operating systems and apps updated.",
            "Encrypt devices that hold work data.",
            "Enable remote-wipe for lost or stolen devices.",
            "Report a lost or stolen device immediately so access can be cut.",
        ),
        "Owner / IT Lead", "Annually",
    ),
)


def render_policy(policy: Policy, org: str = DEFAULT_ORG,
                  incident_contact: str = "[Incident Lead — name & number]") -> str:
    """Render one policy to plain Markdown with the org name filled in."""
    scope = policy.scope.format(org=org)
    rules = "\n".join(
        f"{i}. {rule.format(org=org, incident_contact=incident_contact)}"
        for i, rule in enumerate(policy.rules, start=1)
    )
    return (
        f"### {policy.title}\n\n"
        f"**Purpose.** {policy.purpose}\n\n"
        f"**Who it covers.** {scope}\n\n"
        f"**The rules.**\n{rules}\n\n"
        f"**Owner:** {policy.owner_role}  \n"
        f"**Review:** {policy.review_cadence}\n"
    )


# ---------------------------------------------------------------------------
# 3. Communication during incidents script
# ---------------------------------------------------------------------------

INCIDENT_PHASES: tuple[str, ...] = (
    "detect", "contain", "eradicate", "recover", "post-incident",
)


@dataclass(frozen=True)
class IncidentScript:
    id: str
    audience: str
    phase: str
    channel: str
    when_to_use: str
    approver: str
    template: str


# {placeholders} stay literal in the kit so the team fills them at go-time.
INCIDENT_SCRIPTS: tuple[IncidentScript, ...] = (
    IncidentScript(
        "staff-alert", "Internal staff", "contain", "Internal chat / all-hands",
        "First message to the team once an incident is confirmed.",
        "Incident Lead",
        "Team — we are responding to a security incident affecting "
        "{systems_affected}. Please {staff_action} now. Do not discuss this "
        "outside the company or post about it. Direct all questions to "
        "{incident_contact}. Next update by {next_update_time}.",
    ),
    IncidentScript(
        "staff-allclear", "Internal staff", "recover", "Internal chat / all-hands",
        "When systems are restored and normal work resumes.",
        "Incident Lead",
        "Update — the incident affecting {systems_affected} is resolved and "
        "systems are back to normal as of {resolved_time}. Thank you for "
        "your patience. If you notice anything unusual, tell {incident_contact}. "
        "A short review follows so we come out stronger.",
    ),
    IncidentScript(
        "customer-notice", "Customers", "contain", "Email / status page",
        "Early, honest notice while you are still responding.",
        "Owner",
        "We are writing to let you know we identified a security issue on "
        "{date} affecting {systems_affected}. We acted quickly to contain it "
        "and are investigating with care. {customer_impact_statement} We will "
        "share another update by {next_update_time}. Questions: {support_contact}.",
    ),
    IncidentScript(
        "customer-resolution", "Customers", "recover", "Email / status page",
        "Closing the loop once service is restored.",
        "Owner",
        "Update on the {date} security issue: it is now resolved. "
        "{what_we_did} {what_we_changed} We take the trust you place in us "
        "seriously and are sorry for any disruption. Questions: {support_contact}.",
    ),
    IncidentScript(
        "breach-affected", "Affected individuals", "post-incident", "Email / letter",
        "If personal information was exposed (PIPEDA / PHIPA may require notice).",
        "Owner + Privacy Lead (consider legal review)",
        "We are notifying you that a security incident on {date} may have "
        "exposed the following information about you: {data_categories}. Here "
        "is what happened, what we have done, and steps you can take: "
        "{protective_steps}. We have reported this as required. For help, "
        "contact {privacy_contact}.",
    ),
    IncidentScript(
        "regulator-notice", "Privacy regulator", "post-incident", "Official form / letter",
        "Report to the Privacy Commissioner when a breach poses real risk of "
        "significant harm (PIPEDA) or per PHIPA for health information.",
        "Owner + Privacy Lead (legal review recommended)",
        "Organization: {org}. Date of incident: {date}. Nature of breach: "
        "{breach_nature}. Personal information involved: {data_categories}. "
        "Estimated individuals affected: {affected_count}. Containment and "
        "remediation: {remediation}. Notification to individuals: {notice_status}. "
        "Contact: {privacy_contact}.",
    ),
    IncidentScript(
        "partner-notice", "Partners & vendors", "contain", "Email / phone",
        "When a partner's data or shared systems may be involved.",
        "Owner",
        "We are managing a security incident that may touch our shared "
        "{shared_resource}. As a precaution we have {precaution_taken}. Please "
        "watch for {what_to_watch_for} and let us know of anything unusual. "
        "Coordination contact: {incident_contact}.",
    ),
    IncidentScript(
        "media-holding", "Media / public", "contain", "Spokesperson statement",
        "A short holding line if the incident becomes public. One spokesperson only.",
        "Owner (single approved spokesperson)",
        "We are aware of a security incident and are responding with urgency. "
        "Protecting our customers' information is our priority. We have engaged "
        "the right expertise, are taking steps to contain it, and will share "
        "verified information as it becomes available.",
    ),
)

COMMS_PRINCIPLES: tuple[str, ...] = (
    "Be first, be honest, be brief — silence reads as a cover-up.",
    "Say what you know, what you don't yet know, and when you'll update next.",
    "One approved spokesperson. Everyone else routes questions to them.",
    "Never speculate on cause, numbers, or blame before the facts are in.",
    "Write a timeline as you go — it protects you and speeds the review.",
    "Tell people what to DO (the action) before why it happened.",
)


def incident_script(audience: str, phase: str | None = None) -> list[IncidentScript]:
    """Return matching scripts for an audience (optionally a phase)."""
    aud = audience.strip().lower()
    matches = [s for s in INCIDENT_SCRIPTS if s.audience.lower() == aud]
    if phase is not None:
        ph = phase.strip().lower()
        matches = [s for s in matches if s.phase.lower() == ph]
    return matches


# ---------------------------------------------------------------------------
# 4. Mini-guide: talking to non-technical people about cyber risk
# ---------------------------------------------------------------------------

GUIDE_PRINCIPLES: tuple[str, ...] = (
    "Lead with the business, not the technology: money, time, trust, "
    "reputation, and legal exposure.",
    "Translate every risk into 'if this happens, then this is the cost.'",
    "Use one analogy they already understand (a door, a key, insurance).",
    "Give one clear recommendation, not five options.",
    "Quantify with ranges, not false precision: 'a day or two offline.'",
    "Replace fear with a next step — people act on direction, not dread.",
    "Check for understanding: ask them to say it back in their own words.",
)


@dataclass(frozen=True)
class JargonTerm:
    term: str
    plain: str
    analogy: str


JARGON_GLOSSARY: tuple[JargonTerm, ...] = (
    JargonTerm(
        "Phishing", "A fake email or text that tricks someone into clicking, "
        "paying, or giving up a password.",
        "A con artist in a delivery uniform talking their way through the door."),
    JargonTerm(
        "Ransomware", "Malicious software that locks your files until you pay — "
        "and paying is no guarantee.",
        "A burglar who changes all your locks and sells you the new keys."),
    JargonTerm(
        "Multi-factor authentication (MFA)", "A second check beyond your "
        "password, like a code on your phone.",
        "A deadbolt on top of the doorknob lock."),
    JargonTerm(
        "Patch / update", "A fix the vendor releases to close a known security "
        "hole.",
        "Repairing a lock the manufacturer just warned everyone is pickable."),
    JargonTerm(
        "Encryption", "Scrambling data so it's useless to anyone without the "
        "key.",
        "A document shredder that can be perfectly un-shredded only by you."),
    JargonTerm(
        "Firewall", "A filter that decides what network traffic is allowed in "
        "or out.",
        "A bouncer checking everyone at the door against the guest list."),
    JargonTerm(
        "Backup", "A spare copy of your data you can restore after loss or "
        "attack.",
        "A photocopy of every important document, kept in a different building."),
    JargonTerm(
        "Breach", "An incident where data is accessed or taken by someone who "
        "shouldn't have it.",
        "Discovering the filing cabinet was opened and copied overnight."),
    JargonTerm(
        "Endpoint", "Any device that connects to your systems — laptop, phone, "
        "tablet.",
        "Every door and window into the building."),
    JargonTerm(
        "Zero-day", "A brand-new flaw that attackers know about before a fix "
        "exists.",
        "A lock flaw the locksmith hasn't learned about yet."),
    JargonTerm(
        "Social engineering", "Manipulating a person, not a computer, to get "
        "access.",
        "Sweet-talking the receptionist instead of breaking the lock."),
    JargonTerm(
        "Attack surface", "All the ways someone could possibly get in.",
        "The total number of doors, windows, and vents on the building."),
)


@dataclass(frozen=True)
class TalkingScenario:
    situation: str
    say_this: str
    not_this: str


TALKING_SCENARIOS: tuple[TalkingScenario, ...] = (
    TalkingScenario(
        "Asking the owner to fund MFA",
        "For about the cost of a coffee per person each month, a stolen "
        "password stops being enough to drain the bank account.",
        "We need to deploy TOTP-based 2FA across the identity provider."),
    TalkingScenario(
        "Explaining why backups matter",
        "If ransomware hit tomorrow, tested backups are the difference between "
        "a bad day and a closed business.",
        "We have no immutable, air-gapped recovery tier."),
    TalkingScenario(
        "Justifying patching downtime",
        "A 20-minute update tonight closes a hole criminals are already using "
        "this week.",
        "There's an unpatched CVE with a public exploit in the wild."),
    TalkingScenario(
        "Reporting an incident to the board",
        "Here's what happened, what it cost us, what we've fixed, and the one "
        "thing we're changing so it can't repeat.",
        "We observed anomalous lateral movement and exfiltration indicators."),
)


# ---------------------------------------------------------------------------
# Kit assembly + rendering
# ---------------------------------------------------------------------------


def build_kit(org: str = DEFAULT_ORG,
              register: tuple[Risk, ...] = DEFAULT_RISK_REGISTER) -> dict:
    """Assemble the entire kit as a plain dict (JSON-serialisable)."""
    return {
        "name": KIT_NAME,
        "version": KIT_VERSION,
        "org": org,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "risk_model": {
            "likelihood_scale": LIKELIHOOD_SCALE,
            "impact_scale": IMPACT_SCALE,
            "bands": [asdict(b) for b in RISK_BANDS],
            "register": [asdict(r) for r in register],
            "heat_map": [asdict(c) for c in build_heat_map(register)],
            "ranked": [asdict(r) for r in rank_risks(register)],
        },
        "policies": [asdict(p) for p in POLICIES],
        "incident_comms": {
            "phases": list(INCIDENT_PHASES),
            "principles": list(COMMS_PRINCIPLES),
            "scripts": [asdict(s) for s in INCIDENT_SCRIPTS],
        },
        "plain_language_guide": {
            "principles": list(GUIDE_PRINCIPLES),
            "glossary": [asdict(t) for t in JARGON_GLOSSARY],
            "scenarios": [asdict(s) for s in TALKING_SCENARIOS],
        },
    }


def kit_payload(org: str = DEFAULT_ORG) -> str:
    """JSON string of the kit — what the web console and agent ingest."""
    return json.dumps(build_kit(org), indent=2, ensure_ascii=False)


def _render_heat_map_md(register: tuple[Risk, ...]) -> str:
    head = "| Impact \\ Likelihood | 1 Rare | 2 Unlikely | 3 Possible | 4 Likely | 5 Almost certain |"
    sep = "|---|---|---|---|---|---|"
    rows = [head, sep]
    for impact in range(5, 0, -1):
        cells = [f"**{impact}**"]
        for likelihood in range(1, 6):
            rs = score_risk(likelihood, impact)
            ids = [r.id for r in register
                   if r.likelihood == likelihood and r.impact == impact]
            label = f"{rs.score} {rs.band[0]}"
            if ids:
                label += f" · {','.join(ids)}"
            cells.append(label)
        rows.append("| " + " | ".join(cells) + " |")
    legend = "  \n".join(
        f"- **{b.name}** ({b.min_score}-{b.max_score}): {b.action}"
        for b in RISK_BANDS
    )
    register_lines = "\n".join(
        f"- **{r.id} {r.title}** ({r.category}) — L{r.likelihood} x I{r.impact} "
        f"= {score_risk(r.likelihood, r.impact).score} "
        f"({score_risk(r.likelihood, r.impact).band}). {r.note}"
        for r in register
    )
    return (
        "## 2. Risk Heat-Map Template\n\n"
        "Score each risk: **Likelihood (1-5) x Impact (1-5)**. The cell colour "
        "is the band; cells list the starter risks placed on the map.\n\n"
        f"{chr(10).join(rows)}\n\n"
        f"**Bands.**  \n{legend}\n\n"
        f"**Starter risk register** (edit the numbers for your business):\n\n"
        f"{register_lines}\n"
    )


def _render_incident_md() -> str:
    principles = "\n".join(f"- {p}" for p in COMMS_PRINCIPLES)
    blocks = []
    for s in INCIDENT_SCRIPTS:
        blocks.append(
            f"#### {s.audience} — {s.phase} ({s.channel})\n"
            f"*When to use:* {s.when_to_use}  \n"
            f"*Approver:* {s.approver}\n\n"
            f"> {s.template}\n"
        )
    return (
        "## 3. Communication During Incidents Script\n\n"
        f"**Principles.**\n{principles}\n\n"
        "Fill the `{placeholders}` at go-time. Keep one approved spokesperson.\n\n"
        + "\n".join(blocks)
    )


def _render_guide_md() -> str:
    principles = "\n".join(f"{i}. {p}" for i, p in enumerate(GUIDE_PRINCIPLES, 1))
    glossary = "\n".join(
        f"| {t.term} | {t.plain} | {t.analogy} |" for t in JARGON_GLOSSARY
    )
    scenarios = "\n\n".join(
        f"**{s.situation}**  \n✅ Say: \"{s.say_this}\"  \n🚫 Not: \"{s.not_this}\""
        for s in TALKING_SCENARIOS
    )
    return (
        "## 4. Mini-Guide: How to Talk to Non-Technical People About Cyber Risk\n\n"
        f"**Principles.**\n{principles}\n\n"
        "**Jargon → plain language.**\n\n"
        "| Term | In plain words | Analogy |\n|---|---|---|\n"
        f"{glossary}\n\n"
        "**What to say when…**\n\n"
        f"{scenarios}\n"
    )


def render_markdown(org: str = DEFAULT_ORG,
                    register: tuple[Risk, ...] = DEFAULT_RISK_REGISTER) -> str:
    """Render the full kit as one Markdown document."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    policies_md = "\n".join(render_policy(p, org=org) for p in POLICIES)
    return (
        f"# {KIT_NAME}\n\n"
        f"*Version {KIT_VERSION} · prepared for {org} · {generated}*\n\n"
        "A plain-language cyber resilience starter pack for small and medium "
        "businesses. Four pieces: policy templates, a risk heat-map, an "
        "incident communication script, and a guide to talking about cyber "
        "risk without jargon. Edit anything in `[brackets]` or `{braces}`.\n\n"
        "> Practical guidance, not legal advice. For PIPEDA / PHIPA breach "
        "obligations, confirm specifics with a qualified advisor.\n\n"
        "## 1. Simple Policy Templates\n\n"
        f"{policies_md}\n"
        f"{_render_heat_map_md(register)}\n"
        f"{_render_incident_md()}\n"
        f"{_render_guide_md()}\n"
        "---\n\n"
        "*ClearGlass Inc. · Clarity Is Power · Burlington, Ontario*\n"
    )


def write_outputs(org: str = DEFAULT_ORG) -> dict[str, Path]:
    """Write Markdown + JSON to operations/ and refresh the web data file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md = render_markdown(org)
    payload = build_kit(org)

    paths = {
        "markdown_latest": OUTPUT_DIR / "smb-cyber-trust-kit.md",
        "json_latest": OUTPUT_DIR / "smb-cyber-trust-kit.json",
        "markdown_archive": ARCHIVE_DIR / f"smb-cyber-trust-kit-{stamp}.md",
        "web_data": WEB_DATA_PATH,
    }
    paths["markdown_latest"].write_text(md, encoding="utf-8")
    paths["markdown_archive"].write_text(md, encoding="utf-8")
    paths["json_latest"].write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["web_data"].write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return paths


def run() -> dict[str, Path]:
    """Entry point for the universal bot runner — writes the kit with defaults."""
    paths = write_outputs()
    print(f"{KIT_NAME} v{KIT_VERSION} written:")
    for label, path in paths.items():
        print(f"  {label}: {path.relative_to(ROOT)}")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{KIT_NAME} content engine")
    parser.add_argument("--org", default=DEFAULT_ORG,
                        help="Business name to personalise the kit")
    parser.add_argument("--print", action="store_true", dest="to_stdout",
                        help="Print Markdown to stdout instead of writing files")
    parser.add_argument("--json", action="store_true",
                        help="Print the kit JSON payload to stdout")
    args = parser.parse_args(argv)

    if args.json:
        print(kit_payload(args.org))
        return 0
    if args.to_stdout:
        print(render_markdown(args.org))
        return 0

    paths = write_outputs(args.org)
    for label, path in paths.items():
        print(f"{label}: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
