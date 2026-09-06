"use server";

// Server actions for the human approval gate. These run on the server, post the
// decision to the control plane (which records it in the append-only audit
// ledger), then revalidate the affected pages so the cockpit reflects the new
// state immediately. The cockpit never executes the gated side effect itself —
// it only records the human decision; execution happens downstream.
import { revalidatePath } from "next/cache";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface DecisionResult {
  ok: boolean;
  error?: string;
}

async function decide(
  id: number,
  decision: "approve" | "reject",
  note: string,
): Promise<DecisionResult> {
  try {
    const res = await fetch(`${API_BASE}/approvals/${id}/${decision}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decided_by: "admin-cockpit", note }),
      cache: "no-store",
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return { ok: false, error: `control plane returned ${res.status}${detail ? `: ${detail}` : ""}` };
    }
    revalidatePath("/approvals");
    revalidatePath("/");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "control plane unreachable" };
  }
}

export async function approveAction(id: number, note: string): Promise<DecisionResult> {
  return decide(id, "approve", note);
}

export async function rejectAction(id: number, note: string): Promise<DecisionResult> {
  return decide(id, "reject", note);
}
