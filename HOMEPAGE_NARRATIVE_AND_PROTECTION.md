# Homepage — Narrative & Protection Layer

Copy deck, protection placement map, and behaviour reference for the ClearGlass
homepage (`index.html`).

**Everything here is additive.** No existing section, route, component, or line
of copy was removed, replaced, or shortened. Three new sections were inserted
between existing ones, four existing sections were marked as protected regions,
and one pre-existing contrast defect was corrected (§ 6).

---

## 1. Narrative flow, top to bottom

Curiosity → trust → action. New sections are marked **NEW**.

| # | Section | Role in the story |
|---|---|---|
| 1 | Classification banner | Sets the register before a word is read |
| 2 | Hero (`#hero`) | Mission, value, primary + secondary CTA |
| 3 | Mission strip | One-sentence statement of what the work does |
| 4 | Manifesto (`#vision`) | The founding principle, stated plainly |
| 5 | Values (`#values`) | Transparency · Integrity · Intelligence |
| 6 | **Doctrine (`#doctrine`)** | **NEW** — the promise: *why* it is built this way |
| 7 | Services (`#services`) | The three capability lines |
| 8 | Artemis command (`#artemis-command`) | The platform as a command surface |
| 9 | Products (`#products`) | Systems and prototypes |
| 10 | Timeline (`#timeline`) | Prototype → operational system |
| 11 | Founder (`#founder`) | The operator behind the work |
| 12 | **Proof (`#proof`)** | **NEW** — credibility: what is enforced, not claimed |
| 13 | Banking law (`#banking-law-strategist`) | Specialist depth |
| 14 | WSIDS (`#wsids`) | Defensive posture and mission boundary |
| 15 | Catalog (`#full-catalog`) | Every surface in one place |
| 16 | **Engage (`#engage`)** | **NEW** — three concrete entry paths |
| 17 | Contact CTA (`#contact`) | The close (unchanged) |
| 18 | Signup / Government / Footer | Conversion tail (unchanged) |

The three additions fill the three genuine gaps: the page stated *what* and
*how* but never *why* (6), asserted trust without evidence (12), and closed with
a CTA that had no on-ramp (16).

---

## 2. Copy deck — what shipped

### 2.1 Hero — unchanged, and deliberately so

The live hero already carries a headline, subheadline, two CTAs, the command
rail, and three capability cards. It was left exactly as-is: it is dense enough
that adding to it would cost LCP and clarity, both of which are budgeted (§ 5).

Alternates below are **spec, not shipped** — drop-in replacements if the hero is
ever revisited.

> **H1 alt A** — Governed AI systems for high-stakes operations. *(current)*
> **H1 alt B** — Autonomy you can put in front of a regulator.
> **H1 alt C** — The system is only as good as its audit trail.
>
> **Sub alt A** — ClearGlass Inc. designs AI automation, agent systems,
> cybersecurity programs, legal-tech workflows, OSINT operations, and enterprise
> architecture for leaders who need speed without losing control. *(current)*
> **Sub alt B** — We build the governed layer between an ambitious automation
> plan and the day it has to answer for itself.
>
> **Primary CTA** — Request a Strategic Brief → *(current)*
> **Secondary CTA** — View Capabilities → *(current)*

### 2.2 Doctrine — `#doctrine` *(shipped)*

- **Eyebrow** — DOCTRINE
- **H2** — Most systems fail quietly. **These are built to be watched.**
- **Lede** — ClearGlass builds operating systems for decisions that carry
  consequence — where an automation that drifts, a control that lapses, or an
  approval that never happened becomes somebody's very bad quarter. **We design
  for the audit before we design for the demo.**

| | Tenet | Body |
|---|---|---|
| 01 · SCOPE | Nothing runs unbounded. | Every agent is issued a blast radius, a policy boundary, and a named human who owns the outcome. Capability without a limit is just a liability with a countdown. |
| 02 · EVIDENCE | Every action leaves a record. | Decisions, approvals, and executions land in an append-only ledger with a risk score attached. If it happened, it is provable — and if it is not provable, it does not ship. |
| 03 · CONTROL | Speed that survives scrutiny. | Automation earns autonomy tier by tier. Low-risk work runs clean and unattended; anything touching money, law, or safety stops at a human gate by design, not by exception. |

Each tenet is a plain-language restatement of something the commerce control
plane actually enforces (`governance.py` risk tiers, the append-only `events`
ledger, `ALWAYS_ESCALATE`). The copy is cinematic; the claims are not invented.

### 2.3 Proof — `#proof` *(shipped)*

- **Eyebrow** — VERIFIED POSTURE
- **H2** — Trust is a **build artifact**, not a claim.
- **Sub** — The governance model below is not a brochure promise. It is enforced
  in code, exercised by tests, and it fails the build when violated — which is
  the only version of a guarantee worth quoting.

**Panel 1 — "What the system guarantees"** (five invariants, each true of the
shipped control plane): approval-gated execution, append-only risk-scored audit
ledger, authenticated admin routes that fail closed in production, money paths
covered by integration tests, and unconditional escalation for
pricing/payment/tax/refund/fulfilment.

**Panel 2 — "The rest is shared privately"**: a redacted operating readout
behind the idle-blur veil, plus the visible rights line and a link to the
content policy.

> **On social proof:** no client counts, revenue figures, testimonials, or logos
> were invented. An HTML comment marks the slot where real, attributable proof
> belongs. A fabricated metric on this page would undercut every verifiable
> claim sitting above it — which is the whole argument the section makes.

### 2.4 Engage — `#engage` *(shipped)*

- **Eyebrow** — ENGAGE
- **H2** — Three ways to **start**.
- **Sub** — Pick the smallest one that answers your question. Scope grows from
  evidence, not from an assumption about what you need.

| Path | Headline | CTA | Target |
|---|---|---|---|
| 01 | Strategic brief. | Request a brief → | `mailto:` founder |
| 02 | System review. | See engagements → | `offers/index.html` |
| 03 | Build engagement. | Review pricing → | `pricing.html` |

- **Closing microcopy** — What happens next: a scoped reply, a written summary
  of what we heard, and a fixed-scope proposal before any work begins. No
  retainer is required to have the first conversation.

No response-time SLA was written in: that is an operational commitment for the
business to make, not for a copy pass to invent.

### 2.5 Microcopy added elsewhere

- Footer copyright extended to **"© <year> ClearGlass Inc. All rights
  reserved."** with a new **Content Policy** link.
- Per-region stamp: `© 2026 ClearGlass Inc. · All rights reserved · REF <token> · <date>`
- Veil chip: `Preview paused — interact to resume`
- Print-only notice: `© 2026 ClearGlass Inc. All rights reserved. Retrieved from
  www.clearglassinc.com — reuse requires written permission.`

---

## 3. Protection placement map

`data-cg-protect="light|dark"` marks a region; the value only picks the ink so
the mark reads on that background.

| Region | Why it is protected |
|---|---|
| `#doctrine` **NEW** | The framing that is easiest to lift wholesale |
| `#artemis-command` | Proprietary command-surface framework |
| `#founder` | Biography, credentials, positioning |
| `#proof` **NEW** | The governance model — the most copied asset on the page |
| `#banking-law-strategist` | Specialist legal framework |
| `#wsids` | Mission-boundary doctrine |
| `#engage` **NEW** | Engagement model and pricing ladder |

Each protected region gets, from `/cg-content-shield.js`:

1. **`.cg-mark`** — a tiled diagonal `CLEARGLASS INC / PROPRIETARY` watermark,
   painted as a CSS mask so one tile serves both light and dark sections.
   Survives any screenshot of the region.
2. **`.cg-stamp`** — a corner line carrying the copyright, a per-session
   reference token, and the retrieval date. Makes a leaked capture traceable to
   a session rather than merely branded.
3. **`data-cg-protected`** — reuses the context-menu shielding that
   `/asset-protection.js` already applies site-wide, rather than registering a
   second handler for the same job.

Not protected, on purpose: the hero, mission strip, values, services, products,
timeline, catalog, and the closing CTA. These are the pages' discovery surface —
they should be quotable, shareable, and indexable without friction.

---

## 4. Behaviour reference

`/cg-content-shield.js` — text-side companion to the existing
`/asset-protection.js` (which handles images site-wide). Loaded after it so both
share one session token. Idempotent; no dependencies.

| Behaviour | Trigger | Effect |
|---|---|---|
| Provenance stamp | Load | `.cg-mark` + `.cg-stamp` injected into each protected region |
| Copy attribution | `copy` inside a protected region, selection ≥ 140 chars | Clipboard carries the selection **plus** source URL, reference token, retrieval date, and reuse-terms link |
| Short-selection bypass | Selection < 140 chars | Left completely alone — copying an email address should not yield four lines of boilerplate |
| Drag block | `dragstart` in a protected region | Prevented |
| Context menu | Right-click in a protected region or on any image | Prevented by `/asset-protection.js` |
| Veil | Tab blur / hidden / 60 s idle | `[data-cg-veil]` body blurs, chip appears |
| Unveil | Focus, pointer, key, wheel, or touch | Restored; keyboard focus inside holds it open |
| Print | Print / save-as-PDF | Watermark at full strength, fixed ownership notice, veil lifted so the print is not a blurred mess |

### Deliberate non-goals

The shield does **not** intercept print, save, view-source, developer tools, or
keyboard shortcuts, and does not disable text selection. Those are trivially
bypassed, break assistive technology and translation tools, and cost more in
goodwill than they return. `/asset-protection.js` documents the same boundary.

The copy handler calls `preventDefault()`, but it does not deny the copy — that
call is the only way to *add* data to the clipboard. The selection still copies
verbatim and in full.

**Client-side measures are deterrence and provenance, not access control.**
Anything that genuinely must not be seen belongs behind server-side
authentication. The veil is a courtesy against shoulder-surfing and idle
screenshots, not a permission boundary — which is why the gated material in
`#proof` is a redacted shape of a readout rather than the real thing.

---

## 5. Budgets and verification

`lighthouserc.json` gates `index.html` at performance ≥ 0.95, accessibility
≥ 0.95, SEO = 1.0, LCP ≤ 2500 ms, CLS ≤ 0.1. The layer was built to fit:

- Watermark and stamp are **absolutely positioned and injected after paint**, so
  they cannot shift layout. Measured CLS with the layer active: **0.0008**.
- The watermark is an **inline SVG mask** — no network request, no image decode.
- CSS ships in the existing inline `<style>` block rather than a new
  render-blocking stylesheet; the script is a small deferred file.
- Animation is limited to one opacity pulse, disabled under
  `prefers-reduced-motion`, as are the card and veil transitions.
- No `MutationObserver` — regions are static in the markup, so one pass at load
  is enough.
- New assets added to `sw.js` `PRECACHE`; `VERSION` bumped `cg-v37 → cg-v38`.

Verified in Chromium: all seven regions stamped, watermark `pointer-events:none`
(never intercepts a click), copy attribution correct, short selections
untouched, veil blurs on blur and restores on activity.

Green locally: `site_reliability_audit.py` (0 errors, 0 warnings),
`seo_audit.py` (0 errors, no `index.html` findings), `internal_links.py --check`
(141 pages current), `generate_search_assets.py` (regenerated in the same
commit, as the generator expects).

---

## 6. One pre-existing defect corrected

`assets/css/glass.css` sets `h1,…,h6 { color:#0c0e12 !important }` (line 293)
and `.sh-dark h2 { color:#0c0e12 !important }` (line 234) for its light-glass
redesign. On the dark command surfaces — background `rgb(8,13,20)` — that
renders the section headings as near-black on near-black: **effectively
invisible today** on `#artemis-command`, `#wsids`, and `#banking-law-strategist`.

The new `#proof` section inherited the same fault. Rather than ship one readable
dark heading beside three invisible ones, a scoped rule restores contrast for
those four sections. It is additive — no existing rule was edited or removed —
and it raises the accessibility budget rather than changing an intended look.

**This is worth a wider look:** the same global `!important` almost certainly
hits dark sections on other pages across the site. Only the homepage was in
scope here.

---

## 7. Extending to other pages

1. Add `<script defer src="/cg-content-shield.js"></script>` after the existing
   `asset-protection.js` include.
2. Mark regions with `data-cg-protect="light"` or `"dark"`.
3. For a veiled preview, wrap the content:
   `<div class="cg-veil" data-cg-veil><div class="cg-veil__body">…</div></div>`
4. Copy the `.cg-*` rules out of the homepage `<style>` block, or lift them into
   `assets/css/` if more than a couple of pages need them.

Enforcement, monitoring, and takedown are covered in
`legal/CONTENT_THEFT_RESPONSE_PLAN.md`.

---

© 2026 ClearGlass Inc. All rights reserved.
