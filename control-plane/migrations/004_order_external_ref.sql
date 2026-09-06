-- ClearGlass Commerce — order idempotency key (Postgres).
-- Stripe redelivers webhooks; `external_ref` stores the checkout-session id so
-- `checkout.session.completed` retries can never create a duplicate order.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS external_ref VARCHAR(160);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_external_ref
    ON orders(external_ref) WHERE external_ref IS NOT NULL;
