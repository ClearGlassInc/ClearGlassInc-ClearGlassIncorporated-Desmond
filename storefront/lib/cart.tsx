"use client";

// Client-side cart for the storefront. State lives in React context and is
// mirrored to localStorage so a cart survives reloads. Line items carry the
// governed price (in cents) straight from the catalog, so the cart total always
// matches what the control plane will charge at checkout.
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Product } from "./catalog";

export interface CartLine {
  slug: string;
  title: string;
  amount: number; // unit price in cents
  currency: string;
  quantity: number;
}

interface CartContextValue {
  lines: CartLine[];
  count: number;
  total: number; // cents
  add: (product: Product, quantity?: number) => void;
  setQuantity: (slug: string, quantity: number) => void;
  remove: (slug: string) => void;
  clear: () => void;
}

const STORAGE_KEY = "clearglass-cart-v1";
const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Load once on mount (client only) to avoid SSR/localStorage mismatch.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setLines(JSON.parse(raw) as CartLine[]);
    } catch {
      /* corrupt or unavailable storage — start empty */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
    } catch {
      /* storage full or blocked — cart still works in-memory */
    }
  }, [lines, hydrated]);

  const value = useMemo<CartContextValue>(() => {
    const count = lines.reduce((n, l) => n + l.quantity, 0);
    const total = lines.reduce((n, l) => n + l.amount * l.quantity, 0);
    return {
      lines,
      count,
      total,
      add: (product, quantity = 1) =>
        setLines((prev) => {
          const existing = prev.find((l) => l.slug === product.slug);
          if (existing) {
            return prev.map((l) =>
              l.slug === product.slug ? { ...l, quantity: l.quantity + quantity } : l,
            );
          }
          return [
            ...prev,
            {
              slug: product.slug,
              title: product.title,
              amount: product.amount,
              currency: product.currency,
              quantity,
            },
          ];
        }),
      setQuantity: (slug, quantity) =>
        setLines((prev) =>
          quantity <= 0
            ? prev.filter((l) => l.slug !== slug)
            : prev.map((l) => (l.slug === slug ? { ...l, quantity } : l)),
        ),
      remove: (slug) => setLines((prev) => prev.filter((l) => l.slug !== slug)),
      clear: () => setLines([]),
    };
  }, [lines]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
