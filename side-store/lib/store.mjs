/**
 * Side Store pricing — the money math behind the cart in `side-store.html`.
 *
 * The page carries this logic inline, which meant the arithmetic that decides
 * what a customer is charged had no test of any kind. This module is a
 * faithful port of that inline `price()` function, extracted so the rules can
 * be exercised directly; `store.test.mjs` pins every branch of it against the
 * committed catalog.
 *
 * `assertPageConstantsMatch` guards the one risk extraction introduces: the
 * page and this module drifting apart. The test reads the page and fails if a
 * constant here no longer matches the one shipped to customers.
 *
 * All amounts are integer cents. Currency arithmetic in floating point
 * accumulates error — `0.1 + 0.2 !== 0.3` — and an error of one cent in a tax
 * line is a reconciliation problem, so nothing here ever holds a fractional
 * amount.
 */

/** Free shipping at or above this subtotal (cents, after any discount). */
export const FREE_SHIP = 2500;

/** Flat shipping charged below the free-shipping threshold (cents). */
export const FLAT_SHIP = 499;

/** Ontario HST. */
export const TAX_RATE = 0.13;

/** Bundle discount tiers: [minimum quantity, rate]. Highest match wins. */
export const BUNDLE_TIERS = [
  [5, 0.15],
  [3, 0.10],
];

/** Ceiling on the bundle rate, so a new tier can never discount past it. */
export const MAX_BUNDLE_RATE = 0.15;

/** Convert a decimal price to integer cents. */
export function cents(price) {
  return Math.round(Number(price) * 100);
}

/** Bundle discount rate for a total item quantity. */
export function bundleRate(quantity) {
  let rate = 0;
  for (const [minimum, tierRate] of BUNDLE_TIERS) {
    if (quantity >= minimum) {
      rate = tierRate;
      break;
    }
  }
  return Math.min(rate, MAX_BUNDLE_RATE);
}

/**
 * Price a cart.
 *
 * @param {Record<string, number>} cart  item id -> quantity
 * @param {Array<{id: string, name: string, price: number}>} items  catalog
 * @returns {{lines: Array, qty: number, rate: number, pct: number,
 *            sub: number, disc: number, ship: number, tax: number, tot: number}}
 *          every amount in integer cents
 */
export function price(cart, items) {
  const byId = new Map(items.map((item) => [item.id, item]));

  const lines = [];
  let sub = 0;
  let qty = 0;

  for (const id of Object.keys(cart)) {
    const item = byId.get(id);
    const quantity = cart[id];
    // An unknown id or a non-positive quantity contributes nothing. Silently
    // skipping is deliberate: a stale localStorage cart naming a delisted SKU
    // must still check out, minus that line.
    if (!item || !(quantity > 0)) continue;
    const unit = cents(item.price);
    const lineTotal = unit * quantity;
    sub += lineTotal;
    qty += quantity;
    lines.push({ id, name: item.name, unit, qty: quantity, lt: lineTotal });
  }

  const rate = bundleRate(qty);
  const disc = Math.round(sub * rate);
  const discountedSub = sub - disc;
  // No lines means no shipping — an empty cart is not "under the threshold".
  const ship = lines.length && discountedSub < FREE_SHIP ? FLAT_SHIP : 0;
  const tax = Math.round((discountedSub + ship) * TAX_RATE);
  const tot = discountedSub + ship + tax;

  return {
    lines,
    qty,
    rate,
    pct: Math.round(rate * 100),
    sub,
    disc,
    ship,
    tax,
    tot,
  };
}

/**
 * Assert the shipped page still declares the constants this module uses.
 *
 * Extracting the math created one new failure mode: `side-store.html` changing
 * a constant while this copy keeps the old value, so the tests keep passing
 * against arithmetic no customer sees. This closes that gap.
 *
 * @param {string} html  contents of side-store.html
 * @returns {string[]}   mismatches; empty when the page and module agree
 */
export function assertPageConstantsMatch(html) {
  const expected = {
    FREE_SHIP: String(FREE_SHIP),
    FLAT_SHIP: String(FLAT_SHIP),
    TAX_RATE: String(TAX_RATE),
  };

  const problems = [];
  for (const [name, value] of Object.entries(expected)) {
    const found = new RegExp(`\\b${name}\\s*=\\s*([0-9.]+)`).exec(html);
    if (!found) {
      problems.push(`${name} is no longer declared in side-store.html`);
    } else if (found[1] !== value) {
      problems.push(`${name}: page has ${found[1]}, store.mjs has ${value}`);
    }
  }

  // The tier table is expressed differently in the page (an if/else ladder),
  // so compare the rates it names rather than its structure.
  for (const [, tierRate] of BUNDLE_TIERS) {
    if (!html.includes(String(tierRate))) {
      problems.push(`bundle rate ${tierRate} is not present in side-store.html`);
    }
  }
  return problems;
}
