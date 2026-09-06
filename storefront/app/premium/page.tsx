import { requirePremiumSession } from "@/lib/auth";
import { createAssetToken } from "@/lib/asset-signing";
import { emitSecurityLog } from "@/lib/request-logging";

export const metadata = {
  title: "Premium Intelligence Blueprint | ClearGlass Store",
  alternates: { canonical: "/premium" },
  description: "Protected premium architecture content rendered by authenticated server components.",
  other: { copyright: "© ClearGlass Inc. All rights reserved." },
};

const premiumCopy = {
  headline: "ClearGlassInc Artemis protected intelligence workflow",
  prompt: "Analyze live and historical signals, explain evidence lineage, and prepare an operator-approved action package.",
  workflow: ["Authenticated intake", "Ontology-grounded enrichment", "Human approval", "Audited execution"],
};

export default async function PremiumPage() {
  const session = await requirePremiumSession();
  const token = createAssetToken("artemis-blueprint.pdf", session.sub);
  emitSecurityLog({
    event: "premium_ssr_render",
    fingerprint: session.sub,
    path: "/premium",
    referrer: null,
    timestamp: new Date().toISOString(),
  });

  return (
    <article aria-labelledby="premium-title">
      <p style={{ color: "#9aa6c8" }}>© ClearGlass Inc. All rights reserved.</p>
      <h1 id="premium-title">{premiumCopy.headline}</h1>
      <p style={{ color: "#9aa6c8", lineHeight: 1.6 }}>{premiumCopy.prompt}</p>
      <ol>
        {premiumCopy.workflow.map((step) => <li key={step}>{step}</li>)}
      </ol>
      <a href={`/download/${token}`} style={{ color: "#9fc4ff" }}>Download expiring premium asset</a>
    </article>
  );
}
