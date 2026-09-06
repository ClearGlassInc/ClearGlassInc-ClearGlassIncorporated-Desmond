"use client";

// Client shell for the storefront: provides the cart context to the whole app
// and renders the header with a live item-count badge. Server-rendered page
// content is passed through as children, so pages stay server components.
import type { ReactNode } from "react";
import { CartProvider, useCart } from "./cart";

export function StoreShell({ children }: { children: ReactNode }) {
  return (
    <CartProvider>
      <Header />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: 24 }}>{children}</main>
      <footer style={{ maxWidth: 1080, margin: "0 auto", padding: "0 24px 24px", color: "#9aa6c8", fontSize: 13 }}>
        © ClearGlass Inc. All rights reserved.
      </footer>
    </CartProvider>
  );
}

function Header() {
  const { count } = useCart();
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 24px",
        borderBottom: "1px solid rgba(124,150,255,.16)",
      }}
    >
      <a href="/" style={{ color: "inherit", textDecoration: "none" }}>
        <strong>ClearGlass Store</strong>
      </a>
      <a
        href="/cart"
        style={{
          color: "#9fc4ff",
          textDecoration: "none",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        Cart
        <span
          style={{
            minWidth: 20,
            textAlign: "center",
            padding: "1px 7px",
            borderRadius: 999,
            background: count > 0 ? "#a78bfa" : "rgba(124,150,255,.2)",
            color: count > 0 ? "#0b0e1a" : "#9aa6c8",
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          {count}
        </span>
      </a>
    </header>
  );
}
