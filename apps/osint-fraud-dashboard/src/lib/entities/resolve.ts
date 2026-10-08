// Entity resolution that prefers explicit identifiers and treats everything
// else as a candidate. A shared address, a similar name or a shared domain is
// never taken as common ownership, control, collusion or wrongdoing; it only
// produces a CANDIDATE link that a reviewer confirms or rejects.

export type ResolvableKind = "VENDOR" | "ORGANIZATION";

export interface ResolvableEntity {
  kind: ResolvableKind;
  id: string;
  recordId: string;
  name: string;
  identifier: string | null; // taxId for vendors, registrationNumber for organizations
  domain: string | null;
  address: string | null;
  organizationId?: string | null;
}

export type LinkBasis =
  | "EXPLICIT_IDENTIFIER"
  | "CANDIDATE_NAME_SIMILARITY"
  | "CANDIDATE_SHARED_ADDRESS"
  | "CANDIDATE_SHARED_DOMAIN";

export interface ProposedLink {
  fromKind: ResolvableKind;
  fromId: string;
  toKind: ResolvableKind;
  toId: string;
  relationType: string;
  basis: LinkBasis;
  basisDetail: string;
  /** CONFIRMED only when the source record itself states the link. */
  status: "CANDIDATE" | "CONFIRMED";
}

export const SIMILARITY_DISCLAIMER =
  "Similarity is a reason to check, not evidence of common ownership, control, collusion or wrongdoing.";

const LEGAL_SUFFIXES = new Set(["inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation", "co", "company", "plc", "lp", "llp"]);

export function normaliseName(name: string): string[] {
  return name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9 ]+/g, " ")
    .split(/\s+/)
    .filter((t) => t && !LEGAL_SUFFIXES.has(t));
}

export function nameSimilarity(a: string, b: string): number {
  const ta = new Set(normaliseName(a));
  const tb = new Set(normaliseName(b));
  if (ta.size === 0 || tb.size === 0) return 0;
  const inter = [...ta].filter((t) => tb.has(t)).length;
  return inter / (ta.size + tb.size - inter);
}

export function normaliseAddress(address: string): string {
  return address
    .toLowerCase()
    .replace(/[.,#]/g, " ")
    .replace(/\bstreet\b/g, "st")
    .replace(/\bavenue\b/g, "ave")
    .replace(/\broad\b/g, "rd")
    .replace(/\bsuite\b|\bunit\b/g, "ste")
    .replace(/\s+/g, " ")
    .trim();
}

export const NAME_SIMILARITY_THRESHOLD = 0.75;

function ordered(a: ResolvableEntity, b: ResolvableEntity): [ResolvableEntity, ResolvableEntity] {
  return `${a.kind}:${a.recordId}` <= `${b.kind}:${b.recordId}` ? [a, b] : [b, a];
}

export function proposeLinks(entities: ResolvableEntity[]): ProposedLink[] {
  const links: ProposedLink[] = [];
  const orgById = new Map(entities.filter((e) => e.kind === "ORGANIZATION").map((e) => [e.id, e]));

  // 1. Links the source records state explicitly.
  for (const v of entities) {
    if (v.kind === "VENDOR" && v.organizationId && orgById.has(v.organizationId)) {
      const org = orgById.get(v.organizationId)!;
      links.push({
        fromKind: "VENDOR",
        fromId: v.id,
        toKind: "ORGANIZATION",
        toId: org.id,
        relationType: "vendor_record_names_organization",
        basis: "EXPLICIT_IDENTIFIER",
        basisDetail: `Vendor record ${v.recordId} names organization ${org.recordId} explicitly.`,
        status: "CONFIRMED",
      });
    }
  }

  // 2. Pairwise candidates.
  for (let i = 0; i < entities.length; i++) {
    for (let j = i + 1; j < entities.length; j++) {
      const [a, b] = ordered(entities[i], entities[j]);
      const base = { fromKind: a.kind, fromId: a.id, toKind: b.kind, toId: b.id, status: "CANDIDATE" as const };

      if (a.identifier && b.identifier && a.identifier.replace(/\W/g, "").toUpperCase() === b.identifier.replace(/\W/g, "").toUpperCase()) {
        links.push({
          ...base,
          relationType: "same_identifier",
          basis: "EXPLICIT_IDENTIFIER",
          basisDetail: `${a.recordId} and ${b.recordId} carry the same registration/tax identifier. Confirm it is not a data-entry error before merging.`,
        });
      }
      const sim = nameSimilarity(a.name, b.name);
      if (sim >= NAME_SIMILARITY_THRESHOLD) {
        const differentIds = a.identifier && b.identifier && a.identifier !== b.identifier;
        links.push({
          ...base,
          relationType: "possible_same_entity",
          basis: "CANDIDATE_NAME_SIMILARITY",
          basisDetail:
            `Names "${a.name}" and "${b.name}" have token similarity ${sim.toFixed(2)} (threshold ${NAME_SIMILARITY_THRESHOLD}).` +
            (differentIds ? " Their identifiers differ, which points against them being the same entity." : "") +
            ` ${SIMILARITY_DISCLAIMER}`,
        });
      }
      if (a.address && b.address && normaliseAddress(a.address) === normaliseAddress(b.address)) {
        links.push({
          ...base,
          relationType: "shares_address",
          basis: "CANDIDATE_SHARED_ADDRESS",
          basisDetail: `Both records list the address "${a.address}". Shared offices, registered agents and serviced addresses are common. ${SIMILARITY_DISCLAIMER}`,
        });
      }
      if (a.domain && b.domain && a.domain.toLowerCase() === b.domain.toLowerCase()) {
        links.push({
          ...base,
          relationType: "shares_domain",
          basis: "CANDIDATE_SHARED_DOMAIN",
          basisDetail: `Both records list the domain ${a.domain}. Shared hosting or a parent-company domain can explain this. ${SIMILARITY_DISCLAIMER}`,
        });
      }
    }
  }
  return links;
}
