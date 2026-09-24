// Where PayPal returns the buyer after they approve (PAYPAL_RETURN_URL).
// Approving is not paying: the control plane captures an approved PayPal
// payment only after a person approves the capture, and the order is paid only
// when PayPal's signed webhook confirms the capture.
import { OrderStatusPanel } from "@/lib/OrderStatusPanel";

export default function PayPalReturn() {
  return (
    <section style={{ maxWidth: 560 }}>
      <OrderStatusPanel
        title="Approved at PayPal"
        pending="You approved the payment at PayPal. It has not been charged yet: ClearGlass captures approved PayPal payments after review, and PayPal emails your receipt when that happens." />
      <a href="/" style={link}>
        Back to ClearGlass
      </a>
    </section>
  );
}

const link: React.CSSProperties = {
  display: "inline-block",
  marginTop: 18,
  padding: "12px 22px",
  borderRadius: 10,
  border: "1px solid rgba(124,150,255,.3)",
  background: "linear-gradient(180deg,rgba(124,150,255,.3),rgba(124,150,255,.08))",
  color: "#fff",
  textDecoration: "none",
};
