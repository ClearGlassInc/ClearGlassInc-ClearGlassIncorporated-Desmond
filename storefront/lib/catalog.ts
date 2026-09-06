// Display catalog for the storefront.
//
// These entries drive what the shopper *sees*. They do not drive what they are
// *charged*: `slug` doubles as the price-book SKU, the control plane resolves the
// offer server-side from `app/data/pricebook.json`, and in live mode Stripe prices it
// from the Price the offer names. So these amounts are display only — if they drift,
// Stripe's Price wins and the customer is charged that. Keep them in step anyway;
// showing one number and charging another is its own kind of broken.
export interface Product {
  slug: string; // also the price-book SKU
  title: string;
  amount: number; // unit price in cents — display only
  currency: string;
  blurb: string;
  interval?: "month" | "year"; // set when the offer recurs
  note?: string; // any caveat shown next to the price
}

export const CATALOG: Product[] = [
  {
    slug: "risk-audit-90",
    title: "ClearGlass 90-Minute Cyber Risk Audit",
    amount: 29700,
    currency: "cad",
    blurb:
      "A focused 90-minute cybersecurity and AI-risk assessment for small businesses and professionals, followed by prioritized findings and practical next actions.",
  },
  {
    slug: "business-protection-monthly",
    title: "ClearGlass Business Protection — monthly",
    amount: 10000,
    currency: "cad",
    blurb:
      "Ongoing cybersecurity guidance, risk monitoring support, and practical defensive recommendations for small businesses.",
    interval: "month",
  },
  {
    slug: "business-protection-annual",
    title: "ClearGlass Business Protection — annual",
    amount: 100000,
    currency: "cad",
    blurb:
      "The same ongoing protection, billed yearly instead of monthly.",
    interval: "year",
  },
];

export function findProduct(slug: string): Product | undefined {
  return CATALOG.find((p) => p.slug === slug);
}

export function formatPrice(amount: number, currency: string): string {
  return `${currency.toUpperCase()} $${(amount / 100).toFixed(2)}`;
}

// Price as shown to the shopper, including the billing interval for subscriptions.
export function formatOfferPrice(product: Product): string {
  const base = formatPrice(product.amount, product.currency);
  return product.interval ? `${base} / ${product.interval}` : base;
}
