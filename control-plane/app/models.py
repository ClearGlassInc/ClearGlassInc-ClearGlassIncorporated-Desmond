"""ORM models — mirrors migrations/001_init.sql.

The append-only ``events`` table is the audit ledger; ``approvals`` is the human gate.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB in Postgres, plain JSON elsewhere (SQLite for local/dev/demo runs).
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all commerce tables."""


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(120), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    consent_marketing: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # live | test | unknown; dashboard counts only live for confirmed revenue.
    environment: Mapped[str] = mapped_column(String(16), default="unknown")
        # Upstream payment reference (Stripe checkout-session id) — dedupe key so
    # webhook redelivery can never book the same order twice.
    external_ref: Mapped[str | None] = mapped_column(
        String(160), nullable=True, unique=True, index=True
    )
    # Where the parcel goes. Held on the order rather than the customer because a
    # customer can ship to a different address each time, and a dropship supplier
    # is handed the address that was given at *this* checkout — reusing a stale
    # one sends someone else's parcel to a previous address.
    ship_to_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ship_to_address1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ship_to_address2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ship_to_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ship_to_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ship_to_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    ship_to_zip: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ship_to_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # pending → drafted → confirmed → shipped, or unfulfillable (see fulfillment.py)
    fulfillment_status: Mapped[str] = mapped_column(String(32), default="pending")
    # Migration 009. Refunds and disputes name a PaymentIntent, not a Checkout
    # Session, so this is how a charge.refunded event finds the order it reverses.
    payment_intent: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    # Cumulative (Stripe's charge.amount_refunded), so redelivery cannot subtract twice.
    amount_refunded: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    dispute_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    # Migration 010. The ClearGlass order this payment settles, when checkout
    # started from one. Deliberately not unique: two payments naming one order
    # is the double-payment case reconciliation must see, not a row to refuse.
    order_ref: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CommercialOrder(Base):
    """A ClearGlass order: one offer, one server-set price, either processor.

    Created before the buyer chooses Stripe or PayPal, so the reference, the
    price and the campaign exist independently of any processor. Payments
    settle into ``orders`` (one row per processor settlement) and point back
    here through ``orders.order_ref``. ``payment_state`` moves only through
    :mod:`app.order_states`; fulfillment is derived, never stored.
    """

    __tablename__ = "commercial_orders"
    # Mirrors migrations/010_commercial_orders.sql, so the SQLite schema the
    # tests run on refuses an unknown state exactly as Postgres does.
    __table_args__ = (
        CheckConstraint(
            "payment_state IN ('CREATED', 'CHECKOUT_STARTED', 'PAYMENT_PENDING', "
            "'PAYMENT_PROCESSING', 'PAID', 'PAYMENT_FAILED', 'CANCELED', 'REFUNDED', "
            "'PARTIALLY_REFUNDED', 'DISPUTED', 'CHARGEBACK')",
            name="commercial_orders_state_check",
        ),
        CheckConstraint(
            "provider IS NULL OR provider IN ('stripe', 'paypal')",
            name="commercial_orders_provider_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(120))
    offer_name: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    # Server-priced from the price book, in major units like Order.total.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    checkout_mode: Mapped[str] = mapped_column(String(16), default="payment")
    payment_state: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    # stripe | paypal, once the buyer chooses; the latest choice wins.
    provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Stripe Checkout Session id or PayPal order id of the latest checkout.
    provider_checkout_ref: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    # The ledger row whose verified settlement made this order PAID.
    payment_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    # live | test | unknown, from the verifying processor event.
    environment: Mapped[str] = mapped_column(String(16), default="unknown")
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    # Set when the ledger and this order disagree (a second payment, an amount
    # or currency mismatch, money after a cancel). Never cleared automatically.
    reconciliation_required: Mapped[bool] = mapped_column(default=False, index=True)
    reconciliation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Shipment(Base):
    """A supplier's fulfillment of an order, and the tracking it produced.

    Separate from ``Order`` because one order can ship in several parcels — a
    print-on-demand supplier routes items to whichever facility can make them, so
    a two-item order regularly arrives as two shipments with different carriers.
    Collapsing that into columns on ``Order`` would lose one of the tracking
    numbers, and the customer would be chasing a parcel we never told them about.
    """

    __tablename__ = "shipments"

    # Mirrors the partial unique index in migrations/005_fulfillment.sql. Without
    # it here, `Base.metadata.create_all` (SQLite dev, demo and the whole test
    # suite) would build a weaker schema than production, so the idempotency this
    # table claims would be untested exactly where it is cheapest to test.
    __table_args__ = (
        Index(
            "idx_shipments_supplier_shipment",
            "supplier",
            "supplier_shipment_id",
            unique=True,
            sqlite_where=text("supplier_shipment_id IS NOT NULL"),
            postgresql_where=text("supplier_shipment_id IS NOT NULL"),
        ),
        Index("idx_shipments_supplier_order", "supplier", "supplier_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    supplier: Mapped[str] = mapped_column(String(32), default="printful")
    # The supplier's own order id. Deliberately NOT unique: one supplier order
    # can produce several parcels, which is the entire reason this is a table.
    supplier_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # The supplier's id for *this parcel*. This is the idempotency key — unique
    # per supplier — so a redelivered `package_shipped` updates its own row while
    # a genuine second parcel still gets one of its own.
    supplier_shipment_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    tracking_number: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # What the supplier charged us, against Order.total the customer paid — the
    # two together are the margin, which is the whole economics of dropshipping.
    supplier_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Payout(Base):
    """A Stripe payout (settlement of platform balance to a connected bank account).

    Populated from ``payout.created`` / ``payout.updated`` / ``payout.paid`` webhooks.
    Deliberately stores no raw bank details: ``destination`` is Stripe's opaque external-account
    token (e.g. ``ba_…``), never an account or routing number. ``amount`` is in major units
    (dollars), matching :class:`Order.total`.
    """

    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stripe_payout_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    destination: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    arrival_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"))
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=10)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(48))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Event(Base):
    """Append-only audit ledger. Rows are never updated or deleted."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    result: Mapped[str] = mapped_column(String(32), default="ok")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")


class Approval(Base):
    """Human approval gate for high/critical actions."""

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="high")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    requested_by: Mapped[str] = mapped_column(String(120), default="operator")
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), unique=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    orders: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal(0))
    aov: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    refund_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal(0))


class Lead(Base):
    """Internal CRM lead record for the ClearGlass Revenue Command System."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # What the browser sees instead of the sequential id (migration 008).
    public_ref: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid.uuid4, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), index=True)
    company: Mapped[str | None] = mapped_column(String(240), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str | None] = mapped_column(String(160), nullable=True)
    service_interest: Mapped[str] = mapped_column(String(160))
    primary_goal: Mapped[str] = mapped_column(Text, default="")
    current_challenge: Mapped[str] = mapped_column(Text, default="")
    business_context: Mapped[str] = mapped_column(Text, default="")
    desired_timeline: Mapped[str | None] = mapped_column(String(80), nullable=True)
    investment_range: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(120), default="direct")
    landing_page: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    utm_first_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_first_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_first_campaign: Mapped[str | None] = mapped_column(String(160), nullable=True)
    utm_last_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_last_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_last_campaign: Mapped[str | None] = mapped_column(String(160), nullable=True)
    consent_marketing: Mapped[bool] = mapped_column(default=False)
    stage: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    owner: Mapped[str] = mapped_column(String(120), default="unassigned")
    next_action: Mapped[str] = mapped_column(Text, default="Review new lead")
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    score_explanation: Mapped[str] = mapped_column(Text, default="")
    expected_value_cad: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_recurring_value_cad: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LeadActivity(Base):
    """Immutable-ish activity timeline entries; correction means adding a new entry."""

    __tablename__ = "lead_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(120), default="system")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ServiceOrder(Base):
    """Paid-service fulfillment record linked one-to-one to a commerce order."""

    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    sku: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="INTAKE_REQUIRED", index=True)
    scope_status: Mapped[str] = mapped_column(String(40), default="AWAITING_SCOPE_CONFIRMATION")
    delivery_owner: Mapped[str] = mapped_column(String(120), default="unassigned")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_next_step: Mapped[str] = mapped_column(Text, default="Complete the secure intake.")
    internal_checklist: Mapped[list] = mapped_column(PortableJSON, default=list)
    file_links: Mapped[list] = mapped_column(PortableJSON, default=list)
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_cost_cad: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    testimonial_eligible: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class RevenueControlLog(Base):
    """Daily commercial action ledger; engineering activity is not a substitute for it."""

    __tablename__ = "revenue_control_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_date: Mapped[str] = mapped_column(String(10), index=True)
    action: Mapped[str] = mapped_column(Text)
    target: Mapped[str] = mapped_column(Text, default="")
    expected_outcome: Mapped[str] = mapped_column(Text, default="")
    action_taken: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    owner: Mapped[str] = mapped_column(String(120), default="unassigned")
    status: Mapped[str] = mapped_column(String(40), default="NOT_STARTED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class IntegrationHealth(Base):
    """Last known health evidence for revenue-system integrations."""

    __tablename__ = "integration_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    integration: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
