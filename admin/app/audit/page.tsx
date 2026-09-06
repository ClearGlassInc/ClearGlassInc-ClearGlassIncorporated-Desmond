// Audit ledger viewer — the append-only record of every governed action. This
// is the operator's accountability surface: timestamp, actor, action, target,
// result and risk score for each event, newest first.
import { listEvents } from "../../lib/api";
import { formatTs, resultColor, riskColor } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const events = await listEvents(200);
  return (
    <section>
      <h1 style={{ fontSize: 30 }}>Audit ledger</h1>
      <p style={{ color: "#9aa6c8" }}>
        Append-only event log from the control plane. Every material change is recorded here with
        its actor and risk score — nothing material happens off-ledger.
      </p>
      {events.length === 0 ? (
        <p style={{ color: "#5f6a8a", fontFamily: "monospace", marginTop: 18 }}>
          No events yet, or the control plane is unreachable at the configured API base.
        </p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 18, fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#9aa6c8", fontSize: 12 }}>
              <th style={{ padding: 8 }}>#</th>
              <th style={{ padding: 8 }}>Timestamp</th>
              <th style={{ padding: 8 }}>Actor</th>
              <th style={{ padding: 8 }}>Action</th>
              <th style={{ padding: 8 }}>Target</th>
              <th style={{ padding: 8 }}>Result</th>
              <th style={{ padding: 8 }}>Risk</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                <td style={{ padding: 8, fontFamily: "monospace", color: "#5f6a8a" }}>{e.id}</td>
                <td style={{ padding: 8, color: "#5f6a8a", whiteSpace: "nowrap" }}>
                  {formatTs(e.ts)}
                </td>
                <td style={{ padding: 8, color: "#9fc4ff" }}>{e.actor}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>{e.action}</td>
                <td style={{ padding: 8, color: "#9aa6c8" }}>{e.target ?? "—"}</td>
                <td style={{ padding: 8, color: resultColor(e.result), fontWeight: 600 }}>
                  {e.result}
                </td>
                <td style={{ padding: 8 }}>
                  <span style={{ color: riskColor(e.risk_tier), fontWeight: 700 }}>
                    {e.risk_score}
                  </span>{" "}
                  <span style={{ color: "#5f6a8a", fontSize: 11 }}>{e.risk_tier}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
