-- CRCS Phase 0: an opaque reference for each lead, additive after 007_revenue_command.sql.
--
-- POST /revenue/leads used to return the lead's SERIAL id. Ids are sequential,
-- so any visitor could read the lead count off their own receipt, and the
-- checkout accepted that id back. The browser now receives public_ref instead;
-- the id stays internal. See docs/crcs/IMPLEMENTATION_SEQUENCE.md item 0.3.
--
-- gen_random_uuid() is built in from PostgreSQL 13.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS public_ref UUID;
UPDATE leads SET public_ref = gen_random_uuid() WHERE public_ref IS NULL;
ALTER TABLE leads ALTER COLUMN public_ref SET DEFAULT gen_random_uuid();
ALTER TABLE leads ALTER COLUMN public_ref SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_public_ref ON leads(public_ref);
