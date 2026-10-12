import test from "node:test";
import assert from "node:assert/strict";
import { evaluateOperation } from "../lib/policy";

test("risk threshold is fail-closed at 60 and remains permissive below threshold", () => {
  assert.equal(evaluateOperation({ riskScore: 59, operationClass: "reversible-in-world" }).outcome, "allow");
  const highRisk = evaluateOperation({ riskScore: 60, operationClass: "reversible-in-world" });
  assert.equal(highRisk.outcome, "require-approval");
  assert.equal(highRisk.code, "HIGH_RISK_APPROVAL_REQUIRED");
});

test("external operation is denied when there is no explicitly authorized connector", () => {
  const result = evaluateOperation({ riskScore: 10, operationClass: "external-communication" });
  assert.equal(result.outcome, "deny");
  assert.equal(result.code, "CONNECTOR_NOT_AUTHORIZED");
});

test("connector authorization does not replace explicit human approval", () => {
  const result = evaluateOperation({
    riskScore: 10,
    operationClass: "payment",
    connectorAuthorized: true
  });
  assert.equal(result.outcome, "require-approval");
  assert.equal(result.code, "EXTERNAL_ACTION_APPROVAL_REQUIRED");
});

test("approved, explicitly authorized external proposal passes decision gate without execution", () => {
  const result = evaluateOperation({
    riskScore: 99,
    operationClass: "security-sensitive",
    connectorAuthorized: true,
    approvalGranted: true
  });
  assert.equal(result.outcome, "allow");
  assert.match(result.reason, /does not execute/i);
});

test("emergency stop overrides approvals and connector grants", () => {
  const result = evaluateOperation({
    riskScore: 0,
    operationClass: "reversible-in-world",
    emergencyStop: true,
    approvalGranted: true,
    connectorAuthorized: true
  });
  assert.equal(result.outcome, "deny");
  assert.equal(result.code, "EMERGENCY_STOP_ACTIVE");
});

test("invalid risk scores are denied", () => {
  assert.equal(evaluateOperation({ riskScore: 101, operationClass: "read-only" }).outcome, "deny");
  assert.equal(evaluateOperation({ riskScore: Number.NaN, operationClass: "read-only" }).outcome, "deny");
});
