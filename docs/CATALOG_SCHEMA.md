# Canonical product catalog — contract and setup checklist

**Risk:** `docs/BASELINE.md` R8.
**Tooling:** `tools/catalog_contract.py`, `tests/test_catalog_contract.py`.

A governed checkout must reject any request whose SKU, amount, currency or
product type does not match the approved catalog. That check is only as strong
as the catalog behind it — and today the catalog cannot support it, because the
fields to check against do not exist.

**Nothing in this document invents a value.** Every gap below is reported as a
gap. What a SKU's refund policy is, or whether an engagement is a service or a
subscription, is a business decision, not something tooling may guess.

---

## 1. Where the catalogs are, and which one decides

| File | Entries | Role |
|---|---:|---|
| `control-plane/app/data/pricebook.json` | 3 | **Server-side price authority.** `POST /checkout/session` resolves amounts here and nowhere else. This file decides what a customer is charged. |
| `data/store/catalog.json` | 5 | Service engagements with live `buy.stripe.com` URLs, rendered by the static site. |
| `data/side-store/catalog.json` | 57 | Impulse SKUs, projected out of `side-store.html` by `tools/side_store_catalog.py`. |

They are three different catalogs with three different shapes. `CLAUDE.md`
already warns against conflating the first two.

---

## 2. The contract

| Field | Required | Why |
|---|---|---|
| `sku` | yes | The join key across catalog, order, processor and ledger. |
| `product_name` | yes | What the customer is told they bought. |
| `product_type` | yes | One of `digital`, `physical`, `subscription`, `service`. Decides which fulfillment path may run. |
| `approved_price` | yes | Integer minor units. The only amount a checkout may charge. |
| `currency` | yes | ISO 4217. A price without one is not a price. |
| `tax_policy` | yes | How tax is applied. Stripe rejects session creation when this is unsettled. |
| `shipping_policy` | physical only | Omit for digital goods. |
| `fulfillment_type` | yes | What happens after a verified payment. Without it, fulfillment is improvised. |
| `delivery_entitlement` | digital only | What access the buyer is granted, and for how long. |
| `inventory_source` | yes | Where stock is authoritative. Absent, an oversell cannot be detected. |
| `active` | yes | Whether the SKU may be sold right now. |
| `refund_policy_ref` | yes | Pointer to the published policy the buyer agreed to. |
| `stripe_price_id` | where applicable | Stripe's own price authority. |
| `etsy_listing_id` | where applicable | Etsy listing this SKU maps to. |
| `paypal_reference_id` | where applicable | PayPal item/reference id. |

### Aliases

A catalog can satisfy a field under a name it already uses, where the meaning is
unambiguous. No rewrite is required to become compliant:

| Canonical | Accepted as |
|---|---|
| `sku` | `id` |
| `product_name` | `name`, `label` |
| `approved_price` | `amount_cents`, `amount`, `price` |
| `tax_policy` | `tax_behavior` |
| `stripe_price_id` | `stripe_price` |

Aliases are listed only where equivalence is certain. Guessing one would defeat
the purpose of the check.

---

## 3. Measured gap, 2026-09-15

```
python3 tools/catalog_contract.py
```

| Catalog | Entries | Contract-complete | Required fields missing |
|---|---:|---:|---|
| `pricebook.json` | 3 | **0** | `product_type`, `fulfillment_type`, `inventory_source`, `refund_policy_ref` |
| `data/store/catalog.json` | 5 | **0** | the four above, plus `tax_policy`, `active` |
| `data/side-store/catalog.json` | 57 | **0** | the four above, plus `tax_policy`, `active` |

**65 SKUs. None contract-complete.**

Already satisfied by existing keys: `approved_price`, `product_name` in all
three; `tax_policy` in the price book via `tax_behavior`.

The consistent gap is the same four fields everywhere — the ones that say what
kind of thing a SKU is, what happens after payment, where stock lives, and what
the buyer can demand back. Those are precisely the fields a fulfillment or
refund decision needs, which is why a governed checkout cannot be completed
without them.

---

## 4. Owner setup checklist

Four decisions per catalog, then one value per SKU. **No item here can be
derived from the repository.**

- [ ] **`product_type`** — classify each SKU as `digital`, `physical`,
      `subscription` or `service`. The price book's `kind: recurring` entries
      are likely `subscription`, but "likely" is not a classification, and this
      field decides which fulfillment path may run.
- [ ] **`fulfillment_type`** — what happens after a verified payment webhook.
      For digital goods this must name the mechanism: expiring signed link,
      licence/entitlement record, or authenticated delivery. Never a permanent
      unprotected URL.
- [ ] **`inventory_source`** — where stock is authoritative per SKU, or an
      explicit "unlimited" for digital goods. Without it an oversell is
      undetectable.
- [ ] **`refund_policy_ref`** — the published policy each SKU is sold under.
      This must point at something a customer can actually read.
- [ ] **`tax_policy`** — for `data/store/catalog.json` and the side store. The
      price book already carries `tax_behavior`. Per `render.yaml`, Stripe Tax
      stays off until Settings → Tax has an origin address, a registration and
      a default tax code.
- [ ] **`active`** — explicit sellability for the two catalogs lacking it.
- [ ] **Processor ids** — `stripe_price_id` is present in the price book;
      `etsy_listing_id` and `paypal_reference_id` are absent everywhere and are
      only needed for SKUs sold on those channels.

### Also outstanding, and blocking before this matters

- **R3 — three live entry prices.** CAD 1,250 is quoted in
  `commercial/OUTREACH_2026-09-15.md`, 297.00 sits in the price book, 249.00 is
  on the live site checkout. **There is no SKU for the 1,250 assessment
  anywhere.** A canonical catalog cannot be canonical while the headline offer
  is absent from it.
- **Digital fulfillment source** — no object storage, signed-link service or
  licence system is configured. `fulfillment_type` for a digital SKU has nothing
  to point at until one exists.

---

## 5. Enforcement, and why it is not on yet

```bash
python3 tools/catalog_contract.py            # gap report, always exit 0
python3 tools/catalog_contract.py --json     # machine-readable
python3 tools/catalog_contract.py --strict   # exit 1 while any SKU is incomplete
```

`--strict` is the future gate. It is **deliberately not wired into
`scripts/ci_local.py` or `ci.yml`**, and `tests/test_catalog_contract.py`
asserts that it stays that way. Turning it on today would fail the build on all
65 SKUs to report something this tool already reports on demand — noise, not a
gate.

**Turn it on when the checklist above is complete.** At that point it stops
being a report and starts being the thing that keeps the catalog honest.

The validator never writes to a catalog. `test_audit_entry_does_not_mutate_the_entry`
pins that.
