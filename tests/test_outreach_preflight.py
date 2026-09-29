"""The outreach pre-send gate blocks what went out on 2026-09-29, and passes a
compliant message. All names and addresses here are fictional."""

from __future__ import annotations

import json

from bots import outreach_preflight as op

COMPLIANT = """Hello Example Accounting team,

One concrete item since my note on 20 September. example.ca publishes no
DMARC record. The CAD $249 Quick-Audit covers it.

Desmond Otieno
ClearGlass Inc., PO Box 0000, Burlington ON L7R 0A0
desmondotieno@icloud.com | 289-707-0269

Reply STOP and I will not write again.
"""

# The shape of the follow-ups that went out on 2026-09-29.
SENT_WITH_PLACEHOLDER = """Hello Example Accounting team,

One concrete item since my note on 20 September.

Desmond Otieno
ClearGlass Inc., Burlington, Ontario
[ADD MAILING ADDRESS BEFORE SENDING]
desmondotieno@icloud.com | 289-707-0269

Reply STOP and I will not write again.

On Sun, Sep 20, 2026 03:56 PM, Desmond <sender@example.com> wrote:

> Hello Example Accounting team,
> Reply STOP to end messages.
"""


def codes(result: op.Result) -> set[str]:
    return {f.code for f in result.failures}


def test_compliant_message_is_ready():
    result = op.check(COMPLIANT)
    assert result.ready, result.failures
    assert not result.warnings


def test_the_29_september_follow_up_is_blocked():
    result = op.check(SENT_WITH_PLACEHOLDER)
    assert not result.ready
    assert codes(result) == {"PLACEHOLDER", "MAILING_ADDRESS"}
    assert "[ADD MAILING ADDRESS BEFORE SENDING]" in result.failures[0].detail


def test_city_and_province_alone_is_not_a_mailing_address():
    text = COMPLIANT.replace("PO Box 0000, Burlington ON L7R 0A0", "Burlington, Ontario")
    assert codes(op.check(text)) == {"MAILING_ADDRESS"}


def test_template_tokens_are_blocked():
    for token in ("{{First name}}", "[INSERT observation]", "<<company>>", "TODO"):
        text = COMPLIANT.replace("Hello Example Accounting team,", f"Hello {token},")
        assert "PLACEHOLDER" in codes(op.check(text)), token


def test_a_placeholder_in_quoted_text_still_blocks():
    text = COMPLIANT + "\n> Hi {{First name}},\n"
    assert "PLACEHOLDER" in codes(op.check(text))


def test_opt_out_must_be_in_the_new_text_not_only_the_quote():
    text = COMPLIANT.replace("Reply STOP and I will not write again.", "")
    text += "\nOn Sun, Sep 20, 2026 03:56 PM, Desmond wrote:\n> Reply STOP to end messages.\n"
    assert codes(op.check(text)) == {"OPT_OUT"}


def test_unsubscribe_wording_counts_as_opt_out():
    text = COMPLIANT.replace(
        "Reply STOP and I will not write again.", 'Reply "unsubscribe" to be removed.'
    )
    assert op.check(text).ready


def test_sender_must_be_identified():
    text = COMPLIANT.replace("ClearGlass Inc., ", "")
    assert codes(op.check(text)) == {"SENDER_ID"}


def test_contact_on_the_mx_less_domain_is_blocked():
    text = COMPLIANT.replace("desmondotieno@icloud.com", "hello@clearglassinc.com")
    assert codes(op.check(text)) == {"DEAD_CONTACT"}


def test_health_sector_is_a_warning_not_a_block():
    text = COMPLIANT.replace("Example Accounting team", "Example Dental clinic team")
    result = op.check(text)
    assert result.ready
    assert [w.code for w in result.warnings] == ["HEALTH_SECTOR"]


def test_postal_code_letters_follow_canada_post_rules():
    assert op.POSTAL_CODE_RE.search("L7R 0A0")
    assert op.POSTAL_CODE_RE.search("l7r0a0")
    assert not op.POSTAL_CODE_RE.search("D7R 0A0")  # D is never used
    assert not op.POSTAL_CODE_RE.search("W7R 0A0")  # W never leads


def test_cli_exit_status_and_json(tmp_path, capsys):
    good = tmp_path / "good.txt"
    bad = tmp_path / "bad.txt"
    good.write_text(COMPLIANT, encoding="utf-8")
    bad.write_text(SENT_WITH_PLACEHOLDER, encoding="utf-8")

    assert op.main([str(good)]) == 0
    assert "READY" in capsys.readouterr().out

    assert op.main(["--json", str(good), str(bad)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert [r["ready"] for r in report] == [True, False]
