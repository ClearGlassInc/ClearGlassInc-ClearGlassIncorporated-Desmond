import type { Prisma } from "@/generated/prisma/client";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { ClassificationBadge, OriginBadge, SyntheticBadge, VerificationBadge } from "@/components/labels";
import { Card, Empty, Flash, PageHeader, sp, When } from "@/components/ui";

type Search = Promise<Record<string, string | string[] | undefined>>;
const VERIFICATION = ["UNVERIFIED", "PARTIALLY_VERIFIED", "VERIFIED", "DISPUTED", "REJECTED"] as const;
const ORIGINS = ["SYNTHETIC", "PUBLIC_SOURCE", "INTERNAL_RECORD", "ANALYST_ENTERED"] as const;

export default async function EvidencePage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  const params = await searchParams;
  const q = (sp(params.q) ?? "").trim().slice(0, 200);
  const verification = sp(params.verification);
  const origin = sp(params.origin);
  const incomplete = sp(params.incomplete) === "1";
  const where: Prisma.EvidenceWhereInput = {};
  if (q) where.OR = [{ title: { contains: q, mode: "insensitive" } }, { excerpt: { contains: q, mode: "insensitive" } }, { recordId: { contains: q, mode: "insensitive" } }];
  if (verification && (VERIFICATION as readonly string[]).includes(verification)) where.verificationStatus = verification as (typeof VERIFICATION)[number];
  if (origin && (ORIGINS as readonly string[]).includes(origin)) where.origin = origin as (typeof ORIGINS)[number];
  if (incomplete) where.NOT = { missingFields: { isEmpty: true } };
  const evidence = await ctx.db.evidence.findMany({ where, include: { source: true }, orderBy: { recordId: "asc" } });
  const created = sp(params.created);

  return (
    <>
      <PageHeader
        title="Evidence library"
        subtitle="Original material as collected: excerpt, location, timestamps and content hash. Extracted statements and analyst interpretation are kept separately."
        actions={
          can(ctx.actor.role, "evidence:create") ? (
            <a className="btn" href="/evidence/new">
              Add evidence
            </a>
          ) : null
        }
      />
      <Flash ok={created ? `${created} evidence record(s) added, ${sp(params.skipped) ?? 0} already present` : sp(params.ok)} error={sp(params.error)} />
      <Card className="mb-4">
        <form className="flex flex-wrap items-end gap-3" method="get" role="search">
          <div className="flex flex-col gap-1">
            <label htmlFor="q">Search</label>
            <input id="q" name="q" defaultValue={q} placeholder="Id, title or excerpt text" />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="verification">Verification</label>
            <select id="verification" name="verification" defaultValue={verification ?? ""}>
              <option value="">Any</option>
              {VERIFICATION.map((v) => (
                <option key={v} value={v}>
                  {v.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="origin">Origin</label>
            <select id="origin" name="origin" defaultValue={origin ?? ""}>
              <option value="">Any</option>
              {ORIGINS.map((v) => (
                <option key={v} value={v}>
                  {v.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" name="incomplete" value="1" defaultChecked={incomplete} /> Missing provenance only
          </label>
          <button className="btn-quiet" type="submit">
            Apply
          </button>
        </form>
      </Card>
      <Card>
        {evidence.length === 0 ? (
          <Empty>No evidence matches.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th scope="col">Evidence</th>
                  <th scope="col">Source</th>
                  <th scope="col">Origin / access</th>
                  <th scope="col">Verification</th>
                  <th scope="col">Missing provenance</th>
                  <th scope="col">Collected</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <a href={`/evidence/${e.id}`}>{e.recordId}</a> <SyntheticBadge synthetic={e.isSynthetic} />
                      <div className="max-w-md">{e.title}</div>
                    </td>
                    <td className="text-xs">{e.source.title}</td>
                    <td>
                      <div className="flex flex-col items-start gap-1">
                        <OriginBadge origin={e.origin} hideSynthetic />
                        <ClassificationBadge value={e.accessClassification} />
                      </div>
                    </td>
                    <td>
                      <VerificationBadge status={e.verificationStatus} />
                    </td>
                    <td className="text-xs">{e.missingFields.length ? e.missingFields.join(", ") : <span className="muted">none</span>}</td>
                    <td className="text-xs">
                      <When at={e.collectedAt} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
