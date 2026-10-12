"use client";

import { useEffect, useMemo, useState } from "react";
import {
  advanceOneHour,
  afterActionReport,
  captureSnapshot,
  createInitialState,
  decideApproval,
  emergencyStop,
  forkBranch,
  injectEvent,
  pauseRun,
  reportAsMarkdown,
  restoreCheckpoint,
  resumeRun,
  startRun,
  terminateRun
} from "../lib/engine";
import type { InjectedEventKind, WorldState } from "../lib/model";
import { PERSONAS, SCENARIO } from "../lib/scenario";

type View = "overview" | "forge" | "personas" | "narrative" | "governance" | "intelligence";

const NAV: { id: View; label: string; code: string }[] = [
  { id: "overview", label: "Command overview", code: "01" },
  { id: "forge", label: "World Forge", code: "02" },
  { id: "personas", label: "Persona Engine", code: "03" },
  { id: "narrative", label: "Event timeline", code: "04" },
  { id: "governance", label: "Governance core", code: "05" },
  { id: "intelligence", label: "Intelligence reports", code: "06" }
];

const INJECTS: { kind: InjectedEventKind; label: string; detail: string }[] = [
  { kind: "supplier-disruption", label: "Supplier disruption", detail: "Availability pressure" },
  { kind: "rumor-escalation", label: "Rumor escalation", detail: "Communications pressure" },
  { kind: "restore-verified", label: "Verify recovery", detail: "Integrity checkpoint" },
  { kind: "board-briefing", label: "Board briefing", detail: "Oversight request" },
  { kind: "identity-anomaly", label: "Identity anomaly", detail: "Defensive telemetry" },
  { kind: "containment-progress", label: "Containment progress", detail: "Defensive milestone" }
];

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function statusLabel(status: WorldState["status"]) {
  return status.replace("-", " ").toUpperCase();
}

function Meter({ label, value, tone = "cyan" }: { label: string; value: number; tone?: "cyan" | "violet" | "red" | "amber" }) {
  return (
    <div className="meter-row">
      <div className="meter-label"><span>{label}</span><strong>{value}%</strong></div>
      <div className="meter-track"><div className={"meter-fill " + tone} style={{ width: value + "%" }} /></div>
    </div>
  );
}

function IconMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 48 48" role="presentation">
        <path d="M24 3 42 13.5v21L24 45 6 34.5v-21L24 3Z" />
        <path d="M15 29V18l9-5 9 5v11l-9 5-9-5Z" />
        <path d="M24 13v21M15 18l18 11M33 18 15 29" />
      </svg>
    </div>
  );
}

export default function DelosConsole() {
  const [state, setState] = useState<WorldState>(() => createInitialState());
  const [hydrated, setHydrated] = useState(false);
  const [view, setView] = useState<View>("overview");
  const [selectedPersona, setSelectedPersona] = useState(PERSONAS[0].id);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("delos-os-glassfall-v1");
      if (stored) {
        const parsed = JSON.parse(stored) as WorldState;
        if (parsed && parsed.scenarioId === SCENARIO.id && Array.isArray(parsed.events) && Array.isArray(parsed.agents)) {
          setState(parsed);
        }
      }
    } catch {
      setNotice("Saved demo state could not be read. A fresh synthetic world is loaded.");
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem("delos-os-glassfall-v1", JSON.stringify(state));
    } catch {
      setNotice("Browser storage is unavailable; this session may not survive refresh.");
    }
  }, [state, hydrated]);

  const pending = useMemo(() => state.approvals.filter((approval) => approval.status === "pending"), [state.approvals]);
  const latestEvents = useMemo(() => [...state.events].sort((a, b) => b.simHour - a.simHour).slice(0, 6), [state.events]);
  const currentPersona = PERSONAS.find((persona) => persona.id === selectedPersona) || PERSONAS[0];
  const title = NAV.find((item) => item.id === view)?.label || "Command overview";
  const runIsFrozen = state.safetyStop || ["terminated", "stopped", "completed"].includes(state.status);
  const latestCheckpoint = state.checkpoints[state.checkpoints.length - 1];
  const baseline = state.snapshots[0];

  function controlRun() {
    setNotice("");
    setState((current) => {
      if (current.status === "ready") return startRun(current);
      if (current.status === "running") return pauseRun(current);
      if (current.status === "paused") return resumeRun(current);
      return current;
    });
  }

  function inject(kind: InjectedEventKind) {
    setState((current) => injectEvent(current, kind));
    setNotice("Synthetic inject added. Risk review and audit evidence updated.");
  }

  function makeFork() {
    const branch = "GLASSFALL-ALT-" + String(state.snapshots.length + 1).padStart(2, "0");
    setState((current) => forkBranch(current, branch));
    setNotice("Branch checkpoint captured. This fork is isolated to the local synthetic demo.");
  }

  function resetDemo() {
    setState(createInitialState());
    setNotice("Demo reset to the original synthetic fixture.");
  }

  function exportMarkdown() {
    downloadFile("operation-glassfall-report.md", reportAsMarkdown(state), "text/markdown;charset=utf-8");
  }

  function exportJson() {
    downloadFile("operation-glassfall-report.json", JSON.stringify(afterActionReport(state), null, 2), "application/json;charset=utf-8");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <IconMark />
          <div>
            <div className="brand-name">DELOS<span>OS</span></div>
            <div className="brand-caption">CLEARG LASS / SIMULATION</div>
          </div>
        </div>

        <div className="workspace-label">OPERATIONS SUITE <span className="tiny-dot" /></div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {NAV.map((item) => (
            <button key={item.id} className={"nav-item " + (view === item.id ? "active" : "")} onClick={() => setView(item.id)}>
              <span className="nav-code">{item.code}</span>
              <span>{item.label}</span>
              {item.id === "governance" && pending.length > 0 ? <span className="nav-count">{pending.length}</span> : null}
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        <div className="sidebar-scenario">
          <div className="eyebrow">ACTIVE SCENARIO</div>
          <div className="scenario-mini-title">Operation Glassfall</div>
          <div className="scenario-mini-meta">72H / ENTERPRISE CRISIS</div>
          <div className="mini-progress"><span style={{ width: state.missionProgress + "%" }} /></div>
          <div className="mini-progress-label"><span>T+{String(state.simHour).padStart(2, "0")}H</span><span>{state.missionProgress}%</span></div>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">CG</span>
          <div className="operator-copy"><strong>ClearGlass Operator</strong><span>LOCAL DEMO ROLE</span></div>
          <span className="online-indicator" aria-label="Local interface active" />
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumbs"><span>DELOS OS</span><b>/</b><strong>{title}</strong></div>
          <div className="topbar-actions">
            <div className="environment-tag"><span className="safe-dot" /> SYNTHETIC ENVIRONMENT</div>
            <div className="divider-vertical" />
            <button className="icon-button" title="Reset synthetic demo" aria-label="Reset synthetic demo" onClick={resetDemo}>↺</button>
            <button className="operator-avatar" title="Local demo operator">DO</button>
          </div>
        </header>

        <main className="main-content">
          <section className="page-heading">
            <div>
              <div className="overline"><span className="overline-line" /> WORLD OPERATIONS / {SCENARIO.id}</div>
              <h1>{view === "overview" ? <>Design reality.<br /><em>Test every outcome.</em></> : title}</h1>
              <p className="heading-copy">
                {view === "overview"
                  ? "A controlled environment for pressure-testing decisions before the real world gets a vote."
                  : "Inspect the synthetic world, its decision record, and the boundaries governing every agent."}
              </p>
            </div>
            <div className="heading-status">
              <span className={"status-pip " + state.status} />
              <div><span className="eyebrow">RUN STATE</span><strong>{statusLabel(state.status)}</strong></div>
              <div className="status-divider" />
              <div><span className="eyebrow">SIM CLOCK</span><strong>T+{String(state.simHour).padStart(2, "0")}<small> / 72H</small></strong></div>
            </div>
          </section>

          <div className="demo-warning">
            <span className="warning-symbol">i</span>
            <div><strong>Prototype / synthetic-only mode</strong><span>Local browser persistence. No live connectors, production tools, external messages, or real customer data are enabled.</span></div>
            <span className="demo-badge">SAFE MODE</span>
          </div>

          {notice ? <div className="notice-line" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Dismiss message">×</button></div> : null}

          {view === "overview" ? (
            <>
              <section className="metric-grid" aria-label="World metrics">
                <div className="metric-card accent-cyan"><div className="metric-top"><span>SIMULATED TIME</span><span className="metric-glyph">◷</span></div><div className="metric-value">{String(state.simHour).padStart(2, "0")}<small> / 72 H</small></div><div className="metric-foot"><span className="foot-line" /> Scenario clock</div></div>
                <div className="metric-card"><div className="metric-top"><span>THREAT PRESSURE</span><span className="metric-glyph">⌁</span></div><div className="metric-value">{state.threatLevel}<small> / 100</small></div><div className="metric-foot"><span className="metric-dot red-dot" /> Synthetic signal severity</div></div>
                <div className="metric-card"><div className="metric-top"><span>SUPPLIER CAPACITY</span><span className="metric-glyph">◇</span></div><div className="metric-value">{state.supplierCapacity}<small>%</small></div><div className="metric-foot"><span className="metric-dot cyan-dot" /> Continuity index</div></div>
                <div className="metric-card"><div className="metric-top"><span>APPROVAL QUEUE</span><span className="metric-glyph">⌑</span></div><div className="metric-value">{String(pending.length).padStart(2, "0")}<small> PENDING</small></div><div className="metric-foot"><span className="metric-dot amber-dot" /> Human decision required</div></div>
              </section>

              <section className="control-strip">
                <div className="control-context"><span className="live-rings"><i /></span><div><strong>SIMULATION CONTROL</strong><span>All controls operate on synthetic state only.</span></div></div>
                <div className="control-buttons">
                  <button className="button button-primary" onClick={controlRun} disabled={runIsFrozen}>{state.status === "ready" ? "▶  Launch" : state.status === "running" ? "Ⅱ  Pause" : state.status === "paused" ? "▶  Resume" : "Unavailable"}</button>
                  <button className="button button-secondary" onClick={() => setState((current) => advanceOneHour(current))} disabled={state.status !== "running" || runIsFrozen}>+1 simulated hour</button>
                  <button className="button button-secondary" onClick={() => setState((current) => captureSnapshot(current, "Operator checkpoint"))} disabled={runIsFrozen}>◇ Checkpoint</button>
                  <button className="button button-danger" onClick={() => setState((current) => emergencyStop(current))} disabled={state.safetyStop}>■ Global stop</button>
                </div>
              </section>

              <div className="dashboard-grid">
                <section className="panel world-panel">
                  <div className="panel-header"><div><div className="eyebrow">WORLD / 01</div><h2>Operational field</h2></div><span className="panel-tag">SCHEMATIC VIEW</span></div>
                  <div className="world-map">
                    <div className="map-grid" />
                    <svg className="map-lines" viewBox="0 0 600 300" preserveAspectRatio="none" aria-label="Synthetic topology schematic">
                      <path d="M70 80 L180 100 L280 60 L395 105 L520 70" />
                      <path d="M180 100 L205 200 L325 230 L395 105" />
                      <path d="M325 230 L490 210 L520 70" />
                      <path d="M70 80 L90 205 L205 200" />
                      <path d="M280 60 L310 145 L395 105 L490 210" />
                    </svg>
                    <div className="map-coordinate coord-one">NORTH / IDENTITY</div><div className="map-coordinate coord-two">CORE / BUSINESS SYSTEMS</div><div className="map-coordinate coord-three">SOUTH / SUPPLY CHAIN</div>
                    <div className="map-node node-identity"><span className="node-ring" /><b>IDENTITY</b><small>TELEMETRY</small></div>
                    <div className="map-node node-core"><span className="node-ring" /><b>CORE SYSTEMS</b><small>SIMULATED</small></div>
                    <div className="map-node node-edge"><span className="node-ring" /><b>SUPPLIER</b><small>CAPACITY {state.supplierCapacity}%</small></div>
                    <div className="map-node node-comms"><span className="node-ring" /><b>COMMS</b><small>REVIEW</small></div>
                    <div className="map-status"><span className="safe-dot" /> 4 LOGICAL ZONES <span>•</span> NO LIVE NETWORK</div>
                  </div>
                  <div className="world-panel-foot"><span><i className="legend-dot" /> Simulated asset</span><span><i className="legend-dot legend-alert" /> Risk focus</span><span>WORLD HASH <b>{state.runId.slice(-8).toUpperCase()}</b></span></div>
                </section>

                <section className="panel objectives-panel">
                  <div className="panel-header"><div><div className="eyebrow">MISSION / 02</div><h2>Objectives & resilience</h2></div><span className="metric-glyph">◎</span></div>
                  <div className="objective-list">
                    {SCENARIO.objectives.map((objective, index) => {
                      const value = index === 0 ? Math.min(100, state.missionProgress + 18) : index === 1 ? Math.min(100, state.supplierCapacity) : index === 2 ? Math.min(100, state.reputation) : Math.min(100, state.integrity);
                      return <div className="objective" key={objective.id}><div className="objective-head"><span className="objective-index">{objective.id}</span><span className="objective-state">{value >= objective.target ? "ON TRACK" : index === 1 && value < 60 ? "AT RISK" : "IN PROGRESS"}</span></div><p>{objective.label}</p><Meter label="Readiness" value={value} tone={value < 50 ? "red" : index === 2 ? "violet" : "cyan"} /></div>;
                    })}
                  </div>
                  <div className="objective-summary"><span>MISSION PROGRESS</span><strong>{state.missionProgress}%</strong><div className="mini-progress"><span style={{ width: state.missionProgress + "%" }} /></div></div>
                </section>
              </div>

              <div className="lower-grid">
                <section className="panel agents-panel">
                  <div className="panel-header"><div><div className="eyebrow">PERSONA ENGINE / 03</div><h2>Agent operations</h2></div><button className="text-link" onClick={() => setView("personas")}>Inspect roster ↗</button></div>
                  <div className="agent-list">
                    {state.agents.map((agent) => {
                      const persona = PERSONAS.find((item) => item.id === agent.personaId) || PERSONAS[0];
                      return <button key={agent.personaId} className="agent-row" onClick={() => { setSelectedPersona(agent.personaId); setView("personas"); }}>
                        <span className={"agent-avatar avatar-" + (PERSONAS.findIndex((item) => item.id === agent.personaId) % 4)}>{persona.name.split(" ").map((word) => word[0]).slice(0, 2).join("")}</span>
                        <span className="agent-info"><strong>{persona.name}</strong><small>{persona.role}</small></span>
                        <span className={"agent-state " + agent.status}><i />{agent.status.replace("-", " ")}</span>
                        <span className="agent-confidence">{agent.confidence}%<small>CONF.</small></span>
                      </button>;
                    })}
                  </div>
                </section>

                <section className="panel timeline-panel">
                  <div className="panel-header"><div><div className="eyebrow">CANONICAL EVENTS / 04</div><h2>Event stream</h2></div><button className="text-link" onClick={() => setView("narrative")}>Full timeline ↗</button></div>
                  <div className="event-stream">
                    {latestEvents.map((event) => <div className="event-row" key={event.id}>
                      <div className={"event-marker " + (event.riskScore >= 70 ? "event-marker-alert" : event.category === "milestone" ? "event-marker-good" : "")} />
                      <div className="event-copy"><div><span className="event-time">T+{String(event.simHour).padStart(2, "0")}H</span><span className="event-category">{event.category}</span></div><strong>{event.title}</strong><p>{event.detail}</p></div>
                      <span className={"risk-chip " + (event.riskScore >= 70 ? "risk-high" : event.riskScore >= 40 ? "risk-medium" : "risk-low")}>{event.riskScore}</span>
                    </div>)}
                  </div>
                </section>
              </div>
            </>
          ) : null}

          {view === "forge" ? (
            <section className="panel detail-panel">
              <div className="panel-header"><div><div className="eyebrow">WORLD FORGE / REVISION 01</div><h2>Operation Glassfall configuration</h2></div><span className="panel-tag">READ-ONLY FIXTURE</span></div>
              <p className="detail-lead">{SCENARIO.description}</p>
              <div className="configuration-grid">
                <div className="config-card"><span>WORLD TYPE</span><strong>Corporate / Cyber / Crisis</strong><small>Synthetic enterprise and supplier topology</small></div>
                <div className="config-card"><span>SIMULATION HORIZON</span><strong>72 simulated hours</strong><small>One operator advance equals one hour</small></div>
                <div className="config-card"><span>PHYSICAL / SOCIAL RULES</span><strong>Scenario constrained</strong><small>Only events in the synthetic scenario can change state</small></div>
                <div className="config-card"><span>CONNECTOR PERMISSIONS</span><strong className="red-text">NONE ENABLED</strong><small>No network, payment, production, or customer data integrations</small></div>
              </div>
              <h3 className="subheading">Victory and failure conditions</h3>
              <div className="condition-list"><div><span className="condition-icon success">✓</span><div><strong>Success objective</strong><p>Complete the 72-hour timeline, preserve a reviewable audit trail, and resolve or explicitly defer high-risk approvals.</p></div></div><div><span className="condition-icon danger">!</span><div><strong>Safety failure state</strong><p>Emergency stop is triggered, a world state fails validation, or a requested action exceeds declared permissions.</p></div></div></div>
              <div className="panel-actions"><button className="button button-secondary" onClick={() => setState((current) => captureSnapshot(current, "World Forge configuration checkpoint"))}>Capture configuration snapshot</button><button className="button button-primary" onClick={() => setView("overview")}>Return to operations</button></div>
            </section>
          ) : null}

          {view === "personas" ? (
            <div className="persona-layout">
              <section className="panel persona-list-panel"><div className="panel-header"><div><div className="eyebrow">PERSONA ENGINE / 07 ENTITIES</div><h2>Persona roster</h2></div></div>
                {PERSONAS.map((persona) => <button key={persona.id} className={"persona-select " + (selectedPersona === persona.id ? "selected" : "")} onClick={() => setSelectedPersona(persona.id)}><span className="persona-select-mark">{persona.name.split(" ").map((word) => word[0]).slice(0, 2).join("")}</span><span><strong>{persona.name}</strong><small>{persona.role}</small></span><span className="chevron">›</span></button>)}
              </section>
              <section className="panel persona-detail"><div className="panel-header"><div><div className="eyebrow">IDENTITY PROFILE / {currentPersona.id.toUpperCase()}</div><h2>{currentPersona.name}</h2></div><span className="panel-tag">SYNTHETIC PERSONA</span></div>
                <p className="detail-lead">{currentPersona.goal}</p>
                <div className="persona-facts"><div><span>BEHAVIORAL PROFILE</span><strong>{currentPersona.personality}</strong></div><div><span>RISK CLASS</span><strong>{currentPersona.riskLevel}/5</strong></div><div><span>MEMORY SCOPE</span><strong>{currentPersona.memoryScope}</strong></div></div>
                <h3 className="subheading">Expertise</h3><div className="pill-list">{currentPersona.expertise.map((item) => <span className="soft-pill" key={item}>{item}</span>)}</div>
                <h3 className="subheading">Available permissions</h3><div className="boundary-list">{currentPersona.permissions.map((item) => <div key={item}><span className="tiny-check">✓</span>{item}</div>)}</div>
                <h3 className="subheading">Knowledge boundary</h3><div className="boundary-callout">{currentPersona.knowledgeBoundary}</div>
                <h3 className="subheading">Approval requirements</h3><div className="pill-list">{currentPersona.approvalRequirements.map((item) => <span className="soft-pill amber-pill" key={item}>{item}</span>)}</div>
              </section>
            </div>
          ) : null}

          {view === "narrative" ? (
            <section className="panel detail-panel">
              <div className="panel-header"><div><div className="eyebrow">NARRATIVE DIRECTOR / EVENT JOURNAL</div><h2>Canonical event timeline</h2></div><span className="panel-tag">{state.events.length} EVENTS</span></div>
              <p className="detail-lead">Every event below is a synthetic fact or scenario inject. Operators can branch future outcomes without rewriting prior checkpoints.</p>
              <div className="inject-toolbar"><span className="eyebrow">INJECT A CONTROLLED EVENT</span>{INJECTS.map((item) => <button className="button button-small button-secondary" key={item.kind} onClick={() => inject(item.kind)} disabled={runIsFrozen}>{item.label}</button>)}</div>
              <div className="full-timeline">{[...state.events].sort((a, b) => b.simHour - a.simHour).map((event) => <div className="full-timeline-row" key={event.id}><div className="timeline-hour">T+{String(event.simHour).padStart(2, "0")}<small>HOUR</small></div><div className="timeline-spine"><span className={event.riskScore >= 70 ? "danger-spine" : event.category === "milestone" ? "success-spine" : ""} /></div><div className="full-timeline-copy"><div className="inline-tags"><span className="event-category">{event.category}</span><span className={"risk-chip " + (event.riskScore >= 70 ? "risk-high" : event.riskScore >= 40 ? "risk-medium" : "risk-low")}>RISK {event.riskScore}</span></div><h3>{event.title}</h3><p>{event.detail}</p><small>ORIGIN: {event.source.toUpperCase()}</small></div></div>)}</div>
            </section>
          ) : null}

          {view === "governance" ? (
            <>
              <section className="governance-banner"><div className="governance-emblem">◇</div><div><div className="eyebrow">GOVERNANCE CORE / FAIL-CLOSED</div><h2>Human authority stays in the loop.</h2><p>Approvals in this prototype record a simulated decision only. No real-world connector is invoked.</p></div><div className="governance-mode">DEFAULT DENY <span>●</span></div></section>
              <div className="dashboard-grid governance-grid">
                <section className="panel"><div className="panel-header"><div><div className="eyebrow">POLICY GATE / 01</div><h2>Approval queue</h2></div><span className="panel-tag">{pending.length} PENDING</span></div>
                  {state.approvals.length === 0 ? <div className="empty-state">No approval requests have been generated.</div> : <div className="approval-list">{[...state.approvals].reverse().map((approval) => <div className="approval-card" key={approval.id}><div className="approval-top"><span className={"risk-chip " + (approval.riskScore >= 80 ? "risk-high" : "risk-medium")}>RISK {approval.riskScore}</span><span className={"approval-status " + approval.status}>{approval.status}</span></div><h3>{approval.action}</h3><p>{approval.rationale}</p>{approval.status === "pending" && !runIsFrozen ? <div className="approval-actions"><button className="button button-small button-primary" onClick={() => setState((current) => decideApproval(current, approval.id, "approved"))}>Record approval</button><button className="button button-small button-secondary" onClick={() => setState((current) => decideApproval(current, approval.id, "rejected"))}>Reject</button></div> : <small className="approval-foot">{approval.approver ? "DECIDED BY " + approval.approver.toUpperCase() : "DECISION LOCKED BY RUN STATE"} {approval.decidedAt ? "· " + new Date(approval.decidedAt).toLocaleTimeString() : ""}</small>}</div>)}</div>}
                </section>
                <section className="panel audit-panel"><div className="panel-header"><div><div className="eyebrow">AUDIT REGISTRY / 02</div><h2>Operator activity</h2></div><span className="metric-glyph">≋</span></div><div className="audit-list">{[...state.audit].reverse().slice(0, 12).map((entry) => <div className="audit-row" key={entry.id}><span className="audit-time">T+{String(entry.simHour).padStart(2, "0")}</span><div><strong>{entry.action}</strong><p>{entry.detail}</p><small>{entry.actor} · {entry.approvalStatus} · risk {entry.riskScore}</small></div></div>)}</div><div className="audit-disclaimer">Prototype note: this client-side log is replayable demo evidence, not an immutable server-side audit ledger.</div></section>
              </div>
              <section className="panel stop-panel"><div><div className="eyebrow">EMERGENCY CONTROL</div><h2>Freeze this synthetic world</h2><p>Stops all simulation transitions and preserves the current browser state. Recovery requires a reset in this prototype.</p></div><button className="button button-danger" disabled={state.safetyStop} onClick={() => setState((current) => emergencyStop(current))}>■ Trigger global stop</button></section>
            </>
          ) : null}

          {view === "intelligence" ? (
            <div className="report-layout">
              <section className="panel report-main"><div className="panel-header"><div><div className="eyebrow">INTELLIGENCE / AFTER-ACTION</div><h2>Decision intelligence report</h2></div><span className="panel-tag">LOCAL EXPORT</span></div>
                <p className="detail-lead">{afterActionReport(state).executiveSummary}</p>
                <div className="report-kpis"><div><span>Mission progress</span><strong>{state.missionProgress}%</strong></div><div><span>High-risk events</span><strong>{state.events.filter((event) => event.riskScore >= 70).length}</strong></div><div><span>Approvals accepted</span><strong>{state.approvals.filter((approval) => approval.status === "approved").length}</strong></div><div><span>Audit records</span><strong>{state.audit.length}</strong></div></div>
                <h3 className="subheading">Persona engine proposals <span className="subheading-note">SYNTHETIC · NO TOOLS</span></h3>
                <p className="proposal-intro">Bounded personas generate decision options from the scenario record. These proposals are not actions; high-risk recommendations stay gated for an operator decision.</p>
                <div className="proposal-list">
                  {[...state.agentDecisions].reverse().slice(0, 8).map((decision) => {
                    const persona = PERSONAS.find((item) => item.id === decision.personaId) || PERSONAS[0];
                    return <article className="decision-card" key={decision.id}>
                      <div className="decision-top">
                        <span className="decision-persona">{persona.name}</span>
                        <span className={"risk-chip " + (decision.riskScore >= 70 ? "risk-high" : decision.riskScore >= 40 ? "risk-medium" : "risk-low")}>RISK {decision.riskScore}</span>
                      </div>
                      <div className="decision-intent">{decision.intent}</div>
                      <strong className="decision-action">{decision.chosenAction}</strong>
                      <p className="decision-rationale">{decision.rationale}</p>
                      <div className="decision-foot"><span>{decision.approvalStatus === "pending" ? "HUMAN REVIEW REQUIRED" : "SIMULATION ONLY"}</span><span>EXTERNAL SIDE EFFECT: NO</span></div>
                    </article>;
                  })}
                  {state.agentDecisions.length === 0 ? <div className="empty-state">No persona proposals yet. Launch the scenario and advance the clock or inject a synthetic event to generate bounded recommendations.</div> : null}
                </div>
                <h3 className="subheading">Recommended actions</h3>{afterActionReport(state).recommendations.map((item, index) => <div className="recommendation-row" key={item}><span>0{index + 1}</span><p>{item}</p></div>)}
                <h3 className="subheading">Current branch</h3><div className="boundary-callout"><strong>{state.branchName}</strong> · T+{String(state.simHour).padStart(2, "0")}H · {state.status.toUpperCase()} {state.parentSnapshotId ? "· forked from " + state.parentSnapshotId : "· baseline branch"}</div>
                <div className="panel-actions"><button className="button button-primary" onClick={exportMarkdown}>↓ Export Markdown</button><button className="button button-secondary" onClick={exportJson}>↓ Export JSON</button></div>
              </section>
              <section className="panel branch-panel"><div className="panel-header"><div><div className="eyebrow">TIMELINE EXPLORER</div><h2>Snapshot & branch comparison</h2></div></div><p className="panel-description">Capture a baseline, fork an alternate branch, then compare scenario metrics without contacting external systems.</p><div className="branch-actions"><button className="button button-secondary" onClick={() => setState((current) => captureSnapshot(current, "Comparison baseline"))} disabled={runIsFrozen}>Capture baseline</button><button className="button button-secondary" onClick={makeFork} disabled={runIsFrozen}>Fork current state</button><button className="button button-secondary" onClick={() => { if (latestCheckpoint) setState((current) => restoreCheckpoint(current, latestCheckpoint.id)); }} disabled={!latestCheckpoint || runIsFrozen}>Restore last checkpoint</button></div>
                {baseline ? <div className="compare-table"><div className="compare-heading"><span>METRIC</span><span>CHECKPOINT</span><span>CURRENT</span></div>{([{label:"Threat level",a:baseline.threatLevel,b:state.threatLevel},{label:"Supplier capacity",a:baseline.supplierCapacity,b:state.supplierCapacity},{label:"Reputation",a:baseline.reputation,b:state.reputation},{label:"Integrity",a:baseline.integrity,b:state.integrity},{label:"Mission progress",a:baseline.missionProgress,b:state.missionProgress}] as const).map((item) => <div className="compare-row" key={item.label}><span>{item.label}</span><strong>{item.a}%</strong><strong className={item.a === item.b ? "" : item.b > item.a ? "positive-delta" : "negative-delta"}>{item.b}%</strong></div>)}<small className="compare-foot">Checkpoint: T+{String(baseline.simHour).padStart(2, "0")} · {baseline.label} · {state.snapshots.length} snapshot(s) recorded</small></div> : <div className="empty-state">No checkpoint yet. Capture a baseline to enable comparison.</div>}
                <div className="branch-current"><span className="branch-node" /><div><strong>{state.branchName}</strong><small>{state.parentSnapshotId ? "CHILD BRANCH" : "BASELINE BRANCH"} · {state.checkpoints.length} CHECKPOINT(S)</small></div></div>
              </section>
            </div>
          ) : null}

          <footer className="page-footer"><span><b>DELOS OS</b> / CLEARGLASS INC.</span><span>DESIGN REALITY. TEST EVERY OUTCOME.</span><span>BUILD 0.1.0 · DEMO MODE</span></footer>
        </main>
      </div>
    </div>
  );
}
