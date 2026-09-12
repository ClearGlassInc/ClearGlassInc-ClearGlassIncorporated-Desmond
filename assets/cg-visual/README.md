# ClearGlass Visual Engine (`assets/cg-visual/`)

Additive, production-safe realtime visualization engine for the static site. ES
modules, zero runtime dependencies, self-hosted (CSP-safe: no `eval`, no
`Function`, no remote code, no network). Fully progressive: content renders
first, the engine enhances after, and it degrades silently to nothing on
unsupported browsers.

## Coherence model

One authoritative **WorldState** drives every visual. The causal pipeline is:

```
EVENT → VALIDATE (zero-trust) → CLASSIFY → STATE TRANSITION → SIM UPDATE → SCENE UPDATE → RENDER
```

A single event fans out across multiple layers (particles, graph, signals,
anomalies, entropy). Multi-scale sync runs three cadences: MICRO (every step),
MESO (~15 Hz), MACRO (~2 Hz).

## Layout

- `core/` — pure, DOM-free, deterministic model (node-testable):
  `rng`, `temporal` (EWMA), `entropy`, `events` (bounded queue + burst
  compression + backpressure), `particle-pool` (fixed-capacity, zero per-frame
  allocation), `fields`, `governor` (`ClearGlassGPUResourceGovernor`, hysteresis,
  median+P95), `importance`, `graph`, `signals`, `provenance` (symbolic DEMO
  hash), `anomaly` (SIMULATION), `ai-pipeline` (observable stages only),
  `simulation` (WorldState), `replay` (deterministic record/replay).
- `render/` — browser layer: `backend` (WebGPU → WebGL2 → Canvas2D → static
  chain), `scenes` (SceneManager + FIELD/GRAPH/NETWORK/TELEMETRY/ANOMALY/RADAR/
  PROVENANCE/AI_PIPELINE), `hud` (dev-only), `failure-injection` (dev-only),
  `engine` (orchestrator: loop, governor, reduced-motion, context-loss recovery).
- `cg-visual-boot.js` — progressive `type="module"` entry, wired into pages.
- `cg-visual.css` — layout-neutral decorative host (`z-index:-1`, `pointer-events:none`).

## Safety / honesty labels

Entropy is a **visual activity index**, never a cyber-risk score. Provenance
hashes are **symbolic DEMO digests** (not cryptographic; the real SHA-256 RFED
chain lives elsewhere in the repo). Anomalies are labelled **SIMULATION**. The
AI pipeline shows only observable governance stages — never private
chain-of-thought.

## Config

- `<body data-cg-visual="FIELD,GRAPH">` — scene list (`off` disables).
- `?cgvisual=off` / `localStorage['cg-visual-off']='1'` — kill switch.
- `?cgdebug=1` / `localStorage['cg-visual-debug']='1'` — dev HUD + fault controller.
- `?cgfault=forceCanvas,floodEvents,...` — dev-only failure injection.
- Reduced motion integrates with the site toggle (`localStorage['cgm-motion-preference']`).

## Tests

Headless model suite (no GPU, no browser):

```bash
node --test "assets/cg-visual/tests/*.test.mjs"
```

Playwright headless-Chromium smoke (uses the preinstalled Chromium; needs a
resolvable `playwright-core`):

```bash
CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
CG_PW_CORE=/abs/path/to/node_modules/playwright-core/index.js \
node assets/cg-visual/tests/browser-smoke.mjs
```
