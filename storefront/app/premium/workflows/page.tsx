import { requirePremiumSession } from "@/lib/auth";

export const metadata = {
  title: "Protected Workflow Examples | ClearGlass Premium",
  alternates: { canonical: "/premium/workflows" },
  description: "Server-side examples for premium workflow rendering.",
  other: { copyright: "© ClearGlass Inc. All rights reserved." },
};

export default async function WorkflowExamplesPage() {
  await requirePremiumSession();
  return (
    <section aria-labelledby="workflow-title">
      <p style={{ color: "#9aa6c8" }}>© ClearGlass Inc. All rights reserved.</p>
      <h1 id="workflow-title">Authenticated SSR workflow examples</h1>
      <pre style={{ whiteSpace: "pre-wrap", background: "rgba(12,16,38,.8)", padding: 16, borderRadius: 12 }}>
{`state_machine:
  intake -> enrich -> evaluate -> approval_required -> execute
invariant:
  premium prompts and operator playbooks are never serialized into public bundles`}
      </pre>
    </section>
  );
}
