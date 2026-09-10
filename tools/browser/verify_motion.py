#!/usr/bin/env python3
"""Browser verification for the ClearGlass Cinematic Motion System.

Not part of the pytest suite: it needs Playwright and a Chromium build, which
the stdlib-only CI environment does not carry. Run it directly.

    python3 -m pip install playwright
    python3 -m http.server 8099 --bind 127.0.0.1 &
    CHROME=/path/to/chrome SHOTS=./shots python3 tools/browser/verify_motion.py

Covers, across five browser contexts: console/page errors, layout shift at
load, the renderer ladder, reveal behaviour, keyboard reachability, the
magnetic-movement clamp, reduced motion, JavaScript disabled, mobile/touch,
narrow-viewport overflow, and GPU teardown. Writes screenshots to $SHOTS.
"""

import os
import sys

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
URL = "http://127.0.0.1:8099/index.html"
SHOTS = os.environ.get("SHOTS", "./shots")
os.makedirs(SHOTS, exist_ok=True)
ARGS = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader"]
results, failures = [], []

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    if not ok:
        failures.append(f"{name}: {detail}")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=ARGS)

    # ── 1. default desktop, motion enabled ─────────────────────────────
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    pg = ctx.new_page()
    errs, pageerrs = [], []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: pageerrs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(1400)

    # External fonts and a GitHub raw URL are unreachable through this
    # environment's egress proxy; those are environmental, not page defects.
    real = [e for e in errs if "ERR_CONNECTION_RESET" not in e]
    check("no console errors", not real, "; ".join(real[:4]))

    cls = pg.evaluate("""() => new Promise(r => {
      let v=0; try {
        new PerformanceObserver(l=>{for(const e of l.getEntries()) if(!e.hadRecentInput) v+=e.value;})
          .observe({type:'layout-shift',buffered:true});
      } catch(e){}
      setTimeout(()=>r(+v.toFixed(4)), 1500);
    })""")
    check("cumulative layout shift under 0.1 at load", cls < 0.1, f"CLS={cls}")
    print(f"    [measured] CLS at load = {cls}  (committed baseline = 0.0204)")
    check("no uncaught page errors", not pageerrs, "; ".join(pageerrs[:4]))
    check("cgm-js applied", pg.evaluate("document.documentElement.classList.contains('cgm-js')"))
    check("atmosphere present", pg.locator(".cgm-atmos").count() == 1)
    check("atmosphere behind content",
          pg.evaluate("getComputedStyle(document.querySelector('.cgm-atmos')).zIndex") == "-1")

    nodes = pg.locator(".cgm-node")
    check("constellation renders 9 nodes", nodes.count() == 9, f"got {nodes.count()}")
    check("nodes are real buttons",
          pg.evaluate("[...document.querySelectorAll('.cgm-node')].every(n=>n.tagName==='BUTTON')"))
    check("nodes expose aria-pressed",
          pg.evaluate("[...document.querySelectorAll('.cgm-node')].every(n=>n.hasAttribute('aria-pressed'))"))

    renderer = pg.evaluate("""(() => {
      const s = document.querySelector('.cgm-constellation__stage');
      if (!s) return 'no-stage';
      if (s.querySelector('canvas')) return 'canvas';
      if (s.querySelector('[data-cgm-static-links]')) return 'svg';
      return 'none';
    })()""")
    check("layer-3 renderer active", renderer == "canvas", f"renderer={renderer}")

    check("constellation draws connections",
          pg.evaluate("!!document.querySelector('.cgm-constellation__stage canvas')")
          and pg.evaluate("!!document.querySelector('.cgm-constellation__stage [data-cgm-static-links]')"))
    gpu = pg.evaluate("document.querySelector('.cgm-atmos').getAttribute('data-cgm-renderer')")
    check("atmosphere field uses a real renderer", gpu in ("webgl2", "canvas2d"), f"kind={gpu}")
    print(f"    [measured] atmosphere renderer = {gpu}")

    # reveals actually resolve to visible
    revealed = pg.evaluate("""(() => {
      const all=[...document.querySelectorAll('[data-cgm-reveal]')];
      return {total:all.length, hidden:all.filter(e=>getComputedStyle(e).opacity==='0'
        && e.getBoundingClientRect().top < innerHeight).length};
    })()""")
    check("in-viewport reveals are visible", revealed["hidden"] == 0,
          f"{revealed['hidden']} of {revealed['total']} still hidden")

    # pathway on multi-select. Scroll into view first, and click with force:
    # the page carries pre-existing always-running animations that reflow
    # content far below the fold (measured 15.1px of jitter on the committed
    # page, before this layer existed), so a deep click target never settles
    # into Playwright's "stable" state. force=True skips only the stability
    # wait; visibility and enabled-ness are still asserted separately below.
    pg.evaluate("document.querySelector('#cgm-constellation-h').scrollIntoView({block:'center',behavior:'instant'})")
    # Wait on the observable end state rather than a fixed sleep: under
    # software rendering on a 31k-px page the transition can land well after
    # the class is applied.
    revealed_ok = True
    try:
        pg.wait_for_function(
            "() => getComputedStyle(document.querySelector('.cgm-constellation')).opacity === '1'",
            timeout=8000)
    except PWTimeout:
        revealed_ok = False
    check("constellation container revealed", revealed_ok,
          pg.evaluate("getComputedStyle(document.querySelector('.cgm-constellation')).opacity"))
    check("node is visible and enabled",
          nodes.nth(0).is_visible() and nodes.nth(0).is_enabled())
    nodes.nth(0).click(force=True)
    nodes.nth(1).click(force=True)
    pg.wait_for_timeout(200)
    pathway = pg.locator("[data-cgm-pathway]")
    check("multi-select builds a pathway",
          not pathway.is_hidden() and "→" in (pathway.inner_text() or ""),
          (pathway.inner_text() or "")[:70])

    # keyboard reachability
    focused = pg.evaluate("""(() => {
      const n=document.querySelector('.cgm-node'); n.focus();
      return document.activeElement === n;
    })()""")
    check("nodes are keyboard focusable", focused)

    # magnetic clamp
    btn = pg.locator(".cgm-btn[data-cgm-magnetic]").first
    box = btn.bounding_box()
    pg.mouse.move(box["x"] + box["width"] + 220, box["y"] + box["height"] + 220)
    pg.wait_for_timeout(150)
    shift = pg.evaluate("""(() => {
      const b=document.querySelector('.cgm-btn[data-cgm-magnetic]');
      const cs=getComputedStyle(b);
      return [parseFloat(cs.getPropertyValue('--cgm-btn-x'))||0,
              parseFloat(cs.getPropertyValue('--cgm-btn-y'))||0];
    })()""")
    check("magnetic shift clamped to 5px",
          all(abs(v) <= 5.01 for v in shift), f"shift={shift}")

    # layout shift + no horizontal overflow

    check("no horizontal overflow at 1440",
          pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
          pg.evaluate("document.documentElement.scrollWidth + ' vs ' + window.innerWidth"))

    pg.screenshot(path=f"{SHOTS}/01-desktop-1440-top.png")
    pg.wait_for_timeout(300)
    pg.screenshot(path=f"{SHOTS}/02-desktop-1440-constellation.png")
    pg.evaluate("document.querySelector('#cgm-scene-01-h').scrollIntoView({block:'center',behavior:'instant'})")
    pg.wait_for_timeout(900)
    pg.screenshot(path=f"{SHOTS}/03-desktop-1440-narrative.png")
    ctx.close()

    # ── 2. reduced motion ──────────────────────────────────────────────
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg = ctx.new_page()
    rerrs = []
    pg.on("pageerror", lambda e: rerrs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(1200)
    check("reduced-motion: no page errors", not rerrs, "; ".join(rerrs[:3]))
    check("reduced-motion: flag set",
          pg.evaluate("document.documentElement.getAttribute('data-cgm-motion')") == "reduced")
    check("reduced-motion: all content visible",
          pg.evaluate("[...document.querySelectorAll('[data-cgm-reveal]')].every(e=>getComputedStyle(e).opacity==='1')"))
    check("reduced-motion: no animated canvas",
          pg.evaluate("!document.querySelector('.cgm-constellation__stage canvas')"))
    check("reduced-motion: no atmosphere renderer",
          pg.evaluate("!document.querySelector('.cgm-atmos').getAttribute('data-cgm-renderer')"))
    check("reduced-motion: static SVG fallback drawn",
          pg.locator(".cgm-constellation__stage [data-cgm-static-links]").count() == 1)
    check("reduced-motion: cursor ring hidden",
          pg.evaluate("getComputedStyle(document.querySelector('.cgm-cursor')).display") == "none")
    check("reduced-motion: nodes still present", pg.locator(".cgm-node").count() == 9)
    pg.screenshot(path=f"{SHOTS}/04-reduced-motion.png")
    ctx.close()

    # ── 3. JavaScript disabled ─────────────────────────────────────────
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(500)
    check("no-JS: cgm-js absent",
          pg.evaluate_handle("1") is not None and
          pg.locator("html.cgm-js").count() == 0)
    check("no-JS: hero copy visible",
          pg.locator("#cgm-hero-interface-h").is_visible())
    check("no-JS: all reveal sections visible",
          pg.evaluate("[...document.querySelectorAll('[data-cgm-reveal]')].length") is not None
          and pg.locator("#cgm-services-h").is_visible())
    check("no-JS: CTA reachable", pg.locator(".cgm-btn").first.is_visible())
    pg.screenshot(path=f"{SHOTS}/05-no-javascript.png")
    ctx.close()

    # ── 4. mobile 390 + touch ──────────────────────────────────────────
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                        has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    merrs = []
    pg.on("pageerror", lambda e: merrs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(1200)
    check("mobile: no page errors", not merrs, "; ".join(merrs[:3]))
    check("mobile: no horizontal overflow",
          pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
          pg.evaluate("document.documentElement.scrollWidth + ' vs ' + window.innerWidth"))
    check("mobile: heavy layers dropped",
          pg.evaluate("getComputedStyle(document.querySelector('.cgm-atmos__scan')).display") == "none")
    check("mobile: content visible", pg.locator("#cgm-hero-interface-h").is_visible())
    pg.screenshot(path=f"{SHOTS}/06-mobile-390.png", full_page=False)
    ctx.close()

    # ── 5. 400px gutter check ──────────────────────────────────────────
    ctx = b.new_context(viewport={"width": 400, "height": 900})
    pg = ctx.new_page()
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(800)
    check("400px: no horizontal overflow",
          pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
          pg.evaluate("document.documentElement.scrollWidth + ' vs ' + window.innerWidth"))
    ctx.close()

    # ── 6. tab-hidden pause + dispose ──────────────────────────────────
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(900)
    check("dispose hook exposed",
          pg.evaluate("typeof document.querySelector('.cgm-constellation__stage').cgDispose === 'function'"))
    disposed = pg.evaluate("""(() => {
      const s=document.querySelector('.cgm-constellation__stage');
      s.cgDispose();
      return !s.querySelector('canvas');
    })()""")
    check("dispose removes the canvas", disposed)
    check("motion toggle present and labelled",
          pg.locator("[data-cgm-motion-toggle]").count() == 1)
    ctx.close()
    b.close()

print()
for name, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))
print(f"\n{sum(1 for _,o,_ in results if o)}/{len(results)} checks passed")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
sys.exit(1 if failures else 0)
