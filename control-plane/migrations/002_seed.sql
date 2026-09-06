-- Minimal seed data for local development. Safe to re-run.

INSERT INTO products (slug, title, status, margin_pct) VALUES
    ('aurora-desk-lamp', 'Aurora LED Desk Lamp', 'active', 58.00),
    ('summit-water-bottle', 'Summit Insulated Bottle', 'active', 62.00)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO variants (product_id, sku, price, currency)
SELECT id, 'AURORA-STD', 49.00, 'CAD' FROM products WHERE slug = 'aurora-desk-lamp'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO variants (product_id, sku, price, currency)
SELECT id, 'SUMMIT-750', 34.00, 'CAD' FROM products WHERE slug = 'summit-water-bottle'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO inventory (variant_id, on_hand, reorder_threshold)
SELECT id, 8, 10 FROM variants WHERE sku = 'AURORA-STD';

INSERT INTO inventory (variant_id, on_hand, reorder_threshold)
SELECT id, 120, 20 FROM variants WHERE sku = 'SUMMIT-750';

INSERT INTO metrics_daily (day, revenue, orders, conversion_rate, aov, refund_rate) VALUES
    (to_char(now()::date, 'YYYY-MM-DD'), 1240.00, 31, 0.0240, 40.00, 0.0150)
ON CONFLICT (day) DO NOTHING;
