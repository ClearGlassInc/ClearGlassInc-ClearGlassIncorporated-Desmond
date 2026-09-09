import test from "node:test";
import assert from "node:assert/strict";
import { assessIntegrity } from "../lib/truth-fabric/schema";

const hash = "a".repeat(64);
const base = { caseId: "demo-001", claim: "demo claim", humanGateRequired: true };

test("dual independent channels produce a high integrity result", () => {
  const result = assessIntegrity({
    ...base,
    evidence: [
      { id: "a", source: "camera_a", capturedAt: "2026-09-08T21:00:00Z", sha256: hash, metadata: {}, independent: true },
      { id: "b", source: "camera_b", capturedAt: "2026-09-08T21:00:01Z", sha256: hash, metadata: {}, independent: true },
    ],
  });
  assert.equal(result.status, "verified");
  assert.equal(result.score, 100);
});

test("single-channel evidence remains under review", () => {
  const result = assessIntegrity({
    ...base,
    evidence: [{ id: "a", source: "camera_a", capturedAt: "2026-09-08T21:00:00Z", sha256: hash, metadata: {}, independent: false }],
  });
  assert.equal(result.status, "review");
  assert.ok(result.reasons.length >= 2);
});
