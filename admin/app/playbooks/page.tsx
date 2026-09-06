// Premium playbooks — an authenticated SSR page.
//
// The premium copy, workflows, and prompts are fetched and rendered ENTIRELY on
// the server. There is no client component here and no API the browser could
// call to pull the raw content — an unauthenticated visitor is redirected by
// middleware before this runs, and requireSession() re-checks as a backstop.
// Download links are minted server-side as signed, expiring tokens.
import type { Metadata } from "next";
import { requireSession } from "@/lib/session";
import { getPlaybooks } from "@/lib/premium";
import { signAsset } from "@/lib/signing";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Premium playbooks — ClearGlass Commerce Admin",
  description: "Operator workflows and agent prompts for the governed commerce engine.",
  robots: { index: false, follow: false },
  alternates: { canonical: "/playbooks" },
};

export default async function PlaybooksPage() {
  const session = await requireSession("/playbooks");
  const playbooks = await getPlaybooks();

  // Mint a short-lived signed download link per asset, bound to this operator.
  const withLinks = await Promise.all(
    playbooks.map(async (p) => {
      const signed = await signAsset(p.id, session.sub);
      return { ...p, href: `/api/download/${p.id}?token=${encodeURIComponent(signed.token)}` };
    }),
  );

  return (
    <section>
      <h1 style={{ fontSize: 30 }}>Premium playbooks</h1>
      <p style={{ color: "#9aa6c8" }}>
        Confidential operator workflows and agent prompts. Rendered server-side for
        authorized operators only.
      </p>

      {withLinks.map((p) => (
        <article
          key={p.id}
          style={{
            marginTop: 22,
            padding: 20,
            borderRadius: 14,
            border: "1px solid rgba(124,150,255,.16)",
            background: "rgba(124,150,255,.05)",
          }}
        >
          <h2 style={{ fontSize: 20, marginTop: 0 }}>{p.title}</h2>
          <p style={{ color: "#c3ccec" }}>{p.summary}</p>

          <h3 style={{ fontSize: 15, color: "#9fc4ff" }}>Workflow</h3>
          <ol style={{ color: "#c3ccec", lineHeight: 1.6 }}>
            {p.workflow.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>

          <h3 style={{ fontSize: 15, color: "#9fc4ff" }}>Agent prompt</h3>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              padding: 14,
              borderRadius: 10,
              background: "#0b1020",
              color: "#dbe4ff",
              border: "1px solid rgba(124,150,255,.16)",
              overflowX: "auto",
            }}
          >
            {p.prompt}
          </pre>

          <a
            href={p.href}
            style={{
              display: "inline-block",
              marginTop: 12,
              padding: "8px 14px",
              borderRadius: 10,
              border: "1px solid rgba(124,150,255,.5)",
              background: "rgba(124,150,255,.18)",
              color: "#eef2ff",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            Download signed copy (.md) ↓
          </a>
          <span style={{ color: "#6b7699", fontSize: 12, marginLeft: 10 }}>
            link expires in 5 minutes
          </span>
        </article>
      ))}
    </section>
  );
}
