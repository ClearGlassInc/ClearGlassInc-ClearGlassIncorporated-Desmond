// Admin client for the commerce control plane. Server-only: it carries the
// control-plane admin key, which must never reach a browser (ADR 0002 rule 2).
import "server-only";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// The control plane gates approvals, the audit ledger, metrics and the revenue
// pipeline behind ADMIN_API_KEY. Without this header every admin page read an
// empty list (401) as soon as a key was set, which production requires.
export function controlPlaneHeaders(): Record<string, string> {
  const key = process.env.ADMIN_API_KEY;
  return key ? { Authorization: `Bearer ${key}` } : {};
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...controlPlaneHeaders(), ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export interface MetricsOverview {
  revenue: number;
  orders: number;
  conversion_rate: number;
  aov: number;
  refund_rate: number;
  open_approvals: number;
  window_days: number;
}

export interface Approval {
  id: number;
  action: string;
  target: string | null;
  risk_score: number;
  risk_tier: string;
  status: string;
  requested_by: string;
  decided_by: string | null;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  ts: string;
  actor: string;
  action: string;
  target: string | null;
  result: string;
  risk_score: number;
  risk_tier: string;
}

// Read helpers used by server components. Each tolerates an unreachable control
// plane by surfacing a typed fallback rather than crashing the render.
export async function getOverview(windowDays = 7): Promise<MetricsOverview | null> {
  try {
    return await api<MetricsOverview>(`/metrics/overview?window_days=${windowDays}`);
  } catch {
    return null;
  }
}

export async function listApprovals(status = "pending"): Promise<Approval[]> {
  try {
    return await api<Approval[]>(`/approvals?status=${encodeURIComponent(status)}`);
  } catch {
    return [];
  }
}

export async function listEvents(limit = 100): Promise<AuditEvent[]> {
  try {
    return await api<AuditEvent[]>(`/events?limit=${limit}`);
  } catch {
    return [];
  }
}

// ── ClearGlass Revenue Command System (control-plane /revenue/*) ─────────────
// Field names mirror control-plane/app/schemas.py. Money is CAD.

export interface RevenueCockpit {
  generated_at: string;
  confirmed_revenue_cad: number;
  gross_revenue_cad: number;
  refunded_cad: number;
  disputed_open_cad: number;
  dispute_lost_cad: number;
  verified_mrr_cad: number | null;
  active_subscriptions: number | null;
  past_due_subscriptions: number | null;
  unpriced_subscriptions: number | null;
  revenue_by_campaign: { campaign: string; orders: number; confirmed_revenue_cad: number }[];
  test_revenue_cad: number;
  pipeline_estimate_cad: number;
  mrr_cad: number;
  gross_margin_cad: number | null;
  qualified_leads: number;
  new_leads: number;
  meetings_booked: number;
  proposals: number;
  won: number;
  lost: number;
  close_rate: number | null;
  open_service_orders: number;
  due_actions: number;
  webhook_health: string;
  booking_health: string;
  crm_health: string;
  revenue_action_required: boolean;
  // Migration 010. Optional so this page still renders against an older control plane.
  revenue_by_provider?: {
    provider: string;
    orders: number;
    gross_cad: number;
    refunded_cad: number;
    confirmed_revenue_cad: number;
  }[];
  commercial_orders_by_state?: Record<string, number>;
  reconciliation_required?: number;
  checkout_started_30d?: number;
}

// A ClearGlass order (control-plane/app/commerce_orders.py admin_view).
export interface ClearGlassOrder {
  order_ref: string;
  offer: string;
  amount: number;
  currency: string;
  provider: string | null;
  payment_state: string;
  payment_verified: boolean;
  fulfillment_state: string;
  state: string;
  environment: string;
  utm_campaign: string | null;
  reconciliation_required: boolean;
  reconciliation_reason: string | null;
  created_at: string | null;
  payments: { id: number; provider: string; status: string; total: number; currency: string; environment: string }[];
}

export interface RevenueLead {
  id: number;
  public_ref: string;
  full_name: string;
  email: string;
  company: string | null;
  service_interest: string;
  source: string;
  stage: string;
  owner: string;
  next_action: string;
  next_action_at: string | null;
  lead_score: number;
  score_explanation: string;
  consent_marketing: boolean;
  created_at: string;
}

export interface RevenueControlLogRow {
  id: number;
  action_date: string;
  action: string;
  target: string;
  expected_outcome: string;
  evidence: string;
  result: string;
  next_action: string;
  due_date: string | null;
  owner: string;
  status: string;
}

// These return null when the control plane cannot be read, so the page can say
// "no data" instead of showing zeros that look like real figures.
export async function getRevenueCockpit(): Promise<RevenueCockpit | null> {
  try {
    return await api<RevenueCockpit>("/revenue/cockpit");
  } catch {
    return null;
  }
}

export async function listRevenueLeads(limit = 50): Promise<RevenueLead[] | null> {
  try {
    return await api<RevenueLead[]>(`/revenue/leads?limit=${limit}`);
  } catch {
    return null;
  }
}

export async function listRevenueControlLog(limit = 14): Promise<RevenueControlLogRow[] | null> {
  try {
    return await api<RevenueControlLogRow[]>(`/revenue/control-log?limit=${limit}`);
  } catch {
    return null;
  }
}

export async function listClearGlassOrders(limit = 25): Promise<ClearGlassOrder[] | null> {
  try {
    return await api<ClearGlassOrder[]>(`/commerce/orders?limit=${limit}`);
  } catch {
    return null;
  }
}
