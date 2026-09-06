-- ClearGlass Commerce — dropship fulfillment (Postgres).
--
-- Adds the destination address to an order and a shipments table for what the
-- supplier actually did with it. Before this, an order recorded that money had
-- arrived and nothing about where the goods were going.
--
-- Shipments are a separate table rather than columns on `orders` because a
-- print-on-demand supplier splits an order across facilities: two items can ship
-- as two parcels, with two carriers and two tracking numbers.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_name VARCHAR(160);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_address1 VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_address2 VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_city VARCHAR(120);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_state VARCHAR(64);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_country VARCHAR(2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_zip VARCHAR(32);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ship_to_email VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment_status VARCHAR(32) NOT NULL DEFAULT 'pending';

CREATE TABLE IF NOT EXISTS shipments (
    id                SERIAL PRIMARY KEY,
    order_id             INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    supplier             VARCHAR(32)  NOT NULL DEFAULT 'printful',
    supplier_order_id    VARCHAR(120),
    supplier_shipment_id VARCHAR(120),
    status            VARCHAR(32)  NOT NULL DEFAULT 'draft',
    tracking_number   VARCHAR(160),
    tracking_url      TEXT,
    carrier           VARCHAR(64),
    service           VARCHAR(120),
    supplier_cost     NUMERIC(12, 2),
    currency          VARCHAR(3)   NOT NULL DEFAULT 'CAD',
    shipped_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shipments_order_id ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_supplier_order
    ON shipments(supplier, supplier_order_id);

-- Idempotency for shipment webhooks, keyed on the *parcel* rather than the
-- order. Printful redelivers `package_shipped`, so a retry must update its own
-- row; but a split order emits one notice per parcel with the same order id, so
-- keying on the order would let the second parcel overwrite the first one's
-- tracking number and leave a customer chasing a parcel we never mentioned.
CREATE UNIQUE INDEX IF NOT EXISTS idx_shipments_supplier_shipment
    ON shipments(supplier, supplier_shipment_id) WHERE supplier_shipment_id IS NOT NULL;
