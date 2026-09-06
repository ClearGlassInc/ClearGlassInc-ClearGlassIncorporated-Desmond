// Premium content — the copy, workflows, and agent prompts that must never be
// shipped to an unauthenticated visitor.
//
// This lives in a server module. It is only ever imported by server components
// and route handlers (never by a "use client" file), so Next.js keeps it out of
// the client bundle entirely: the bytes below are not in any JS the browser
// downloads. Authenticated pages render it as HTML; the download route emits it
// as a file behind a signed, expiring token.
import { cache } from "react";

export interface Playbook {
  id: string;
  title: string;
  summary: string;
  workflow: string[];
  prompt: string;
}

const PLAYBOOKS: Playbook[] = [
  {
    id: "pricing-governor",
    title: "Governed repricing workflow",
    summary:
      "How the operator drafts a margin-safe price change and routes it through the human approval gate — never a live edit.",
    workflow: [
      "Pull current price, cost, and 14-day conversion from /metrics.",
      "Draft a candidate price within the guardrail band (never below floor margin).",
      "Score the action; pricing is high-risk, so it is queued, not executed.",
      "Await an approvals row reaching `approved` before any live change.",
      "On approval, apply and write the change to the append-only audit ledger.",
    ],
    prompt:
      "You are the ClearGlass pricing operator. Propose at most one price change per SKU per day, " +
      "always inside the configured guardrail band, never below the floor margin. Output a DRAFT only; " +
      "do not execute. Include rationale, expected margin impact, and the risk tier. Pricing is always high risk.",
  },
  {
    id: "content-publish",
    title: "Content publish workflow",
    summary: "Drafting and queuing storefront copy for human review before it goes live.",
    workflow: [
      "Generate product copy grounded only in real catalog attributes.",
      "Never fabricate reviews, inventory, urgency, or sales.",
      "Queue the publish (medium risk) for approval.",
      "Publish on approval; log the event with a risk score.",
    ],
    prompt:
      "You are the ClearGlass content operator. Write factual, on-brand product copy using only the " +
      "provided catalog attributes. Do not invent reviews, stock levels, discounts, or urgency. Return a DRAFT " +
      "for human approval.",
  },
];

/** All playbooks (cached per request). Server-only. */
export const getPlaybooks = cache(async (): Promise<Playbook[]> => PLAYBOOKS);

/** Render a playbook as a downloadable, self-contained Markdown document. */
export function playbookToMarkdown(p: Playbook): string {
  const steps = p.workflow.map((s, i) => `${i + 1}. ${s}`).join("\n");
  return [
    `# ${p.title}`,
    "",
    `> © ${new Date().getFullYear()} ClearGlass Inc. Confidential — authorized operators only.`,
    "",
    p.summary,
    "",
    "## Workflow",
    steps,
    "",
    "## Agent prompt",
    "```",
    p.prompt,
    "```",
    "",
  ].join("\n");
}

/** Look up a single downloadable asset by id, or null. */
export async function getAssetMarkdown(assetId: string): Promise<{ filename: string; body: string } | null> {
  const p = PLAYBOOKS.find((x) => x.id === assetId);
  if (!p) return null;
  return { filename: `${p.id}.md`, body: playbookToMarkdown(p) };
}
