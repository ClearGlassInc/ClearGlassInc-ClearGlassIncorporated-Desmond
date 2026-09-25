"use client";

// Live order status for the pages a buyer lands on after Stripe or PayPal.
// Polls the control plane briefly. It says "verified" only when the control
// plane does, which happens only after a signed processor webhook; until then
// it says the payment is awaiting confirmation, never that it was received.
import { useEffect, useState } from "react";
import { getOrderStatus, type OrderStatus } from "./api";
import { formatPrice } from "./catalog";
import { forgetOrder, recalledOrder } from "./order-session";

const POLLS = 10;
const INTERVAL_MS = 3000;

export function OrderStatusPanel({ title, pending }: { title: string; pending: string }) {
  const [status, setStatus] = useState<OrderStatus | null>(null);
  const [orderRef, setOrderRef] = useState<string | null>(null);

  useEffect(() => {
    const remembered = recalledOrder();
    if (!remembered) return;
    setOrderRef(remembered.orderRef);
    let cancelled = false;
    let polls = 0;
    async function poll() {
      try {
        const next = await getOrderStatus(remembered!.orderRef);
        if (cancelled) return;
        setStatus(next);
        if (next.payment_verified) {
          forgetOrder();
          return;
        }
      } catch {
        // Unreachable control plane: keep the neutral message.
      }
      polls += 1;
      if (polls < POLLS && !cancelled) setTimeout(poll, INTERVAL_MS);
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status?.payment_verified) {
    return (
      <div aria-live="polite">
        <h1 style={heading}>Payment verified</h1>
        <p style={text}>
          Order <code>{status.order_ref}</code> for {status.offer},{" "}
          {formatPrice(Math.round(status.amount * 100), status.currency.toLowerCase())}. We will contact you to start
          the work.
        </p>
      </div>
    );
  }
  return (
    <div aria-live="polite">
      <h1 style={heading}>{title}</h1>
      <p style={text}>
        {pending}
        {orderRef ? (
          <>
            {" "}
            Order reference: <code>{orderRef}</code>
            {status ? ` (status: ${status.payment_state.toLowerCase().replace(/_/g, " ")})` : ""}.
          </>
        ) : null}
      </p>
    </div>
  );
}

const heading: React.CSSProperties = { fontSize: 30, marginTop: 8 };

const text: React.CSSProperties = { color: "#9aa6c8", marginTop: 8, lineHeight: 1.7 };
