// Thin client for the commerce control plane.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    // Surface the control plane's own message. A rejected checkout explains itself
    // ("unknown sku", "cannot mix recurring and one-time items"), and a bare status
    // code would strand the shopper with nothing actionable.
    const detail = await res
      .json()
      .then((body) => (typeof body?.detail === "string" ? body.detail : null))
      .catch(() => null);
    throw new Error(detail ?? `API ${path} failed: ${res.status}`);
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

// A checkout line names what the customer wants, never what it costs. The control
// plane prices every SKU from its own price book, so a tampered request is rejected
// rather than charged — do not add an `amount` field here.
export interface CheckoutLineItem {
  sku: string;
  quantity?: number;
}

export interface CheckoutSession {
  id: string;
  url: string;
  mode: string; // "live" | "mock"
  checkout_mode: string; // "payment" | "subscription"
  amount_total: number;
  currency: string;
}

// Create a checkout session via the control plane. Returns a live Stripe
// Checkout URL when STRIPE_SECRET_KEY is configured, or a deterministic mock
// session URL otherwise — so the buy flow works in every environment.
//
// `clientReferenceId` is forwarded as Stripe's idempotency key: a double-clicked or
// retried checkout reuses the first session instead of opening a second one.
export async function createCheckout(
  items: CheckoutLineItem[],
  customerEmail?: string,
  clientReferenceId?: string,
): Promise<CheckoutSession> {
  return api<CheckoutSession>("/checkout/session", {
    method: "POST",
    body: JSON.stringify({
      items,
      customer_email: customerEmail ?? null,
      client_reference_id: clientReferenceId ?? newAttemptId(),
    }),
  });
}

// One id per checkout attempt. Stripe treats it as the idempotency key, so it must
// be stable across retries of the same attempt and different between attempts.
export function newAttemptId(): string {
  const globalCrypto = typeof crypto !== "undefined" ? crypto : undefined;
  if (globalCrypto?.randomUUID) return `cg_${globalCrypto.randomUUID()}`;
  return `cg_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}
