// Skeleton definition for a rule derived from an incident. Every value the
// analyst must decide is a TODO placeholder, and the schema refuses TODOs,
// so nothing here can be activated without being filled in.

export function draftFromIncident(incident: { recordId: string; title: string }, evidenceIds: string[]): unknown {
  const key = `R-${incident.recordId.toUpperCase().replace(/[^A-Z0-9-]/g, "-")}`.slice(0, 40);
  const cite = { evidenceIds: evidenceIds.slice(0, 1), incidentIds: [incident.recordId], assumption: null };
  return {
    schemaVersion: 1,
    ruleKey: key,
    name: `Derived from ${incident.recordId}`,
    description: "TODO: describe what the rule flags and what it cannot see.",
    illustrative: false,
    disclaimer: null,
    supportingIncidentIds: [incident.recordId],
    supportingEvidenceIds: evidenceIds,
    requiredFields: ["vendorRecordId", "occurredAt"],
    entityMatching: "explicit_vendor_record_id",
    thresholds: {
      windowDays: {
        value: 0,
        unit: "days",
        rationale: "TODO: set the value and state its documented basis, or label it an analyst assumption.",
        basis: "ANALYST_ASSUMPTION",
        evidenceIds: [],
      },
    },
    pattern: {
      kind: "sequence_within_window",
      groupBy: "vendorRecordId",
      first: { recordType: "BANK_DETAIL_CHANGE", description: "TODO: first documented event", support: cite },
      then: { recordType: "PAYMENT", description: "TODO: following documented event", support: cite },
      window: { days: { threshold: "windowDays" }, description: "TODO: why the window matters", support: { evidenceIds: [], incidentIds: [], assumption: "TODO: state the assumption or cite evidence" } },
    },
    missingDataBehavior: "INSUFFICIENT_DATA",
    benignExplanations: ["TODO: known legitimate explanations"],
    falsePositiveConsiderations: ["TODO: when this fires on legitimate activity"],
    reviewPriority: "MEDIUM",
  };
}
