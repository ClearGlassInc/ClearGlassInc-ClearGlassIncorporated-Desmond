"""Authenticated, rate-limited APEX plan endpoint.

This endpoint prepares and audits a plan. It never executes a plan or contacts an
LLM, source URL, quantum service, deployment, messaging or payment system.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .. import apex_core
from ..audit import log_event
from ..config import Settings, get_settings
from ..db import get_session
from ..governance import score_action
from ..security import rate_limit, require_admin

router = APIRouter(prefix="/apex", tags=["apex"])
_throttle = rate_limit("apex_plan", "rate_limit_decisions_per_minute")

_SENSITIVE_INPUT = re.compile(
    r"password|passcode|api[ -]?key|secret key|private key|credit card|card number|\bcvv\b|"
    r"credential|social insurance|health card|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"sk-[A-Za-z0-9_-]{16,}|bearer\s+[A-Za-z0-9._~-]{16,}",
    re.IGNORECASE,
)


class APEXSourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    uri: str = Field(min_length=1, max_length=1024)
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class APEXPlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_id: str = Field(
        default_factory=lambda: "APEX-" + secrets.token_hex(6).upper(),
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )
    objective: str = Field(min_length=8, max_length=2000)
    requested_action: str = Field(
        default="apex_plan_mission",
        pattern=r"^[a-z][a-z0-9_]{0,79}$",
    )
    sources: list[APEXSourceIn] = Field(default_factory=list, max_length=20)


@router.post("/plan", dependencies=[Depends(_throttle)])
def plan_mission(
    req: APEXPlanIn,
    actor: str = Depends(require_admin),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Plan a mission using current policy; emit metadata-only audit evidence."""
    supplied_text = " ".join([req.objective, *(source.uri for source in req.sources)])
    if _SENSITIVE_INPUT.search(supplied_text):
        raise HTTPException(
            status_code=422,
            detail=(
                "Sensitive credentials or personal identifiers are not accepted; "
                "no plan was created."
            ),
        )

    try:
        sources = tuple(
            apex_core.EvidenceRef(source_id=item.source_id, uri=item.uri, sha256=item.sha256)
            for item in req.sources
        )
        plan = apex_core.create_plan(
            mission_id=req.mission_id,
            objective=req.objective,
            requested_action=req.requested_action,
            sources=sources,
            fingerprint_key=(
                settings.crcs_audit_hash_key or "local-development-key-change-in-production"
            ),
        )
    except apex_core.APEXInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    objective_fingerprint = hmac.new(
        (
            settings.crcs_audit_hash_key or "local-development-key-change-in-production"
        ).encode("utf-8"),
        req.objective.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    plan_assessment = score_action("apex_plan_mission", {})
    log_event(
        session,
        actor="apex:" + actor,
        action="apex_plan_mission",
        target=req.mission_id,
        payload={
            "plan_id": plan.plan_id,
            "plan_fingerprint": plan.plan_fingerprint,
            "objective_hmac": objective_fingerprint,
            "requested_action": req.requested_action,
            "source_count": len(req.sources),
            "source_ids": [source.source_id for source in req.sources],
            "source_digests_declared": sum(bool(source.sha256) for source in req.sources),
            "execution_status": "not_executed",
        },
        result="planned_only",
        assessment=plan_assessment,
    )
    return plan.to_dict()
