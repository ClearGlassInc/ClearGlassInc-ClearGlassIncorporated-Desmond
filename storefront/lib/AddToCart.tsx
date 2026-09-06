"use client";

// Add-to-cart button. Embeds in server-rendered product listings; on click it
// pushes the governed catalog line into the cart and briefly confirms.
import { useState } from "react";
import type { Product } from "./catalog";
import { useCart } from "./cart";

export function AddToCart({ product, block = false }: { product: Product; block?: boolean }) {
  const { add } = useCart();
  const [added, setAdded] = useState(false);

  function onClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    add(product, 1);
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  }

  return (
    <button
      onClick={onClick}
      style={{
        width: block ? "100%" : undefined,
        marginTop: 12,
        padding: "10px 18px",
        borderRadius: 10,
        border: "1px solid rgba(124,150,255,.3)",
        background: added
          ? "rgba(52,211,153,.18)"
          : "linear-gradient(180deg,rgba(124,150,255,.22),rgba(124,150,255,.06))",
        color: added ? "#34d399" : "#fff",
        cursor: "pointer",
        fontWeight: 600,
      }}
    >
      {added ? "Added ✓" : "Add to cart"}
    </button>
  );
}
