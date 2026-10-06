import assert from "node:assert/strict";
import test from "node:test";

process.env.CLEARGLASS_OPERATIONS_ENABLED = "true";
process.env.CLEARGLASS_OPERATIONS_MODE = "mock";

import { canDeleteEvidence, getOperationsStore, sha256Hex, syntheticPrincipal } from "../lib/operations/store";
import { operationsConfig } from "../lib/operations/features";

test("operations default feature flags keep sensitive modules off", () => {
  assert.equal(operationsConfig.features.voice, false);
  assert.equal(operationsConfig.features.dispatch, false);
  assert.equal(operationsConfig.features.forensicAnalysis, false);
  assert.equal(operationsConfig.features.lpr, false);
  assert.equal(operationsConfig.features.biometricVerification, false);
});

test("SHA-256 is deterministic for identical evidence bytes", () => {
  const bytes = new TextEncoder().encode("synthetic evidence");
  assert.equal(
    sha256Hex(bytes),
    "48736e58b409ed0241c8d7bed9dc188a59e13002f48e7492850bec15b59147b6",
  );
});

test("tenant authorization denies cross-tenant incident access", () => {
  const store = getOperationsStore();
  const operator = syntheticPrincipal();
  const incident = store.createIncident(operator, {
    title: "tenant boundary",
    category: "test",
    priority: "low",
  });
  const foreign = { ...syntheticPrincipal("foreign"), tenantId: "other-tenant" };
  assert.throws(() => store.getIncident(foreign, incident.id), /forbidden|tenant isolation/);
});

test("invalid incident transitions are rejected server-side", () => {
  const store = getOperationsStore();
  const operator = syntheticPrincipal();
  const incident = store.createIncident(operator, {
    title: "transition boundary",
    category: "test",
    priority: "low",
  });
  assert.throws(() => store.updateStatus(operator, incident.id, "closed"), /invalid incident transition/);
});

test("core vertical slice completes with quarantine, evidence version, verified hash and audit trail", async () => {
  const result = await getOperationsStore().runSyntheticVerticalSlice();
  assert.equal(result.synthetic, true);
  assert.equal(result.verification.matches, true);
  assert.equal(result.evidence.status, "available");
  assert.equal(result.evidence.sha256, result.verification.computedSha256);
  assert.equal(result.evidence.version, 1);
  assert.equal(result.evidence.currentVersionId, result.evidenceVersions[0]?.id);
  assert.equal(result.evidenceVersions[0]?.original, true);
  assert.equal(result.incident.status, "in_review");
  assert.ok(result.assignment.assignee);
  assert.ok(result.audit.some((e) => e.action === "incident.created"));
  assert.ok(result.audit.some((e) => e.action === "evidence.ingested"));
  assert.ok(result.audit.some((e) => e.action === "evidence.scan_completed"));
  assert.ok(result.audit.some((e) => e.action === "evidence.verified"));
  assert.ok(result.audit.some((e) => e.action === "incident.status_changed"));
});

test("legal hold prevents evidence deletion", () => {
  const evidence = {
    id: "evidence-1",
    tenantId: "clearglass-demo-tenant",
    incidentId: "incident-1",
    filename: "synthetic.txt",
    contentType: "text/plain",
    sizeBytes: 10,
    sha256: "0".repeat(64),
    storageKey: "mock://evidence/evidence-1/original",
    status: "available" as const,
    createdBy: "operator-demo",
    createdAt: "2020-01-01T00:00:00.000Z",
    version: 1,
    currentVersionId: "version-1",
  };
  const hold = {
    id: "hold-1",
    tenantId: evidence.tenantId,
    reason: "synthetic test",
    placedBy: "reviewer-demo",
    placedAt: "2020-01-01T00:00:00.000Z",
    active: true,
  };
  const policy = {
    id: "retention-1",
    tenantId: evidence.tenantId,
    name: "synthetic",
    retentionDays: 1,
    createdAt: "2020-01-01T00:00:00.000Z",
  };
  assert.equal(canDeleteEvidence(evidence, hold, new Date("2026-01-01T00:00:00.000Z"), policy), false);
  assert.equal(canDeleteEvidence(evidence, undefined, new Date("2026-01-01T00:00:00.000Z"), policy), true);
});

test("mock/live separation is explicit", () => {
  assert.equal(operationsConfig.mode, "mock");
  assert.equal(operationsConfig.features.evidence, true);
});
