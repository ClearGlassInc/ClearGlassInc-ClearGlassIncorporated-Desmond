// Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
// Proprietary and confidential. See LICENSE for terms.
/**
 * Product source adapters.
 *
 * The site publishes products in three places, in three shapes, and this module
 * is the only part of the sync that knows the difference. Each adapter reads
 * *structured* data — an embedded JSON island, a generated catalog, the control
 * plane's price book — and never re-parses rendered HTML for prices. Where the
 * structured data is ambiguous ("from CAD $2,500"), the adapter says so and
 * withholds the product instead of guessing an amount to charge.
 *
 * Every adapter emits the same `SourceProduct` shape, so the planner downstream
 * has one contract regardless of where a product came from.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";

import { normalizeImages } from "./images.js";
import { AmountError, assertMinorAmount, normalizeCurrency, toMinorUnits } from "./money.js";
import type { ParseResult, ProductIssue, Recurrence, SourceProduct, SourceVariant } from "./types.js";

export interface AdapterContext {
  /** Repository root — every source path is resolved from here. */
  root: string;
  /** Public origin of the GitHub Pages site, e.g. `https://www.clearglassinc.com`. */
  baseUrl: string;
  /** `owner/repo`, written to Stripe metadata as `source_repository`. */
  repository: string;
  /** Fallback currency for sources that do not carry one per product. */
  defaultCurrency: string;
}

export interface SourceAdapter {
  name: string;
  /** Path, relative to the repo root, that this adapter reads. */
  file: string;
  description: string;
  /** Excluded from `--source all`; must be named explicitly. */
  optIn?: boolean;
  parse(context: AdapterContext): ParseResult;
}

/**
 * Phrases that make a listed price a *starting point* rather than the amount to
 * charge. A Stripe Price is an exact number; "from $2,500" and "deposit" are
 * quote-driven, so the product is reported for manual correction instead.
 */
const AMBIGUOUS_PRICE_MARKERS = [
  /\bfrom\b/i,
  /\bstarting\b/i,
  /\bdeposit\b/i,
  /\bquote\b/i,
  /\bcontact\b/i,
  /\bper (?:hour|day|seat|user)\b/i,
  /\bTBD\b/i,
];

const RECURRING_INTERVALS: Record<string, Recurrence["interval"]> = {
  day: "day",
  daily: "day",
  week: "week",
  weekly: "week",
  mo: "month",
  month: "month",
  monthly: "month",
  yr: "year",
  year: "year",
  yearly: "year",
  annual: "year",
  annually: "year",
};

function issue(
  sourceId: string,
  adapter: string,
  field: string,
  message: string,
  severity: ProductIssue["severity"] = "error",
): ProductIssue {
  return { sourceId, adapter, field, message, severity };
}

/** Detect a billing interval from free-text price copy such as "CAD $600 / month". */
export function detectInterval(text: string | undefined): Recurrence | undefined {
  if (!text) return undefined;
  const match = /(?:\/|\bper\b|\beach\b|\bbilled\b)\s*([a-z]+)/i.exec(text);
  const word = match?.[1]?.toLowerCase();
  const interval = word ? RECURRING_INTERVALS[word] : undefined;
  if (interval) return { interval, interval_count: 1 };
  if (/\b(monthly|per month|\/mo)\b/i.test(text)) return { interval: "month", interval_count: 1 };
  if (/\b(annually|yearly|per year|\/yr)\b/i.test(text)) return { interval: "year", interval_count: 1 };
  return undefined;
}

/** Return the marker that makes a price ambiguous, or null when it is exact. */
export function ambiguityIn(text: string | undefined): string | null {
  if (!text) return null;
  for (const marker of AMBIGUOUS_PRICE_MARKERS) {
    const found = marker.exec(text);
    if (found) return found[0];
  }
  return null;
}

/**
 * Content hash of a product, over the fields that would change a Stripe record.
 *
 * Stored as `source_hash`; the planner compares it to the value already in
 * Stripe to decide between an update and a no-op, and it seeds the idempotency
 * key so a retried create cannot double up.
 */
export function hashProduct(product: Omit<SourceProduct, "sourceHash">): string {
  const canonical = JSON.stringify({
    sourceId: product.sourceId,
    name: product.name,
    description: product.description ?? null,
    category: product.category ?? null,
    sourceUrl: product.sourceUrl,
    images: product.images,
    inventoryStatus: product.inventoryStatus ?? null,
    variants: product.variants
      .map((variant) => ({
        variantKey: variant.variantKey,
        amountMinor: variant.amountMinor,
        currency: variant.currency,
        recurring: variant.recurring ?? null,
        taxBehavior: variant.taxBehavior ?? null,
      }))
      .sort((a, b) => a.variantKey.localeCompare(b.variantKey)),
  });
  return createHash("sha256").update(canonical).digest("hex").slice(0, 32);
}

function finalize(product: Omit<SourceProduct, "sourceHash">): SourceProduct {
  return { ...product, sourceHash: hashProduct(product) };
}

function readJsonFile(root: string, relative: string): unknown {
  return JSON.parse(readFileSync(path.join(root, relative), "utf8"));
}

/**
 * Pull the JSON island out of an HTML page.
 *
 * `side-store.html` ships its catalogue as `<script id="catalog"
 * type="application/json">`, which the page itself parses at boot — so reading
 * that block gives exactly the data the site renders, with no HTML scraping and
 * no risk of the two drifting.
 */
export function extractJsonIsland(html: string, id: string): unknown {
  const pattern = new RegExp(
    `<script[^>]*id=["']${id}["'][^>]*>([\\s\\S]*?)</script>`,
    "i",
  );
  const match = pattern.exec(html);
  if (!match?.[1]) {
    throw new Error(`no <script id="${id}"> JSON block found`);
  }
  return JSON.parse(match[1]);
}

/* ── side-store.html — the retail accessory catalogue ──────────────────── */

const sideStoreAdapter: SourceAdapter = {
  name: "side-store",
  file: "side-store.html",
  description: "Retail accessory catalogue embedded in side-store.html as a JSON island",
  parse(context) {
    const products: SourceProduct[] = [];
    const issues: ProductIssue[] = [];
    const html = readFileSync(path.join(context.root, "side-store.html"), "utf8");
    const raw = extractJsonIsland(html, "catalog");
    if (!Array.isArray(raw)) {
      throw new Error("side-store catalog island is not a JSON array");
    }

    const seen = new Set<string>();
    for (const [index, entry] of raw.entries()) {
      const item = (entry ?? {}) as Record<string, unknown>;
      const sku = typeof item.sku === "string" ? item.sku.trim() : "";
      const sourceId = `side-store:${sku || `index-${index}`}`;

      if (!sku) {
        issues.push(issue(sourceId, "side-store", "sku", `entry ${index} has no sku`));
        continue;
      }
      if (seen.has(sku)) {
        issues.push(issue(sourceId, "side-store", "sku", `duplicate sku ${sku} in the catalogue`));
        continue;
      }
      seen.add(sku);

      const name = typeof item.name === "string" ? item.name.trim() : "";
      if (!name) {
        issues.push(issue(sourceId, "side-store", "name", "product has no name"));
        continue;
      }

      // The catalogue states its currency once, in the page copy ("all prices
      // in CAD"), so per-item currency falls back to the run default.
      const currency = normalizeCurrency(
        typeof item.currency === "string" ? item.currency : context.defaultCurrency,
      );

      let amountMinor: number;
      try {
        amountMinor = toMinorUnits(item.price, currency);
      } catch (error) {
        issues.push(
          issue(sourceId, "side-store", "price", (error as AmountError).message),
        );
        continue;
      }

      const { images, failures } = normalizeImages(item.image ?? item.images, context.baseUrl);
      const notes = failures.map((failure) => `image: ${failure}`);
      for (const failure of failures) {
        issues.push(issue(sourceId, "side-store", "image", failure, "warning"));
      }

      const variant: SourceVariant = {
        variantKey: "default",
        amountMinor,
        currency,
        taxBehavior: "exclusive",
      };

      products.push(
        finalize({
          sourceId,
          adapter: "side-store",
          sku,
          name,
          description: typeof item.description === "string" ? item.description.trim() : undefined,
          category: typeof item.category === "string" ? item.category.trim() : undefined,
          sourceUrl: `${context.baseUrl}/side-store.html#${encodeURIComponent(sku)}`,
          images,
          // No inventory status. The catalogue carries no stock field, and
          // stamping "in_stock" on every item would be inventing availability —
          // exactly what the operating rules forbid. Add an authoritative stock
          // field to the source first if this needs to reach Stripe.
          variants: [variant],
          notes,
        }),
      );
    }
    return { products, issues };
  },
};

/* ── data/store/catalog.json — the generated services catalogue ─────────── */

const storeCatalogAdapter: SourceAdapter = {
  name: "store",
  file: "data/store/catalog.json",
  description: "Generated services catalog (scripts/store_sync.py distils store.html into this)",
  parse(context) {
    const products: SourceProduct[] = [];
    const issues: ProductIssue[] = [];
    const catalog = readJsonFile(context.root, "data/store/catalog.json") as Record<string, unknown>;
    const entries = Array.isArray(catalog.products) ? catalog.products : [];

    for (const entry of entries) {
      const item = (entry ?? {}) as Record<string, unknown>;
      const sku = typeof item.sku === "string" ? item.sku.trim() : "";
      const sourceId = `store:${sku}`;
      if (!sku) {
        issues.push(issue("store:<unknown>", "store", "sku", "catalog entry has no sku"));
        continue;
      }

      const name = typeof item.name === "string" ? item.name.trim() : "";
      if (!name) {
        issues.push(issue(sourceId, "store", "name", "product has no name"));
        continue;
      }

      const priceDisplay = typeof item.price_display === "string" ? item.price_display : "";
      const etransfer = typeof item.etransfer_amount === "string" ? item.etransfer_amount : "";

      // These are quote-driven engagements. `amount_cents` is the floor of a
      // range, not the amount a customer owes, and creating a Stripe Price from
      // it would advertise a fixed fee the business never agreed to.
      const marker = ambiguityIn(priceDisplay) ?? ambiguityIn(etransfer);
      if (marker) {
        issues.push(
          issue(
            sourceId,
            "store",
            "price_display",
            `price is quote-driven (${JSON.stringify(priceDisplay || etransfer)} contains "${marker}") — ` +
              "a Stripe Price needs one exact amount. Set a fixed amount, or keep this engagement quote-only.",
          ),
        );
        continue;
      }

      let currency: string;
      let amountMinor: number;
      try {
        currency = normalizeCurrency(item.currency ?? context.defaultCurrency);
        amountMinor = assertMinorAmount(item.amount_cents, currency);
      } catch (error) {
        issues.push(issue(sourceId, "store", "amount_cents", (error as AmountError).message));
        continue;
      }

      const recurring = detectInterval(priceDisplay);
      const { images, failures } = normalizeImages(item.image ?? item.images, context.baseUrl);
      for (const failure of failures) {
        issues.push(issue(sourceId, "store", "image", failure, "warning"));
      }

      const notes = failures.map((failure) => `image: ${failure}`);
      if (item.live_checkout === false) {
        notes.push("storefront has live card checkout disabled for this SKU (Interac e-Transfer fallback)");
      }

      const variant: SourceVariant = {
        variantKey: recurring ? `${recurring.interval}ly` : "default",
        amountMinor,
        currency,
        taxBehavior: "exclusive",
      };
      if (recurring) variant.recurring = recurring;

      products.push(
        finalize({
          sourceId,
          adapter: "store",
          sku,
          name,
          description:
            typeof item.short === "string" && item.short.trim() ? item.short.trim() : undefined,
          category: "Professional services",
          sourceUrl: `${context.baseUrl}/store.html`,
          images,
          variants: [variant],
          notes,
        }),
      );
    }
    return { products, issues };
  },
};

/* ── clearglass-commerce price book — opt-in ───────────────────────────── */

const pricebookAdapter: SourceAdapter = {
  name: "pricebook",
  file: "clearglass-commerce/control-plane/app/data/pricebook.json",
  description:
    "Commerce control-plane price book. Opt-in: its offers already name live-mode Stripe Prices.",
  optIn: true,
  parse(context) {
    const products: SourceProduct[] = [];
    const issues: ProductIssue[] = [];
    const book = readJsonFile(
      context.root,
      "clearglass-commerce/control-plane/app/data/pricebook.json",
    ) as Record<string, unknown>;
    const offers = Array.isArray(book.offers) ? book.offers : [];

    // One Stripe product can carry several offers (monthly + annual of the same
    // subscription), so offers are grouped by their stripe_product_id when they
    // name one and by sku otherwise. Each offer becomes a variant.
    const groups = new Map<string, Record<string, unknown>[]>();
    for (const entry of offers) {
      const offer = (entry ?? {}) as Record<string, unknown>;
      if (offer.active === false) continue;
      const key =
        typeof offer.stripe_product_id === "string" && offer.stripe_product_id
          ? `product:${offer.stripe_product_id}`
          : `sku:${String(offer.sku ?? "")}`;
      const bucket = groups.get(key);
      if (bucket) bucket.push(offer);
      else groups.set(key, [offer]);
    }

    for (const [key, bucket] of groups) {
      const first = bucket[0];
      if (!first) continue;
      const groupSku = typeof first.sku === "string" ? first.sku : "";
      // The product key must not depend on which intervals happen to be on sale
      // today. Deriving it from the offers present would rename the product —
      // and orphan the old one — the moment an annual plan is added or dropped,
      // so the cadence suffix is stripped whether or not the group has one offer.
      const sku = key.startsWith("product:") ? productSku(groupSku) : groupSku;
      const sourceId = `pricebook:${sku}`;

      if (!sku) {
        issues.push(issue("pricebook:<unknown>", "pricebook", "sku", "offer has no sku"));
        continue;
      }

      const variants: SourceVariant[] = [];
      let failed = false;
      for (const offer of bucket) {
        const offerSku = typeof offer.sku === "string" ? offer.sku : sku;
        let currency: string;
        let amountMinor: number;
        try {
          currency = normalizeCurrency(offer.currency ?? context.defaultCurrency);
          amountMinor = assertMinorAmount(offer.amount, currency);
        } catch (error) {
          issues.push(issue(sourceId, "pricebook", `${offerSku}.amount`, (error as AmountError).message));
          failed = true;
          continue;
        }

        const kind = String(offer.kind ?? "one_time");
        const variant: SourceVariant = {
          variantKey: offerSku,
          label: typeof offer.name === "string" ? offer.name : undefined,
          amountMinor,
          currency,
          taxBehavior: normalizeTaxBehavior(offer.tax_behavior),
        };
        if (kind === "recurring") {
          const interval = RECURRING_INTERVALS[String(offer.interval ?? "")];
          if (!interval) {
            issues.push(
              issue(sourceId, "pricebook", `${offerSku}.interval`, `recurring offer has no usable interval (${String(offer.interval)})`),
            );
            failed = true;
            continue;
          }
          variant.recurring = { interval, interval_count: 1 };
        }
        if (typeof offer.stripe_price_id === "string" && offer.stripe_price_id) {
          variant.stripePriceIdHint = offer.stripe_price_id;
        }
        variants.push(variant);
      }

      if (failed || variants.length === 0) continue;

      const name = typeof first.name === "string" ? first.name : sku;
      const descriptions = bucket
        .map((offer) => (typeof offer.description === "string" ? offer.description : ""))
        .filter(Boolean);
      const product: Omit<SourceProduct, "sourceHash"> = {
        sourceId,
        adapter: "pricebook",
        sku,
        name: baseName(name),
        description: sharedDescription(descriptions),
        category: "Professional services",
        sourceUrl: `${context.baseUrl}/checkout/`,
        images: [],
        variants,
        notes: [
          "price book offers already name Stripe objects in the live account; " +
            "ids are verified against the target account before reuse",
        ],
      };
      if (typeof first.stripe_product_id === "string" && first.stripe_product_id) {
        product.stripeProductIdHint = first.stripe_product_id;
      }
      products.push(finalize(product));
    }
    return { products, issues };
  },
};

/** Trailing billing-cadence token on an offer sku, e.g. `…-monthly`. */
const CADENCE_SUFFIX = /-(?:monthly|annual|annually|yearly|weekly|daily|quarterly|month|year)$/i;

/**
 * The product-level key for an offer sku.
 *
 * Offers of one product differ by cadence (`business-protection-monthly` and
 * `-annual`); the product itself is `business-protection`. Stripping the suffix
 * unconditionally — rather than diffing the skus present — is what makes the key
 * independent of which intervals are currently on sale.
 */
export function productSku(offerSku: string): string {
  const stripped = offerSku.replace(CADENCE_SUFFIX, "");
  return stripped || offerSku;
}

/** Drop the "— monthly" / "— annual" suffix so grouped offers share a product name. */
function baseName(name: string): string {
  return name.split(/\s+[—–-]\s+/)[0]?.trim() || name;
}

/** Trailing sentence naming one billing cadence, e.g. "Billed monthly." */
const CADENCE_SENTENCE = /\s*\bBilled\s+(?:monthly|yearly|annually|weekly|daily|quarterly)\s*\.?\s*$/i;

/**
 * A description that is true of every variant on the shared Stripe Product.
 *
 * One Stripe Product carries several Prices, so a description copied from the
 * first offer would tell an annual subscriber their plan is "Billed monthly".
 * The cadence belongs to the Price, not the Product, so it is stripped when the
 * offers are grouped; if what remains still differs between offers, no product
 * description is set rather than asserting one variant's copy over the others.
 */
export function sharedDescription(descriptions: string[]): string | undefined {
  const neutral = descriptions.map((text) => text.replace(CADENCE_SENTENCE, "").trim()).filter(Boolean);
  if (neutral.length === 0) return undefined;
  const [first] = neutral;
  return neutral.every((text) => text === first) ? first : undefined;
}

function normalizeTaxBehavior(value: unknown): SourceVariant["taxBehavior"] {
  return value === "inclusive" || value === "exclusive" ? value : "unspecified";
}

/* ── registry ──────────────────────────────────────────────────────────── */

export const ADAPTERS: SourceAdapter[] = [sideStoreAdapter, storeCatalogAdapter, pricebookAdapter];

export function adapterNames(): string[] {
  return ADAPTERS.map((adapter) => adapter.name);
}

/** Adapters included by `--source all`: everything published on GitHub Pages. */
export function defaultAdapterNames(): string[] {
  return ADAPTERS.filter((adapter) => !adapter.optIn).map((adapter) => adapter.name);
}

/**
 * Run the named adapters and merge their output.
 *
 * A source that throws (missing file, unparseable JSON) is reported as an error
 * issue rather than crashing the run, so one broken page cannot block the rest
 * of the catalogue from syncing.
 */
export function collectProducts(names: string[], context: AdapterContext): ParseResult {
  const products: SourceProduct[] = [];
  const issues: ProductIssue[] = [];
  for (const name of names) {
    const adapter = ADAPTERS.find((candidate) => candidate.name === name);
    if (!adapter) {
      issues.push(issue(`${name}:<adapter>`, name, "source", `unknown source ${JSON.stringify(name)}`));
      continue;
    }
    try {
      const result = adapter.parse(context);
      products.push(...result.products);
      issues.push(...result.issues);
    } catch (error) {
      issues.push(
        issue(`${name}:<adapter>`, name, "source", `failed to read ${adapter.file}: ${(error as Error).message}`),
      );
    }
  }
  return { products, issues };
}
