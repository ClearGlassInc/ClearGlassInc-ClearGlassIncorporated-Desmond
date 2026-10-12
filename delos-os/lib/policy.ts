export type OperationClass =
  | "read-only"
  | "reversible-in-world"
  | "external-communication"
  | "financial-action"
  | "payment"
  | "production-deployment"
  | "data-export"
  | "destructive"
  | "security-sensitive"
  | "connector-scope-change";

export type PolicyOutcome = "allow" | "require-approval" | "deny";

export type PolicyInput = {
  riskScore: number;
  operationClass: OperationClass;
  emergencyStop?: boolean;
  connectorAuthorized?: boolean;
  approvalGranted?: boolean;
};

export type PolicyResult = {
  outcome: PolicyOutcome;
  code: string;
  reason: string;
};

const EXTERNAL_ACTIONS = new Set<OperationClass>([
  "external-communication",
  "financial-action",
  "payment",
  "production-deployment",
  "data-export",
  "destructive",
  "security-sensitive",
  "connector-scope-change"
]);

/**
 * Pure policy-decision function. It never executes operations.
 * Production callers must apply this decision in a server-side transaction
 * and independently validate actor, tenant, approval digest, and state version.
 */
export function evaluateOperation(input: PolicyInput): PolicyResult {
  if (!Number.isFinite(input.riskScore) || input.riskScore < 0 || input.riskScore > 100) {
    return {
      outcome: "deny",
      code: "INVALID_RISK_SCORE",
      reason: "Risk score must be a finite number between 0 and 100."
    };
  }

  if (input.emergencyStop) {
    return {
      outcome: "deny",
      code: "EMERGENCY_STOP_ACTIVE",
      reason: "Emergency stop freezes all operation proposals and state transitions."
    };
  }

  if (EXTERNAL_ACTIONS.has(input.operationClass) && !input.connectorAuthorized) {
    return {
      outcome: "deny",
      code: "CONNECTOR_NOT_AUTHORIZED",
      reason: "External operation is denied because no explicitly authorized connector is available."
    };
  }

  const mandatoryHumanReview = EXTERNAL_ACTIONS.has(input.operationClass) || input.riskScore >= 60;
  if (mandatoryHumanReview && !input.approvalGranted) {
    return {
      outcome: "require-approval",
      code: EXTERNAL_ACTIONS.has(input.operationClass) ? "EXTERNAL_ACTION_APPROVAL_REQUIRED" : "HIGH_RISK_APPROVAL_REQUIRED",
      reason: "An authorized human must approve this exact proposal before any state-changing operation can be applied."
    };
  }

  return {
    outcome: "allow",
    code: "POLICY_ALLOWED",
    reason: "The proposal satisfies this policy function's risk and connector checks. This result does not execute it."
  };
}
