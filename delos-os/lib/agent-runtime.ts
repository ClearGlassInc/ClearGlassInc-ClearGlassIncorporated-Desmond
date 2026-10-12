import type { AgentDecision, SimulationEvent, WorldMetrics } from "./model";

/**
 * Provider contract for persona reasoning. Production model adapters should
 * implement the same output contract and remain behind a server-side policy gate.
 * This MVP intentionally uses deterministic synthetic rules and has no LLM key.
 */
export type PersonaReasoningContext = {
  simHour: number;
  event: SimulationEvent;
  metrics: WorldMetrics;
};

export interface PersonaReasoningProvider {
  readonly name: string;
  propose(context: PersonaReasoningContext): AgentDecision[];
}

export class SyntheticRulesProvider implements PersonaReasoningProvider {
  readonly name = "synthetic-rules-v1";

  propose(context: PersonaReasoningContext): AgentDecision[] {
    const event = context.event;
    const proposals: Omit<AgentDecision, "id" | "simHour" | "sourceEventId" | "recordedAt" | "toolName" | "inputSummary" | "outputSummary">[] = [
      {
        personaId: "security-analyst",
        intent: "Correlate evidence and preserve telemetry",
        chosenAction: "Record a synthetic evidence bundle and validate incident scope",
        rationale: "Keep observed signals separate from assumptions; no live accounts or logs are queried.",
        riskScore: Math.min(58, event.riskScore),
        approvalStatus: "not-required",
        externalSideEffect: false
      },
      {
        personaId: "incident-commander",
        intent: "Establish accountable incident priorities",
        chosenAction: "Assign a decision owner and compare containment with recovery options",
        rationale: "A coordinated response should preserve reversibility and state which evidence is still missing.",
        riskScore: event.riskScore,
        approvalStatus: event.riskScore >= 60 ? "pending" : "not-required",
        externalSideEffect: false
      },
      {
        personaId: "response-agent",
        intent: "Prepare a bounded defensive playbook proposal",
        chosenAction: event.riskScore >= 60
          ? "Queue containment recommendation for operator approval"
          : "Prepare a reversible synthetic checklist step",
        rationale: "The response agent can recommend and record simulated work only; it has no executable tools.",
        riskScore: event.riskScore,
        approvalStatus: event.riskScore >= 60 ? "pending" : "not-required",
        externalSideEffect: false
      }
    ];

    if (event.category === "intelligence" || event.category === "governance") {
      proposals.push({
        personaId: "communications-director",
        intent: "Separate verified facts from narrative pressure",
        chosenAction: "Draft an internal fact-checked update and hold publication",
        rationale: "No external message is sent; uncertainty and approval requirements remain explicit.",
        riskScore: 32,
        approvalStatus: "not-required",
        externalSideEffect: false
      });
    }

    if (event.title.toLowerCase().includes("supplier") || event.category === "incident") {
      proposals.push({
        personaId: "finance-officer",
        intent: "Estimate synthetic business impact",
        chosenAction: "Compare supplier downtime and contingency capacity scenarios",
        rationale: "Financial values are scenario estimates only and do not touch a real ledger or payment rail.",
        riskScore: 34,
        approvalStatus: "not-required",
        externalSideEffect: false
      });
    }

    if (event.category === "governance" || event.category === "decision") {
      proposals.push({
        personaId: "board-advisor",
        intent: "Challenge assumptions and request provenance",
        chosenAction: "Request an evidence-backed impact summary with named decision owners",
        rationale: "Oversight is advisory and cannot override the operator or grant tool permission.",
        riskScore: 24,
        approvalStatus: "not-required",
        externalSideEffect: false
      });
    }

    return proposals.map((proposal, index) => ({
      ...proposal,
      id: event.id + "-" + proposal.personaId + "-" + index,
      recordedAt: new Date().toISOString(),
      simHour: context.simHour,
      sourceEventId: event.id,
      toolName: null,
      inputSummary: JSON.stringify({
        sourceEventId: event.id,
        eventCategory: event.category,
        metrics: context.metrics
      }),
      outputSummary: proposal.chosenAction
    }));
  }
}
