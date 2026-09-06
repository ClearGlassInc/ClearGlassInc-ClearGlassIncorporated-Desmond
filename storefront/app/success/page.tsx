// Post-checkout success page. Stripe Checkout (or the dev mock) redirects here
// after a completed payment; the order is recorded server-side via the Stripe
// webhook (checkout.session.completed).
export default function CheckoutSuccess() {
  return (
    <section style={{ maxWidth: 560 }}>
      <div style={{ fontSize: 40 }}>✅</div>
      <h1 style={{ fontSize: 30, marginTop: 8 }}>Order confirmed</h1>
      <p style={{ color: "#9aa6c8", marginTop: 8, lineHeight: 1.7 }}>
        Thank you — your payment was received. A receipt is on its way to your email, and your order
        has been recorded in the ClearGlass commerce control plane. No fabricated claims, no hidden
        fees.
      </p>
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
