import test from "node:test";
import assert from "node:assert/strict";
import { isMilitaryAircraft } from "../lib/live-ops/adsbexchange";

test("ADS-B Exchange military dbFlags bit identifies military aircraft", () => {
  assert.equal(isMilitaryAircraft({ dbFlags: 1 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 3 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 0 }), false);
  assert.equal(isMilitaryAircraft({ dbFlags: 2 }), false);
});

test("military dbFlags accepts numeric strings and explicit legacy flag", () => {
  assert.equal(isMilitaryAircraft({ dbFlags: "1" }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: "0" }), false);
  assert.equal(isMilitaryAircraft({ mil: true }), true);
  assert.equal(isMilitaryAircraft({}), false);
});
