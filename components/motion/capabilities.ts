/** Node positions are fixed data, not random per render, so the graph is
 *  stable across reloads and identical between server and client markup. */
export interface Capability {
  readonly id: string;
  readonly label: string;
  /** Percentage coordinates within the constellation stage. */
  readonly x: number;
  readonly y: number;
  readonly copy: string;
}

export const HUB_ID = "operations";

export const CAPABILITIES: readonly Capability[] = [
  { id: "strategy", label: "Strategy", x: 50, y: 12, copy: "Positioning, offer design and the sequencing decisions that determine what the rest of the system is even for." },
  { id: "experience", label: "Experience", x: 79, y: 25, copy: "Interface, narrative and information design — how quickly a visitor understands what you do and what to do next." },
  { id: "engineering", label: "Engineering", x: 90, y: 52, copy: "The build itself: performant, accessible, typed, and maintainable by someone who is not the original author." },
  { id: "automation", label: "Automation", x: 79, y: 79, copy: "Governed workflows that remove manual steps without removing the human approval that keeps them safe." },
  { id: "ai", label: "AI", x: 50, y: 90, copy: "Model-assisted work under the same rule as everything else here: read-only analysis, drafted change, human approval, logged execution." },
  { id: "security", label: "Security", x: 21, y: 79, copy: "Threat modelling, header and edge posture, dependency integrity, and evidence you can hand an auditor." },
  { id: "discoverability", label: "Discoverability", x: 10, y: 52, copy: "Technical SEO, structured data and internal link authority — being findable by the people already looking." },
  { id: "analytics", label: "Analytics", x: 21, y: 25, copy: "Measurement that answers a decision. Fewer dashboards, more resolved questions." },
  { id: HUB_ID, label: "Operations", x: 50, y: 51, copy: "The connective layer: runbooks, ownership, escalation and the boring reliability work that compounds." },
] as const;

export interface Edge {
  readonly from: string;
  readonly to: string;
}

/** Hub-and-spoke plus a ring, derived once from the node order. */
export function buildEdges(): readonly Edge[] {
  const ring = CAPABILITIES.filter((c) => c.id !== HUB_ID);
  const edges: Edge[] = [];
  ring.forEach((node, i) => {
    edges.push({ from: node.id, to: HUB_ID });
    const next = ring[(i + 1) % ring.length];
    if (next !== undefined) edges.push({ from: node.id, to: next.id });
  });
  return edges;
}
