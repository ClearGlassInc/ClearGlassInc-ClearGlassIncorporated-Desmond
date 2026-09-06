import { headers } from "next/headers";
import { NextResponse } from "next/server";
import Stripe from "stripe";

export const runtime = "nodejs";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-06-30.basil",
  typescript: true,
});

export async function POST(request: Request) {
  const signature = (await headers()).get("stripe-signature");
  const rawBody = await request.text();

  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      rawBody,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!,
    );
  } catch {
    return NextResponse.json({ error: "Invalid webhook signature" }, { status: 400 });
  }

  if (event.type !== "checkout.session.completed") {
    return NextResponse.json({ received: true });
  }

  const session = event.data.object as Stripe.Checkout.Session;

  if (
    session.payment_status !== "paid" ||
    session.mode !== "payment" ||
    session.currency !== "cad" ||
    session.amount_total !== 149900
  ) {
    return NextResponse.json({ error: "Payment validation failed" }, { status: 400 });
  }

  const expectedPriceId = process.env.STRIPE_CRITICAL_MINERALS_PRICE_ID!;
  const lineItems = await stripe.checkout.sessions.listLineItems(session.id, {
    expand: ["data.price"],
    limit: 10,
  });

  const purchased = lineItems.data.some(
    (item) => item.price?.id === expectedPriceId && item.quantity === 1,
  );

  if (!purchased) {
    return NextResponse.json({ error: "Unexpected product" }, { status: 400 });
  }

  // Transactionally:
  // 1. Reject if event.id was previously processed.
  // 2. Evaluate compliance/risk gates.
  // 3. Create a time-bounded, customer-bound fulfillment entitlement.
  // 4. Append a tamper-evident audit event; never log full payment data.

  return NextResponse.json({ received: true });
}
