import { redirect } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { config } from "@/lib/config";
import { CANONICAL_FIELDS } from "@/lib/import/fields";
import { OriginBadge } from "@/components/labels";
import { Card, PageHeader, When } from "@/components/ui";
import { ImportForm } from "./ImportForm";

export default async function ImportPage() {
  const ctx = await requireCtx();
  if (!can(ctx.actor.role, "import:run")) redirect("/?error=" + encodeURIComponent("Your role cannot import data"));
  const cfg = config();
  const batches = await ctx.db.importBatch.findMany({ include: { submittedBy: true }, orderBy: { createdAt: "desc" }, take: 25 });
  return (
    <>
      <PageHeader
        title="Import center"
        subtitle={`CSV or JSON, up to ${Math.round(cfg.importMaxBytes / 1024)} KB and ${cfg.importMaxRows} rows. Dates are ISO 8601; amounts are plain decimals. A column that is present but empty counts as "blank"; a column that is absent counts as "not supplied", and rules treat it as unknown.`}
      />
      <ImportForm />
      <Card title="Fields by record type" className="mt-4">
        <dl className="grid gap-3 text-sm md:grid-cols-3">
          {Object.entries(CANONICAL_FIELDS).map(([type, fields]) => (
            <div key={type}>
              <dt className="font-semibold text-slate-200">{type.toLowerCase()}</dt>
              <dd className="font-mono text-xs text-slate-400">{fields.join(", ")}</dd>
            </div>
          ))}
        </dl>
        <p className="muted mt-3">Example files, including invalid and duplicate ones for testing, are in examples/imports/.</p>
      </Card>
      <Card title="Import history" className="mt-4">
        <div className="overflow-x-auto"><table>
          <thead>
            <tr>
              <th scope="col">File</th>
              <th scope="col">Type</th>
              <th scope="col">Origin</th>
              <th scope="col">Result</th>
              <th scope="col">By</th>
              <th scope="col">When</th>
            </tr>
          </thead>
          <tbody>
            {batches.map((b) => (
              <tr key={b.id}>
                <td>
                  {b.filename}
                  <div className="muted font-mono text-[11px]">sha256 {b.fileHash.slice(0, 16)}...</div>
                </td>
                <td className="text-xs">{b.recordType.toLowerCase()}</td>
                <td>
                  <OriginBadge origin={b.origin} />
                </td>
                <td className="text-xs">
                  {b.status.toLowerCase()}: {b.acceptedRows} accepted, {b.rejectedRows} rejected, {b.duplicateRows} duplicate
                </td>
                <td className="text-xs">{b.submittedBy.name}</td>
                <td className="text-xs">
                  <When at={b.createdAt} />
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </>
  );
}
