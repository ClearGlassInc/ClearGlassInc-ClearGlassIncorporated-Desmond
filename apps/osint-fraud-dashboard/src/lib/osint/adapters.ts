// Source adapters bring evidence into the workspace.
//
// None of the adapters in this prototype contacts a live service:
//  - "manual-url" records a URL and excerpt the analyst supplies. The URL is a
//    citation; the server never fetches it.
//  - "mock-registry" returns synthetic fixtures for demonstration.
// A future live adapter must call assertOutboundAllowed() before any request,
// respect the source's terms, authentication and rate limits, and never bypass
// paywalls, CAPTCHAs or access controls. Content it returns is data, never
// instructions to this application or to any model.

import { z } from "zod";
import { contentHash } from "../hash";
import { cleanText, parsePublicUrl } from "../text";
import { parseIsoDate } from "../import/validate";
import type { NormalizedEvidence } from "../import/validate";
import { EVIDENCE_PROVENANCE_FIELDS } from "../import/fields";

export type CollectedEvidence = Omit<NormalizedEvidence, "kind" | "row">;

export interface SourceAdapter {
  id: string;
  label: string;
  description: string;
  /** True only when the adapter reaches a live external service. */
  live: boolean;
  origin: "PUBLIC_SOURCE" | "SYNTHETIC";
  extractionMethod: "MANUAL_EXCERPT" | "MOCK_ADAPTER";
  collect(input: Record<string, string>, now: Date): CollectedEvidence[];
}

export class AdapterInputError extends Error {
  constructor(readonly issues: string[]) {
    super("Adapter input is invalid");
  }
}

const optional = z
  .string()
  .optional()
  .transform((v) => (v && v.trim() ? cleanText(v).trim() : null));
const optionalDate = z
  .string()
  .optional()
  .transform((v, ctx) => {
    if (!v || !v.trim()) return null;
    const d = parseIsoDate(v);
    if (!d) {
      ctx.addIssue({ code: "custom", message: "Use ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ)" });
      return z.NEVER;
    }
    return d;
  });

const manualSchema = z.object({
  recordId: optional,
  url: z.string().transform((v, ctx) => {
    const p = parsePublicUrl(v);
    if (!p.ok) {
      ctx.addIssue({ code: "custom", message: p.error });
      return z.NEVER;
    }
    return p.url;
  }),
  title: z.string().trim().min(3, "Title is required").max(300).transform((v) => cleanText(v)),
  excerpt: z.string().trim().min(10, "Paste the exact excerpt you are relying on (at least 10 characters)").max(20_000).transform((v) => cleanText(v)),
  sourceTitle: z.string().trim().min(2, "Name the source").max(300).transform((v) => cleanText(v)),
  sourcePublisher: optional,
  sourceKind: z.enum(["PUBLIC_WEB", "PUBLIC_RECORD"]).default("PUBLIC_WEB"),
  documentLocation: optional,
  publishedAt: optionalDate,
  observedAt: optionalDate,
  collectedAt: optionalDate,
  limitations: optional,
});

function finish(e: Omit<CollectedEvidence, "provided" | "missing" | "contentHash">, provided: string[]): CollectedEvidence {
  const missing = EVIDENCE_PROVENANCE_FIELDS.filter((f) => e[f] === null);
  return {
    ...e,
    provided,
    missing,
    contentHash: contentHash({ excerpt: e.excerpt, url: e.url, documentLocation: e.documentLocation, publishedAt: e.publishedAt }),
  };
}

export const manualUrlAdapter: SourceAdapter = {
  id: "manual-url",
  label: "Public source (manual excerpt)",
  description: "Record a public URL and the exact excerpt you collected. The server does not fetch the URL.",
  live: false,
  origin: "PUBLIC_SOURCE",
  extractionMethod: "MANUAL_EXCERPT",
  collect(input, now) {
    const p = manualSchema.safeParse(input);
    if (!p.success) throw new AdapterInputError(p.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`));
    const d = p.data;
    const recordId = d.recordId ?? `EV-${now.toISOString().slice(0, 10).replace(/-/g, "")}-${contentHash({ u: d.url, x: d.excerpt }).slice(0, 8).toUpperCase()}`;
    const provided = Object.entries(input).filter(([, v]) => v && v.trim()).map(([k]) => k).sort();
    return [
      finish(
        {
          recordId,
          title: d.title,
          excerpt: d.excerpt,
          url: d.url,
          sourceTitle: d.sourceTitle,
          sourcePublisher: d.sourcePublisher,
          sourceKind: d.sourceKind,
          documentLocation: d.documentLocation,
          publishedAt: d.publishedAt,
          observedAt: d.observedAt,
          collectedAt: d.collectedAt ?? now,
          accessClassification: "PUBLIC",
          limitations: d.limitations,
        },
        provided,
      ),
    ];
  },
};

// Synthetic registry entries. Names use the reserved .example TLD and are fictional.
const MOCK_REGISTRY = [
  { id: "SYN-REG-001", name: "Example Paving Ltd", text: "SYNTHETIC REGISTRY ENTRY. Example Paving Ltd, registration EX-100-001, status active, registered office 100 Example Street, Testville." },
  { id: "SYN-REG-002", name: "Sample Office Supply Inc", text: "SYNTHETIC REGISTRY ENTRY. Sample Office Supply Inc, registration EX-100-002, status active, registered office 200 Sample Avenue, Testville." },
  { id: "SYN-REG-003", name: "Northwind Facility Services Ltd", text: "SYNTHETIC REGISTRY ENTRY. Northwind Facility Services Ltd, registration EX-100-003, status active, registered office 300 Fixture Road, Testville." },
];

export const mockRegistryAdapter: SourceAdapter = {
  id: "mock-registry",
  label: "Synthetic business registry (mock)",
  description: "Returns fictional registry entries for demonstration. No external service is contacted.",
  live: false,
  origin: "SYNTHETIC",
  extractionMethod: "MOCK_ADAPTER",
  collect(input, now) {
    const q = (input.query ?? "").trim().toLowerCase();
    if (q.length < 2) throw new AdapterInputError(["query: enter at least 2 characters"]);
    return MOCK_REGISTRY.filter((r) => r.name.toLowerCase().includes(q)).map((r) =>
      finish(
        {
          recordId: `${r.id}-${now.toISOString().slice(0, 10).replace(/-/g, "")}`,
          title: `Registry entry: ${r.name} (synthetic)`,
          excerpt: r.text,
          url: null,
          sourceTitle: "Synthetic Business Registry (mock adapter)",
          sourcePublisher: "ClearGlass prototype fixtures",
          sourceKind: "PUBLIC_RECORD",
          documentLocation: `entry ${r.id}`,
          publishedAt: null,
          observedAt: now,
          collectedAt: now,
          accessClassification: "PUBLIC",
          limitations: "Synthetic fixture produced by a mock adapter; it describes no real company.",
        },
        ["query"],
      ),
    );
  },
};

export const ADAPTERS: Record<string, SourceAdapter> = {
  [manualUrlAdapter.id]: manualUrlAdapter,
  [mockRegistryAdapter.id]: mockRegistryAdapter,
};

const PRIVATE_HOST = /^(localhost|.*\.local|.*\.internal|0\.0\.0\.0|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1\]?|\[?f[cd][0-9a-f]{2}:|\[?fe80:)/i;
const IP_LITERAL = /^(\d{1,3}\.){3}\d{1,3}$|^\[[0-9a-f:]+\]$/i;

/**
 * Guard for server-side fetching by a future live adapter. Refuses anything
 * that is not https, any IP literal or private host, and any host not on the
 * explicit allowlist (OSINT_FETCH_ALLOWLIST, empty by default, so every fetch
 * is refused). Redirects must be re-checked with this function per hop.
 */
export function assertOutboundAllowed(raw: string, allowlist: readonly string[]): URL {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    throw new Error("Outbound fetch refused: not a URL");
  }
  if (u.protocol !== "https:") throw new Error("Outbound fetch refused: only https is allowed");
  if (u.username || u.password) throw new Error("Outbound fetch refused: credentials in URL");
  const host = u.hostname.toLowerCase();
  // WHATWG URL parsing already normalises decimal/hex IPv4 forms and brackets IPv6.
  if (IP_LITERAL.test(host)) throw new Error("Outbound fetch refused: IP literals are not allowed");
  if (PRIVATE_HOST.test(host)) throw new Error("Outbound fetch refused: private or local host");
  if (u.port && u.port !== "443") throw new Error("Outbound fetch refused: non-standard port");
  if (!allowlist.map((h) => h.toLowerCase()).includes(host)) throw new Error(`Outbound fetch refused: ${host} is not on the allowlist`);
  return u;
}

export function fetchAllowlist(env: Record<string, string | undefined> = process.env): string[] {
  return (env.OSINT_FETCH_ALLOWLIST ?? "")
    .split(",")
    .map((h) => h.trim())
    .filter(Boolean);
}
