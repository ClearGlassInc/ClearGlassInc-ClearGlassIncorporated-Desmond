"use client";

// Which ClearGlass order this tab is paying. Kept in sessionStorage so the
// return pages can ask the control plane for its verified status, and so a
// buyer who comes back from Stripe and chooses PayPal pays the *same* order:
// the control plane then refuses a second checkout once one payment settles,
// and flags a second payment instead of losing it. Every access is guarded,
// because storage is unavailable in some private windows.
const KEY = "clearglass-order-v1";

export interface RememberedOrder {
  orderRef: string;
  sku: string;
  quantity: number;
}

export function rememberOrder(order: RememberedOrder): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(order));
  } catch {
    // No storage: the return page falls back to a message without a live status.
  }
}

export function recalledOrder(): RememberedOrder | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as RememberedOrder;
    return typeof value?.orderRef === "string" && /^CG-ORD-20\d\d-[0-9A-Z]{8}$/.test(value.orderRef) ? value : null;
  } catch {
    return null;
  }
}

export function forgetOrder(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Nothing to forget.
  }
}
