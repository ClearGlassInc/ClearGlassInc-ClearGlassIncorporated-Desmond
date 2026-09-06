from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .agent import build_report, root_policy
from .schemas import AgentReport, HealthResponse, SignalPacket
from .security import verify_clear_glass_request

VERSION = os.getenv("CLEARGLASS_AGENT_VERSION", "0.1.0")

app = FastAPI(
    title="ClearGlass Agent Service",
    version=VERSION,
    description="ClearGlassInc-only lawful public-source and defensive risk-intelligence agent service.",
)

allowed_origins = [origin.strip() for origin in os.getenv("CLEARGLASS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["X-ClearGlass-Org", "X-ClearGlass-API-Key", "Content-Type"],
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=VERSION)


@app.get("/policy")
def policy(_: dict[str, str] = Depends(verify_clear_glass_request)) -> dict[str, object]:
    return root_policy()


@app.post("/v1/signal", response_model=AgentReport)
def signal_report(
    packet: SignalPacket,
    request: Request,
    principal: dict[str, str] = Depends(verify_clear_glass_request),
) -> AgentReport:
    del request
    return build_report(packet, principal)
