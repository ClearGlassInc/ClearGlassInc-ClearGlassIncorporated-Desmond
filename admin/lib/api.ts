// Admin client for the commerce control plane.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
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
