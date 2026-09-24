-- Refunds, disputes and campaign attribution on orders. Additive after 008_lead_public_ref.sql.
--
-- Before this, charge.refunded and charge.dispute.* were written to the audit
-- ledger only. The order stayed `paid`, so the cockpit counted a refunded or
-- charged-back sale as confirmed revenue. Charges and disputes name a
-- PaymentIntent, not a Checkout Session, so the order now keeps the
-- PaymentIntent it was paid with, which is how a refund finds its order.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_intent VARCHAR(120);
-- Cumulative, in the order's currency: Stripe's charge.amount_refunded, so a
-- redelivered refund event sets the same value rather than subtracting twice.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS amount_refunded NUMERIC(12,2) NOT NULL DEFAULT 0;
-- Stripe's dispute status (needs_response, under_review, won, lost, ...); NULL = never disputed.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS dispute_status VARCHAR(32);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS utm_source VARCHAR(120);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(120);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(160);

CREATE INDEX IF NOT EXISTS idx_orders_payment_intent ON orders(payment_intent);
CREATE INDEX IF NOT EXISTS idx_orders_utm_campaign ON orders(utm_campaign);
