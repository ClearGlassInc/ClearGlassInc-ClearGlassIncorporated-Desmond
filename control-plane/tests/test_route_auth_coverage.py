"""Every mutating route must reject an unauthenticated caller, or be exempt.

This is the gate ``CLAUDE.md`` describes as "enforced by test rather than
convention, because convention is what fails silently". Adding a router to
``create_app`` without ``dependencies=admin``, or a ``@router.post`` inside an
otherwise-gated router that quietly bypasses the check, produces no error, no
warning and no failing test — the endpoint simply ships open.

The check is **behavioural, not structural**: it sets ``ADMIN_API_KEY``, then
calls each mutating endpoint with no credential and requires a 401 or 403.
Introspecting the dependency graph would be easier and weaker — a route can
carry ``require_admin`` in its signature and still be reachable, and the shape
of ``app.routes`` is a FastAPI implementation detail that changes between
versions (included routers are nested rather than flattened in the version
pinned here, which silently empties any test that walks it looking for
``APIRoute``). Sending a real request cannot be fooled by either.

The exemption list is deliberately explicit and small. Adding to it is a
security decision that shows up in a diff and needs a reason written down; that
is the point of enumerating them rather than pattern-matching a path prefix.
"""

from __future__ import annotations

import pytest

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app
    from app.models import Base

    from app import config as config_module
    from app import db as db_module

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False

ADMIN_KEY = "test-admin-key-not-a-real-credential"

MUTATING_METHODS = ("post", "put", "patch", "delete")

# Mutating routes deliberately NOT behind require_admin. path -> why that is safe.
EXEMPT: dict[str, str] = {
    "/checkout/session": (
        "Customer checkout. Takes SKUs and quantities only; every amount is resolved "
        "server-side from the price book, so an open endpoint cannot choose what to "
        "pay. Rate limited per IP."
    ),
    "/webhooks/stripe": (
        "Stripe webhook. Authenticated by Stripe's signature, which an operator "
        "credential cannot substitute for. Idempotent on redelivery via "
        "orders.external_ref. Rate limited per IP."
    ),
    "/sidestore/quote": (
        "Side Store cart quote. Read-only pricing of a proposed cart; server-priced "
        "from the catalog and persists nothing."
    ),
    "/sidestore/checkout/session": (
        "Side Store checkout. Same server-priced contract as /checkout/session: the "
        "request names SKUs and quantities, never amounts. Rate limited per IP."
    ),
    "/billing/portal": (
        "Customer billing portal. Deliberately refuses a caller-supplied Stripe "
        "customer id and derives the customer from the checkout session id instead, "
        "so the caller cannot name whose portal to open. Rate limited per IP."
    ),
    "/fulfillment/webhooks/printful/{secret}": (
        "Supplier shipment webhook, authenticated by the secret in its own URL — "
        "Printful cannot present an operator credential. A wrong secret is refused "
        "with 404 rather than 401, which is asserted separately below so the "
        "exemption cannot hide an endpoint that accepts anything."
    ),
}

# Stand-ins for path parameters. The value is irrelevant — an unauthenticated
# request must be refused before anything looks the identifier up.
PATH_PARAM_STUB = "1"


def _fill(path: str) -> str:
    """Replace {placeholders} so the request reaches the auth dependency."""
    out, depth, buf = [], 0, []
    for char in path:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                buf.clear()
                out.append(PATH_PARAM_STUB)
        elif depth == 0:
            out.append(char)
    return "".join(out)


@pytest.fixture()
def admin_client(monkeypatch):
    """A client for an app booted WITH admin auth enabled."""
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")

    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
    # Settings are cached; without clearing, the app boots in open dev mode and
    # every assertion below would pass for the wrong reason.
    config_module.get_settings.cache_clear()

    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = TestingSession()
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
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        config_module.get_settings.cache_clear()


def _mutating_operations(client) -> list[tuple[str, str]]:
    """(method, path) for every mutating operation in the served OpenAPI schema."""
    schema = client.app.openapi()
    return [
        (method, path)
        for path, operations in schema.get("paths", {}).items()
        for method in operations
        if method.lower() in MUTATING_METHODS
    ]


def test_auth_is_actually_enabled_for_this_fixture(admin_client) -> None:
    """Guard the guard.

    If ADMIN_API_KEY did not take effect, the app runs in open dev mode and
    every gating assertion below passes vacuously.
    """
    from app.security import auth_enabled

    assert auth_enabled(config_module.get_settings()), (
        "ADMIN_API_KEY did not reach the app; the gating assertions would be vacuous"
    )


def test_the_app_exposes_a_real_mutating_surface(admin_client) -> None:
    """Guard against passing because the walk found nothing to check.

    An earlier version of this file inspected ``app.routes`` for ``APIRoute``
    instances. In the FastAPI version pinned here, ``include_router`` leaves a
    nested ``_IncludedRouter`` instead, so that walk saw 3 routes out of 30 and
    would have reported a fully open surface as fully gated.
    """
    operations = _mutating_operations(admin_client)
    assert len(operations) >= 10, (
        f"expected the full commerce surface, found {len(operations)} mutating "
        f"operations: {operations}"
    )


def test_every_mutating_route_rejects_an_unauthenticated_caller(admin_client) -> None:
    open_routes = []
    for method, path in _mutating_operations(admin_client):
        if path in EXEMPT:
            continue
        response = getattr(admin_client, method.lower())(_fill(path))
        if response.status_code not in (401, 403):
            open_routes.append(f"{method.upper()} {path} -> {response.status_code}")

    assert not open_routes, (
        "These mutating routes answered an unauthenticated caller with something "
        "other than 401/403. Gate them behind require_admin, or add an entry to "
        f"EXEMPT in this file saying why they are safe open: {open_routes}"
    )


def test_exemptions_all_correspond_to_a_real_route(admin_client) -> None:
    """A stale exemption is a hole waiting for its path to be reused."""
    live = {path for _method, path in _mutating_operations(admin_client)}
    stale = sorted(set(EXEMPT) - live)
    assert not stale, f"exemptions for routes that no longer exist: {stale}"


@pytest.mark.parametrize("path", sorted(EXEMPT))
def test_every_exemption_carries_a_written_reason(path: str) -> None:
    assert len(EXEMPT[path]) > 40, (
        f"{path}: exemption needs a real justification, not a placeholder"
    )


def test_the_approval_gate_itself_is_closed(admin_client) -> None:
    """The approvals surface is what every high/critical action waits on.

    If deciding an approval were open, the governance model would be
    decorative: anyone could approve the action they had just proposed.
    """
    approvals = [
        (method, path)
        for method, path in _mutating_operations(admin_client)
        if path.startswith("/approvals")
    ]
    assert approvals, "no mutating /approvals routes found"
    for method, path in approvals:
        response = getattr(admin_client, method.lower())(_fill(path))
        assert response.status_code in (401, 403), (
            f"{method.upper()} {path} decides approvals and answered "
            f"{response.status_code} without a credential"
        )


def test_the_refund_path_is_closed(admin_client) -> None:
    """Refunds move money out.

    The payments router is included without blanket admin dependencies so the
    Stripe webhook and checkout stay reachable, which makes the refund's
    per-endpoint gate exactly the kind that is easy to drop by accident.
    """
    refunds = [
        (method, path)
        for method, path in _mutating_operations(admin_client)
        if "refund" in path
    ]
    assert refunds, "no refund route found"
    for method, path in refunds:
        response = getattr(admin_client, method.lower())(_fill(path))
        assert response.status_code in (401, 403), (
            f"{method.upper()} {path} moves money and answered "
            f"{response.status_code} without a credential"
        )


def test_a_valid_credential_is_not_rejected(admin_client) -> None:
    """The gate must refuse the anonymous caller without refusing everyone.

    A dependency that always raises would pass every assertion above while
    taking the whole admin surface offline.
    """
    response = admin_client.post(
        "/store/generate-copy",
        headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        json={},
    )
    assert response.status_code not in (401, 403), (
        f"a valid admin credential was rejected with {response.status_code}"
    )


def test_the_supplier_webhook_refuses_a_wrong_url_secret(admin_client) -> None:
    """The one exempt route whose credential is in its path.

    It is excluded from the 401/403 sweep because a bad secret is refused with
    404 (which does not confirm the endpoint exists). That exemption would hide
    an endpoint that accepted any secret at all, so assert the refusal directly.
    """
    response = admin_client.post(
        "/fulfillment/webhooks/printful/definitely-not-the-configured-secret",
        json={"type": "package_shipped"},
    )
    assert response.status_code in (401, 403, 404), (
        f"the supplier webhook accepted a wrong URL secret with {response.status_code}"
    )
