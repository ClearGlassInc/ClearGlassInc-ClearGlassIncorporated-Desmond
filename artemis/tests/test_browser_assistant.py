import pytest

from artemis.intelligence.browser_assistant import BrowserResearchAssistant, CitedClaim, SecretBox
from artemis.intelligence.platform import AccessContext, ImmutableAuditLog


def ctx(*roles: str) -> AccessContext:
    return AccessContext(
        operator_id="analyst-1",
        roles=frozenset(roles),
        mission_ids=frozenset({"mission-browser"}),
        compartments=frozenset({"public"}),
        coalition="CLEARGLASSINC",
        purpose="investigation",
    )


def test_public_source_capture_note_and_cited_summary_are_audited():
    audit = ImmutableAuditLog()
    assistant = BrowserResearchAssistant(audit)

    tab = assistant.open_tab(ctx("analyst"), "https://example.org/advisory", "Public advisory")
    source = assistant.capture_source(ctx("analyst"), tab.tab_id, "patch immediately", "public-domain")
    note = assistant.write_note(ctx("analyst"), tab.tab_id, "Patch exposure noted.", (source.source_id,))
    artifact = assistant.summarize(
        ctx("analyst"),
        "Defensive summary",
        (CitedClaim("The advisory recommends immediate patching.", (source.source_id,)),),
    )

    assert note.source_ids == (source.source_id,)
    assert artifact.claims[0].source_ids == (source.source_id,)
    assert audit.verify()
    assert len(audit.records) >= 4


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1:8000/admin", "http://service.internal/path"])
def test_osint_ingestion_rejects_non_public_sources(url):
    assistant = BrowserResearchAssistant()
    with pytest.raises(ValueError):
        assistant.open_tab(ctx("analyst"), url, "Blocked")


def test_summary_rejects_uncited_claims():
    assistant = BrowserResearchAssistant()
    with pytest.raises(ValueError, match="requires at least one citation"):
        assistant.summarize(ctx("analyst"), "Bad summary", (CitedClaim("Unsupported claim", ()),))


def test_rbac_blocks_reviewer_from_capture_and_records_denial():
    audit = ImmutableAuditLog()
    assistant = BrowserResearchAssistant(audit)
    with pytest.raises(PermissionError):
        assistant.open_tab(ctx("reviewer"), "https://example.org", "No capture")
    assert audit.verify()
    assert audit.records[-1].decision == "DENY"


def test_secret_box_round_trip_and_tamper_detection():
    box = SecretBox()
    sealed = box.seal("api-token", "correct horse battery staple")
    assert box.open(sealed, "correct horse battery staple") == "api-token"
    sealed["ciphertext"] = sealed["ciphertext"][::-1]
    with pytest.raises(ValueError, match="authentication failed"):
        box.open(sealed, "correct horse battery staple")
