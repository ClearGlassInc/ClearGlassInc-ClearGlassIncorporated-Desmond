"""Request/response contracts (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateCopyRequest(BaseModel):
    product_slug: str
    kind: str = Field(default="description", description="description|faq|ad|email|sms")
    brand_voice: str = "clear, confident, no false claims"


class UpdatePricingRequest(BaseModel):
    sku: str
    old_price: float
    new_price: float
    reason: str = ""


class RefreshProductsRequest(BaseModel):
    source: str = "supplier_feed"
    dry_run: bool = True


class InventoryCheckRequest(BaseModel):
    reorder: bool = False


class CheckoutLineItem(BaseModel):
    """What the customer wants, not what it costs.

    Deliberately carries no price: amounts are resolved server-side from
    :mod:`app.pricebook`. A line item that could name its own ``amount`` would let
    the browser choose what to pay.
    """

    sku: str = Field(description="Price-book SKU being purchased")
    quantity: int = Field(default=1, ge=1)


class CheckoutAttribution(BaseModel):
    """Campaign tags carried to Stripe metadata and onto the paid order.

    Invalid values are dropped by ``app.attribution``, never rejected: marketing
    context must not block a purchase.
    """

    utm_source: str | None = Field(default=None, max_length=200)
    utm_medium: str | None = Field(default=None, max_length=200)
    utm_campaign: str | None = Field(default=None, max_length=200)


class CheckoutRequest(BaseModel):
    """A cart, and who to email. Deliberately not where to return to.

    `success_url` and `cancel_url` used to be accepted here and passed straight to
    Stripe. On a public, unauthenticated endpoint that is a brand-abuse vector: an
    anonymous caller could mint a genuine `checkout.stripe.com` session under the
    ClearGlass account that redirects the buyer to any domain once they have paid.
    The return URLs now come only from CHECKOUT_SUCCESS_URL / CHECKOUT_CANCEL_URL.
    """

    items: list[CheckoutLineItem] = Field(min_length=1, max_length=20)
    customer_email: str | None = None
    # Client-generated attempt id. Passed to Stripe as the idempotency key so a
    # double-click or a retried request reuses the first session instead of opening
    # a second one for the same cart.
    client_reference_id: str | None = Field(default=None, max_length=200)
    attribution: CheckoutAttribution | None = None


class CheckoutSessionOut(BaseModel):
    id: str
    url: str
    mode: str               # live | mock
    checkout_mode: str      # payment | subscription
    amount_total: int
    currency: str


class BillingPortalRequest(BaseModel):
    checkout_session_id: str = Field(min_length=8, max_length=255, pattern=r"^cs_[A-Za-z0-9_]+$")


class BillingPortalOut(BaseModel):
    url: str
    mode: str


class OfferOut(BaseModel):
    """A purchasable offer as advertised to the storefront."""

    sku: str
    name: str
    description: str
    amount: int
    currency: str
    kind: str               # one_time | deposit | recurring
    interval: str | None
    max_quantity: int


class PayoutBankInfoOut(BaseModel):
    configured: bool
    processor: str
    settlement_mode: str
    external_account_id: str | None
    bank_name: str | None
    account_last4: str | None
    routing_hint: str | None
    country: str
    currencies: list[str]
    warnings: list[str] = Field(default_factory=list)


class PayoutOut(BaseModel):
    id: int
    stripe_payout_id: str
    amount: float
    currency: str
    status: str
    destination: str | None
    tenant_id: str | None
    arrival_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RefundRequest(BaseModel):
    order_id: int
    amount: int | None = Field(default=None, description="Cents to refund; None = full refund")
    reason: str = ""


class PayPalOrderOut(BaseModel):
    """A created PayPal order and where to send the buyer to approve it."""

    id: str
    approve_url: str
    mode: str               # live | mock
    status: str             # PayPal's own order status (CREATED, APPROVED, …)
    amount_total: int       # cents, resolved server-side from the price book
    currency: str


class PayPalCaptureRequest(BaseModel):
    """Propose capturing an approved PayPal order (HIGH risk — always gated)."""

    paypal_order_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    reason: str = ""


class EtsyPublishListingRequest(BaseModel):
    """Propose publishing a listing to the live Etsy shop (HIGH risk — always gated)."""

    sku: str
    title: str
    price: float = Field(ge=0, description="List price in the shop currency")
    quantity: int = Field(default=1, ge=0)
    description: str = ""


class EtsySyncInventoryRequest(BaseModel):
    """Propose pushing inventory quantities to live Etsy listings (HIGH risk — gated)."""

    updates: dict[str, int] = Field(
        default_factory=dict, description="Map of Etsy listing_id -> new on-hand quantity"
    )


class EtsyManageOrderRequest(BaseModel):
    """Propose a change to a live Etsy order/receipt (HIGH risk — gated)."""

    receipt_id: str
    action: str = Field(description="e.g. mark_shipped | cancel | refund")
    note: str = ""


class ActionResult(BaseModel):
    """Uniform envelope returned by every governed action."""

    status: str               # executed | queued_for_approval | drafted | error
    action: str
    risk_score: int
    risk_tier: str
    requires_approval: bool
    approval_id: int | None = None
    reasons: list[str] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)


class EventOut(BaseModel):
    id: int
    ts: datetime
    actor: str
    action: str
    target: str | None
    result: str
    risk_score: int
    risk_tier: str

    model_config = {"from_attributes": True}


class ApprovalOut(BaseModel):
    id: int
    action: str
    target: str | None
    risk_score: int
    risk_tier: str
    status: str
    requested_by: str
    decided_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionRequest(BaseModel):
    # Optional human-readable label only. The decider recorded on the approval and in the
    # audit ledger is the authenticated admin credential, not this field — see
    # routers/approvals.py::_resolve_decider. Kept for forensic annotation.
    decided_by: str = Field(default="human", description="Optional display label; not the trusted identity")
    note: str = ""


class MetricsOverview(BaseModel):
    revenue: float
    orders: int
    conversion_rate: float
    aov: float
    refund_rate: float
    open_approvals: int
    window_days: int


class SideStoreCartLine(BaseModel):
    """A Side Store cart line: what, and how many. Never how much."""

    id: str = Field(description="Catalogue item id, e.g. sku_001")
    quantity: int = Field(default=1, ge=1)


class SideStoreCartRequest(BaseModel):
    """Same reasoning as CheckoutRequest: no caller-supplied return URLs."""

    items: list[SideStoreCartLine] = Field(min_length=1, max_length=40)
    customer_email: str | None = None
    client_reference_id: str | None = Field(default=None, max_length=200)


class SideStoreCatalogItemOut(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    description: str
    amount: int


class SideStoreQuoteOut(BaseModel):
    """A priced cart. Every field is in the smallest currency unit (cents)."""

    quantity: int
    subtotal: int
    discount_rate: str
    discount: int
    discounted_subtotal: int
    shipping: int
    free_shipping_applied: bool
    tax: int
    total: int
    currency: str
    #: Tax is quoted at the Ontario HST rate. The store ships Canada-wide and
    #: Stripe Tax charges the destination's rate, so outside Ontario this is an
    #: estimate and the final amount is computed at checkout.
    tax_basis: str
    tax_is_estimate: bool


class RevenueLeadRequest(BaseModel):
    """Public qualification submission. Sensitive free text stays out of analytics."""
    full_name: str = Field(min_length=2, max_length=160)
    work_email: str = Field(min_length=5, max_length=254)
    company: str | None = Field(default=None, max_length=240)
    website: str | None = Field(default=None, max_length=500)
    role: str | None = Field(default=None, max_length=160)
    service_interest: str = Field(min_length=2, max_length=160)
    primary_goal: str = Field(min_length=5, max_length=2000)
    current_challenge: str = Field(min_length=5, max_length=4000)
    business_context: str = Field(default="", max_length=4000)
    desired_timeline: str | None = Field(default=None, max_length=80)
    investment_range: str | None = Field(default=None, max_length=80)
    notes: str = Field(default="", max_length=4000)
    source: str = Field(default="direct", max_length=120)
    landing_page: str | None = Field(default=None, max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    utm_first_source: str | None = Field(default=None, max_length=120)
    utm_first_medium: str | None = Field(default=None, max_length=120)
    utm_first_campaign: str | None = Field(default=None, max_length=160)
    utm_last_source: str | None = Field(default=None, max_length=120)
    utm_last_medium: str | None = Field(default=None, max_length=120)
    utm_last_campaign: str | None = Field(default=None, max_length=160)
    consent_marketing: bool = False
    website_honeypot: str = Field(default="", max_length=100)


class RevenueLeadStageUpdate(BaseModel):
    stage: str
    owner: str | None = Field(default=None, max_length=120)
    next_action: str = Field(min_length=2, max_length=1000)
    next_action_at: datetime | None = None
    expected_value_cad: float | None = Field(default=None, ge=0)
    monthly_recurring_value_cad: float | None = Field(default=None, ge=0)
    note: str = Field(default="", max_length=2000)


class RevenueControlLogRequest(BaseModel):
    action_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    action: str = Field(min_length=2, max_length=2000)
    target: str = Field(default="", max_length=1000)
    expected_outcome: str = Field(default="", max_length=2000)
    action_taken: str = Field(default="", max_length=2000)
    evidence: str = Field(default="", max_length=2000)
    result: str = Field(default="", max_length=2000)
    next_action: str = Field(default="", max_length=2000)
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    owner: str = Field(default="unassigned", max_length=120)
    status: str = Field(default="NOT_STARTED", max_length=40)


class RevenueCheckoutRequest(BaseModel):
    customer_email: str = Field(min_length=5, max_length=254)
    # The opaque reference from the lead receipt, never the sequential lead id.
    reference: UUID | None = None


class RevenueLeadReceipt(BaseModel):
    """What a visitor gets back after qualifying: no score, stage, owner or id.

    A honeypot hit gets the same shape with a reference that matches nothing.
    """
    status: str = "received"
    reference: UUID
    next_step: str
    booking_url: str | None = None


class RevenueOfferOut(BaseModel):
    sku: str
    name: str
    description: str
    amount_cad: float
    currency: str
    scope: list[str]
    exclusions: list[str]
    enabled: bool
    payment_ready: bool
    payment_mode: str
    payment_url: str | None = None
    calendar_url: str | None = None


class RevenueByCampaign(BaseModel):
    campaign: str
    orders: int
    confirmed_revenue_cad: float


class RevenueByProvider(BaseModel):
    """Live, verified money per processor, by the same rule as confirmed revenue."""
    provider: str               # stripe | paypal | other
    orders: int
    gross_cad: float
    refunded_cad: float
    confirmed_revenue_cad: float


class RevenueCockpitOut(BaseModel):
    generated_at: datetime
    # Live, provider-verified money still held: gross − refunded − disputed_open − dispute_lost.
    confirmed_revenue_cad: float
    gross_revenue_cad: float
    refunded_cad: float
    disputed_open_cad: float
    dispute_lost_cad: float
    # From Stripe-verified subscriptions on price-book Prices; None = no subscriptions table.
    verified_mrr_cad: float | None
    active_subscriptions: int | None
    past_due_subscriptions: int | None
    unpriced_subscriptions: int | None
    revenue_by_campaign: list[RevenueByCampaign]
    test_revenue_cad: float
    pipeline_estimate_cad: float
    # Entered by hand on leads; a contract figure, not Stripe data.
    mrr_cad: float
    gross_margin_cad: float | None
    qualified_leads: int
    new_leads: int
    meetings_booked: int
    proposals: int
    won: int
    lost: int
    close_rate: float | None
    open_service_orders: int
    due_actions: int
    webhook_health: str
    booking_health: str
    crm_health: str
    revenue_action_required: bool
    # Migration 010. Defaults keep older admin builds, which do not read these, working.
    revenue_by_provider: list[RevenueByProvider] = Field(default_factory=list)
    commercial_orders_by_state: dict[str, int] = Field(default_factory=dict)
    reconciliation_required: int = 0
    checkout_started_30d: int = 0


class RevenueLeadOut(BaseModel):
    """Admin-only view of a lead. Never returned by a public route."""
    id: int
    public_ref: UUID
    full_name: str
    email: str
    company: str | None
    website: str | None
    role: str | None
    service_interest: str
    desired_timeline: str | None
    investment_range: str | None
    source: str
    stage: str
    owner: str
    next_action: str
    next_action_at: datetime | None
    lead_score: int
    score_explanation: str
    expected_value_cad: float | None
    monthly_recurring_value_cad: float | None
    consent_marketing: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RevenueActivityOut(BaseModel):
    id: int
    lead_id: int
    activity_type: str
    actor: str
    detail: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RevenueServiceOrderOut(BaseModel):
    id: int
    order_id: int
    lead_id: int | None
    sku: str
    status: str
    scope_status: str
    delivery_owner: str
    due_at: datetime | None
    customer_next_step: str
    delivery_confirmed_at: datetime | None
    follow_up_at: datetime | None
    testimonial_eligible: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- ClearGlass orders (app/commerce_orders.py) -----------------------------------

_SKU_PATTERN = r"^[a-z0-9][a-z0-9-]{1,119}$"
# Shape only; the processor is the real check. Refuses what is plainly not an address.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class CommerceOrderRequest(BaseModel):
    """An offer and a quantity. Never a price: the price book sets it.

    ``reference`` links the order to a CRCS lead; it then needs the lead's own
    email, so a reference alone cannot attach an order to someone's record.
    """

    sku: str = Field(pattern=_SKU_PATTERN)
    quantity: int = Field(default=1, ge=1, le=100)
    reference: UUID | None = None
    customer_email: str | None = Field(default=None, max_length=254, pattern=_EMAIL_PATTERN)
    attribution: CheckoutAttribution | None = None


class CommerceOrderOut(BaseModel):
    order_ref: str
    sku: str
    offer: str
    quantity: int
    amount: float
    currency: str
    checkout_mode: str
    payment_state: str
    # Processors this order may be paid through. PayPal is absent for subscriptions.
    providers: list[str]


class CommerceCheckoutRequest(BaseModel):
    provider: Literal["stripe", "paypal"]
    customer_email: str | None = Field(default=None, max_length=254, pattern=_EMAIL_PATTERN)


class CommerceCheckoutOut(BaseModel):
    order_ref: str
    provider: str
    url: str
    mode: str                   # live | mock
    amount: float
    currency: str


class CommerceOrderStatusOut(BaseModel):
    """Public order status. No email, processor id or internal note."""
    order_ref: str
    offer: str
    amount: float
    currency: str
    provider: str | None
    payment_state: str
    # True only after a signed processor event; a checkout redirect alone is False.
    payment_verified: bool
    fulfillment_state: str
    state: str


class ProviderRecord(BaseModel):
    """One processor payment for reconciliation (see app.reconciliation)."""
    provider: Literal["stripe", "paypal"]
    reference: str = Field(min_length=3, max_length=160)
    amount: str = Field(max_length=32)
    currency: str = Field(min_length=3, max_length=3)
    status: str = Field(max_length=32)
    amount_refunded: str = Field(default="0", max_length=32)
    livemode: bool = True
    order_ref: str | None = Field(default=None, max_length=32)
    disputed: bool = False


class ReconciliationRequest(BaseModel):
    provider_records: list[ProviderRecord] = Field(default_factory=list, max_length=5000)



# ── Sentinel Core answered by Claude (routers/sentinel.py) ──────────────────
class SentinelTurn(BaseModel):
    """One earlier turn of the visitor's conversation, text only."""
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class SentinelAskIn(BaseModel):
    """A visitor's question. Everything the model sees arrives through here."""
    question: str = Field(min_length=1, max_length=800)
    mode: Literal["auto", "executive", "technical", "pitch", "analytical"] = "auto"
    # The page the visitor is reading, as a same-site path (checked in the router).
    page: str | None = Field(default=None, max_length=200)
    history: list[SentinelTurn] = Field(default_factory=list, max_length=6)


class SentinelSource(BaseModel):
    path: str
    title: str


class SentinelAnswerOut(BaseModel):
    """What the console renders. No ledger id, no question echo."""
    answer: str
    mode: str
    # "claude" when the model answered; "guard" when the router declined to send.
    engine: Literal["claude", "guard"]
    model: str
    served_by: str
    sources: list[SentinelSource]
    lookups: int
    rounds: int
    refused: bool
    latency_ms: int
    # Opaque; the audit row carries the same value.
    reference: str
