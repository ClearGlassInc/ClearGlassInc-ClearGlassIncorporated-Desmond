import { requireCtx } from "@/lib/auth/server";
import { ClaimBadge, SyntheticBadge } from "@/components/labels";
import { Card, Empty, PageHeader, When } from "@/components/ui";

export default async function IncidentsPage() {
  const ctx = await requireCtx();
  const incidents = await ctx.db.incident.findMany({
    include: { _count: { select: { evidence: true, steps: true, ruleSupport: true } } },
    orderBy: { recordId: "asc" },
  });
  return (
    <>
      <PageHeader
        title="Incidents"
        subtitle="Documented incidents and the rules derived from them. No real or 'suppressed' incident records have been supplied to this workspace; the only incident here is a labelled synthetic fixture. Import incident records as JSON in the Import center."
      />
      <Card>
        {incidents.length === 0 ? (
          <Empty>No incidents imported.</Empty>
        ) : (
          <div className="overflow-x-auto"><table>
            <thead>
              <tr>
                <th scope="col">Incident</th>
                <th scope="col">Status of claims</th>
                <th scope="col">Evidence / steps</th>
                <th scope="col">Rule citations</th>
                <th scope="col">Documented</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.id}>
                  <td>
                    <a href={`/incidents/${i.id}`}>{i.recordId}</a> <SyntheticBadge synthetic={i.isSynthetic} />
                    <div>{i.title}</div>
                  </td>
                  <td>
                    <ClaimBadge status={i.claimStatus} />
                  </td>
                  <td className="tabular-nums">
                    {i._count.evidence} / {i._count.steps}
                  </td>
                  <td className="tabular-nums">{i._count.ruleSupport}</td>
                  <td className="text-xs">
                    <When at={i.documentedAt} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}
