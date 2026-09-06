# Aurora Glass — Futuristic 2050 UI System

**A living-future control surface for ClearGlass.** Layered refractive glass,
holographic edges, luminous prism light, and calm cinematic motion — engineered
to look extraordinary while staying fast, readable, and production-ready.

This document is the implementation-ready spec. The shipping reference build:

- **`futuristic.html`** — self-contained flagship page (hero → system → features → signals → modules → finale)
- **`futuristic-ui.css`** — the portable design system (tokens + components), namespaced `--ag-*`
- Built on the canonical brand primitives in **`tokens.css`** and the global remap in **`theme.css`**

---

## 1. Full visual concept

Aurora Glass treats every surface as a pane of *intelligent glass*: it refracts
the ambient light behind it, catches a specular streak as the cursor passes, and
settles with physical inertia. Behind the content, two slow aurora orbs drift and
breathe over a deep void canvas with a faint holographic grid. The palette is a
single five-stop prism (sky → violet → pink → mint → amber) used sparingly for
light, edges, and highlights — never as flat fills.

The feeling target: *luxury instrument*. Cinematic contrast, generous negative
space, sharp elegant typography (serif display + sans body + mono data). Depth is
communicated through five glass elevation levels and three blur tiers, not through
fake 3D or heavy shadows.

## 2. Desktop layout

- **Floating glass nav** — pill, centered, detached from the top edge; compresses
  (stronger shadow + glow) on scroll; a "glide" pill tracks the hovered link.
- **Hero** — full-viewport, centered, with a breathing aura behind the headline,
  prism-clipped keyword, dual CTA, and a stat row that staggers in.
- **System overview** — asymmetric 2-col split: prose left, a reflective holo data
  panel right (tilts to the cursor).
- **Feature grid** — 3×2 glass cards with icon tiles; lift + glow on hover.
- **Signal strip** — one wide reflective panel holding 4 monospace stat readouts.
- **Modules** — 2-col translucent content modules showing UI states (nominal / approval).
- **Finale** — a launch-screen panel with the largest aura, luminous CTA border.

## 3. Mobile layout

- Nav collapses to a glass sheet dropdown behind a ☰ toggle (blur-lg, full-width).
- All grids collapse to a single column (`--3/--4 → 2 → 1` at 900px / 620px).
- Fluid `clamp()` type scales down without media queries.
- Cursor field, tilt, and magnetic effects are **disabled** on coarse pointers.
- Aura orbs shrink via `vw` sizing; ambient motion stays but is cheap.

## 4. Style guide

| System | Rule |
|--------|------|
| **Background** | Deep void `#05070f` → raised `#0a0e1c`; nebula radial wash; faint 64px holo grid masked to the top |
| **Glass levels** | 0 ambient · 1 resting · 2 raised/nav · 3 hover · 4 modal — opacity climbs with elevation |
| **Blur tiers** | `sm 8px` / `md 16px` / `lg 28px`. Reserve `lg` for hero + modal only; never nest blurred surfaces |
| **Borders** | 1px hairline `rgba(150,175,255,.22)`; strong `.40`; holographic animated prism edge via mask-compositing |
| **Highlights** | Prism stops only: sky `#38bdf8`, violet `#a78bfa`, pink `#f472b6`, mint `#34d399`, amber `#fbbf24` |
| **Typography** | Display/H: Cormorant Garamond (serif). Body/UI: Urbanist. Data: IBM Plex Mono. Fluid `clamp()` scale |
| **Spacing** | 8px base; section gutters `96–128px`; card padding `40px` |
| **Icon style** | Geometric glyphs on a raised glass tile (14px radius) with a small glow |
| **Shadow** | Cool-tinted, soft, diffuse; 3 tiers; paired with an inner sheen |
| **Glow limits** | `sm / md / lg` only; never exceed one `lg` glow per element |
| **Light source** | Top-left. Sheen gradient at 160°; specular streak follows cursor |
| **Dark mode** | Dark **is** the default and only theme; contrast tuned for it |
| **Saturation** | Accents saturate ≤ ~85%; backgrounds desaturated for calm |
| **Contrast** | Body text `#eaf0ff` / dim `#9fabce` on glass ≥ WCAG AA; never place body copy on a raw prism gradient |

## 5. Animation specs

| Motion | Behavior | Timing |
|--------|----------|--------|
| Aurora orbs | drift + scale, alternate | 24s / 30s `ease` |
| Hero aura | opacity + scale breathe | 8s `ease` |
| Holo border | prism gradient sweep | 8s linear |
| Primary button | gradient position breathe | 9s `ease` |
| Cursor field | eased lerp follow (rAF) | factor .14 |
| Panel tilt | ±4–5° perspective toward cursor | .2s spring |
| Magnetic btn | translate .18–.3× offset | spring on leave |
| Card hover | translateY(-6px) + glow | .42s spring |
| Reveal / stagger | translateY(28px)→0, opacity | .7s spring, 80ms steps |
| Nav glide | pill morphs to hovered link | .42s spring |
| Status dot / eq bars | pulse / scaleY loop | 2.4s / 1.4s |

Principle: **only `transform`, `opacity`, and `filter` animate** (compositor-only).
Nothing animates layout, `width/height`, `top/left`, `box-shadow` size, or `blur`.

## 6. Component tokens

All defined in `futuristic-ui.css` under `:root`, namespaced `--ag-*`:

- **Glass**: `--ag-glass-0..4`, `--ag-blur-sm/md/lg`, `--ag-edge`, `--ag-edge-strong`, `--ag-edge-holo`, `--ag-inner-sheen`
- **Light**: `--ag-hi-sky/violet/pink/mint/amber`, `--ag-prism`, `--ag-glow-sm/md/lg`
- **Elevation**: `--ag-sh-1/2/3`
- **Type**: `--ag-fs-display/h1/h2/h3/body/small`, `--ag-tracking`, `--ag-tracking-wide`
- **Space/Radius**: `--ag-sp-1..7`, `--ag-r-xl/lg/md/sm/pill`
- **Motion**: `--ag-ease/spring/glide`, `--ag-dur-1/2/3/slow`
- **Surface text**: `--ag-on`, `--ag-on-dim`, `--ag-on-mute`
- **Component classes**: `.ag-glass(--holo/--reflective)`, `.ag-nav`, `.ag-btn(--primary/--ghost/--luminous)`,
  `.ag-chip`, `.ag-stat`, `.ag-signal`, `.ag-card`, `.ag-grid`, `.ag-divider`, `.ag-hero`, `.ag-finale`

## 7. UI states

- **Default** — glass level 1, hairline border.
- **Hover** — glass level 3, lift, `--ag-glow-sm`, tilt (fine pointer only).
- **Active/press** — `translateY(0) scale(.97)`.
- **Focus-visible** — 2px accent ring + 4px halo (inherited from `ui.css`, keyboard-only).
- **Disabled** — flatten transform/shadow, `opacity .55`, `not-allowed`.
- **Status** — nominal (mint dot), syncing (sky), approval/degraded (amber), failure (pink) — via chip dot color.
- **Reduced motion** — all ambient/kinetic animation off; reveals show instantly.

## 8. Implementation notes — React / Next.js

- Keep the tokens as a global CSS file (`futuristic-ui.css`) imported once in
  `app/layout.tsx`; they are framework-agnostic CSS custom properties.
- Model each component as a thin wrapper composing the `.ag-glass` primitive:
  `<Glass variant="holo reflective">`, `<GlassButton kind="primary">`, `<StatPill>`.
- Ambient backdrop (`ag-backdrop` + orbs + cursor field) lives in the root layout so
  it persists across route transitions; pair with the View Transitions API.
- Put the cursor/tilt/magnetic logic in a single client component mounted once
  (`"use client"`), gated on `matchMedia('(pointer:fine)')` and reduced-motion.
- Prefer server components for content; only interaction layers are client.

## 9. CSS / Tailwind guidance

- Bridge tokens into Tailwind via `theme.extend` reading the CSS vars:
  `colors: { glass: { 1: 'var(--ag-glass-1)' } }`, `boxShadow`, `borderRadius`, etc.
- Author the glass primitive as a Tailwind `@layer components` class rather than
  repeating `backdrop-blur bg-white/5 border ...` on every element — one source of truth.
- Use `backdrop-blur-[16px]` sparingly; expose only the three approved tiers.
- Keep the holographic border as raw CSS (mask-composite) — it has no clean Tailwind utility.

## 10. GSAP / Framer Motion directions

- **GSAP + ScrollTrigger** for the cinematic scroll layer: pin the hero, cross-fade
  section auras, and drive a scrubbed timeline for the reveal stagger. Batch with
  `ScrollTrigger.batch()` and always register a `matchMedia` reduced-motion branch.
- **Framer Motion** alternative: `whileInView` + `staggerChildren` for reveals,
  `useSpring`/`useTransform` on pointer for tilt & magnetic, `layoutId` for the nav
  glide pill. Wrap the app in `<MotionConfig reducedMotion="user">`.
- The static reference build reproduces all of this with IntersectionObserver + rAF
  and CSS keyframes so it ships with **zero JS dependencies**; GSAP/Framer are the
  recommended upgrade path when the surface moves into an app framework.

## 11. Performance optimization

- Fixed backdrop is a single paint layer; orbs are `position:fixed` with
  `will-change: transform` and animate transform only.
- Cap concurrently blurred surfaces; never nest `backdrop-filter`.
- Cursor field is updated via a **lerped rAF loop** writing two CSS vars — not a
  listener-per-frame style thrash.
- Reveal observers `unobserve` after firing (one-shot).
- No render-blocking scripts: all JS is `defer`/inline-at-end; fonts use `display=swap`.
- Respect `content-visibility: auto` on long below-the-fold sections if extended.

## 12. Accessibility

- Full `prefers-reduced-motion: reduce` branch in both CSS and JS — ambient motion,
  tilt, magnetic, cursor field, and reveals all collapse; content is never hidden.
- Contrast: body/dim text verified ≥ AA on glass; body copy never sits on a raw
  prism gradient (only headings use `-webkit-text-fill-color: transparent`, large).
- Keyboard: inherits the site-wide `:focus-visible` ring from `ui.css`; nav toggle
  exposes `aria-expanded` / `aria-controls`; decorative layers are `aria-hidden`.
- Pointer effects gated on `(pointer: fine)` so touch users get no dead interactions.
- Semantic landmarks: `<nav aria-label>`, `<main>`, `<header>`, `<footer>`.

## 13. Do not do

- ❌ Don't nest blurred glass inside blurred glass (compounds GPU cost, muddies contrast).
- ❌ Don't animate `width`, `height`, `top/left`, `box-shadow` size, or `blur` radius.
- ❌ Don't stack more than one `--ag-glow-lg` on an element (overglow).
- ❌ Don't put body text on a live prism gradient — readability first.
- ❌ Don't fake 3D with skewed drop-shadows or parallax layers deeper than a subtle tilt.
- ❌ Don't ship ambient motion without a reduced-motion escape hatch.
- ❌ Don't fabricate live data in the signal/stat modules — label demo values as such.
- ❌ Don't override the brand `--cg-*` primitives; extend with `--ag-*`.

## 14. Component architecture map

```
AuroraGlass
├─ AmbientBackdrop        (fixed: nebula wash · grid · aurora orbs · cursor field)
├─ FloatingNav            (glass pill · glide indicator · mobile sheet)
│   ├─ Brand
│   ├─ NavLinks
│   └─ NavCTA (luminous)
├─ Hero                   (aura · display · prism keyword · CTA · StatRow)
├─ SystemSplit            (prose ⇄ ReflectiveDataPanel[tilt])
├─ FeatureGrid
│   └─ GlassCard × n      (icon tile · title · body · hover lift)
├─ SignalStrip
│   └─ StatReadout × n    (mono · prism-clipped)
├─ ModuleGrid
│   └─ ContentModule × n  (StatusChip · title · body)
├─ Finale                 (launch panel · luminous CTA)
└─ Footer

Primitives:  Glass · GlassButton · Chip · Stat · Signal · Divider
Behaviors:   reveal/stagger (IO) · tilt · magnetic · cursorField · navGlide
```

## 15. Sample code direction

**Hero (structure):**
```html
<header class="ag-hero">
  <div class="ag-hero__aura"></div>
  <div class="ag-hero__panel" data-ag-reveal>
    <span class="ag-chip"><span class="ag-chip__dot"></span>live</span>
    <h1 class="ag-display">A <span class="ag-prism-text">control surface</span>.</h1>
    <div class="ag-hero__cta">
      <a class="ag-btn ag-btn--primary cg-magnetic">Explore</a>
      <a class="ag-btn ag-btn--ghost ag-btn--luminous cg-magnetic">Launch</a>
    </div>
  </div>
</header>
```

**Nav (React sketch):**
```tsx
<nav className="ag-nav" data-scrolled={scrolled}>
  <Brand />
  <div className="ag-nav__links">
    <motion.span layoutId="glide" className="ag-nav__glide" />
    {links.map(l => <a key={l.href} className="ag-nav__link">{l.label}</a>)}
  </div>
</nav>
```

**Card (composed from the primitive):**
```html
<article class="ag-glass ag-card ag-glass--holo" data-tilt>
  <div class="ag-card__icon">◇</div>
  <h3 class="ag-card__title">Holographic borders</h3>
  <p class="ag-card__body">Animated prism edges via mask compositing.</p>
</article>
```

**Luminous CTA border (the core trick — no extra DOM):**
```css
.ag-btn--luminous::before {
  content:""; position:absolute; inset:-1px; border-radius:inherit; padding:1px;
  background: var(--ag-edge-holo); background-size:300% 300%;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  animation: ag-holo 6s linear infinite;
}
```

---

*Aurora Glass · v1.0 — ClearGlass Inc. Extend via `--ag-*`; never override `--cg-*`.*
