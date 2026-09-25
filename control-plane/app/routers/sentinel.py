"""Sentinel Core answered by Claude: the public console's model endpoint.

``GET /sentinel/status`` says which engine is live; the console reads it before
it claims anything. ``POST /sentinel/ask`` answers one question through
``app.sentinel_ai``. It is public on purpose, like checkout: the console runs on
a static site and cannot hold a credential. What keeps it safe to leave open:

* read-only: Claude's only tools read the public site index; nothing is
  written, sent, booked or spent beyond the operator's daily request cap;
* a per-IP throttle and a hard daily cap before any model call;
* a sensitive-data guard that declines, without sending, any question carrying
  a password, key or card number;
* one append-only audit row per answer with a keyed hash of the question,
  never its words, and no ledger id in the response.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import sentinel_ai
from ..audit import log_event
from ..config import Settings, get_settings
from ..db import get_session
from ..governance import score_action
from ..schemas import SentinelAnswerOut, SentinelAskIn
from ..security import rate_limit

router = APIRouter(prefix="/sentinel", tags=["sentinel"])

_throttle = rate_limit("sentinel_ask", "rate_limit_sentinel_per_minute")

SENSITIVE_REPLY = (
    "Please don't share passwords, keys, card numbers or other credentials here. "
    "Sentinel did not send your message anywhere. Ask again without them."
)


def mode_for(question: str) -> str:
    """The writing mode a question implies; mirrors station-chat.js's modeFor()."""
    import re

    q = question.lower()
    if re.search(r"\b(architecture|architect|spec|specification|technical|implement|implementation|integration|api|"
                 r"stack|engineer|engineering|schema|runbook|how (?:does|do|is))\b", q):
        return "technical"
    if re.search(r"\b(compare|comparison|versus|vs|trade ?-?offs?|analy[sz]e|analysis|gaps?|coverage|evaluate|assess)\b", q):
        return "analytical"
    if re.search(r"\b(why (?:choose|clearglass|should|use)|pitch|sell|value|benefits?|convince|worth|roi)\b", q):
        return "pitch"
    return "executive"


@router.get("/status")
def sentinel_status(settings: Settings = Depends(get_settings)) -> dict:
    """Which engine answers, and what is kept. Makes no model call."""
    return sentinel_ai.status(settings)


@router.post("/ask", response_model=SentinelAnswerOut, dependencies=[Depends(_throttle)])
def ask(
    req: SentinelAskIn,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SentinelAnswerOut:
    if not sentinel_ai.enabled(settings):
        raise HTTPException(status_code=503, detail="Sentinel's model is not enabled; the console answers from its rules")
    page = req.page or None
    if page and (not sentinel_ai.PAGE_PATH.match(page) or ".." in page or "//" in page):
        raise HTTPException(status_code=422, detail="page must be a same-site path")
    mode = req.mode if req.mode != "auto" else mode_for(req.question)
    assessment = score_action("sentinel_answer", {}, require_approval_for_high_risk=settings.require_approval_for_high_risk)
    if assessment.requires_approval:  # defensive: the table scores it low; never answer ungoverned
        raise HTTPException(status_code=403, detail="sentinel_answer is gated by governance")
    reference = "SNT-" + secrets.token_hex(5).upper()
    fingerprint = sentinel_ai.question_fingerprint(req.question, settings)
    payload = {"reference": reference, "question_hmac": fingerprint, "mode": mode, "page": page}

    texts = [req.question] + [t.content for t in req.history if t.role == "user"]
    if any(sentinel_ai.SENSITIVE.search(t) for t in texts):
        log_event(session, actor="sentinel_core", action="sentinel_answer", target=page,
                  payload=payload, result="declined_sensitive", assessment=assessment)
        return SentinelAnswerOut(answer=SENSITIVE_REPLY, mode=mode, engine="guard", model="", served_by="",
                                 sources=[], lookups=0, rounds=0, refused=True, latency_ms=0, reference=reference)

    if not sentinel_ai.daily_cap.take(settings.sentinel_daily_request_cap):
        log_event(session, actor="sentinel_core", action="sentinel_answer", target=page,
                  payload=payload, result="daily_cap_reached", assessment=assessment)
        raise HTTPException(status_code=503, detail="Sentinel's daily model budget is spent; the console answers from its rules")

    try:
        answer = sentinel_ai.ask(
            req.question, settings=settings, mode=mode, page=page,
            history=[t.model_dump() for t in req.history],
        )
    except sentinel_ai.SentinelUnavailable as exc:
        log_event(session, actor="sentinel_core", action="sentinel_answer", target=page,
                  payload={**payload, "reason": str(exc)}, result="unavailable", assessment=assessment)
        raise HTTPException(status_code=503, detail="Sentinel's model is unavailable; the console answers from its rules")

    log_event(
        session, actor="sentinel_core", action="sentinel_answer", target=page,
        payload={**payload, "model": answer.served_by, "rounds": answer.rounds, "lookups": answer.lookups,
                 "sources": [s["path"] for s in answer.sources], "latency_ms": answer.latency_ms,
                 "stop_reason": answer.stop_reason},
        result="refused" if answer.refused else "answered", assessment=assessment,
    )
    return SentinelAnswerOut(
        answer=answer.text, mode=answer.mode, engine="claude", model=answer.model, served_by=answer.served_by,
        sources=answer.sources, lookups=len(answer.lookups), rounds=answer.rounds, refused=answer.refused,
        latency_ms=answer.latency_ms, reference=reference,
    )
