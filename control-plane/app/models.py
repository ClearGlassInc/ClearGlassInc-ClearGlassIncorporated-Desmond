"""ORM models — mirrors migrations/001_init.sql.

The append-only ``events`` table is the audit ledger; ``approvals`` is the human gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB in Postgres, plain JSON elsewhere (SQLite for local/dev/demo runs).
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
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
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


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
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
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
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    orders: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    aov: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    refund_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
