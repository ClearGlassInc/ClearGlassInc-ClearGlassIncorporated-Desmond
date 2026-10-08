import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { getOverview } from "@/lib/services/overview";
import { LabelLegend, ReviewStateBadge } from "@/components/labels";
import { Card, Flash, PageHeader, sp, Stat, When } from "@/components/ui";
import { REVIEW_STATES } from "@/lib/review";

export default async function OverviewPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const ctx = await requireCtx();
  const q = await searchParams;
  const o = await getOverview(ctx);
  const recentImports = await ctx.db.importBatch.findMany({ orderBy: { createdAt: "desc" }, take: 5 });

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle="Counts below are taken directly from stored records. The workspace shows no live feeds, fraud probabilities, savings or detection accuracy, because none has been measured."
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Imported records"
          value={o.records.transactions + o.records.vendors + o.records.evidence + o.records.incidents}
          note={`${o.records.transactions} transactions, ${o.records.vendors} vendors, ${o.records.evidence} evidence, ${o.records.incidents} incidents. ${o.records.synthetic} synthetic.`}
        />
        <Stat label="Alerts awaiting review" value={o.alerts.awaitingReview} note={`${o.alerts.insufficientData} of them are insufficient-data alerts waiting for evidence`} />
        <Stat
          label="Evidence with complete provenance"
          value={`${o.evidence.complete} / ${o.evidence.total}`}
          note={`${o.evidence.verified} verified by a reviewer; ${o.evidence.unverified} not yet verified`}
        />
        <Stat
          label="Ingestion errors"
          value={o.ingestion.rejectedRows}
          note={`rows rejected at import. ${o.ingestion.batches} import batches, ${o.ingestion.rejectedBatches} of them rejected; ${o.ingestion.duplicateRows} duplicate rows skipped`}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card title="Alert review states">
          <ul className="space-y-2">
            {REVIEW_STATES.map((s) => (
              <li key={s} className="flex items-center justify-between">
                <a href={`/alerts?status=${s}`} className="no-underline">
                  <ReviewStateBadge state={s} />
                </a>
                <span className="tabular-nums text-slate-200">{o.alerts.byState[s] ?? 0}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Rules and cases">
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span>Active rule versions</span>
              <span className="tabular-nums">{o.rules.active}</span>
            </li>
            <li className="flex justify-between">
              <a href="/rules?status=PENDING_APPROVAL">Versions awaiting approval</a>
              <span className="tabular-nums">{o.rules.pendingApproval}</span>
            </li>
            <li className="flex justify-between">
              <span>Open investigations</span>
              <span className="tabular-nums">{o.investigations.open}</span>
            </li>
            <li className="flex justify-between">
              <span>Public-source / internal records</span>
              <span className="tabular-nums">
                {o.records.publicSource} / {o.records.internal}
              </span>
            </li>
          </ul>
        </Card>
        <Card title="Recent imports">
          {recentImports.length === 0 ? (
            <p className="muted">No imports yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {recentImports.map((b) => (
                <li key={b.id} className="flex flex-col">
                  <span className="truncate text-slate-200">{b.filename}</span>
                  <span className="muted text-xs">
                    {b.status.toLowerCase()} - {b.acceptedRows} accepted, {b.rejectedRows} rejected, {b.duplicateRows} duplicates - <When at={b.createdAt} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="How to read labels" className="mt-6">
        <LabelLegend />
        <p className="muted mt-3">
          A rule <strong>match</strong> is a reason to review. <strong>No match</strong> means the conditions were not met on the supplied records - it is not a
          clearance. <strong>Insufficient data</strong> means required fields were missing, and the records are not cleared.
        </p>
      </Card>
      {can(ctx.actor.role, "audit:view") ? (
        <p className="muted mt-4">
          Security-relevant actions are listed in the <a href="/audit">audit view</a>.
        </p>
      ) : null}
    </>
  );
}
