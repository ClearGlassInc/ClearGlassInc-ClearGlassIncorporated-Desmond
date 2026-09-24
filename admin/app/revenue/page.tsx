// Revenue cockpit: the owner's read-only view of the CRCS pipeline.
//
// This replaces the cockpit that lived on the public revenue-command.html page
// and asked for the master admin key in the browser. Everything here is fetched
// on the server with the key from the environment; the browser only receives
// rendered HTML. Middleware requires a session for /revenue and
// requireSession() re-checks it.
//
// Read-only on purpose. Stage changes and control-log entries stay on the
// control-plane API until per-person roles exist (CRCS Phase 1, item 1.6), so
// no shared login can alter the pipeline from here.
import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { getRevenueCockpit, listClearGlassOrders, listRevenueControlLog, listRevenueLeads } from "@/lib/api";
import { formatTs } from "@/lib/format";
import { requireSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Revenue — ClearGlass Commerce Admin",
  robots: { index: false, follow: false },
  alternates: { canonical: "/revenue" },
};

const cad = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", currencyDisplay: "code" });
const MUTED = "#aab6d3";
const cell: CSSProperties = { padding: 8, verticalAlign: "top", textAlign: "left" };
const panel: CSSProperties = {
  border: "1px solid rgba(124,150,255,.2)",
  borderRadius: 12,
  padding: 16,
  background: "rgba(17,25,40,.6)",
};

// The executive warning the CRCS specification requires, word for word.
const MISSING_ACTION =
  "Commercial action is missing today. Do not substitute engineering work for sales, delivery, collection, retention, or referral activity.";

function money(value: number | null): string {
  return value === null ? "No data" : cad.format(value);
}

const PROCESSOR_NAMES: Record<string, string> = { stripe: "Stripe", paypal: "PayPal", other: "Other" };

function processorName(provider: string | null): string {
  return provider === null ? "Not chosen" : (PROCESSOR_NAMES[provider] ?? provider);
}

export default async function RevenuePage() {
  await requireSession("/revenue");
  const [cockpit, leads, log, orders] = await Promise.all([
    getRevenueCockpit(),
    listRevenueLeads(50),
    listRevenueControlLog(14),
    listClearGlassOrders(25),
  ]);

  if (!cockpit) {
    return (
      <section aria-labelledby="revenue-title">
        <h1 id="revenue-title">Revenue</h1>
        <p role="alert" style={{ ...panel, color: "#ffb4ae" }}>
          The control plane could not be read, so no figures are shown. Check NEXT_PUBLIC_API_BASE and
          ADMIN_API_KEY on this app, and GET /ready on the control plane.
        </p>
      </section>
    );
  }

  // Each figure carries its definition, so an estimate is never read as revenue.
  const figures: { label: string; value: string; definition: string; verified?: boolean }[] = [
    {
      label: "Confirmed revenue",
      value: money(cockpit.confirmed_revenue_cad),
      definition: "Live payments verified by the Stripe or PayPal webhook, less refunds, open disputes and lost disputes.",
      verified: cockpit.confirmed_revenue_cad > 0,
    },
    {
      label: "Gross received",
      value: money(cockpit.gross_revenue_cad),
      definition: "Every verified live payment before refunds and disputes.",
    },
    {
      label: "Refunded",
      value: money(cockpit.refunded_cad),
      definition: "Refunds and reversals the processor has settled.",
    },
    {
      label: "In open disputes",
      value: money(cockpit.disputed_open_cad),
      definition: "Held by a chargeback that is not yet decided. Counts again if the dispute is won.",
    },
    {
      label: "Lost to disputes",
      value: money(cockpit.dispute_lost_cad),
      definition: "Returned to the cardholder by a lost chargeback.",
    },
    {
      label: "Pipeline (estimate)",
      value: money(cockpit.pipeline_estimate_cad),
      definition: "Unverified expected value on open leads, entered by hand. Not revenue.",
    },
    {
      label: "MRR (verified)",
      value: money(cockpit.verified_mrr_cad),
      definition:
        cockpit.verified_mrr_cad === null
          ? "No subscriptions table: migration 006 is not applied."
          : `Active Stripe subscriptions on price-book Prices: ${cockpit.active_subscriptions} active, ` +
            `${cockpit.past_due_subscriptions} past due, ${cockpit.unpriced_subscriptions} on unknown Prices (excluded).`,
    },
    {
      label: "Contracted MRR (entered by hand)",
      value: money(cockpit.mrr_cad),
      definition: "Recurring value typed onto won and active leads. A contract figure, not Stripe data.",
    },
    {
      label: "Gross margin",
      value: money(cockpit.gross_margin_cad),
      definition: "Confirmed revenue less recorded delivery costs. No data until a cost is recorded.",
    },
    {
      label: "Close rate",
      value: cockpit.close_rate === null ? "No data" : `${Math.round(cockpit.close_rate * 100)}%`,
      definition: `Won ÷ (won + lost): ${cockpit.won} won, ${cockpit.lost} lost.`,
    },
    { label: "Test-mode revenue", value: money(cockpit.test_revenue_cad), definition: "Stripe test mode. Never counted." },
    { label: "Qualified leads", value: String(cockpit.qualified_leads), definition: "Leads currently at QUALIFIED." },
    { label: "New leads (7 days)", value: String(cockpit.new_leads), definition: "Created in the last 7 days." },
    { label: "Meetings booked (30 days)", value: String(cockpit.meetings_booked), definition: "meeting_booked activities." },
    { label: "Proposals", value: String(cockpit.proposals), definition: "Leads from PROPOSAL_PENDING to WON." },
    { label: "Open service orders", value: String(cockpit.open_service_orders), definition: "Paid work not yet delivered." },
    { label: "Next actions due", value: String(cockpit.due_actions), definition: "Open leads whose next action date has passed." },
    {
      label: "Checkouts started (30 days)",
      value: cockpit.checkout_started_30d === undefined ? "No data" : String(cockpit.checkout_started_30d),
      definition: "A buyer reached Stripe or PayPal. Not a payment: only a verified webhook is.",
    },
  ];
  const flagged = cockpit.reconciliation_required ?? 0;
  const byProvider = cockpit.revenue_by_provider ?? [];

  return (
    <section aria-labelledby="revenue-title" style={{ display: "grid", gap: 20 }}>
      <header>
        <h1 id="revenue-title" style={{ marginBottom: 4 }}>
          Revenue
        </h1>
        <p style={{ color: MUTED, margin: 0 }}>Generated {formatTs(cockpit.generated_at)}. Read-only.</p>
      </header>

      {cockpit.revenue_action_required ? (
        <p role="alert" style={{ ...panel, borderColor: "#f2cf75", color: "#f2cf75", margin: 0 }}>
          <strong>Warning: </strong>
          {MISSING_ACTION}
        </p>
      ) : (
        <p style={{ ...panel, margin: 0 }}>Today&apos;s Revenue Control Log has a commercial action in progress or done.</p>
      )}

      {flagged > 0 ? (
        <p role="alert" style={{ ...panel, borderColor: "#ff8a80", color: "#ffb4ae", margin: 0 }}>
          <strong>Reconciliation required: </strong>
          {flagged} ClearGlass {flagged === 1 ? "order disagrees" : "orders disagree"} with the payments recorded against them (a
          second payment, an amount or currency mismatch, or money after a cancel). Delivery is held. Nothing is
          corrected automatically: resolve it at Stripe or PayPal, then review the order below.
        </p>
      ) : null}

      <section aria-labelledby="figures-title" style={panel}>
        <h2 id="figures-title" style={{ marginTop: 0 }}>
          Figures and definitions
        </h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ color: MUTED }}>
              <th scope="col" style={cell}>Measure</th>
              <th scope="col" style={cell}>Value</th>
              <th scope="col" style={cell}>Definition</th>
            </tr>
          </thead>
          <tbody>
            {figures.map((f) => (
              <tr key={f.label} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                <th scope="row" style={{ ...cell, fontWeight: 600 }}>
                  {f.label}
                </th>
                <td style={{ ...cell, color: f.verified ? "#f2cf75" : undefined, whiteSpace: "nowrap" }}>
                  {f.value}
                  {f.verified ? " (verified)" : ""}
                </td>
                <td style={{ ...cell, color: MUTED }}>{f.definition}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="provider-title" style={{ ...panel, overflowX: "auto" }}>
        <h2 id="provider-title" style={{ marginTop: 0 }}>
          Verified revenue by processor
        </h2>
        {byProvider.length === 0 ? (
          <p style={{ color: MUTED, margin: 0 }}>This control plane does not report a processor split yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <caption style={{ textAlign: "left", color: MUTED, paddingBottom: 8 }}>
              Live payments only, by the same rule as confirmed revenue. The rows add up to confirmed revenue.
            </caption>
            <thead>
              <tr style={{ color: MUTED }}>
                <th scope="col" style={cell}>Processor</th>
                <th scope="col" style={cell}>Paid orders</th>
                <th scope="col" style={cell}>Gross</th>
                <th scope="col" style={cell}>Refunded</th>
                <th scope="col" style={cell}>Confirmed</th>
              </tr>
            </thead>
            <tbody>
              {byProvider.map((row) => (
                <tr key={row.provider} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                  <th scope="row" style={{ ...cell, fontWeight: 600 }}>{processorName(row.provider)}</th>
                  <td style={cell}>{row.orders}</td>
                  <td style={cell}>{money(row.gross_cad)}</td>
                  <td style={cell}>{money(row.refunded_cad)}</td>
                  <td style={cell}>{money(row.confirmed_revenue_cad)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="orders-title" style={{ ...panel, overflowX: "auto" }}>
        <h2 id="orders-title" style={{ marginTop: 0 }}>
          ClearGlass orders
        </h2>
        {orders === null ? (
          <p role="alert">Orders could not be read from the control plane.</p>
        ) : orders.length === 0 ? (
          <p style={{ color: MUTED, margin: 0 }}>No ClearGlass orders yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <caption style={{ textAlign: "left", color: MUTED, paddingBottom: 8 }}>
              Newest 25. &ldquo;Verified&rdquo; means a signed Stripe or PayPal event settled it; a buyer returning from
              checkout is not enough.
            </caption>
            <thead>
              <tr style={{ color: MUTED }}>
                <th scope="col" style={cell}>Order</th>
                <th scope="col" style={cell}>Amount</th>
                <th scope="col" style={cell}>Processor</th>
                <th scope="col" style={cell}>State</th>
                <th scope="col" style={cell}>Campaign</th>
                <th scope="col" style={cell}>Reconciliation</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_ref} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                  <td style={cell}>
                    <code>{order.order_ref}</code>
                    <br />
                    <span style={{ color: MUTED }}>{order.offer}</span>
                  </td>
                  <td style={{ ...cell, whiteSpace: "nowrap" }}>
                    {order.amount.toFixed(2)} {order.currency}
                  </td>
                  <td style={cell}>
                    {processorName(order.provider)}
                    {order.environment === "test" ? <span style={{ color: MUTED }}> · test mode</span> : null}
                  </td>
                  <td style={cell}>
                    {order.payment_state}
                    {order.payment_verified ? " (verified)" : ""}
                    <br />
                    <span style={{ color: MUTED }}>Fulfillment: {order.fulfillment_state}</span>
                  </td>
                  <td style={cell}>{order.utm_campaign ?? "Unattributed"}</td>
                  <td style={{ ...cell, color: order.reconciliation_required ? "#ffb4ae" : MUTED, whiteSpace: "pre-line" }}>
                    {order.reconciliation_required ? order.reconciliation_reason : "None"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="campaign-title" style={{ ...panel, overflowX: "auto" }}>
        <h2 id="campaign-title" style={{ marginTop: 0 }}>
          Confirmed revenue by campaign
        </h2>
        {cockpit.revenue_by_campaign.length === 0 ? (
          <p style={{ color: MUTED, margin: 0 }}>No verified live payments yet, so no campaign has produced revenue.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <caption style={{ textAlign: "left", color: MUTED, paddingBottom: 8 }}>
              From the utm_campaign carried through checkout to the paid order. Payment Links carry none, so
              their sales show as unattributed.
            </caption>
            <thead>
              <tr style={{ color: MUTED }}>
                <th scope="col" style={cell}>Campaign</th>
                <th scope="col" style={cell}>Paid orders</th>
                <th scope="col" style={cell}>Confirmed revenue</th>
              </tr>
            </thead>
            <tbody>
              {cockpit.revenue_by_campaign.map((row) => (
                <tr key={row.campaign} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                  <th scope="row" style={{ ...cell, fontWeight: 600 }}>{row.campaign}</th>
                  <td style={cell}>{row.orders}</td>
                  <td style={cell}>{money(row.confirmed_revenue_cad)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="health-title" style={panel}>
        <h2 id="health-title" style={{ marginTop: 0 }}>
          Integration health
        </h2>
        <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
          <li>Stripe webhook: {cockpit.webhook_health === "EVIDENCE_PRESENT" ? "events received" : "no events received yet"}</li>
          <li>Booking: {cockpit.booking_health === "CONFIGURED" ? "booking link configured" : "manual follow-up (no booking link set)"}</li>
          <li>Internal CRM: {cockpit.crm_health.toLowerCase()}</li>
        </ul>
      </section>

      <section aria-labelledby="leads-title" style={{ ...panel, overflowX: "auto" }}>
        <h2 id="leads-title" style={{ marginTop: 0 }}>
          Leads
        </h2>
        {leads === null ? (
          <p role="alert">Leads could not be read from the control plane.</p>
        ) : leads.length === 0 ? (
          <p style={{ color: MUTED }}>No leads recorded yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <caption style={{ textAlign: "left", color: MUTED, paddingBottom: 8 }}>
              Newest 50. The score orders review only; it never rejects a lead.
            </caption>
            <thead>
              <tr style={{ color: MUTED }}>
                <th scope="col" style={cell}>Lead</th>
                <th scope="col" style={cell}>Stage</th>
                <th scope="col" style={cell}>Score and reasons</th>
                <th scope="col" style={cell}>Next action</th>
                <th scope="col" style={cell}>Owner</th>
                <th scope="col" style={cell}>Source</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                  <td style={cell}>
                    {lead.full_name}
                    <br />
                    <span style={{ color: MUTED }}>
                      {lead.company || "No company given"} · {lead.email}
                    </span>
                  </td>
                  <td style={cell}>{lead.stage}</td>
                  <td style={cell}>
                    {lead.lead_score}
                    <br />
                    <span style={{ color: MUTED }}>{lead.score_explanation}</span>
                  </td>
                  <td style={cell}>
                    {lead.next_action}
                    {lead.next_action_at ? (
                      <>
                        <br />
                        <span style={{ color: MUTED }}>Due {formatTs(lead.next_action_at)}</span>
                      </>
                    ) : null}
                  </td>
                  <td style={cell}>{lead.owner}</td>
                  <td style={cell}>{lead.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="log-title" style={{ ...panel, overflowX: "auto" }}>
        <h2 id="log-title" style={{ marginTop: 0 }}>
          Revenue Control Log
        </h2>
        {log === null ? (
          <p role="alert">The control log could not be read from the control plane.</p>
        ) : log.length === 0 ? (
          <p style={{ color: MUTED }}>No entries yet. Record today&apos;s commercial action with POST /revenue/control-log.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <caption style={{ textAlign: "left", color: MUTED, paddingBottom: 8 }}>Latest 14 entries.</caption>
            <thead>
              <tr style={{ color: MUTED }}>
                <th scope="col" style={cell}>Date</th>
                <th scope="col" style={cell}>Action and target</th>
                <th scope="col" style={cell}>Evidence and result</th>
                <th scope="col" style={cell}>Next action</th>
                <th scope="col" style={cell}>Status</th>
              </tr>
            </thead>
            <tbody>
              {log.map((row) => (
                <tr key={row.id} style={{ borderTop: "1px solid rgba(124,150,255,.1)" }}>
                  <td style={{ ...cell, whiteSpace: "nowrap" }}>{row.action_date}</td>
                  <td style={cell}>
                    {row.action}
                    {row.target ? <span style={{ color: MUTED }}> · {row.target}</span> : null}
                  </td>
                  <td style={cell}>
                    {row.evidence || "No evidence recorded"}
                    {row.result ? <span style={{ color: MUTED }}> · {row.result}</span> : null}
                  </td>
                  <td style={cell}>
                    {row.next_action || "None recorded"}
                    {row.due_date ? <span style={{ color: MUTED }}> · due {row.due_date}</span> : null}
                  </td>
                  <td style={cell}>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}
