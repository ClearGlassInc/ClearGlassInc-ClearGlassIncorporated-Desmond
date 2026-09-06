from clearglassinc_sdk.guardrails import (
    MaxLengthGuardrail,
    RegexBlocklistGuardrail,
    RequiredKeywordsGuardrail,
    run_guardrails,
)


def test_max_length_guardrail():
    guardrail = MaxLengthGuardrail(max_chars=5)
    assert guardrail.check("hi").passed
    result = guardrail.check("way too long")
    assert not result.passed
    assert "5 characters" in result.reason


def test_regex_blocklist_guardrail_blocks_matches():
    guardrail = RegexBlocklistGuardrail(patterns=[r"sk-[A-Za-z0-9]{10,}"])
    assert guardrail.check("nothing sensitive here").passed
    result = guardrail.check("here is my key sk-abcdefghijklmnop")
    assert not result.passed


def test_required_keywords_guardrail():
    guardrail = RequiredKeywordsGuardrail(keywords=["order", "refund"])
    assert guardrail.check("please process my refund").passed
    assert not guardrail.check("what's the weather today").passed


def test_run_guardrails_short_circuits_on_first_failure():
    guardrails = [MaxLengthGuardrail(max_chars=100), RequiredKeywordsGuardrail(keywords=["hello"])]
    result = run_guardrails(guardrails, "goodbye")
    assert not result.passed
    assert "hello" in result.reason


def test_run_guardrails_passes_when_all_pass():
    guardrails = [MaxLengthGuardrail(max_chars=100)]
    result = run_guardrails(guardrails, "short text")
    assert result.passed
