import { redirect } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { ADAPTERS, manualUrlAdapter, mockRegistryAdapter } from "@/lib/osint/adapters";
import { Card, Flash, PageHeader, sp } from "@/components/ui";
import { collectEvidenceAction } from "../../actions";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function NewEvidencePage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  if (!can(ctx.actor.role, "evidence:create")) redirect("/evidence?error=" + encodeURIComponent("Your role cannot add evidence"));
  const q = await searchParams;
  return (
    <>
      <PageHeader
        title="Add evidence"
        subtitle="Record public-source material you collected yourself. The server never fetches the URL: it is stored as a citation. Do not bypass logins, paywalls, CAPTCHAs or rate limits, and collect only what the investigation needs."
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title={manualUrlAdapter.label} className="xl:col-span-2">
          <p className="muted mb-4">{manualUrlAdapter.description}</p>
          <form action={collectEvidenceAction} className="grid gap-3 md:grid-cols-2">
            <input type="hidden" name="adapterId" value={manualUrlAdapter.id} />
            <div className="flex flex-col gap-1 md:col-span-2">
              <label htmlFor="url">Public URL (http or https)</label>
              <input id="url" name="url" type="url" required placeholder="https://" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="title">Document title</label>
              <input id="title" name="title" required minLength={3} />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="recordId">Evidence id (optional; generated if blank)</label>
              <input id="recordId" name="recordId" pattern="[A-Za-z0-9][A-Za-z0-9._:\-]{0,79}" />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2">
              <label htmlFor="excerpt">Exact excerpt you rely on</label>
              <textarea id="excerpt" name="excerpt" required minLength={10} rows={5} />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="sourceTitle">Source name</label>
              <input id="sourceTitle" name="sourceTitle" required />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="sourcePublisher">Publisher</label>
              <input id="sourcePublisher" name="sourcePublisher" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="sourceKind">Source kind</label>
              <select id="sourceKind" name="sourceKind" defaultValue="PUBLIC_WEB">
                <option value="PUBLIC_WEB">Public web page</option>
                <option value="PUBLIC_RECORD">Public record or registry</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="documentLocation">Location (page, section, paragraph)</label>
              <input id="documentLocation" name="documentLocation" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="publishedAt">Published (YYYY-MM-DD)</label>
              <input id="publishedAt" name="publishedAt" placeholder="2026-01-31" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="observedAt">Event observed (ISO 8601)</label>
              <input id="observedAt" name="observedAt" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="collectedAt">Collected (defaults to now)</label>
              <input id="collectedAt" name="collectedAt" />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2">
              <label htmlFor="limitations">Limitations of this source</label>
              <textarea id="limitations" name="limitations" rows={2} />
            </div>
            <div>
              <button className="btn" type="submit">
                Record evidence
              </button>
            </div>
          </form>
        </Card>
        <Card title={mockRegistryAdapter.label}>
          <p className="muted mb-4">{mockRegistryAdapter.description}</p>
          <form action={collectEvidenceAction} className="grid gap-2">
            <input type="hidden" name="adapterId" value={mockRegistryAdapter.id} />
            <label htmlFor="query">Company name contains</label>
            <input id="query" name="query" required minLength={2} placeholder="paving" />
            <div>
              <button className="btn-quiet" type="submit">
                Search mock registry
              </button>
            </div>
          </form>
          <h3 className="mb-1 mt-6">Adapters in this build</h3>
          <ul className="space-y-1 text-sm">
            {Object.values(ADAPTERS).map((a) => (
              <li key={a.id}>
                {a.label}: <span className="muted">{a.live ? "connects to a live service" : "no live connection"}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
