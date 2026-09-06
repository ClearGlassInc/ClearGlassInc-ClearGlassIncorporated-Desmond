// Public storefront home. In production this lists products from the control
// plane; the scaffold renders the shared static catalog so it builds without a
// live API and stays in sync with the checkout pricing.
import { CATALOG, formatOfferPrice } from "@/lib/catalog";
import { AddToCart } from "@/lib/AddToCart";

export default function Home() {
  return (
    <section>
      <h1 style={{ fontSize: 34 }}>Security engagements</h1>
      <p style={{ color: "#9aa6c8" }}>
        Storefront powered by the ClearGlass commerce control plane. Prices are set server-side and
        every pricing or copy change is governed and audited.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))",
          gap: 16,
          marginTop: 24,
        }}
      >
        {CATALOG.map((p) => (
          <div
            key={p.slug}
            style={{
              border: "1px solid rgba(124,150,255,.16)",
              borderRadius: 14,
              padding: 20,
              background: "rgba(12,16,38,.6)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <a
              href={`/products/${p.slug}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <div style={{ fontWeight: 600 }}>{p.title}</div>
              <div style={{ color: "#9aa6c8", fontSize: 13, marginTop: 6, lineHeight: 1.5 }}>
                {p.blurb}
              </div>
              <div style={{ color: "#a78bfa", marginTop: 8 }}>{formatOfferPrice(p)}</div>
              {p.note && (
                <div style={{ color: "#9aa6c8", fontSize: 12, marginTop: 4 }}>{p.note}</div>
              )}
            </a>
            <AddToCart product={p} block />
          </div>
        ))}
      </div>
    </section>
  );
}
