// Presentation helpers shared across the admin cockpit. Risk tiers mirror the
// control-plane governance model (low → auto, medium → review, high/critical →
// human approval) so the cockpit colour-codes exactly what the API gated.

export function riskColor(tier: string): string {
  switch (tier) {
    case "critical":
      return "#f87171";
    case "high":
      return "#fb923c";
    case "medium":
      return "#facc15";
    default:
      return "#34d399"; // low
  }
}

export function resultColor(result: string): string {
  switch (result) {
    case "executed":
    case "ok":
      return "#34d399";
    case "queued_for_approval":
    case "drafted":
      return "#facc15";
    case "rejected":
    case "error":
      return "#f87171";
    default:
      return "#9aa6c8";
  }
}

// Render the stored UTC timestamp deterministically so server and client markup
// match (avoids React hydration warnings from locale-dependent formatting).
export function formatTs(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}
