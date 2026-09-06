# ClearGlass Electrical System Restoration Agent

An assessment, planning, and documentation agent for restoring a property's
complete electrical system to a safe, code-compliant, maintainable condition.

- **`agent.json`** — manifest (role, modes, phases, safety model, report
  template), matching the layout used by the other agents in `agents/`.
- **`system_prompt.md`** — the full system prompt: mandatory safety rule, core
  directives, the seven working phases (site control → inventory → circuit
  tracing → defect assessment → repair plan → pre-energization testing →
  controlled re-energization), deliverables, final report format, and
  definition of done.

## What it does

Produces the paper side of an electrical restoration: safety and shutdown
plans, complete inventory with unique identifiers, circuit-tracing register,
risk-classified defect register, staged repair plan, panel directories,
pre-energization test checklists, and the final completion report.

## What it never does

It never directs energized work. All physical electrical work is performed by
a qualified licensed electrician, de-energized, locked out/tagged out,
verified dead, and completed under the permits and inspections required by the
local authority having jurisdiction. The agent does not guess conductor
identity, does not cite code rule numbers unverified for the jurisdiction, and
makes no completion claim without test evidence.
