"use client";

import { useState } from "react";
import styles from "./operations.module.css";

type WorkflowResult = {
  ok: boolean;
  mode: "mock" | "live" | "blocked";
  synthetic?: boolean;
  incident?: { id: string; title: string; status: string; priority: string };
  assignment?: { assignee: string; createdAt: string };
  evidence?: { filename: string; sha256: string; sizeBytes: number; status: string };
  verification?: { matches: boolean; recordedSha256: string; computedSha256: string };
  audit?: Array<{ id: string; action: string; actor: string; createdAt: string }>;
  custody?: Array<{ id: string; action: string; actor: string; evidenceSha256: string; createdAt: string }>;
  error?: string;
};

export function OperationsDashboard() {
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [running, setRunning] = useState(false);

  async function runDemo() {
    setRunning(true);
    setResult(null);
    try {
      const response = await fetch("/api/operations", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "run-synthetic-vertical-slice" }),
      });
      const payload = (await response.json()) as WorkflowResult;
      setResult(payload);
    } catch {
      setResult({ ok: false, mode: "blocked", error: "Unable to reach the operations API." });
    } finally {
      setRunning(false);
    }
  }

  const status = result?.ok ? "WORKFLOW VERIFIED" : result ? "ACTION REQUIRED" : "READY";

  return (
    <main className={styles.shell}>
      <div className={styles.noise} aria-hidden="true" />
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>CLEARGLASS · OPERATIONS / EVIDENCE</p>
          <h1>AUTHORIZED<br /><span>OPERATIONS FABRIC</span></h1>
          <p className={styles.lede}>
            Incident intake, human-controlled assignment, evidence integrity, custody events, and audit reconstruction — built as an additive extension to the existing ClearGlass stack.
          </p>
        </div>
        <div className={styles.statusCard}>
          <span>MODULE STATUS</span>
          <strong>{status}</strong>
          <small>{result?.synthetic ? "SYNTHETIC DATA ONLY" : "NO LIVE PROVIDERS CONNECTED"}</small>
        </div>
      </header>

      <section className={styles.grid}>
        {[
          ["01", "INCIDENTS", "Structured intake, priorities, statuses, assignments and operator-controlled escalation."],
          ["02", "RECORDS", "Case-ready domain entities, audit history, retention and legal-hold boundaries."],
          ["03", "EVIDENCE", "Original-byte SHA-256 integrity recording with explicit custody events."],
          ["04", "FORENSICS", "Isolated-worker adapter boundary; no acquisition, unlocking or restricted access."],
          ["05", "VOICE", "Provider-neutral telephony/STT/TTS/SMS interfaces; disabled until verified."],
          ["06", "RECOGNITION", "LPR and consent-based one-to-one biometric interfaces; disabled by default."],
        ].map(([n, title, text]) => (
          <article key={title} className={styles.card}>
            <span className={styles.index}>{n}</span>
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <section className={styles.console}>
        <div className={styles.consoleHead}>
          <div>
            <p className={styles.eyebrow}>PHASE 2 · CORE VERTICAL SLICE</p>
            <h2>Incident → assignment → evidence → audit</h2>
          </div>
          <button className={styles.button} type="button" onClick={runDemo} disabled={running}>
            {running ? "RUNNING…" : "RUN SYNTHETIC WORKFLOW"}
          </button>
        </div>

        <div className={styles.flow}>
          {["CREATE INCIDENT", "ASSIGN OPERATOR", "HASH EVIDENCE", "UPDATE INCIDENT", "REVIEW AUDIT"].map((step, i) => (
            <div className={styles.step} key={step}>
              <span>0{i + 1}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>

        {!result ? (
          <div className={styles.empty}>
            <strong>Human-gated, synthetic demonstration</strong>
            <span>No production records, external providers, government sources, or real personal data are used.</span>
          </div>
        ) : result.ok ? (
          <div className={styles.result}>
            <div className={styles.resultGrid}>
              <div><span>INCIDENT</span><strong>{result.incident?.id.slice(0, 8)}</strong><small>{result.incident?.status}</small></div>
              <div><span>ASSIGNED TO</span><strong>{result.assignment?.assignee}</strong><small>{result.assignment?.createdAt}</small></div>
              <div><span>EVIDENCE HASH</span><strong>{result.evidence?.sha256.slice(0, 16)}…</strong><small>{result.verification?.matches ? "SHA-256 VERIFIED" : "MISMATCH"}</small></div>
            </div>
            <div className={styles.audit}>
              <div className={styles.auditHead}><span>AUDIT HISTORY</span><span>{result.audit?.length ?? 0} EVENTS</span></div>
              {result.audit?.slice(-8).map((event) => (
                <div className={styles.auditRow} key={event.id}>
                  <span>{new Date(event.createdAt).toLocaleTimeString()}</span>
                  <strong>{event.action}</strong>
                  <em>{event.actor}</em>
                </div>
              ))}
            </div>
            <p className={styles.claimBoundary}>
              Hash verification confirms byte-level integrity of the stored synthetic bytes. It does not by itself establish authenticity, provenance, legal admissibility, or what an underlying real-world event means.
            </p>
          </div>
        ) : (
          <div className={styles.error} role="alert">
            <strong>{result.error ?? "Operations workflow failed."}</strong>
            <span>This surface does not fail open or substitute simulated live results for real integrations.</span>
          </div>
        )}
      </section>

      <footer className={styles.footer}>
        <span>STATUS: MOCKED / CORE SLICE</span>
        <span>LIVE AUTH · DURABLE DB · OBJECT STORAGE · PROVIDERS: BLOCKED</span>
        <span>LPR · BIOMETRIC: OFF</span>
      </footer>
    </main>
  );
}
