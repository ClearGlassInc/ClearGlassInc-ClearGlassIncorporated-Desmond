import test from "node:test";
import assert from "node:assert/strict";
import { boundsFor, cleanText, distanceNm, inBounds, isValidCoordinates, parseFiniteNumber } from "../lib/live-ops/types";
import { allowProviderRequest } from "../lib/live-ops/cache";
import { isMilitaryAircraft, normalizeOnGround } from "../lib/live-ops/adsbexchange";

test("Chualar 40 NM bounds contain the center and stay finite", () => {
  const center = { lat: 36.57, lon: -121.525 };
  const bounds = boundsFor(center, 40);
  assert.ok(inBounds(center.lat, center.lon, bounds));
  assert.ok(bounds.lamin < center.lat && bounds.lamax > center.lat);
  assert.ok(bounds.lomin < center.lon && bounds.lomax > center.lon);
  assert.ok(Object.values(bounds).every(Number.isFinite));
});

test("great-circle distance uses nautical miles", () => {
  assert.equal(distanceNm({ lat: 36.57, lon: -121.525 }, 36.57, -121.525), 0);
  assert.ok(distanceNm({ lat: 36.57, lon: -121.525 }, 37.57, -121.525) > 59);
  assert.ok(distanceNm({ lat: 36.57, lon: -121.525 }, 37.57, -121.525) < 61);
});

test("bounds rejects non-finite and outside coordinates", () => {
  const bounds = boundsFor({ lat: 36.57, lon: -121.525 }, 40);
  assert.equal(inBounds(Number.NaN, -121.5, bounds), false);
  assert.equal(inBounds(0, 0, bounds), false);
});

test("external text strips control characters and caps length", () => {
  assert.equal(cleanText("  flight\u0000\n id  "), "flight id");
  assert.equal(cleanText("abcdef", 3), "abc");
  assert.equal(cleanText("  "), null);
});

test("coordinate sanitizers reject absent and out-of-range values", () => {
  assert.equal(parseFiniteNumber(null), null);
  assert.equal(parseFiniteNumber(""), null);
  assert.equal(parseFiniteNumber("36.57"), 36.57);
  assert.equal(isValidCoordinates(36.57, -121.525), true);
  assert.equal(isValidCoordinates(91, -121.525), false);
  assert.equal(isValidCoordinates(36.57, 181), false);
});

test("ADS-B military classification requires the provider military bit or explicit flag", () => {
  assert.equal(isMilitaryAircraft({ dbFlags: 1 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 3 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 2 }), false);
  assert.equal(isMilitaryAircraft({ mil: true }), true);
  assert.equal(isMilitaryAircraft({ flight: "NAVY1" }), false);
});

test("ADS-B on-ground normalization preserves missing values as unknown", () => {
  assert.equal(normalizeOnGround("ground"), true);
  assert.equal(normalizeOnGround(12000), false);
  assert.equal(normalizeOnGround(null), null);
  assert.equal(normalizeOnGround(undefined), null);
});

test("provider request budgets are isolated per provider", () => {
  const provider = "test-provider-" + Date.now();
  assert.equal(allowProviderRequest(provider, 1, 60_000), true);
  assert.equal(allowProviderRequest(provider, 1, 60_000), false);
  assert.equal(allowProviderRequest(provider + "-other", 1, 60_000), true);
});
