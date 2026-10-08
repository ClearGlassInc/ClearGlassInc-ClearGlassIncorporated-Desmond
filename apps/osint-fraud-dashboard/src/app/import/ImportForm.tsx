"use client";

import { useActionState } from "react";
import { importAction, type ImportActionState } from "../actions";

export function ImportForm() {
  const [state, formAction, pending] = useActionState<ImportActionState, FormData>(importAction, null);
  const out = state?.outcome;
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <form action={formAction} className="glass grid gap-3 p-5">
        <h2>Upload</h2>
        <div className="flex flex-col gap-1">
          <label htmlFor="file">File (.csv or .json, UTF-8)</label>
          <input id="file" name="file" type="file" accept=".csv,.json,text/csv,application/json" required />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="format">Format</label>
            <select id="format" name="format" defaultValue="CSV">
              <option value="CSV">CSV</option>
              <option value="JSON">JSON</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="recordType">Records</label>
            <select id="recordType" name="recordType" defaultValue="TRANSACTION">
              <option value="TRANSACTION">Transactions</option>
              <option value="VENDOR">Vendors</option>
              <option value="EVIDENCE">Evidence</option>
              <option value="INCIDENT">Incidents (JSON)</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="origin">Data comes from</label>
            <select id="origin" name="origin" defaultValue="INTERNAL_RECORD">
              <option value="INTERNAL_RECORD">Authorized internal records</option>
              <option value="PUBLIC_SOURCE">Public sources</option>
              <option value="SYNTHETIC">Synthetic fixtures</option>
            </select>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="mapping">Field mapping (optional JSON: column name to field)</label>
          <textarea id="mapping" name="mapping" rows={3} className="font-mono text-xs" placeholder='{"Vendor ID": "vendorRecordId", "Paid on": "occurredAt"}' />
        </div>
        <fieldset className="flex gap-4">
          <legend className="sr-only">Mode</legend>
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" value="validate" defaultChecked /> Validate only
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" value="commit" /> Validate and import
          </label>
        </fieldset>
        <div>
          <button className="btn" type="submit" disabled={pending}>
            {pending ? "Working..." : "Run"}
          </button>
        </div>
        <p className="muted text-xs">
          Import only data you are authorized to hold. A batch with any invalid row is rejected as a whole; identical re-imports are skipped and reported.
        </p>
      </form>

      <section className="glass p-5" aria-live="polite">
        <h2 className="mb-3">Ingestion report</h2>
        {state?.error ? <p role="alert" className="text-rose-200">{state.error}</p> : null}
        {!state ? <p className="muted">Run a file to see its report here.</p> : null}
        {out ? (
          <div className="space-y-3 text-sm">
            <p>
              <strong className={out.status === "REJECTED" ? "text-rose-200" : "text-emerald-200"}>{out.status.toLowerCase()}</strong> - {out.report.filename} (
              {out.report.sizeBytes} bytes, sha256 <code className="text-xs">{out.report.fileHash.slice(0, 16)}...</code>)
            </p>
            <p>
              {out.report.totalRows} rows: {out.report.acceptedRows} {out.report.committed ? "imported" : "would import"}, {out.report.rejectedRows} with errors,{" "}
              {out.report.duplicateRows} duplicates skipped.
            </p>
            {out.report.errors.length ? (
              <div>
                <h3 className="mb-1">Errors to fix</h3>
                <ul className="max-h-72 list-inside list-disc overflow-auto text-rose-100">
                  {out.report.errors.map((e, i) => (
                    <li key={i}>
                      {e.row !== null ? `Row ${e.row}${e.line ? ` (line ${e.line})` : ""}` : "File"}
                      {e.field ? `, ${e.field}` : ""}: {e.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {out.report.duplicates.length ? (
              <div>
                <h3 className="mb-1">Duplicates</h3>
                <ul className="list-inside list-disc">
                  {out.report.duplicates.map((d, i) => (
                    <li key={i}>
                      Row {d.row} ({d.recordId}): {d.reason}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {out.report.warnings.length ? (
              <div>
                <h3 className="mb-1">Warnings</h3>
                <ul className="list-inside list-disc text-amber-100">
                  {out.report.warnings.map((w, i) => (
                    <li key={i}>
                      {w.row !== null ? `Row ${w.row}` : "File"}
                      {w.field ? `, ${w.field}` : ""}: {w.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div>
              <h3 className="mb-1">Column mapping used</h3>
              <ul className="font-mono text-xs">
                {Object.entries(out.report.mapping).map(([col, field]) => (
                  <li key={col}>
                    {col} → {field ?? "(ignored)"}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
