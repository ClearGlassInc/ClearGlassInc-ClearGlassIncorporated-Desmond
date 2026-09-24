-- ClearGlass orders, and the link from each payment back to one. Additive after
-- 009_revenue_integrity.sql.
--
-- Before this, an order row existed only once a processor's webhook booked a
-- payment, so nothing tied a Stripe payment and a PayPal payment for the same
-- purchase together, and nothing recorded which offer, price and campaign a
-- checkout started from. A ClearGlass order (CG-ORD-YYYY-XXXXXXXX) now exists
-- before the buyer chooses a processor; each settlement in `orders` names it.

CREATE TABLE IF NOT EXISTS commercial_orders (
    id                       SERIAL PRIMARY KEY,
    order_ref                VARCHAR(32)   NOT NULL UNIQUE,
    sku                      VARCHAR(120)  NOT NULL,
    offer_name               VARCHAR(240)  NOT NULL,
    quantity                 INTEGER       NOT NULL DEFAULT 1,
    amount                   NUMERIC(12,2) NOT NULL,
    currency                 VARCHAR(3)    NOT NULL DEFAULT 'CAD',
    checkout_mode            VARCHAR(16)   NOT NULL DEFAULT 'payment',
    payment_state            VARCHAR(32)   NOT NULL DEFAULT 'CREATED',
    provider                 VARCHAR(16),
    provider_checkout_ref    VARCHAR(160),
    payment_order_id         INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    environment              VARCHAR(16)   NOT NULL DEFAULT 'unknown',
    lead_id                  INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    utm_source               VARCHAR(120),
    utm_medium               VARCHAR(120),
    utm_campaign             VARCHAR(160),
    reconciliation_required  BOOLEAN       NOT NULL DEFAULT FALSE,
    reconciliation_reason    TEXT,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT commercial_orders_state_check CHECK (payment_state IN (
        'CREATED', 'CHECKOUT_STARTED', 'PAYMENT_PENDING', 'PAYMENT_PROCESSING', 'PAID',
        'PAYMENT_FAILED', 'CANCELED', 'REFUNDED', 'PARTIALLY_REFUNDED', 'DISPUTED', 'CHARGEBACK'
    )),
    CONSTRAINT commercial_orders_provider_check CHECK (provider IS NULL OR provider IN ('stripe', 'paypal'))
);

CREATE INDEX IF NOT EXISTS idx_commercial_orders_order_ref ON commercial_orders(order_ref);
CREATE INDEX IF NOT EXISTS idx_commercial_orders_payment_state ON commercial_orders(payment_state);
CREATE INDEX IF NOT EXISTS idx_commercial_orders_provider_checkout_ref ON commercial_orders(provider_checkout_ref);
CREATE INDEX IF NOT EXISTS idx_commercial_orders_lead_id ON commercial_orders(lead_id);
CREATE INDEX IF NOT EXISTS idx_commercial_orders_utm_campaign ON commercial_orders(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_commercial_orders_reconciliation ON commercial_orders(reconciliation_required);

-- Not unique on purpose: two settlements naming one order is the double
-- payment reconciliation has to see.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_ref VARCHAR(32);
CREATE INDEX IF NOT EXISTS idx_orders_order_ref ON orders(order_ref);
