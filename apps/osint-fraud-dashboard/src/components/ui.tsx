import type { ReactNode } from "react";
import { safeHref } from "@/lib/text";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted mt-1 max-w-3xl">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

export function Card({ title, children, className = "" }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`glass p-5 ${className}`}>
      {title ? <h2 className="mb-3">{title}</h2> : null}
      {children}
    </section>
  );
}

/** Flash messages arrive in the URL; they are rendered as text. */
export function Flash({ ok, error }: { ok?: string; error?: string }) {
  if (!ok && !error) return null;
  return (
    <div
      role={error ? "alert" : "status"}
      className={`mb-4 rounded-lg border px-4 py-3 text-sm ${error ? "border-rose-300/40 bg-rose-400/10 text-rose-100" : "border-emerald-300/40 bg-emerald-400/10 text-emerald-100"}`}
    >
      {error ?? ok}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="muted py-4">{children}</p>;
}

export function Stat({ label, value, note }: { label: string; value: number | string; note?: ReactNode }) {
  return (
    <div className="glass p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-white tabular-nums">{value}</div>
      {note ? <div className="muted mt-1 text-xs">{note}</div> : null}
    </div>
  );
}

/** A URL from imported data: a link only when it is http(s), otherwise inert text. */
export function SourceLink({ url }: { url: string | null }) {
  if (!url) return <span className="muted">not supplied</span>;
  const href = safeHref(url);
  if (!href) return <span className="break-all">{url}</span>;
  return (
    <a href={href} rel="noopener noreferrer nofollow" target="_blank" className="break-all">
      {url}
    </a>
  );
}

export function When({ at }: { at: Date | string | null | undefined }) {
  if (!at) return <span className="muted">not supplied</span>;
  const d = typeof at === "string" ? new Date(at) : at;
  return <time dateTime={d.toISOString()}>{d.toISOString().replace("T", " ").slice(0, 16)} UTC</time>;
}

export function Json({ value }: { value: unknown }) {
  return <pre className="max-h-96 overflow-auto rounded-md bg-black/40 p-3 text-xs text-slate-300">{JSON.stringify(value, null, 2)}</pre>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-white/5 py-2 text-sm sm:grid-cols-[11rem_1fr] sm:gap-3">
      <dt className="text-slate-400">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

export function sp(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}
