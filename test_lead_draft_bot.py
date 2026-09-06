# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/lead_draft_bot.py — generation only, never sends."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots import lead_draft_bot as bot  # noqa: E402
from bots.lead_draft_bot import build_draft, pick_template, render, run  # noqa: E402


def _lead(**over):
    base = {
        "Company": "Acme Accounting",
        "Sector": "Accounting",
        "Recommended_offer": "Security Quick-Audit",
        "Consent_basis": "Published business email (CASL)",
        "Public_source_URL": "https://example.ca/",
        "Next_action": "Personalize + send Template 1",
    }
    base.update(over)
    return base


def test_template_selection():
    assert pick_template("Security Quick-Audit", "Template 1") == "quick_audit"
    assert pick_template("Hardening Sprint (Standard)", "Template 2") == "hardening"
    assert pick_template("Automation", "Template 4") == "automation"


def test_every_draft_carries_casl_footer_and_no_send():
    subject, body = render("quick_audit", "Acme Co", "Accounting")
    assert "unsubscribe" in body.lower()
    assert "Burlington, Ontario" in body
    assert "ClearGlass Inc." in body
    # placeholders for human review — bot must not fabricate name/observation
    assert "{{First name}}" in body
    assert "specific public observation" in body


def test_eligible_lead_produces_draft():
    d = build_draft(_lead())
    assert d.status == "draft"
    assert d.template == "quick_audit"
    assert d.company == "Acme Accounting"
    assert d.verify_contact_at  # a place to confirm the public email


def test_health_sector_is_excluded():
    d = build_draft(_lead(Sector="Health Clinic", Recommended_offer="PHIPA Readiness"))
    assert d.status == "skipped"
    assert "excluded sector" in d.skip_reason


def test_non_casl_consent_is_skipped():
    d = build_draft(_lead(Consent_basis="purchased list"))
    assert d.status == "skipped"
    assert "consent" in d.skip_reason.lower()


def test_bot_has_no_mail_transport():
    """Hard guarantee: the bot cannot send email."""
    src = inspect.getsource(bot)
    for forbidden in ("smtplib", "sendmail", "SMTP(", "send_message", "yagmail", "sendgrid"):
        assert forbidden not in src, f"lead_draft_bot must not send mail ({forbidden})"


def test_run_writes_drafts_and_reports_zero_sends(tmp_path, monkeypatch):
    # Point the bot at a temp outreach dir with one eligible + one excluded lead.
    outreach = tmp_path / "offers" / "outreach"
    outreach.mkdir(parents=True)
    (outreach / "lead-list-test.csv").write_text(
        "Company,Sector,Recommended_offer,Consent_basis,Public_source_URL,Next_action\n"
        '"NOTE: instructional row",,,,,\n'
        '"Acme Accounting",Accounting,Security Quick-Audit,Published business email (CASL),https://acme.ca/,Template 1\n'
        '"Riverside Clinic",Health Clinic,PHIPA Readiness,Published business email (CASL),https://clinic.ca/,Template 3\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(bot, "OUTREACH_DIR", outreach)
    monkeypatch.setattr(bot, "OUT_DIR", outreach / "generated")

    result = run()
    assert result["sends"] == 0
    assert result["ready"] == 1
    assert result["skipped"] == 1
    md = (outreach / "generated" / "drafts-latest.md").read_text()
    assert "Acme Accounting" in md
    assert "DRAFTS" in md  # the no-send banner
