import type {
  ApprovalRequest,
  AuditEvent,
  InjectedEventKind,
  SimulationCheckpoint,
  SimulationEvent,
  WorldMetrics,
  WorldSnapshot,
  WorldState
} from "./model";
import { SyntheticRulesProvider } from "./agent-runtime";
import { evaluateOperation } from "./policy";
import { PERSONAS, SCENARIO } from "./scenario";

const agentProvider = new SyntheticRulesProvider();

function requiresHumanApproval(riskScore: number): boolean {
  return evaluateOperation({ riskScore, operationClass: "reversible-in-world" }).outcome === "require-approval";
}

const INITIAL_TIME = "2026-10-12T00:00:00.000Z";
const now = (): string => new Date().toISOString();
const id = (prefix: string): string =>
  prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
const clamp = (n: number, min = 0, max = 100): number => Math.min(max, Math.max(min, Math.round(n)));

export function scoreRisk(input: {
  severity: number;
  exposure: number;
  uncertainty: number;
  blastRadius: number;
}): number {
  const values = [input.severity, input.exposure, input.uncertainty, input.blastRadius];
  if (values.some((value) => !Number.isFinite(value) || value < 0 || value > 100)) {
    throw new Error("Risk factors must be finite numbers from 0 to 100.");
  }
  return clamp(
    input.severity * 0.45 +
      input.exposure * 0.25 +
      input.uncertainty * 0.15 +
      input.blastRadius * 0.15
  );
}

function appendAudit(
  state: WorldState,
  actor: string,
  action: string,
  detail: string,
  riskScore = 0,
  approvalStatus: AuditEvent["approvalStatus"] = "not-required"
): AuditEvent[] {
  return [
    ...state.audit,
    {
      id: id("audit"),
      recordedAt: now(),
      simHour: state.simHour,
      actor,
      action,
      detail,
      riskScore: clamp(riskScore),
      approvalStatus
    }
  ];
}

function makeEvent(
  simHour: number,
  category: SimulationEvent["category"],
  title: string,
  detail: string,
  severity: number,
  source: string,
  exposure = severity,
  uncertainty = 30,
  blastRadius = severity
): SimulationEvent {
  return {
    id: id("evt"),
    recordedAt: now(),
    simHour,
    category,
    title,
    detail,
    severity: clamp(severity),
    riskScore: scoreRisk({ severity, exposure, uncertainty, blastRadius }),
    source
  };
}

export function createInitialState(): WorldState {
  const initialEvent: SimulationEvent = {
    ...makeEvent(
    0,
    "milestone",
    "Synthetic environment verified",
    "Scenario fixtures loaded. Live connectors, external network access, and production tools are disabled.",
    8,
    "World Forge",
    0,
    5,
    0
    ),
    id: "evt-glassfall-start",
    recordedAt: INITIAL_TIME
  };
  const approvals: ApprovalRequest[] = [
    {
      id: "approval-supplier-isolation",
      requestedAt: INITIAL_TIME,
      action: "Isolate the simulated supplier integration",
      rationale: "Containment may reduce blast radius but risks delaying recovery. Operator decision required.",
      riskScore: 76,
      status: "pending"
    },
    {
      id: "approval-comms-draft",
      requestedAt: INITIAL_TIME,
      action: "Approve a draft executive incident statement",
      rationale: "Messaging must be checked against verified facts before release. This draft stays in the simulation.",
      riskScore: 82,
      status: "pending"
    }
  ];
  const state: WorldState = {
    runId: "run-glassfall-baseline",
    scenarioId: SCENARIO.id,
    scenarioName: SCENARIO.name,
    branchName: "GLASSFALL-BASELINE",
    status: "ready",
    safetyStop: false,
    simHour: 0,
    threatLevel: 28,
    supplierCapacity: 100,
    reputation: 94,
    liquidity: 88,
    integrity: 100,
    missionProgress: 0,
    decisionCount: 0,
    agentDecisions: [],
    lastUpdatedAt: INITIAL_TIME,
    agents: PERSONAS.map((persona, index) => ({
      personaId: persona.id,
      status: index === 4 ? "standby" : "monitoring",
      lastAction: index === 4 ? "Awaiting scripted inject" : "Scenario briefing loaded",
      confidence: index === 4 ? 91 : 82 - (index % 3) * 4,
      load: 18 + ((index * 9) % 35)
    })),
    events: [initialEvent],
    approvals,
    audit: [],
    snapshots: [],
    checkpoints: []
  };
  state.audit = [
    {
      id: "audit-world-initialized",
      recordedAt: INITIAL_TIME,
      simHour: 0,
      actor: "system",
      action: "world.initialized",
      detail: "Operation Glassfall created with synthetic fixtures only.",
      riskScore: 0,
      approvalStatus: "not-required"
    },
    ...approvals.map((approval, index): AuditEvent => ({
      id: "audit-approval-request-" + String(index + 1),
      recordedAt: INITIAL_TIME,
      simHour: 0,
      actor: "policy-engine",
      action: "approval.requested",
      detail: approval.action,
      riskScore: clamp(approval.riskScore),
      approvalStatus: "pending"
    }))
  ];
  return state;
}

export function startRun(state: WorldState): WorldState {
  if (state.safetyStop || state.status !== "ready") return state;
  const next = { ...state, status: "running" as const, lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "simulation.started", "Operator started the synthetic scenario.");
  return next;
}

export function pauseRun(state: WorldState): WorldState {
  if (state.safetyStop || state.status !== "running") return state;
  const next = { ...state, status: "paused" as const, lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "simulation.paused", "Operator paused simulated time.");
  return next;
}

export function resumeRun(state: WorldState): WorldState {
  if (state.safetyStop || state.status !== "paused") return state;
  const next = { ...state, status: "running" as const, lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "simulation.resumed", "Operator resumed simulated time.");
  return next;
}

type InjectPreset = {
  category: SimulationEvent["category"];
  title: string;
  detail: string;
  severity: number;
  exposure: number;
  uncertainty: number;
  blastRadius: number;
};

const INJECTS: Record<InjectedEventKind, InjectPreset> = {
  "supplier-disruption": {
    category: "incident",
    title: "Supplier delivery interruption",
    detail: "Synthetic supplier API reports a delayed shipment and incomplete continuity evidence.",
    severity: 78, exposure: 72, uncertainty: 50, blastRadius: 68
  },
  "rumor-escalation": {
    category: "intelligence",
    title: "Unverified public claim gains traction",
    detail: "A simulated stakeholder channel repeats an unverified claim; communications must not present it as fact.",
    severity: 68, exposure: 62, uncertainty: 82, blastRadius: 61
  },
  "restore-verified": {
    category: "milestone",
    title: "Recovery checkpoint integrity verified",
    detail: "Synthetic restore evidence matches the expected checkpoint digest.",
    severity: 18, exposure: 12, uncertainty: 8, blastRadius: 14
  },
  "board-briefing": {
    category: "decision",
    title: "Board requests an evidence-backed briefing",
    detail: "The simulated board asks for confirmed impact, remaining uncertainty, and the next decision owner.",
    severity: 38, exposure: 34, uncertainty: 28, blastRadius: 34
  },
  "identity-anomaly": {
    category: "incident",
    title: "Identity telemetry anomaly",
    detail: "Synthetic identity logs indicate unusual authentication patterns; no live accounts are queried.",
    severity: 84, exposure: 74, uncertainty: 42, blastRadius: 78
  },
  "containment-progress": {
    category: "milestone",
    title: "Containment evidence improves",
    detail: "A scripted defensive check indicates reduced simulated propagation and preserves evidence.",
    severity: 22, exposure: 24, uncertainty: 16, blastRadius: 20
  }
};

export function injectEvent(state: WorldState, kind: InjectedEventKind): WorldState {
  if (state.safetyStop || ["terminated", "stopped", "completed"].includes(state.status)) return state;
  const preset = INJECTS[kind];
  if (!preset) throw new Error("Unsupported synthetic event.");
  const event = makeEvent(
    state.simHour,
    preset.category,
    preset.title,
    preset.detail,
    preset.severity,
    "Operator-injected synthetic event",
    preset.exposure,
    preset.uncertainty,
    preset.blastRadius
  );
  const proposals = agentProvider.propose({
    runId: state.runId,
    simHour: state.simHour,
    event,
    metrics: metrics(state)
  });
  let next: WorldState = {
    ...state,
    agentDecisions: [...state.agentDecisions, ...proposals],
    events: [...state.events, event],
    threatLevel: clamp(state.threatLevel + (kind === "containment-progress" || kind === "restore-verified" ? -6 : 7)),
    supplierCapacity: clamp(state.supplierCapacity + (kind === "supplier-disruption" ? -18 : kind === "containment-progress" ? 4 : 0)),
    reputation: clamp(state.reputation + (kind === "rumor-escalation" ? -9 : kind === "board-briefing" ? -1 : 0)),
    integrity: clamp(state.integrity + (kind === "restore-verified" ? 2 : kind === "identity-anomaly" ? -3 : 0)),
    decisionCount: state.decisionCount + proposals.length,
    lastUpdatedAt: now()
  };
  next.audit = appendAudit(next, "operator", "event.injected", "Synthetic event injected: " + event.title, event.riskScore);
  next.audit = appendAudit(
    next,
    "synthetic-agent-runtime",
    "agent.proposals.generated",
    proposals.length + " bounded persona proposal(s) generated by " + agentProvider.name + "; no tool execution occurred."
  );
  if (requiresHumanApproval(event.riskScore)) {
    const approval: ApprovalRequest = {
      id: id("approval"),
      requestedAt: now(),
      action: "Review synthetic response to: " + event.title,
      rationale: "High-risk scenario changes require an explicit operator decision before the simulation marks the proposed response as accepted.",
      riskScore: event.riskScore,
      relatedEventId: event.id,
      status: "pending"
    };
    next.approvals = [...next.approvals, approval];
    next.audit = appendAudit(next, "policy-engine", "approval.requested", approval.action, approval.riskScore, "pending");
  }
  next.agents = next.agents.map((agent, index) => ({
    ...agent,
    status: requiresHumanApproval(event.riskScore) && index === 6 ? "awaiting-approval" : event.riskScore >= 60 && index === 1 ? "active" : agent.status,
    lastAction: index === 1 ? "Correlated " + event.title.toLowerCase() : agent.lastAction,
    load: clamp(agent.load + (requiresHumanApproval(event.riskScore) ? 9 : 3))
  }));
  return next;
}

const SCHEDULE: Record<number, InjectPreset> = {
  1: {
    category: "intelligence",
    title: "Abnormal authentication sequence detected",
    detail: "Synthetic identity telemetry contains a cluster of unusual sign-ins. Evidence preservation is recommended.",
    severity: 61, exposure: 66, uncertainty: 37, blastRadius: 55
  },
  6: {
    category: "incident",
    title: "Critical supplier service unavailable",
    detail: "The synthetic logistics provider reports a disruption during the enterprise cyber incident.",
    severity: 79, exposure: 76, uncertainty: 48, blastRadius: 72
  },
  14: {
    category: "intelligence",
    title: "Public narrative diverges from verified facts",
    detail: "A simulated rumor conflicts with the incident record. Communications must use approved facts only.",
    severity: 68, exposure: 62, uncertainty: 76, blastRadius: 61
  },
  24: {
    category: "milestone",
    title: "Isolated recovery checkpoint passes",
    detail: "The synthetic recovery rehearsal passes integrity checks; no production backup was touched.",
    severity: 19, exposure: 10, uncertainty: 8, blastRadius: 13
  },
  36: {
    category: "decision",
    title: "Alternative supplier path validated",
    detail: "A simulated contingency supplier meets the scenario's minimum capacity and evidence requirements.",
    severity: 34, exposure: 26, uncertainty: 18, blastRadius: 25
  },
  48: {
    category: "governance",
    title: "Board asks for decision provenance",
    detail: "The oversight persona requests a traceable rationale, known unknowns, and accountable decision owners.",
    severity: 35, exposure: 22, uncertainty: 18, blastRadius: 24
  },
  60: {
    category: "milestone",
    title: "Containment evidence reaches review threshold",
    detail: "Synthetic defensive checks indicate reduced spread and sufficient evidence for a recovery decision.",
    severity: 27, exposure: 18, uncertainty: 16, blastRadius: 20
  },
  72: {
    category: "milestone",
    title: "72-hour simulation window complete",
    detail: "Scenario clock completed. Review open approvals and export the after-action report.",
    severity: 12, exposure: 8, uncertainty: 5, blastRadius: 9
  }
};

export function advanceOneHour(state: WorldState): WorldState {
  if (state.safetyStop || state.status !== "running" || state.simHour >= SCENARIO.durationHours) return state;
  const nextHour = state.simHour + 1;
  const preset = SCHEDULE[nextHour];
  const next: WorldState = {
    ...state,
    simHour: nextHour,
    missionProgress: clamp((nextHour / SCENARIO.durationHours) * 100),
    threatLevel: clamp(state.threatLevel + (nextHour === 6 ? 11 : nextHour === 14 ? 7 : nextHour === 24 || nextHour === 60 ? -9 : 0)),
    supplierCapacity: clamp(state.supplierCapacity + (nextHour === 6 ? -22 : nextHour === 36 ? 24 : 0)),
    reputation: clamp(state.reputation + (nextHour === 14 ? -8 : nextHour === 48 ? 2 : 0)),
    integrity: clamp(state.integrity + (nextHour === 24 ? 2 : nextHour === 60 ? 1 : 0)),
    status: nextHour >= SCENARIO.durationHours ? "completed" : "running",
    lastUpdatedAt: now()
  };
  if (preset) {
    const event = makeEvent(
      nextHour,
      preset.category,
      preset.title,
      preset.detail,
      preset.severity,
      "Scenario Director",
      preset.exposure,
      preset.uncertainty,
      preset.blastRadius
    );
    const proposals = agentProvider.propose({
      runId: next.runId,
      simHour: nextHour,
      event,
      metrics: metrics(next)
    });
    next.agentDecisions = [...state.agentDecisions, ...proposals];
    next.decisionCount = state.decisionCount + proposals.length;
    next.events = [...state.events, event];
    next.audit = appendAudit(
      next,
      "synthetic-agent-runtime",
      "agent.proposals.generated",
      proposals.length + " bounded persona proposal(s) generated by " + agentProvider.name + "; no tool execution occurred."
    );
    next.agents = next.agents.map((agent) => ({
      ...agent,
      status: requiresHumanApproval(event.riskScore) && agent.personaId === "response-agent"
        ? "awaiting-approval"
        : preset.severity >= 50 && agent.personaId === "security-analyst"
          ? "active"
          : agent.status,
      lastAction: agent.personaId === "incident-commander" ? "Reviewed T+" + String(nextHour).padStart(2, "0") + " scenario update" : agent.lastAction
    }));
    next.audit = appendAudit(
      next,
      "scenario-director",
      "scenario.event",
      event.title,
      event.riskScore,
      requiresHumanApproval(event.riskScore) ? "pending" : "not-required"
    );
    if (requiresHumanApproval(event.riskScore)) {
      const approval: ApprovalRequest = {
        id: id("approval"),
        requestedAt: now(),
        action: "Review response to: " + event.title,
        rationale: "Scenario director surfaced a high-impact inject. Operator approval applies only to this synthetic world.",
        riskScore: event.riskScore,
        relatedEventId: event.id,
        status: "pending"
      };
      next.approvals = [...state.approvals, approval];
      next.audit = appendAudit(next, "policy-engine", "approval.requested", approval.action, approval.riskScore, "pending");
    }
  }
  return next;
}

export function decideApproval(state: WorldState, approvalId: string, decision: "approved" | "rejected"): WorldState {
  if (state.safetyStop || ["terminated", "stopped"].includes(state.status)) return state;
  const target = state.approvals.find((approval) => approval.id === approvalId);
  if (!target || target.status !== "pending") return state;
  const decidedAt = now();
  const approvals = state.approvals.map((approval) =>
    approval.id === approvalId ? { ...approval, status: decision, approver: "Local demo operator", decidedAt } : approval
  );
  const next = {
    ...state,
    approvals,
    agentDecisions: state.agentDecisions.map((proposal) =>
      target.relatedEventId &&
      proposal.sourceEventId === target.relatedEventId &&
      proposal.approvalStatus === "pending"
        ? { ...proposal, approvalStatus: decision }
        : proposal
    ),
    lastUpdatedAt: decidedAt
  };
  next.audit = appendAudit(
    next,
    "operator",
    decision === "approved" ? "approval.accepted" : "approval.rejected",
    target.action + ". Simulated decision recorded; no real connector or external action was invoked.",
    target.riskScore,
    decision
  );
  if (decision === "approved") {
    next.decisionCount += 1;
    next.agents = next.agents.map((agent) => ({
      ...agent,
      status: agent.status === "awaiting-approval" ? "active" : agent.status,
      lastAction: agent.status === "awaiting-approval" ? "Approval recorded in simulation only" : agent.lastAction
    }));
  }
  return next;
}

function metrics(state: WorldState): WorldMetrics {
  return {
    threatLevel: state.threatLevel,
    supplierCapacity: state.supplierCapacity,
    reputation: state.reputation,
    liquidity: state.liquidity,
    integrity: state.integrity,
    missionProgress: state.missionProgress
  };
}

export function captureSnapshot(state: WorldState, label = "Manual checkpoint"): WorldState {
  const snapId = id("snap");
  const checkpoint: SimulationCheckpoint = {
    id: snapId,
    label,
    capturedAt: now(),
    simHour: state.simHour,
    status: state.status,
    branchName: state.branchName,
    ...metrics(state),
    events: state.events.map((event) => ({ ...event })),
    agentDecisions: state.agentDecisions.map((decision) => ({ ...decision })),
    approvals: state.approvals.map((approval) => ({ ...approval })),
    audit: state.audit.map((entry) => ({ ...entry })),
    agents: state.agents.map((agent) => ({ ...agent })),
    decisionCount: state.decisionCount
  };
  const snapshot: WorldSnapshot = {
    id: snapId,
    label,
    capturedAt: checkpoint.capturedAt,
    simHour: state.simHour,
    branchName: state.branchName,
    ...metrics(state),
    eventCount: state.events.length,
    auditCount: state.audit.length,
    stateDigest: [state.runId, state.simHour, state.threatLevel, state.supplierCapacity, state.reputation, state.integrity, state.events.length].join(":")
  };
  const next = { ...state, snapshots: [...state.snapshots, snapshot], checkpoints: [...state.checkpoints, checkpoint], lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "snapshot.created", label + " captured at T+" + String(state.simHour).padStart(2, "0") + ".");
  return next;
}

export function forkBranch(state: WorldState, branchName: string): WorldState {
  if (state.safetyStop || ["terminated", "stopped"].includes(state.status)) return state;
  const checkpointed = captureSnapshot(state, "Fork point for " + branchName);
  const next = {
    ...checkpointed,
    branchName,
    parentSnapshotId: checkpointed.snapshots[checkpointed.snapshots.length - 1]?.id,
    status: "paused" as const,
    lastUpdatedAt: now()
  };
  next.audit = appendAudit(next, "operator", "branch.forked", "Forked from the captured parent state into " + branchName + ".");
  return next;
}

export function restoreCheckpoint(state: WorldState, checkpointId: string): WorldState {
  if (state.safetyStop || ["terminated", "stopped"].includes(state.status)) return state;
  const checkpoint = state.checkpoints.find((item) => item.id === checkpointId);
  if (!checkpoint) throw new Error("Checkpoint not found.");
  const next: WorldState = {
    ...state,
    simHour: checkpoint.simHour,
    status: "paused",
    branchName: state.branchName,
    threatLevel: checkpoint.threatLevel,
    supplierCapacity: checkpoint.supplierCapacity,
    reputation: checkpoint.reputation,
    liquidity: checkpoint.liquidity,
    integrity: checkpoint.integrity,
    missionProgress: checkpoint.missionProgress,
    events: checkpoint.events.map((event) => ({ ...event })),
    agentDecisions: checkpoint.agentDecisions.map((decision) => ({ ...decision })),
    approvals: checkpoint.approvals.map((approval) => ({ ...approval })),
    agents: checkpoint.agents.map((agent) => ({ ...agent })),
    decisionCount: checkpoint.decisionCount,
    lastUpdatedAt: now()
  };
  next.audit = appendAudit(next, "operator", "checkpoint.restored", "Restored synthetic state from " + checkpoint.label + ". Previous audit entries are retained in checkpoints; this action is also recorded here.");
  return next;
}

export function emergencyStop(state: WorldState): WorldState {
  if (state.safetyStop) return state;
  const next: WorldState = { ...state, status: "stopped", safetyStop: true, lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "emergency.stop", "Global emergency stop: all simulation transitions frozen; current state preserved.");
  return next;
}

export function terminateRun(state: WorldState): WorldState {
  if (state.safetyStop || ["terminated", "stopped", "completed"].includes(state.status)) return state;
  const next: WorldState = { ...state, status: "terminated", lastUpdatedAt: now() };
  next.audit = appendAudit(next, "operator", "simulation.terminated", "Operator terminated the simulation; state retained for review.");
  return next;
}

export function afterActionReport(state: WorldState) {
  const highRiskEvents = state.events.filter((event) => requiresHumanApproval(event.riskScore));
  const pending = state.approvals.filter((approval) => approval.status === "pending");
  const completed = state.approvals.filter((approval) => approval.status === "approved");
  return {
    platform: "DELOS OS",
    scenario: state.scenarioName,
    scenarioId: state.scenarioId,
    branch: state.branchName,
    runId: state.runId,
    status: state.status,
    simulatedHours: state.simHour,
    executiveSummary:
      "Operation Glassfall reached T+" + String(state.simHour).padStart(2, "0") +
      " with threat level " + state.threatLevel + "/100, supplier capacity " + state.supplierCapacity +
      "%, and " + pending.length + " approval(s) still awaiting an operator decision. All data and actions in this report are synthetic.",
    keyDecisions: state.audit.filter((entry) => entry.action.startsWith("approval.") || entry.action.startsWith("branch.") || entry.action.startsWith("emergency.")),
    agentPerformance: state.agents.map((agent) => ({
      personaId: agent.personaId,
      status: agent.status,
      confidence: agent.confidence,
      load: agent.load,
      lastAction: agent.lastAction
    })),
    personaProposals: state.agentDecisions.map((decision) => ({ ...decision })),
    risksIdentified: highRiskEvents.map((event) => ({
      title: event.title,
      simHour: event.simHour,
      riskScore: event.riskScore,
      detail: event.detail
    })),
    missedOpportunities: pending.map((approval) => approval.action),
    recommendations: [
      "Resolve or explicitly defer every pending approval before closing the exercise.",
      "Compare the baseline and forked branch before selecting a response playbook.",
      "Preserve evidence and separate verified facts from scenario assumptions.",
      "Validate all production integrations, tenancy boundaries, and human-approval controls before any live pilot."
    ],
    kpis: {
      missionProgress: state.missionProgress,
      highRiskEventCount: highRiskEvents.length,
      approvalsRequested: state.approvals.length,
      approvalsAccepted: completed.length,
      approvalsPending: pending.length,
      decisionsRecorded: state.decisionCount,
      personaProposals: state.agentDecisions.length,
      auditEvents: state.audit.length,
      integrity: state.integrity,
      reputation: state.reputation,
      supplierCapacity: state.supplierCapacity
    },
    replayableTimeline: state.events.map((event) => ({
      simHour: event.simHour,
      title: event.title,
      detail: event.detail,
      category: event.category,
      riskScore: event.riskScore
    }))
  };
}

export function reportAsMarkdown(state: WorldState): string {
  const report = afterActionReport(state);
  const lines = [
    "# DELOS OS — Operation Glassfall After-Action Report",
    "",
    "Synthetic simulation report. No real systems or people were involved.",
    "",
    "## Executive summary",
    report.executiveSummary,
    "",
    "## KPIs",
    ...Object.entries(report.kpis).map(([key, value]) => "- " + key + ": " + String(value)),
    "",
    "## Risks identified",
    ...(report.risksIdentified.length
      ? report.risksIdentified.map((risk) => "- T+" + String(risk.simHour).padStart(2, "0") + " — " + risk.title + " (risk " + risk.riskScore + "/100): " + risk.detail)
      : ["- No events at or above the human-review threshold in the current state."]),
    "",
    "## Persona proposals (synthetic only)",
    ...(report.personaProposals.length
      ? report.personaProposals.map((proposal) => "- " + proposal.recordedAt + " T+" + String(proposal.simHour).padStart(2, "0") + " " + proposal.personaId + ": " + proposal.chosenAction + " (risk " + proposal.riskScore + "/100; tool " + (proposal.toolName ?? "none") + "; input " + proposal.inputSummary + "; output " + proposal.outputSummary + "; approval " + proposal.approvalStatus + "; external side effect: " + proposal.externalSideEffect + ")")
      : ["- No persona proposals recorded yet."]),
    "",
    "## Key decisions",
    ...(report.keyDecisions.length
      ? report.keyDecisions.map((entry) => "- " + entry.action + ": " + entry.detail)
      : ["- No approval or branch decision has been recorded."]),
    "",
    "## Recommended next actions",
    ...report.recommendations.map((item) => "- " + item),
    "",
    "## Timeline",
    ...report.replayableTimeline.map((event) => "- T+" + String(event.simHour).padStart(2, "0") + " [" + event.category + "] " + event.title + " — risk " + event.riskScore + "/100")
  ];
  return lines.join("\n");
}
