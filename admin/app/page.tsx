// Admin overview — KPI snapshot, governance posture, and a recent-activity
// preview, all pulled live from the control plane at request time.
import { getOverview, listApprovals, listEvents } from "../lib/api";
import { formatTs, resultColor, riskColor } from "../lib/format";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [m, pending, events] = await Promise.all([
    getOverview(),
    listApprovals("pending"),
    listEvents(8),
  ]);

  return (
    <section>
      <h1 style={{ fontSize: 30 }}>Store overview</h1>

      {pending.length > 0 && (
        <a
          href="/approvals"
          style={{
            display: "block",
            marginTop: 14,
            padding: "12px 16px",
            borderRadius: 12,
            border: "1px solid rgba(251,146,60,.4)",
            background: "rgba(251,146,60,.1)",
            color: "#fdba74",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          ⚠ {pending.length} action{pending.length === 1 ? "" : "s"} awaiting human approval →
        </a>
      )}

      {!m ? (
        <p style={{ color: "#9aa6c8", marginTop: 18 }}>
          Control plane unreachable. Start it at <code>http://localhost:8000</code>.
        </p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
            gap: 14,
            marginTop: 18,
          }}
        >
          <Stat label="Revenue" value={`$${m.revenue}`} />
          <Stat label="Orders" value={`${m.orders}`} />
          <Stat label="Conversion" value={`${(m.conversion_rate * 100).toFixed(2)}%`} />
          <Stat label="AOV" value={`$${m.aov}`} />
          <Stat label="Refund rate" value={`${(m.refund_rate * 100).toFixed(2)}%`} />
          <Stat label="Open approvals" value={`${m.open_approvals}`} />
        </div>
      )}

      <h2 style={{ fontSize: 18, marginTop: 32, marginBottom: 8 }}>Recent activity</h2>
      {events.length === 0 ? (
        <p style={{ color: "#5f6a8a", fontFamily: "monospace" }}>No events yet.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {events.map((e) => (
            <li
              key={e.id}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "baseline",
                padding: "8px 0",
                borderTop: "1px solid rgba(124,150,255,.1)",
                fontSize: 13,
              }}
            >
              <span style={{ color: "#5f6a8a", whiteSpace: "nowrap", fontFamily: "monospace" }}>
                {formatTs(e.ts)}
              </span>
              <span style={{ color: "#9fc4ff" }}>{e.actor}</span>
              <span style={{ fontWeight: 600 }}>{e.action}</span>
              <span style={{ color: "#9aa6c8" }}>{e.target ?? ""}</span>
              <span style={{ marginLeft: "auto", color: resultColor(e.result), fontWeight: 600 }}>
                {e.result}
              </span>
              <span style={{ color: riskColor(e.risk_tier), fontSize: 11, fontWeight: 700 }}>
                {e.risk_tier}
              </span>
            </li>
          ))}
        </ul>
      )}
      <a href="/audit" style={{ color: "#9fc4ff", fontSize: 13, display: "inline-block", marginTop: 10 }}>
        View full audit ledger →
      </a>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        border: "1px solid rgba(124,150,255,.16)",
        borderRadius: 12,
        padding: 16,
        background: "rgba(12,16,38,.6)",
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 800, color: "#a78bfa" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#9aa6c8", marginTop: 4 }}>{label}</div>
    </div>
  );
}
