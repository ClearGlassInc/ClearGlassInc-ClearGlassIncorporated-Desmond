#!/usr/bin/env python3
"""Browser verification for the React motion system on the Next route.

Companion to verify_motion.py, which covers the static-site layer. Needs
Playwright and a Chromium build, so it is not part of the pytest suite.

    npm run build && npx next start -p 3033 &
    CHROME=/path/to/chrome URL=http://127.0.0.1:3033/motion-system \
      SHOTS=./shots python3 tools/browser/verify_next.py

Covers hydration under the app's CSP, the renderer ladder, the reduced-motion
substitution, JavaScript disabled, mobile/touch, and narrow-viewport overflow.
"""

import os
import sys

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
URL = os.environ.get("URL", "http://127.0.0.1:3033/motion-system")
SHOTS = os.environ.get("SHOTS", "./shots")
os.makedirs(SHOTS, exist_ok=True)
ARGS = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader"]
res, fails = [], []

def ck(n, ok, d=""):
    res.append((n, bool(ok), d))
    if not ok:
        fails.append(f"{n}: {d}")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=ARGS)

    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    errs, pe = [], []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: pe.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(2200)
    ck("no page errors", not pe, "; ".join(pe[:3]))
    notable = [e for e in errs if "404" not in e]
    ck("no console errors (incl. CSP + hydration)", not notable, "; ".join(notable[:3]))
    if len(notable) != len(errs):
        print("    [note] a 404 was logged: the Next app ships no favicon.ico")
    ck("hydrated: 9 interactive nodes", pg.locator(".cgm-node").count() == 9,
       f"got {pg.locator('.cgm-node').count()}")
    ck("motion resolved to full",
       pg.evaluate("document.documentElement.getAttribute('data-cgm-motion')") == "full")
    ck("signal-field canvas mounted", pg.locator(".cgm-stage__canvas").count() == 1)
    ck("static SVG graph also in DOM", pg.locator(".cgm-stage__svg").count() >= 1)
    ck("preference control rendered", pg.locator(".cgm-pref").count() == 1)
    ck("custom cursor mounted", pg.locator(".cgm-cursor").count() == 1)
    ck("atmosphere behind content",
       pg.evaluate("getComputedStyle(document.querySelector('.cgm-atmos')).zIndex") == "-1")
    ck("live badge states its value in text",
       "HEALTHY" in (pg.locator(".cgm-badge").first.inner_text() or "").upper())
    ck("glass cards rendered", pg.locator(".cgm-glass").count() >= 16,
       f"got {pg.locator('.cgm-glass').count()}")

    cls = pg.evaluate("""() => new Promise(r => {
      let v=0; try { new PerformanceObserver(l=>{for(const e of l.getEntries())
        if(!e.hadRecentInput) v+=e.value;}).observe({type:'layout-shift',buffered:true}); } catch(e){}
      setTimeout(()=>r(+v.toFixed(4)), 1500); })""")
    ck("CLS under 0.1 at load", cls < 0.1, f"CLS={cls}")
    print(f"    [measured] Next route CLS at load = {cls}")

    pg.locator("#cgm-constellation-h").scroll_into_view_if_needed()
    pg.wait_for_timeout(900)
    n = pg.locator(".cgm-node")
    n.nth(0).click(force=True)
    n.nth(1).click(force=True)
    pg.wait_for_timeout(300)
    path = pg.locator(".cgm-readout__path").inner_text() or ""
    ck("pathway builds", "→" in path, path[:60])
    ck("pathway is aria-live",
       pg.locator('.cgm-readout__path[aria-live="polite"]').count() == 1)
    shape_ok = True
    try:
        pg.wait_for_function(
            """() => { const d = document.querySelector('.cgm-node[aria-pressed="true"] .cgm-node__dot');
                       return d !== null && getComputedStyle(d).borderRadius !== '50%'; }""",
            timeout=5000)
    except PWTimeout:
        shape_ok = False
    ck("selection is not colour-only", shape_ok)
    ck("keyboard focus reaches a node",
       pg.evaluate("""(()=>{const n=document.querySelector('.cgm-node'); n.focus();
         return document.activeElement === n;})()"""))
    ck("no horizontal overflow at 1440",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth+1"))
    pg.screenshot(path=f"{SHOTS}/07-next-motion-system.png")
    ctx.close()

    ctx = b.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg = ctx.new_page()
    rpe = []
    pg.on("pageerror", lambda e: rpe.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(1600)
    ck("reduced: no page errors", not rpe, "; ".join(rpe[:3]))
    ck("reduced: static graph substituted", pg.locator(".cgm-stage__svg").count() >= 1)
    ck("reduced: no animated canvas", pg.locator(".cgm-stage__canvas").count() == 0)
    ck("reduced: no custom cursor", pg.locator(".cgm-cursor").count() == 0)
    ck("reduced: all content visible",
       pg.evaluate("[...document.querySelectorAll('.cgm-r')].every(e=>getComputedStyle(e).opacity==='1')"))
    pg.screenshot(path=f"{SHOTS}/08-next-reduced-motion.png")
    ctx.close()

    ctx = b.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(400)
    ck("no-JS: hero visible", pg.locator("#cgm-hero-h").is_visible())
    ck("no-JS: static graph visible", pg.locator(".cgm-stage__svg").count() >= 1)
    ck("no-JS: narrative visible", pg.locator("#cgm-scene-01-h").is_visible())
    ck("no-JS: CTA reachable", pg.locator(".cgm-btn").first.is_visible())
    pg.screenshot(path=f"{SHOTS}/10-next-no-javascript.png")
    ctx.close()

    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                        has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    mpe = []
    pg.on("pageerror", lambda e: mpe.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(1600)
    ck("mobile: no page errors", not mpe, "; ".join(mpe[:3]))
    ck("mobile: no horizontal overflow",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth+1"),
       pg.evaluate("document.documentElement.scrollWidth+' vs '+window.innerWidth"))
    ck("mobile: canvas dropped on low power", pg.locator(".cgm-stage__canvas").count() == 0)
    ck("mobile: content visible", pg.locator("#cgm-hero-h").is_visible())
    pg.screenshot(path=f"{SHOTS}/09-next-mobile-390.png")
    ctx.close()

    ctx = b.new_context(viewport={"width": 400, "height": 900})
    pg = ctx.new_page()
    pg.goto(URL, wait_until="load")
    pg.wait_for_timeout(900)
    ck("400px: no horizontal overflow",
       pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth+1"),
       pg.evaluate("document.documentElement.scrollWidth+' vs '+window.innerWidth"))
    ctx.close()
    b.close()

print()
for n, ok, d in res:
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"   [{d}]" if d and not ok else ""))
print(f"\n{sum(1 for _, o, _ in res if o)}/{len(res)} checks passed")
if fails:
    print("\nFAILURES:")
    for f in fails:
        print("  -", f)
sys.exit(1 if fails else 0)
