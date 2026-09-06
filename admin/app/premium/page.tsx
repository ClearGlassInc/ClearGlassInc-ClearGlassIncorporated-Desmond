import { requirePremiumSession } from "@/lib/auth";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Premium Workflows — ClearGlass Commerce Admin",
  description: "Authenticated server-rendered premium workflows and AI prompts.",
  alternates: { canonical: "/premium" },
};

const premiumPrompt = `Review governed commerce anomalies, draft a reversible action package, and stop before high-risk execution until approval is recorded.`;

export default async function PremiumPage() {
  const session = await requirePremiumSession();
  return (
    <section aria-labelledby="premium-title" style={{ display: "grid", gap: 16 }}>
      <h1 id="premium-title">Premium operator workflows</h1>
      <p>Signed in as {session.sub}. This copy is rendered only after authenticated SSR succeeds.</p>
      <h2>Governed AI prompt</h2>
      <pre style={{ whiteSpace: "pre-wrap" }}>{premiumPrompt}</pre>
      <a href="/api/assets/sign?asset=operator-playbook.pdf">Generate expiring download link</a>
    </section>
  );
}
