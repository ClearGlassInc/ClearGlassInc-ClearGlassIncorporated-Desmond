import { nextStates, type ReviewStateName } from "@/lib/review";
import type { RoleName } from "@/lib/auth/roles";
import { can } from "@/lib/auth/roles";
import { stateLabel } from "./labels";

/** Review decision form. Only offers moves the signed-in role may make; the server checks again. */
export function DecisionForm({
  action,
  hidden,
  state,
  role,
  decidePermission,
}: {
  action: (f: FormData) => Promise<void>;
  hidden: Record<string, string>;
  state: ReviewStateName;
  role: RoleName;
  decidePermission: "alert:decide" | "investigation:decide";
}) {
  const options = nextStates(state).filter((o) => can(role, o.level === "triage" ? "alert:triage" : decidePermission));
  if (options.length === 0) return <p className="muted">Your role cannot change this review state.</p>;
  const field = `rationale-${Object.values(hidden).join("-")}`;
  return (
    <form action={action} className="space-y-3">
      {Object.entries(hidden).map(([k, v]) => (
        <input key={k} type="hidden" name={k} value={v} />
      ))}
      <div className="flex flex-col gap-1">
        <label htmlFor={`${field}-to`}>Move to</label>
        <select id={`${field}-to`} name="to" required>
          {options.map((o) => (
            <option key={o.to} value={o.to}>
              {stateLabel(o.to)}
              {o.level === "decide" ? " (reviewer decision)" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor={field}>Rationale (required, at least 10 characters)</label>
        <textarea id={field} name="rationale" required minLength={10} rows={3} placeholder="What you checked and why this state is right" />
      </div>
      <button className="btn" type="submit">
        Record decision
      </button>
    </form>
  );
}

export function RationaleField({ id, label = "Rationale (required)" }: { id: string; label?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} name="rationale" required minLength={10} rows={2} />
    </div>
  );
}
