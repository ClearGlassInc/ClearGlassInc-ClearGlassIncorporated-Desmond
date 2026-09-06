// Post-checkout cancel page. Stripe Checkout (or the dev mock) redirects here
// when a customer abandons or cancels payment. No charge is made.
export default function CheckoutCancel() {
  return (
    <section style={{ maxWidth: 560 }}>
      <div style={{ fontSize: 40 }}>↩️</div>
      <h1 style={{ fontSize: 30, marginTop: 8 }}>Checkout cancelled</h1>
      <p style={{ color: "#9aa6c8", marginTop: 8, lineHeight: 1.7 }}>
        No payment was taken. Your cart is still available whenever you’re ready — pick up where you
        left off, no pressure.
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
        Back to the collection
      </a>
    </section>
  );
}
