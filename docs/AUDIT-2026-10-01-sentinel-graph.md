# Sentinel Core Intelligence Graph — Audit — 2026-10-01

**Base:** `main` at `005cf25` (includes PR #159, merge `c5f4ff8`)
**Branch:** `claude/sentinel-core-design-system-xb2mnc`
**Scope:** `station-chat.js` (graph and console CSS/JS), `sw.js`, `tests/test_sentinel_core.py`

Labels: **VERIFIED** (observed in a rendered page or a command named here),
**INFERENCE**, **NOT VERIFIED**. Three builds were measured side by side:

| Build | Source |
|---|---|
| A | `station-chat.js` at `8488d7b` (before PR #159) |
| B | `station-chat.js` at `origin/main` (`005cf25`) |
| C | this branch |

Method: headless Chromium 1194 (Playwright), `authority-network.html` served
locally, service worker blocked, each build injected for `station-chat.js`.
Viewports: 440×956 (iPhone 16 Pro Max), 393×852 (iPhone 15), 412×923
(Pixel 9), 390×844, 768×1024, 1440×900. Graph states probed: whole graph,
Company focused, Company focused then zoomed out ×4 (the reported iPhone
screenshot), home page selected, Labels layer on.

**Not verified:** real iOS Safari or Android Chrome on hardware. Emulated
viewports in Chromium do not reproduce WebKit rendering or a GPU.

---

## 1. Defects found

| # | Defect | Severity | Root cause | Introduced |
|---|---|---|---|---|
| D1 | Console live dot lost its ring pulse on every page | P1 regression | Graph CSS declared `@keyframes cgstLive`, which already named the console's dot animation; the later declaration replaced it | PR #159 |
| D2 | Labels cut off by the canvas edge (9–12 per phone run on B) | P1 | Labels always drawn on the side away from the core, with no viewport check | Before #159 |
| D3 | Node targets 10–14 px; a tap 9 px off-centre missed (0/7) and could unfocus the cluster | P1 | Hit area is the drawn dot only | Before #159 |
| D4 | 12 cluster groups stayed tab stops with the Clusters layer off, showing no focus | P1 (WCAG 2.4.7) | Focus ring is the boundary circle, which that layer hides | Before #159 |
| D5 | Directory rows 15 px, feed entries 13 px, layer chips 22 px | P1 (WCAG 2.5.8) | Text-height buttons | Before #159 |
| D6 | Bearing labels (000–330) at 3.12:1 contrast | P2 (WCAG 1.4.3) | `#56626e` on graphite | Before #159 |
| D7 | 35 CSS + 24 SMIL animations run for as long as the graph is open; idle 6.6–7.4 fps at 4× CPU throttle | P2 (WCAG 2.2.2, battery) | Ambient motion added in #159 never stops; the radar sweep never stopped before #159 either | #159 (worse), before |
| D8 | 19 console animations kept painting under the opaque graph overlay | P2 | Nothing paused them while the graph was open | Before #159 |
| D9 | Labels could be pushed under HUD controls or over the core disc | P2 | Collision pass had no obstacles | Introduced and fixed on this branch before merge |

## 2. Changes (C)

- D1: graph keyframes renamed `cgstGLive`. Test `test_console_keyframes_are_uniquely_named` fails on `main` (finds `cgstLive`) and passes here.
- D2/D9: the label pass now (a) treats the core disc and every HUD control as placed obstacles, (b) tries a page label on its default side, then the other side, then hides it until hover or zoom, (c) slides a cluster name back inside the canvas when its cluster is on screen, else hides it.
- D3: once a cluster is focused or the view is zoomed in (viewBox ≤ 520), a real tap (`event.detail > 0`) that hits no node selects the nearest node within 16 px. Keyboard Enter on a cluster is unchanged.
- D4: turning the Clusters layer off sets the cluster groups to `tabindex="-1"` and `aria-hidden="true"`; turning it on restores both.
- D5: graph controls at least 24 px on every pointer; at least 30 px on `(pointer: coarse)`. Directory rows use `line-height`, so their ellipsis still works (11 truncated titles keep `…`).
- D6: bearing labels `#74818e` (4.86:1).
- D7: `CALM_MS = 5000`. Five seconds after the last pointer, key, wheel or focus event, every graph CSS animation pauses, the SVG clock pauses (`pauseAnimations()`), and the radar, pulses and waves fade out. Any interaction wakes it.
- D8: while the graph is open, the console's sheet and rail pause their animations; they resume on close (19 → 0 → 19, verified).
- `sw.js` `VERSION` `cg-v63` → `cg-v64`: `station-chat.js` loads on every mapped page and is served stale-while-revalidate, so without a bump a returning visitor runs the old script on the first visit after deploy.

## 3. Results — VERIFIED

Totals across the five graph states, per build and viewport:

| Viewport | Build | Overlapping labels | Cropped labels | Under HUD | KPI text cut | Targets < 24 px | Text < 4.5:1 | Hidden tab stops | Live dot |
|---|---|---|---|---|---|---|---|---|---|
| iPhone 16 Pro Max | A | 26 | 12 | 0 | 5 | 12 | 4 | 12 | ring |
| | B | 0 | 9 | 0 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |
| iPhone 15 | A | 30 | 16 | 0 | 6 | 12 | 4 | 12 | ring |
| | B | 0 | 12 | 0 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |
| Pixel 9 | A | 29 | 16 | 0 | 6 | 12 | 4 | 12 | ring |
| | B | 0 | 12 | 0 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |
| 390 px | A | 30 | 16 | 0 | 6 | 12 | 4 | 12 | ring |
| | B | 0 | 12 | 0 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |
| 768 px | A | 12 | 2 | 4 | 0 | 12 | 5 | 12 | ring |
| | B | 0 | 2 | 5 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |
| 1440 px | A | 7 | 2 | 0 | 0 | 12 | 5 | 12 | ring |
| | B | 0 | 2 | 0 | 0 | 12 | 1 | 12 | **fade** |
| | C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ring |

"Targets < 24 px" lists at most 12 per run. C under `prefers-reduced-motion`
(440 px) also reads 0 on every column, with 0 CSS animations running.

Other checks:

| Check | B | C |
|---|---|---|
| Taps 9 px off a node, Company focused (7 nodes) | 0/7 select | 7/7 select |
| Dead-centre taps | 7/7 | 7/7 |
| Labels over the core, every node selected in turn (173), at 440 / 393 / 1440 px | 0 / – / 0 | 0 / 0 / 0 |
| Focus trap (40 Tabs) and Esc closes | holds, closes | holds, closes |
| Page errors | 0 | 0 |

Performance, 440 px, 4× CPU throttle, software rendering. Absolute numbers are
pessimistic; compare across rows.

| Build, state | Idle fps (5 s) | p95 frame | Layout ms / 5 s | Main-thread ms / 5 s |
|---|---|---|---|---|
| A, idle | 8.6–9.0 | 150–167 | 36–89 | 4486–4708 |
| B, idle | 6.6–7.4 | 167–217 | 132–172 | 4661–4848 |
| C, awake (< 5 s) | 7.0–7.6 | 217–283 | 88–108 | 4529–4641 |
| C, settled (> 5 s) | 23.0–27.4 | 67 | 0 | 1202–1267 |
| B / C, reduced motion | 32–36 / 38–39 | 50 | — | — |

Data provenance: every panel figure was recomputed from
`data/site-index.json` by an independent stdlib Python implementation
(entities, relationships, directed links, reciprocal, components, reach, mean
path, diameter, modularity, cut points, clusters, centralisation, confidence,
density, relationships per entity): **15/15 match** the rendered values.

Gates: `python3 scripts/ci_local.py` 10 passed, 0 failed, Lighthouse skipped
(network). `tests/test_sentinel_core.py`, `test_inline_script_syntax.py`,
`test_sentinel_homepage.py`: 38 passed.

## 4. Regression review

- **Zoom cost, VERIFIED, small regression.** Longest main-thread task across 8 zoom steps, reduced motion, 3 runs: B 709/714/867 ms, C 742/804/903 ms (4× throttle). The label pass now measures each wanted label up to twice and reads the HUD rectangles. INFERENCE: about 20 ms on unthrottled hardware.
- **Awake style cost.** The first wake after settling restyles the graph subtree once (`[data-calm] *`). It is a single recalculation, not per frame.
- **Labels hidden by design.** A label that fits neither side waits for hover, focus or zoom. Tapping or zooming reveals it; the directory lists every page.
- **Labels still cross non-core structure.** A label may lie over edges or another cluster's nodes, as before #159. Only the core disc and HUD controls are obstacles.
- **Snap scope.** In a focused cluster, a tap within 16 px of a node now selects it instead of unfocusing the cluster; a tap farther away behaves as before.
- **Settled state.** Paused routes keep their colours (outbound white, inbound blue) but stop flowing until the next interaction.

## 5. Remaining — NOT FIXED here

- **Focus order at ≤ 1100 px (WCAG 2.4.3).** The layout reorders panels with CSS `order` (canvas first) while the DOM keeps desktop order, so Tab reaches the left panel before the canvas. Fixing it needs a DOM reorder that the desktop grid must absorb; separate change.
- **Page animations under the overlay.** 9 animations from page scripts (`neon-pulse`, `.btn` rings, `cgr-scan`) keep running beneath the open graph. Not this component's code.
- **Small text.** KPI labels 7.5 px, node metrics about 7.6 px on screen. No WCAG minimum applies, but on a phone it is small.
- **Real devices: NOT VERIFIED.** iOS Safari's SMIL, `pointer: coarse` and `backdrop-filter` behaviour were not observed on hardware.
- **CI: NOT VERIFIED.** GitHub Actions still assigns no runner (`runner_id: 0`, CLAUDE.md); checks on the PR will read red without running.

## 6. Strongest case against merging

The settle behaviour changes the product's look after five idle seconds: the
sweep, pulses and waves fade and the field stops moving. If the brand intent is a
graph that is always in motion, that is a visible change. What would change
this recommendation: a decision that ambient motion matters more than WCAG
2.2.2 conformance and idle battery use, in which case `CALM_MS` is the one value
to raise, and a pause control would then be required instead.
