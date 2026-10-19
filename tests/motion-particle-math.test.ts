import assert from "node:assert/strict";
import test from "node:test";
import { particleRadiusCssPixels } from "../components/motion/particle-math";

test("particle radius remains stable in CSS pixels across supported DPR scales", () => {
  const cssHeight = 800;
  const expected = Math.max(1, cssHeight * 0.002);

  for (const dpr of [1, 1.25, 1.5, 2]) {
    const backingHeight = Math.round(cssHeight * dpr);
    const radius = particleRadiusCssPixels(backingHeight, dpr);
    assert.ok(
      Math.abs(radius - expected) < 0.01,
      `expected ${radius}px CSS radius near ${expected}px at DPR ${dpr}`,
    );
  }
});

test("invalid DPR values fall back to a finite 1x scale", () => {
  for (const dpr of [0, Number.NaN, Number.POSITIVE_INFINITY, -2]) {
    assert.equal(particleRadiusCssPixels(800, dpr), 1.6);
  }
});
