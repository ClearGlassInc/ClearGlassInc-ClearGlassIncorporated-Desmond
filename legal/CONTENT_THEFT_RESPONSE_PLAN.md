# ClearGlass Inc. — Content Theft Response Plan

**Outbound runbook.** What to do when ClearGlass material is copied without
permission: how to notice it, how to preserve proof before it disappears, and
how far to escalate.

This is the mirror image of the inbound procedure. Related documents:

| Document | Covers |
|---|---|
| `legal/WEBSITE_POLICY_TEMPLATES.md` § "Copyright / trademark complaint and takedown procedure" | **Inbound** — someone complaining to us |
| `legal/IP_PROTECTION_NOTICE.md` | Ownership register, trade secrets, protection strategy |
| `legal/content-policy.html` | The public reuse terms an infringer is breaching |
| `/asset-protection.js`, `/cg-content-shield.js` | The deterrence and provenance layer described in § 2.2 |

> Not legal advice. Escalation beyond stage 3 goes through counsel. Deadlines,
> statutory language, and remedies vary by jurisdiction.

---

## 1. Scope

Applies to ClearGlass-owned copy, design systems, page structure, brand assets,
diagrams, framework names, and documentation — published or under NDA.

**Triage first. Not every copy is worth a response.**

| Tier | What it looks like | Response |
|---|---|---|
| **T1 — Attribution gap** | Quoted with no credit; a paraphrase; a screenshot in a deck | Usually none, or a polite request for credit |
| **T2 — Substantial copy** | Pages, sections, or frameworks lifted near-verbatim; brand assets reused | Stage 1 → 3 |
| **T3 — Passing off** | Cloned site, ClearGlass name/marks presented as theirs, client-facing confusion, or NDA material in the open | Stage 1 → 5, immediately, with counsel |

Over-enforcing T1 costs goodwill and reputation for far more than it protects.
Under-enforcing T3 risks the mark itself.

---

## 2. Monitoring

### 2.1 What to run

Set a recurring review — monthly is enough for T2, and any credible tip
short-circuits the schedule.

- **Exact-phrase search.** Take 2–3 distinctive sentences from high-value pages
  (the doctrine copy, the governance invariants, framework names) and search
  them in quotes across major engines. Distinctive phrasing is the single most
  effective detector; generic marketing language is not worth tracking.
- **Brand and framework terms.** `ClearGlass`, `ClearGlassInc`, `Artemis`,
  `PERCIVAL`, `WSIDS`, `ClearPulse`, plus any product name in the footer.
- **Image reverse search** on the holographic seal, the hero still, and any
  published diagram.
- **Code and content reuse.** GitHub code search for distinctive identifiers and
  comment strings; the repo already runs `ip-protection-scan.yml` on a schedule
  for the credential and dependency side.
- **Referrer anomalies.** A spike from an unfamiliar domain often means the page
  is embedded or mirrored there.

### 2.2 What the site already does for you

Every protected homepage region carries a session reference (`REF …`) rendered
into the visible stamp, and copied text from those regions carries a source
line, the reference, and the retrieval date. When a copy surfaces with that
block intact, provenance is already established — capture it before the
infringer notices and strips it.

Client-side measures are deterrence and provenance only. They are trivially
bypassed by anyone who wants to bypass them, and nothing sensitive should rely
on them. Material that genuinely must not be seen belongs behind server-side
authentication, not behind a blur.

---

## 3. Evidence capture — do this before making contact

Once you make contact, the material often disappears. **Capture first, always.**

Preserve, for each infringing URL:

1. **Full-page screenshot** showing the URL bar, the page content, and the
   system clock.
2. **Saved HTML** (`Save Page As → Complete`) plus, where relevant, the raw
   response (`curl -sSL <url> -o evidence.html -D headers.txt`).
3. **An independent archive snapshot** — a third-party archive service creates a
   timestamped copy you did not author, which is materially stronger than your
   own screenshot.
4. **The URL, capture timestamp (with timezone), and the capturing person.**
5. **A side-by-side diff** against the ClearGlass original, with the matching
   passages marked. This is what a host or registrar actually acts on.
6. **Our priority evidence**: the original's publication date — the Git commit
   that first published the passage (`git log --diff-filter=A -- <path>`) and
   the corresponding `sitemap.xml` `lastmod`. Contemporaneous version history is
   the strongest authorship record available here.

Store under `operations/evidence/<domain>-<YYYY-MM-DD>/` with a short
`README.md` stating what was captured, when, by whom, and from where. Do not
edit captured files afterwards; add notes alongside them instead.

> Per `legal/IP_PROTECTION_NOTICE.md` § 1.1, human-authorship evidence matters
> for AI-assisted material. Commit history, prompt/revision trail, and editorial
> decisions are part of the evidence package, not an afterthought.

---

## 4. Escalation ladder

Climb one stage at a time. Stop as soon as it resolves.

**Stage 1 — Direct request (T2+).**
Short, factual, non-threatening email to the site owner. State the ClearGlass
URL, the infringing URL, the specific material, and one of two asks: attribute
it properly, or remove it, within a stated reasonable window. No legal
characterisation, no damages talk. Most cases end here, and the ones that end
here end cheaply.

**Stage 2 — Formal notice.**
If ignored, send a written notice invoking the reuse terms in
`legal/content-policy.html`. Include claimant identity, the protected work, the
exact URLs, the asserted right and jurisdiction, a good-faith statement, and a
signature — the same elements we require of inbound complainants in
`legal/WEBSITE_POLICY_TEMPLATES.md`, applied to ourselves.

**Stage 3 — Intermediary takedown.**
Send the notice to the parties who can act without the infringer's cooperation:
the **host** (identify via WHOIS / the site's IP), the **registrar**, the **CDN**,
and the **platform** if it is hosted on one. Attach the § 3 evidence package and
the side-by-side diff. Hosts act on documented, specific notices and ignore
vague ones.

**Stage 4 — Search delisting.**
Where the copy is outranking or duplicating ClearGlass pages, file a removal
request with the search engines under their copyright process. This limits
commercial harm even while the page stays up.

**Stage 5 — Counsel.**
Engage counsel for: T3 passing off, NDA or trade-secret exposure, client-facing
confusion, commercial-scale copying, or any counter-notice. Hand over the
evidence directory and the full correspondence thread.

---

## 5. Roles and record

| Step | Owner |
|---|---|
| Monitoring sweep, triage | Operations |
| Evidence capture | Whoever finds it — immediately, before contact |
| Stage 1–2 contact | Founder / COO |
| Stage 3–4 filings | Founder / COO, with the evidence package |
| Stage 5 | External counsel |

Keep one row per incident: date found, tier, URLs, evidence path, stages
attempted with dates, outcome, and date closed. The log matters — a documented
pattern of enforcement is what makes later escalation credible, and a gap in it
is the first thing an opposing party will point at.

---

## 6. Two failure modes to avoid

- **Threatening before capturing.** The material vanishes, and the claim goes
  with it. Evidence first, contact second. Every time.
- **Overstating the claim.** Do not assert rights we cannot substantiate, invent
  damages figures, or send legal-sounding threats without review. An
  overreaching notice is refused by hosts, and it hands the other side a story.

---

© 2026 ClearGlass Inc. All rights reserved.
