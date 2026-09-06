"use client";

// Cart page. Lists the in-progress cart, lets the shopper adjust quantities, and
// checks out the whole cart as one governed checkout session (live Stripe URL or
// the dev mock). No fabricated scarcity or pressure — just the cart and the total.
import { useState } from "react";
import { createCheckout } from "@/lib/api";
import { formatPrice } from "@/lib/catalog";
import { useCart } from "@/lib/cart";

export default function CartPage() {
  const { lines, total, setQuantity, remove } = useCart();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currency = lines[0]?.currency ?? "cad";

  async function checkout() {
    if (lines.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      // Send SKUs and quantities only — the control plane prices the cart, so the
      // total charged never depends on what is sitting in localStorage.
      const session = await createCheckout(
        lines.map((l) => ({ sku: l.slug, quantity: l.quantity })),
      );
      window.location.href = session.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout failed — please try again.");
      setLoading(false);
    }
  }

  return (
    <section style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 30 }}>Your cart</h1>

      {lines.length === 0 ? (
        <p style={{ color: "#9aa6c8", marginTop: 12 }}>
          Your cart is empty.{" "}
          <a href="/" style={{ color: "#9fc4ff" }}>
            Browse the collection →
          </a>
        </p>
      ) : (
        <>
          <ul style={{ listStyle: "none", padding: 0, margin: "18px 0 0" }}>
            {lines.map((l) => (
              <li
                key={l.slug}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  padding: "14px 0",
                  borderTop: "1px solid rgba(124,150,255,.12)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{l.title}</div>
                  <div style={{ color: "#a78bfa", fontSize: 13, marginTop: 4 }}>
                    {formatPrice(l.amount, l.currency)} each
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button onClick={() => setQuantity(l.slug, l.quantity - 1)} style={stepBtn}>
                    −
                  </button>
                  <span style={{ minWidth: 24, textAlign: "center" }}>{l.quantity}</span>
                  <button onClick={() => setQuantity(l.slug, l.quantity + 1)} style={stepBtn}>
                    +
                  </button>
                </div>
                <div style={{ minWidth: 90, textAlign: "right", fontWeight: 600 }}>
                  {formatPrice(l.amount * l.quantity, l.currency)}
                </div>
                <button
                  onClick={() => remove(l.slug)}
                  aria-label={`Remove ${l.title}`}
                  style={{ ...stepBtn, color: "#f87171", borderColor: "rgba(248,113,113,.4)" }}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 18,
              paddingTop: 18,
              borderTop: "1px solid rgba(124,150,255,.2)",
            }}
          >
            <span style={{ color: "#9aa6c8" }}>Total</span>
            <span style={{ fontSize: 22, fontWeight: 800, color: "#a78bfa" }}>
              {formatPrice(total, currency)}
            </span>
          </div>

          <button
            onClick={checkout}
            disabled={loading}
            style={{
              marginTop: 18,
              padding: "12px 22px",
              borderRadius: 10,
              border: "1px solid rgba(124,150,255,.3)",
              background: "linear-gradient(180deg,rgba(124,150,255,.3),rgba(124,150,255,.08))",
              color: "#fff",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
              fontWeight: 600,
            }}
          >
            {loading ? "Starting checkout…" : "Checkout"}
          </button>
          {error && (
            <p role="alert" style={{ color: "#f87171", marginTop: 12 }}>
              {error}
            </p>
          )}
        </>
      )}
    </section>
  );
}

const stepBtn: React.CSSProperties = {
  width: 30,
  height: 30,
  borderRadius: 8,
  border: "1px solid rgba(124,150,255,.3)",
  background: "rgba(12,16,38,.6)",
  color: "#eef2ff",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
};
