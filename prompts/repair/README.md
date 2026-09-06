# Prompt & Agent Repair Pack

Version-controlled prompts for diagnosing and hardening ClearGlass prompt and
agent workflows — engineering-style (reproduce → isolate → repair → validate →
harden), not guesswork.

| File | Use when |
|------|----------|
| [`prompt-workflow-repair.md`](prompt-workflow-repair.md) | A **static prompt** (single or chained) produces unstable, mis-formatted, or off-task output. Inspect it like code, isolate the faulty instruction, rewrite with tighter structure. |
| [`agent-repair-workflow.md`](agent-repair-workflow.md) | A **running agent** workflow fails at runtime. Reconstruct the path from logs/traces, classify the failure, repair the weakest link, validate against normal / boundary / adversarial cases. |

Both keep repairs safe: analysis and rewrites are free; sensitive or irreversible
changes are recommended for human approval, never auto-applied — matching the
control plane in [`sentinel/PERCIVAL_V8_SPEC.md`](../../sentinel/PERCIVAL_V8_SPEC.md).
