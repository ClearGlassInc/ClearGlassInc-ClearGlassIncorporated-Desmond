"use client";

// Per-row decision controls for a pending approval. Optimistically disables
// while the server action is in flight and surfaces control-plane errors inline
// so a failed decision is never silently dropped.
import { useState } from "react";
import { approveAction, rejectAction } from "./actions";

export function ApprovalActions({ id }: { id: number }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Server Actions are async, but React 18's startTransition requires a
  // synchronous callback — so track in-flight state explicitly. try/finally
  // guarantees the controls re-enable and a thrown decision surfaces an error
  // inline rather than being silently dropped.
  async function run(decision: "approve" | "reject") {
    setError(null);
    setPending(true);
    try {
      const fn = decision === "approve" ? approveAction : rejectAction;
      const res = await fn(id, note);
      if (!res.ok) setError(res.error ?? "decision failed");
    } catch {
      setError("decision failed — control plane unreachable");
    } finally {
      setPending(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 220 }}>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="decision note (optional)"
        disabled={pending}
        style={{
          padding: "6px 8px",
          borderRadius: 8,
          border: "1px solid rgba(124,150,255,.2)",
          background: "rgba(7,10,20,.6)",
          color: "#eef2ff",
          fontSize: 12,
        }}
      />
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => run("approve")}
          disabled={pending}
          style={btn("#34d399", pending)}
        >
          {pending ? "…" : "Approve"}
        </button>
        <button
          onClick={() => run("reject")}
          disabled={pending}
          style={btn("#f87171", pending)}
        >
          {pending ? "…" : "Reject"}
        </button>
      </div>
      {error && (
        <span role="alert" style={{ color: "#f87171", fontSize: 11 }}>
          {error}
        </span>
      )}
    </div>
  );
}

function btn(color: string, disabled: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: "6px 10px",
    borderRadius: 8,
    border: `1px solid ${color}55`,
    background: `${color}1f`,
    color,
    fontWeight: 600,
    fontSize: 12,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}
