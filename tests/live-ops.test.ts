import test from "node:test";
import assert from "node:assert/strict";
import { boundsFor, cleanText, distanceNm, inBounds } from "../lib/live-ops/types";

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
