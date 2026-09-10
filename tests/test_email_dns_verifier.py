from operations.email.verify_email_dns import evaluate, unquote_txt


def test_unquote_txt_joins_dns_chunks():
    assert unquote_txt('"v=spf1 include:_spf.google.com " "~all"') == "v=spf1 include:_spf.google.com ~all"


def test_evaluate_accepts_complete_google_workspace_configuration():
    records = {
        ("clearglassinc.com", "MX"): ["1 smtp.google.com."],
        ("clearglassinc.com", "TXT"): ['"google-site-verification=opaque"', '"v=spf1 include:_spf.google.com ~all"'],
        ("_dmarc.clearglassinc.com", "TXT"): ['"v=DMARC1; p=none; rua=mailto:desmond@clearglassinc.com"'],
        ("google._domainkey.clearglassinc.com", "TXT"): ['"v=DKIM1; k=rsa; p=publickey"'],
    }

    checks = evaluate(lambda name, kind: records.get((name, kind), []), dkim_selector="google")

    assert all(check.passed for check in checks)


def test_evaluate_fails_closed_for_duplicate_spf_and_missing_controls():
    records = {
        ("clearglassinc.com", "MX"): ["10 mail.example.net."],
        ("clearglassinc.com", "TXT"): ['"v=spf1 include:_spf.google.com ~all"', '"v=spf1 -all"'],
    }

    checks = evaluate(lambda name, kind: records.get((name, kind), []))

    assert {check.name for check in checks if not check.passed} == {"MX", "SPF", "DMARC", "DKIM"}
