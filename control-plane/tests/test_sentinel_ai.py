"""Sentinel Core answered by Claude: the loop, the guards and the ledger.

No test here calls the Anthropic API. A scripted fake client stands in for the
model, so what is pinned is everything ClearGlass controls: which tools Claude
gets (read-only, strict), how the loop ends (a round cap that withdraws the
tools), what is sent (fallbacks, adaptive thinking, the cached system prompt),
what is refused before any call (credentials, a spent daily cap, an off-site
page), and what the ledger keeps (a keyed hash, never the question).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import sentinel_ai  # noqa: E402
from app.config import Settings  # noqa: E402
from app.governance import score_action  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "data" / "site-index.json"
REPO_PROMPT = ROOT / "prompts" / "sentinel_core_system_prompt.md"


def _settings(**overrides) -> Settings:
    base = {"sentinel_ai_enabled": True, "sentinel_site_index_path": str(INDEX_PATH)}
    base.update(overrides)
    return Settings(**base)


class _Messages:
    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        # the SDK serializes at call time; the loop keeps appending to one list
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        if not self.script:
            raise AssertionError("the loop asked the model more times than the script allows")
        return self.script.pop(0)


class FakeClient:
    def __init__(self, script: list) -> None:
        self.beta = NS(messages=_Messages(script))


def tool_use(name: str, args: dict, block_id: str = "toolu_1"):
    return NS(stop_reason="tool_use", model="claude-opus-5",
              content=[NS(type="thinking", thinking=""), NS(type="tool_use", id=block_id, name=name, input=args)])


def final(text: str, model: str = "claude-opus-5"):
    return NS(stop_reason="end_turn", model=model, content=[NS(type="text", text=text)])


@pytest.fixture(autouse=True)
def _fresh_state():
    sentinel_ai.reset_index_cache()
    sentinel_ai.daily_cap.reset()
    yield
    sentinel_ai.reset_index_cache()
    sentinel_ai.daily_cap.reset()


# ── prompt and tools ─────────────────────────────────────────────────────────
def test_packaged_prompt_is_the_repository_prompt() -> None:
    """The image holds only control-plane/, so the prompt ships twice. They must agree."""
    if not REPO_PROMPT.is_file():
        pytest.skip("not a repository checkout")
    assert sentinel_ai.PROMPT_PATH.read_bytes() == REPO_PROMPT.read_bytes(), (
        "control-plane/app/data/sentinel_system_prompt.md differs from prompts/sentinel_core_system_prompt.md; "
        "copy the prompts/ file over it"
    )


def test_only_the_prompt_is_sent_not_its_documentation() -> None:
    prompt = sentinel_ai.system_prompt()
    assert prompt.startswith("You are Sentinel Core")
    assert "What this file is" not in prompt
    for rule in ("Open with the answer", "Never take an action", "Untrusted input", "Writing modes"):
        assert rule in prompt, rule


def test_the_tools_only_read_and_are_strict() -> None:
    assert {t["name"] for t in sentinel_ai.TOOLS} == {"search_site", "get_page", "list_clusters", "get_cluster"}
    for tool in sentinel_ai.TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True, tool["name"]
        assert schema["additionalProperties"] is False, tool["name"]
        assert sorted(schema["required"]) == sorted(schema["properties"]), tool["name"]


def test_sentinel_answers_are_low_risk_and_auto_execute() -> None:
    assessment = score_action("sentinel_answer")
    assert assessment.tier.value == "low" and not assessment.requires_approval


def test_the_index_ranks_the_obvious_page() -> None:
    index = sentinel_ai.SiteIndex(json.loads(INDEX_PATH.read_text(encoding="utf-8")))
    assert index.search("pricing", 3)[0]["path"] == "pricing.html"
    assert index.search("osint workflow", 3)[0]["path"] == "blog/osint-workflow-that-survives-contact-with-reality.html"
    page = index.page("pricing.html")
    assert page and page["related"] and page["cluster"] == "Services & Engagements"
    result, paths, is_error = sentinel_ai.run_tool(index, "get_page", {"path": "../../etc/passwd"})
    assert is_error and not paths and "error" in result
    _, _, unknown = sentinel_ai.run_tool(index, "delete_page", {})
    assert unknown


def test_an_index_row_with_an_off_site_path_is_dropped() -> None:
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    data["pages"].append({"path": "javascript:alert(1)", "title": "x", "role": "page"})
    data["pages"].append({"path": "https://evil.example/x.html", "title": "x", "role": "page"})
    index = sentinel_ai.SiteIndex(data)
    assert all(sentinel_ai.PAGE_PATH.match(p) and "//" not in p for p in index.pages)


# ── the loop ─────────────────────────────────────────────────────────────────
def test_the_loop_reads_the_site_then_answers() -> None:
    pytest.importorskip("anthropic")
    client = FakeClient([
        tool_use("search_site", {"query": "pricing", "limit": 3}, "toolu_1"),
        tool_use("get_page", {"path": "pricing.html"}, "toolu_2"),
        final("**Pricing & Engagements** lists the plans. Start there, then book a scoped estimate."),
    ])
    answer = sentinel_ai.ask("Where is the pricing page?", settings=_settings(), mode="executive",
                             page="index.html", client=client)
    assert answer.rounds == 3 and answer.lookups == ["search_site", "get_page"]
    assert answer.sources == [{"path": "pricing.html", "title": "Pricing & Engagements"}]
    assert not answer.refused and answer.text.startswith("**Pricing & Engagements**")

    calls = client.beta.messages.calls
    first = calls[0]
    assert first["model"] == "claude-opus-5"
    assert first["fallbacks"] == "default" and sentinel_ai.FALLBACK_BETA in first["betas"]
    assert first["thinking"] == {"type": "adaptive"}
    assert first["output_config"] == {"effort": "medium"}
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert first["tool_choice"] == {"type": "auto"}
    # the page context and the question travel as separate blocks
    user = first["messages"][0]["content"]
    assert user[0]["text"].startswith("Writing mode: executive.") and user[1]["text"] == "Where is the pricing page?"
    # tool results answer the tool_use ids, as JSON the model can read
    results = calls[1]["messages"][-1]["content"]
    assert results[0]["tool_use_id"] == "toolu_1"
    assert json.loads(results[0]["content"])["results"][0]["path"] == "pricing.html"


def test_the_last_round_withdraws_the_tools() -> None:
    pytest.importorskip("anthropic")
    client = FakeClient([
        tool_use("search_site", {"query": "cyber", "limit": 5}),
        final("Cyber Defense Console is the hub."),
    ])
    answer = sentinel_ai.ask("cyber?", settings=_settings(sentinel_max_tool_rounds=1), client=client)
    assert answer.rounds == 2
    assert client.beta.messages.calls[-1]["tool_choice"] == {"type": "none"}


def test_a_refusal_is_reported_not_rendered_as_an_answer() -> None:
    pytest.importorskip("anthropic")
    client = FakeClient([NS(stop_reason="refusal", model="claude-opus-5", content=[])])
    answer = sentinel_ai.ask("something declined", settings=_settings(), client=client)
    assert answer.refused and answer.stop_reason == "refusal" and not answer.sources


def test_history_starts_with_the_visitor_and_is_bounded() -> None:
    turns = [{"role": "assistant", "content": "hi"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * 5000} for i in range(10)
    ]
    history = sentinel_ai._history(turns)
    assert history[0]["role"] == "user"
    assert len(history) <= sentinel_ai.MAX_HISTORY_TURNS
    assert all(len(t["content"]) <= sentinel_ai.MAX_HISTORY_CHARS for t in history)


def test_the_ledger_fingerprint_is_keyed_and_hides_the_words() -> None:
    a = sentinel_ai.question_fingerprint("Where is the pricing page?", _settings(sentinel_audit_hash_key="k1"))
    b = sentinel_ai.question_fingerprint("Where is the pricing page?", _settings(sentinel_audit_hash_key="k2"))
    assert a != b and len(a) == 64 and "pricing" not in a


def test_status_claims_the_model_only_when_it_can_answer(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert sentinel_ai.status(_settings())["enabled"] is False
    assert sentinel_ai.status(_settings(sentinel_ai_enabled=False))["engine"] == "rule-guided"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    live = sentinel_ai.status(_settings())
    assert live["enabled"] is True and live["engine"] == "claude" and live["model"] == "claude-opus-5"


# ── the route ────────────────────────────────────────────────────────────────
try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import config as config_module
    from app import db as db_module
    from app.main import create_app
    from app.models import Base, Event

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs the pure tests only
    _HAS_WEB_STACK = False


@pytest.fixture()
def api(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    pytest.importorskip("anthropic")
    monkeypatch.setenv("SENTINEL_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("SENTINEL_SITE_INDEX_PATH", str(INDEX_PATH))
    config_module.get_settings.cache_clear()
    engine = create_engine("sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[db_module.get_session] = override_session
    state = NS(client=None, fake=None, Session=Session, monkeypatch=monkeypatch)

    def script(*responses):
        state.fake = FakeClient(list(responses))
        monkeypatch.setattr(sentinel_ai, "make_client", lambda: state.fake)

    state.script = script
    state.client = TestClient(app, raise_server_exceptions=False)
    try:
        yield state
    finally:
        config_module.get_settings.cache_clear()


def _events(state) -> list:
    with state.Session() as session:
        return session.query(Event).filter(Event.action == "sentinel_answer").all()


def test_the_route_answers_and_the_ledger_keeps_no_words(api) -> None:
    api.script(tool_use("search_site", {"query": "pricing", "limit": 3}),
               final("**Pricing & Engagements** has the published plans."))
    res = api.client.post("/sentinel/ask", json={"question": "Where is the pricing page?", "page": "index.html"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["engine"] == "claude" and body["mode"] == "executive" and not body["refused"]
    assert body["sources"] == [{"path": "pricing.html", "title": "Pricing & Engagements"}]
    assert body["reference"].startswith("SNT-")
    (event,) = _events(api)
    assert event.result == "answered" and event.risk_tier == "low"
    assert event.payload["reference"] == body["reference"]
    assert len(event.payload["question_hmac"]) == 64
    assert "pricing page" not in json.dumps(event.payload).lower()


def test_a_question_carrying_a_credential_is_never_sent(api) -> None:
    api.script()  # any model call fails the test
    res = api.client.post("/sentinel/ask", json={"question": "my password is hunter2, is that ok?"})
    assert res.status_code == 200 and res.json()["engine"] == "guard" and res.json()["refused"]
    assert api.fake.beta.messages.calls == []
    assert _events(api)[0].result == "declined_sensitive"


def test_off_site_pages_and_spent_budgets_are_refused_before_any_call(api) -> None:
    api.script()
    assert api.client.post("/sentinel/ask", json={"question": "hi", "page": "https://evil.example/"}).status_code == 422
    api.monkeypatch.setenv("SENTINEL_DAILY_REQUEST_CAP", "0")
    config_module.get_settings.cache_clear()
    res = api.client.post("/sentinel/ask", json={"question": "What is ClearGlass?"})
    assert res.status_code == 503 and "budget" in res.json()["detail"]
    assert api.fake.beta.messages.calls == []


def test_the_route_is_off_until_configured(api) -> None:
    api.monkeypatch.setenv("SENTINEL_AI_ENABLED", "false")
    config_module.get_settings.cache_clear()
    assert api.client.get("/sentinel/status").json()["enabled"] is False
    assert api.client.post("/sentinel/ask", json={"question": "hello"}).status_code == 503


def test_the_mode_follows_the_question_on_auto(api) -> None:
    api.script(final("It is a static site with a FastAPI control plane."))
    res = api.client.post("/sentinel/ask", json={"question": "How does the architecture work?", "mode": "auto"})
    assert res.json()["mode"] == "technical"
    assert api.fake.beta.messages.calls[0]["messages"][-1]["content"][0]["text"].startswith("Writing mode: technical.")
