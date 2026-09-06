// The human approval gate. High/critical actions land here and execute only
// when approved. Decisions are made via server actions that post to the control
// plane and write to the append-only audit ledger.
import { listApprovals } from "../../lib/api";
import { formatTs, riskColor } from "../../lib/format";
import { ApprovalActions } from "./ApprovalActions";

// Decisions mutate server state, so never serve a cached render.
export const dynamic = "force-dynamic";

export default async function ApprovalsPage() {
  const approvals = await listApprovals("pending");
  return (
    <section>
      <h1 style={{ fontSize: 30 }}>Pending approvals</h1>
      <p style={{ color: "#9aa6c8" }}>
        Pricing, payments, refunds, fulfillment and reorders are gated. Nothing here has executed —
        approving only records the human decision; the side effect runs downstream.
      </p>
      {approvals.length === 0 ? (
        <p style={{ color: "#5f6a8a", fontFamily: "monospace", marginTop: 18 }}>
          No pending approvals. The queue is clear.
        </p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 18 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#9aa6c8", fontSize: 12 }}>
              <th style={{ padding: 8 }}>#</th>
              <th style={{ padding: 8 }}>Action</th>
              <th style={{ padding: 8 }}>Target</th>
              <th style={{ padding: 8 }}>Risk</th>
              <th style={{ padding: 8 }}>Requested by</th>
              <th style={{ padding: 8 }}>Created</th>
              <th style={{ padding: 8 }}>Decision</th>
            </tr>
          </thead>
          <tbody>
            {approvals.map((a) => (
              <tr key={a.id} style={{ borderTop: "1px solid rgba(124,150,255,.12)" }}>
                <td style={{ padding: 8, fontFamily: "monospace" }}>{a.id}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>{a.action}</td>
                <td style={{ padding: 8, color: "#9aa6c8" }}>{a.target ?? "—"}</td>
                <td style={{ padding: 8 }}>
                  <span
                    style={{
                      color: riskColor(a.risk_tier),
                      fontWeight: 700,
                      textTransform: "uppercase",
                      fontSize: 12,
                    }}
                  >
                    {a.risk_tier}
                  </span>{" "}
                  <span style={{ color: "#5f6a8a", fontSize: 12 }}>({a.risk_score})</span>
                </td>
                <td style={{ padding: 8, color: "#9aa6c8" }}>{a.requested_by}</td>
                <td style={{ padding: 8, color: "#5f6a8a", fontSize: 12 }}>
                  {formatTs(a.created_at)}
                </td>
                <td style={{ padding: 8 }}>
                  <ApprovalActions id={a.id} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
