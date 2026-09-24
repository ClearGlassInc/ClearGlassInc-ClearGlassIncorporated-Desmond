// Where Stripe Checkout (or the dev mock) returns the buyer.
//
// Arriving here does not mean the money arrived: an asynchronous payment method
// can still fail, and the order is paid only when Stripe's signed webhook says
// so. This page used to announce "your payment was received" to everyone who
// landed on it. It now says the payment is submitted, and shows "verified" only
// when the control plane has verified it.
import { OrderStatusPanel } from "@/lib/OrderStatusPanel";

export default function CheckoutSuccess() {
  return (
    <section style={{ maxWidth: 560 }}>
      <OrderStatusPanel
        title="Payment submitted"
        pending="Thank you. Stripe is confirming your payment; your receipt comes by email once it does, and the order is confirmed only then." />
      <a
        href="/"
        style={{
          display: "inline-block",
          marginTop: 18,
          padding: "12px 22px",
          borderRadius: 10,
          border: "1px solid rgba(124,150,255,.3)",
          background: "linear-gradient(180deg,rgba(124,150,255,.3),rgba(124,150,255,.08))",
          color: "#fff",
          textDecoration: "none",
        }}
      >
        Continue shopping
      </a>
    </section>
  );
}
