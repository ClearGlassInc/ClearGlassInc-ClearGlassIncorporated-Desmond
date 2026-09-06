"""FastAPI application factory for the commerce control plane."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .routers import (
    approvals,
    etsy,
    events,
    fulfillment,
    inventory,
    metrics,
    orders,
    payments,
    sidestore,
    store,
)
from .security import (
    auth_enabled,
    peer_is_trusted_proxy,
    require_admin,
    verify_startup_posture,
)


def create_app() -> FastAPI:
    settings = get_settings()
    # Refuse to boot a production control plane with an unauthenticated admin surface.
    verify_startup_posture(settings)
    if settings.auto_create_tables:
        from .db import engine
        from .models import Base

        Base.metadata.create_all(engine)
    app = FastAPI(
        title="ClearGlass Autonomous E-Commerce Operator",
        version=__version__,
        description=(
            "Governed commerce control plane. Read-only analysis -> draft -> approval -> "
            "execution. Every material change is risk-scored and written to an append-only ledger."
        ),
    )

    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.app_env.lower() in {"production", "prod"}:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    @app.get("/health", tags=["meta"])
    def health(request: Request) -> dict:
        """Liveness: the process is up. Makes no external calls.

        Also reports the address this request arrived from and whether its
        ``X-Forwarded-For`` is currently trusted. Behind a reverse proxy the per-IP
        throttles can only key on the real caller once ``TRUSTED_PROXY_IPS`` names the
        router, and that address is otherwise hard to discover — this turns it into one
        curl against the deployed service. It echoes the caller its own address; no
        other party's data is exposed.
        """
        peer = request.client.host if request.client else "unknown"
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": __version__,
            "admin_auth": "enabled" if auth_enabled(settings) else "disabled",
            "client_peer": peer,
            "forwarded_for": (
                "trusted"
                if settings.trusted_proxy_hops > 0
                and peer_is_trusted_proxy(peer, settings.trusted_proxy_ips)
                else "ignored"
            ),
        }

    @app.get("/ready", tags=["meta"])
    def ready() -> dict:
        """Readiness: the service can reach its database. Use for orchestrator checks."""
        from sqlalchemy import text

        from .db import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - exercised via fault injection
            raise HTTPException(status_code=503, detail=f"database unavailable: {type(exc).__name__}")
        return {"status": "ready", "database": "ok", "version": __version__}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "governance": "high/critical actions require human approval",
        }

    # Administrative surfaces (governed actions + the approval gate itself) require an
    # admin credential. Customer flows (checkout), the Stripe webhook (signature-verified),
    # and read-only telemetry (metrics/events) stay open by design.
    admin = [Depends(require_admin)]
    app.include_router(store.router, dependencies=admin)
    app.include_router(payments.router)  # per-endpoint: only the refund is gated (see router)
    app.include_router(sidestore.router)  # customer cart: public, rate limited, server-priced
    app.include_router(orders.router, dependencies=admin)
    app.include_router(inventory.router, dependencies=admin)
    app.include_router(metrics.router)
    app.include_router(events.router)
    app.include_router(approvals.router, dependencies=admin)
    # Etsy is an operator surface end to end: connection state and verification read
    # credential-backed shop identity, and the write endpoints propose live-shop changes.
    app.include_router(etsy.router, dependencies=admin)
    # Fulfillment mixes surfaces, so it is gated per endpoint rather than wholesale:
    # the supplier catalogue and an order's tracking are read-only, confirming a
    # supplier order is admin-gated, and the shipment webhook cannot carry an
    # operator credential (it is authenticated by its URL secret instead).
    app.include_router(fulfillment.router)
    return app


app = create_app()


def main() -> None:
    """Console entry point: ``python -m app.main`` (dev convenience)."""
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
