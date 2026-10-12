export type RunStatus = "ready" | "running" | "paused" | "completed" | "terminated" | "stopped";
export type AgentStatus = "standby" | "monitoring" | "active" | "awaiting-approval";
export type EventCategory = "intelligence" | "incident" | "decision" | "governance" | "milestone";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export type Persona = {
  id: string;
  name: string;
  role: string;
  goal: string;
  personality: string;
  expertise: string[];
  permissions: string[];
  knowledgeBoundary: string;
  riskLevel: number;
  memoryScope: string;
  approvalRequirements: string[];
};

export type AgentRecord = {
  personaId: string;
  status: AgentStatus;
  lastAction: string;
  confidence: number;
  load: number;
};

export type SimulationEvent = {
  id: string;
  recordedAt: string;
  simHour: number;
  category: EventCategory;
  title: string;
  detail: string;
  severity: number;
  riskScore: number;
  source: string;
};

export type ApprovalRequest = {
  id: string;
  requestedAt: string;
  action: string;
  rationale: string;
  riskScore: number;
  status: ApprovalStatus;
  approver?: string;
  decidedAt?: string;
};

export type AuditEvent = {
  id: string;
  recordedAt: string;
  simHour: number;
  actor: string;
  action: string;
  detail: string;
  riskScore: number;
  approvalStatus: "not-required" | "pending" | "approved" | "rejected";
};

export type WorldMetrics = {
  threatLevel: number;
  supplierCapacity: number;
  reputation: number;
  liquidity: number;
  integrity: number;
  missionProgress: number;
};

export type WorldSnapshot = WorldMetrics & {
  id: string;
  label: string;
  capturedAt: string;
  simHour: number;
  branchName: string;
  eventCount: number;
  auditCount: number;
  stateDigest: string;
};

export type SimulationCheckpoint = WorldMetrics & {
  id: string;
  label: string;
  capturedAt: string;
  simHour: number;
  status: RunStatus;
  branchName: string;
  events: SimulationEvent[];
  approvals: ApprovalRequest[];
  audit: AuditEvent[];
  agents: AgentRecord[];
  decisionCount: number;
};

export type WorldState = WorldMetrics & {
  runId: string;
  scenarioId: string;
  scenarioName: string;
  branchName: string;
  parentSnapshotId?: string;
  status: RunStatus;
  safetyStop: boolean;
  simHour: number;
  decisionCount: number;
  lastUpdatedAt: string;
  agents: AgentRecord[];
  events: SimulationEvent[];
  approvals: ApprovalRequest[];
  audit: AuditEvent[];
  snapshots: WorldSnapshot[];
  checkpoints: SimulationCheckpoint[];
};

export type InjectedEventKind =
  | "supplier-disruption"
  | "rumor-escalation"
  | "restore-verified"
  | "board-briefing"
  | "identity-anomaly"
  | "containment-progress";
