/**
 * Pricing and checkout smoke test for the Side Store.
 *
 * Runs under `node --test`, and through pytest via
 * tests/test_side_store_storefront.py so the storefront's money math is
 * exercised on every build rather than only when someone remembers to run the
 * Node suite.
 *
 * Every case below is stated in integer cents, against the real committed
 * catalog rather than fixtures — a rule that passes on invented SKUs and fails
 * on the shipped ones is worse than no test.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  FREE_SHIP,
  FLAT_SHIP,
  TAX_RATE,
  cents,
  bundleRate,
  price,
  assertPageConstantsMatch,
} from "./store.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const catalog = JSON.parse(
  readFileSync(join(ROOT, "data", "side-store", "catalog.json"), "utf8"),
);
const items = catalog.items;
const bySku = (sku) => items.find((item) => item.sku === sku);

test("catalog loads and every price converts to whole cents", () => {
  assert.ok(items.length >= 50, `expected >= 50 SKUs, got ${items.length}`);
  for (const item of items) {
    const value = cents(item.price);
    assert.ok(Number.isInteger(value), `${item.sku}: ${value} is not an integer`);
    assert.ok(value > 0, `${item.sku}: price must be positive`);
    assert.ok(value <= 1000, `${item.sku}: ${value} exceeds the $10 impulse cap`);
  }
});

test("cents() rounds binary-float prices correctly", () => {
  // 6.99 * 100 is 698.9999999999999 in IEEE 754. Truncating would undercharge
  // by a cent on every unit of the most common price point in the catalog.
  assert.equal(cents(6.99), 699);
  assert.equal(cents(4.99), 499);
  assert.equal(cents(0.1 + 0.2), 30);
});

test("bundle tiers apply at their boundaries and never past the ceiling", () => {
  assert.equal(bundleRate(0), 0);
  assert.equal(bundleRate(2), 0);
  assert.equal(bundleRate(3), 0.10);
  assert.equal(bundleRate(4), 0.10);
  assert.equal(bundleRate(5), 0.15);
  assert.equal(bundleRate(500), 0.15);
});

test("an empty cart is free, not 'under the shipping threshold'", () => {
  const result = price({}, items);
  assert.equal(result.lines.length, 0);
  assert.equal(result.sub, 0);
  assert.equal(result.ship, 0, "an empty cart must never be charged shipping");
  assert.equal(result.tax, 0);
  assert.equal(result.tot, 0);
});

test("a small cart pays flat shipping and HST on the shipped total", () => {
  const item = bySku("USB-C-C-1M");
  assert.ok(item, "USB-C-C-1M must exist in the catalog");

  const result = price({ [item.id]: 1 }, items);
  const unit = cents(item.price);

  assert.equal(result.qty, 1);
  assert.equal(result.sub, unit);
  assert.equal(result.disc, 0, "one item earns no bundle discount");
  assert.equal(result.ship, FLAT_SHIP);
  assert.equal(result.tax, Math.round((unit + FLAT_SHIP) * TAX_RATE));
  assert.equal(result.tot, unit + FLAT_SHIP + result.tax);
});

test("tax is charged on shipping, not only on goods", () => {
  const item = bySku("USB-C-C-1M");
  const result = price({ [item.id]: 1 }, items);
  const goodsOnlyTax = Math.round(cents(item.price) * TAX_RATE);
  assert.notEqual(result.tax, goodsOnlyTax);
  assert.ok(result.tax > goodsOnlyTax);
});

test("the discounted subtotal decides free shipping, not the gross subtotal", () => {
  // The regression that matters: a cart whose gross subtotal clears the
  // threshold but whose discounted subtotal does not must still pay shipping.
  // Charging nothing there gives away shipping on every discounted order.
  const item = bySku("USB-C-C-1M");
  const unit = cents(item.price); // 699

  for (let quantity = 1; quantity <= 12; quantity += 1) {
    const result = price({ [item.id]: quantity }, items);
    const discountedSub = result.sub - result.disc;
    const expected = discountedSub < FREE_SHIP ? FLAT_SHIP : 0;
    assert.equal(
      result.ship,
      expected,
      `qty ${quantity}: gross ${unit * quantity}, discounted ${discountedSub}`,
    );
  }
});

test("free shipping starts exactly at the threshold, not one cent above", () => {
  const cheap = items.reduce((a, b) => (a.price <= b.price ? a : b));
  // Find the first quantity whose discounted subtotal reaches the threshold.
  let quantity = 1;
  let result = price({ [cheap.id]: quantity }, items);
  while (result.sub - result.disc < FREE_SHIP && quantity < 500) {
    quantity += 1;
    result = price({ [cheap.id]: quantity }, items);
  }
  assert.ok(result.sub - result.disc >= FREE_SHIP, "threshold must be reachable");
  assert.equal(result.ship, 0, "at or above the threshold shipping is free");

  const below = price({ [cheap.id]: quantity - 1 }, items);
  assert.equal(below.ship, FLAT_SHIP, "one step below still pays shipping");
});

test("every total is a whole number of cents", () => {
  const [a, b, c] = items;
  for (const cart of [
    { [a.id]: 1 },
    { [a.id]: 3, [b.id]: 2 },
    { [a.id]: 7, [b.id]: 1, [c.id]: 4 },
  ]) {
    const result = price(cart, items);
    for (const field of ["sub", "disc", "ship", "tax", "tot"]) {
      assert.ok(
        Number.isInteger(result[field]),
        `${field} = ${result[field]} is not an integer`,
      );
    }
    assert.equal(result.tot, result.sub - result.disc + result.ship + result.tax);
  }
});

test("unknown ids and non-positive quantities are dropped, not priced", () => {
  const item = bySku("USB-C-C-1M");
  const result = price(
    { [item.id]: 2, "sku_does_not_exist": 5, [items[1].id]: 0, [items[2].id]: -3 },
    items,
  );
  assert.equal(result.lines.length, 1);
  assert.equal(result.qty, 2);
  assert.equal(result.sub, cents(item.price) * 2);
});

test("side-store.html still declares the constants this module prices with", () => {
  const html = readFileSync(join(ROOT, "side-store.html"), "utf8");
  assert.deepEqual(assertPageConstantsMatch(html), []);
});
