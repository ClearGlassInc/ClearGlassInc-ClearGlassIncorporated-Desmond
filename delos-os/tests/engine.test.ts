import test from "node:test";
import assert from "node:assert/strict";
import {
  advanceOneHour,
  captureSnapshot,
  createInitialState,
  decideApproval,
  emergencyStop,
  forkBranch,
  injectEvent,
  restoreCheckpoint,
  scoreRisk,
  startRun,
  terminateRun,
  reportAsMarkdown
} from "../lib/engine";

test("risk scoring is bounded and rejects out-of-range inputs", () => {
  assert.equal(scoreRisk({ severity: 100, exposure: 100, uncertainty: 100, blastRadius: 100 }), 100);
  assert.equal(scoreRisk({ severity: 0, exposure: 0, uncertainty: 0, blastRadius: 0 }), 0);
  assert.throws(() => scoreRisk({ severity: 101, exposure: 0, uncertainty: 0, blastRadius: 0 }));
});

test("a ready simulation starts and simulated time advances only while running", () => {
  const ready = createInitialState();
  assert.equal(advanceOneHour(ready).simHour, 0);
  const running = startRun(ready);
  assert.equal(running.status, "running");
  assert.equal(advanceOneHour(running).simHour, 1);
});

test("scheduled supplier disruption creates a high-risk approval request", () => {
  let state = startRun(createInitialState());
  for (let i = 0; i < 6; i += 1) state = advanceOneHour(state);
  assert.equal(state.simHour, 6);
  assert.ok(state.events.some((event) => event.title === "Critical supplier service unavailable"));
  assert.ok(state.approvals.some((approval) => approval.status === "pending" && approval.riskScore >= 70));
});

test("high-risk injected events produce an approval gate and bounded persona proposals", () => {
  const state = injectEvent(createInitialState(), "identity-anomaly");
  assert.ok(state.approvals.some((approval) => approval.status === "pending" && approval.action.includes("Identity telemetry anomaly")));
  assert.ok(state.audit.some((entry) => entry.action === "approval.requested"));
  assert.ok(state.agentDecisions.length >= 3);
  assert.ok(state.agentDecisions.every((decision) => decision.externalSideEffect === false));
  assert.ok(state.agentDecisions.some((decision) => decision.personaId === "security-analyst"));
  assert.ok(state.agentDecisions.some((decision) => decision.personaId === "incident-commander" && decision.approvalStatus === "pending"));
  assert.ok(state.agentDecisions.some((decision) => decision.personaId === "response-agent" && decision.approvalStatus === "pending"));
  assert.ok(state.audit.some((entry) => entry.action === "agent.proposals.generated"));
});

test("approval decisions are audited and do not execute external actions", () => {
  const state = createInitialState();
  const pending = state.approvals.find((approval) => approval.status === "pending");
  assert.ok(pending);
  const next = decideApproval(state, pending.id, "approved");
  assert.equal(next.approvals.find((approval) => approval.id === pending.id)?.status, "approved");
  assert.ok(next.audit.some((entry) => entry.action === "approval.accepted" && entry.detail.includes("no real connector")));
});

test("fork and restore operate on checkpoints and preserve previous checkpoints", () => {
  let state = startRun(createInitialState());
  state = advanceOneHour(state);
  state = captureSnapshot(state, "Known good");
  const checkpointId = state.checkpoints[0].id;
  state = advanceOneHour(state);
  const forked = forkBranch(state, "GLASSFALL-ALT-01");
  assert.equal(forked.branchName, "GLASSFALL-ALT-01");
  assert.equal(forked.status, "paused");
  const restored = restoreCheckpoint(forked, checkpointId);
  assert.equal(restored.simHour, 1);
  assert.ok(restored.audit.some((entry) => entry.action === "checkpoint.restored"));
  assert.ok(restored.checkpoints.length >= 2);
});

test("emergency stop preserves state and prevents time advancement", () => {
  const running = startRun(createInitialState());
  const stopped = emergencyStop(running);
  assert.equal(stopped.status, "stopped");
  assert.equal(stopped.safetyStop, true);
  assert.equal(advanceOneHour(stopped).simHour, stopped.simHour);
  assert.ok(stopped.audit.some((entry) => entry.action === "emergency.stop"));
});

test("the completed scenario has a hard 72-hour ceiling", () => {
  let state = startRun(createInitialState());
  for (let i = 0; i < 72; i += 1) state = advanceOneHour(state);
  assert.equal(state.simHour, 72);
  assert.equal(state.status, "completed");
  assert.equal(advanceOneHour(state).simHour, 72);
});


test("initial fixture is deterministic across server and browser hydration", () => {
  const first = createInitialState();
  const second = createInitialState();
  assert.equal(first.runId, second.runId);
  assert.equal(first.lastUpdatedAt, second.lastUpdatedAt);
  assert.deepEqual(first.approvals.map((approval) => approval.id), second.approvals.map((approval) => approval.id));
  assert.deepEqual(first.events.map((event) => event.id), second.events.map((event) => event.id));
});

test("after-action Markdown exports real line breaks", () => {
  const markdown = reportAsMarkdown(createInitialState());
  assert.ok(markdown.includes("\n## KPIs\n"));
  assert.ok(!markdown.includes("\\n## KPIs\\n"));
});

test("termination is distinct from emergency stop and prevents future advancement", () => {
  const running = startRun(createInitialState());
  const terminated = terminateRun(running);
  assert.equal(terminated.status, "terminated");
  assert.equal(terminated.safetyStop, false);
  assert.equal(advanceOneHour(terminated).simHour, terminated.simHour);
  assert.ok(terminated.audit.some((entry) => entry.action === "simulation.terminated"));
});
