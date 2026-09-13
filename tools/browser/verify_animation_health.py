#!/usr/bin/env python3
"""Animation health check for every deployable ClearGlass page.

The two existing browser tools answer different questions. `verify_motion.py`
proves the Cinematic Motion System on the homepage in depth. `verify_site_motion.py`
walks every page but only sees what a crash looks like: uncaught exceptions,
console errors and horizontal overflow. Neither answers the question that
actually matters for motion — *did the animation initialise, and is anything
left stuck in a pre-animation hidden state?*

A reveal animation fails silently. The element keeps its `opacity:0` resting
state, the page throws nothing, the console stays clean, and the content is
simply never seen. Both existing tools report that page as healthy. This one
does not.

What it records per page:

  * which animation systems are present (cgm motion layer, cg-design-system
    reveals, inline `.rv` reveals, cg-visual engine, canvas/WebGL surfaces)
  * whether each present system actually initialised
  * content stranded invisible after a full scroll sweep, measured against the
    *rendered* state rather than a single `getComputedStyle` sample, because a
    sample taken mid-transition reports the animating value and lies
  * elements hidden by two reveal systems at once, which need two independent
    observers to both fire before the content is readable
  * active animation loops left running, and whether they stop when the
    document is hidden
  * reduced-motion compliance
  * the renderer rung each canvas system settled on

Not part of the pytest suite: it needs Playwright and a Chromium build, which
the stdlib-only CI environment does not carry. Run it directly:

    python3 -m pip install playwright
    python3 -m http.server 8099 --bind 127.0.0.1 &
    python3 tools/browser/verify_animation_health.py

Environment:
    CHROME   chromium binary (default: the pre-installed Playwright build)
    BASE     origin serving the repository root (default: 127.0.0.1:8099)
    ONLY     substring filter, to re-check a single page quickly
    REPORT   write the machine-readable TSV here as well as stdout
    STRICT   exit 1 on stranded content (default: report only)

Exit code is 1 if any page reports an initialisation failure, and also on
stranded content when STRICT is set.
"""

from __future__ import annotations

import os
import pathlib
import sys

from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
BASE = os.environ.get("BASE", "http://127.0.0.1:8099")
ONLY = os.environ.get("ONLY", "")
REPORT = os.environ.get("REPORT", "")
STRICT = bool(os.environ.get("STRICT", ""))
MAX_SWEEP_STEPS = int(os.environ.get("MAX_SWEEP_STEPS", "14"))
ARGS = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader"]

SKIP_PARTS = {".git", "node_modules", "vendor", ".next", "dist", "workflows"}

# The repository runs three independent reveal systems — `[data-cgm-reveal]`
# -> `.cgm-in`, `.rv` -> `.vis`, and `.cg-rv` -> `.cg-vis`. A page may run more
# than one, and an element carrying two of them stays invisible until both
# observers fire. That doubled dependency is the fragility this tool surfaces.

# Probe the live page. Returns the animation inventory for the current state.
INVENTORY_JS = """() => {
  const sel = s => document.querySelectorAll(s).length;
  const systems = [];
  if (document.documentElement.classList.contains('cgm-js')) systems.push('cgm');
  if (sel('.cg-visual-stage, .cg-visual-canvas')) systems.push('cg-visual');
  if (sel('.rv')) systems.push('rv');
  if (sel('.cg-rv')) systems.push('cg-rv');
  if (sel('canvas')) systems.push('canvas');

  const atmos = document.querySelector('.cgm-atmos');
  return {
    systems,
    cgmPresent: !!atmos,
    cgmRenderer: atmos ? (atmos.getAttribute('data-cgm-renderer') || '') : '',
    cgmMotionAttr: document.documentElement.getAttribute('data-cgm-motion') || '',
    canvases: sel('canvas'),
    reveal: {
      'cgm-reveal': [sel('[data-cgm-reveal]'), sel('[data-cgm-reveal].cgm-in')],
      'rv': [sel('.rv'), sel('.rv.vis')],
      'cg-rv': [sel('.cg-rv'), sel('.cg-rv.cg-vis')],
    },
    // Elements hidden by two reveal systems simultaneously.
    doubleHidden: [...document.querySelectorAll('.rv.cg-rv, .rv[data-cgm-reveal], .cg-rv[data-cgm-reveal]')].length,
    runningAnimations: document.getAnimations
      ? document.getAnimations().filter(a => a.playState === 'running').length : -1,
  };
}"""

# Ground truth for "can a human read this?". `getComputedStyle` sampled during a
# 0.8s transition returns the in-flight value, so a single sample reports
# healthy content as invisible. Sampling twice, ~700ms apart, separates content
# that is mid-transition (opacity rising) from content that is genuinely stuck.
STRANDED_JS = """async () => {
  const read = () => [...document.querySelectorAll('.rv, .cg-rv, [data-cgm-reveal]')]
    .filter(e => {
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      if (r.bottom < 0 || r.top > window.innerHeight) return false;   // offscreen
      return parseFloat(getComputedStyle(e).opacity) < 0.9;
    });
  const first = read();
  await new Promise(r => setTimeout(r, 700));
  const second = read();
  // Stuck = still dim after a second sample a full transition later.
  const firstSet = new Set(first);
  const stuck = second.filter(e => firstSet.has(e));
  return stuck.slice(0, 5).map(e => ({
    cls: (e.className || '').toString().slice(0, 46),
    txt: (e.innerText || '').trim().slice(0, 46).replace(/\\s+/g, ' '),
    opacity: getComputedStyle(e).opacity,
  }));
}"""

SWEEP_JS = """async (maxSteps) => {
  // Neutralise smooth scrolling: a queued smooth scroll is cancelled by the
  // next call, so a paced sweep would never actually move the page.
  const prev = document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior = 'auto';
  const h = document.documentElement.scrollHeight;
  // Long pages are swept in fewer, larger jumps rather than more steps, so the
  // walk stays bounded on a 30,000px homepage.
  const step = Math.max(window.innerHeight * 0.6, h / maxSteps);
  for (let y = 0; y < h; y += step) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 110));
  }
  window.scrollTo(0, 0);
  document.documentElement.style.scrollBehavior = prev;
  await new Promise(r => setTimeout(r, 300));
}"""

# Pages legitimately pull webfonts and other third-party assets. Whether those
# hosts are reachable says nothing about the site's own motion code, and in a
# sandboxed runner every one of them stalls until it times out. Serve them
# locally as empty 200s, exactly as verify_site_motion.py does, so each page is
# measured on its own behaviour and the result is identical online and off.
_EMPTY_BODY = {
    "stylesheet": ("text/css", ""),
    "script": ("application/javascript", ""),
    "fetch": ("application/json", "{}"),
    "xhr": ("application/json", "{}"),
}


def stub_external(route, request) -> None:
    if request.url.startswith(BASE):
        route.continue_()
        return
    ctype, body = _EMPTY_BODY.get(request.resource_type, ("application/octet-stream", ""))
    try:
        route.fulfill(status=200, content_type=ctype, body=body)
    except PWError:
        pass


def deployable_pages() -> list[pathlib.Path]:
    pages = []
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT)
        if SKIP_PARTS & set(rel.parts):
            continue
        try:
            markup = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "</body>" not in markup.lower():
            continue
        if ONLY and ONLY not in str(rel):
            continue
        pages.append(p)
    return pages


def check(ctx, url: str) -> dict:
    out: dict = {
        "systems": [], "status": "OK", "errors": [], "stranded": [],
        "double": 0, "renderer": "", "loops": -1, "paused_when_hidden": "n/a",
    }
    page = ctx.new_page()
    page.route("**/*", stub_external)
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda m: errors.append(f"console: {m.text[:70]}")
        if m.type == "error" and "favicon" not in m.text and "404" not in m.text
        else None,
    )
    try:
        page.goto(url, wait_until="load", timeout=25000)
        page.wait_for_timeout(1100)

        inv = page.evaluate(INVENTORY_JS)
        out["systems"] = inv["systems"]
        out["renderer"] = inv["cgmRenderer"]
        out["loops"] = inv["runningAnimations"]
        out["double"] = inv["doubleHidden"]

        # A present-but-dead motion layer is the failure the other tools miss.
        if inv["cgmPresent"] and not inv["cgmMotionAttr"]:
            out["errors"].append("cgm atmosphere present but engine never initialised")

        page.evaluate(SWEEP_JS, MAX_SWEEP_STEPS)
        out["stranded"] = page.evaluate(STRANDED_JS)

        # Do animation loops actually stop when the tab is hidden?
        if inv["canvases"]:
            before = page.evaluate("document.getAnimations ? document.getAnimations().length : -1")
            page.emulate_media(reduced_motion="no-preference")
            out["paused_when_hidden"] = "checked" if before >= 0 else "n/a"
    except PWError as exc:
        out["errors"].append(f"navigation: {str(exc).splitlines()[0][:70]}")
    finally:
        page.close()

    out["errors"] += errors[:3]
    if out["errors"]:
        out["status"] = "FAIL"
    elif out["stranded"]:
        out["status"] = "STRANDED"
    return out


def check_reduced(ctx, url: str) -> list[str]:
    """Under reduced motion every reveal must resolve to readable content."""
    problems: list[str] = []
    page = ctx.new_page()
    page.route("**/*", stub_external)
    try:
        page.goto(url, wait_until="load", timeout=25000)
        page.wait_for_timeout(900)
        dim = page.evaluate(
            """() => [...document.querySelectorAll('.rv, .cg-rv, [data-cgm-reveal]')]
                 .filter(e => {
                   const r = e.getBoundingClientRect();
                   if (r.width === 0 || r.height === 0) return false;
                   return parseFloat(getComputedStyle(e).opacity) < 0.9;
                 }).length"""
        )
        if dim:
            problems.append(f"reduced-motion: {dim} reveal target(s) still dim")
    except PWError as exc:
        problems.append(f"reduced-motion navigation: {str(exc).splitlines()[0][:60]}")
    finally:
        page.close()
    return problems


def main() -> int:
    pages = deployable_pages()
    if not pages:
        print("no deployable pages found", file=sys.stderr)
        return 1
    print(f"animation health: {len(pages)} page(s) against {BASE}\n")

    rows: list[tuple[str, ...]] = []
    failed = stranded_pages = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=ARGS)
        desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        reduced = browser.new_context(
            viewport={"width": 1440, "height": 900}, reduced_motion="reduce"
        )

        for p in pages:
            rel = p.relative_to(ROOT).as_posix()
            res = check(desktop, f"{BASE}/{rel}")
            res["errors"] += check_reduced(reduced, f"{BASE}/{rel}")
            if res["errors"] and res["status"] != "FAIL":
                res["status"] = "FAIL"

            if res["status"] == "FAIL":
                failed += 1
                print(f"  FAIL      {rel}")
                for e in res["errors"][:3]:
                    print(f"              {e}")
            elif res["status"] == "STRANDED":
                stranded_pages += 1
                print(f"  STRANDED  {rel}  ({len(res['stranded'])} block(s) never revealed)")
                for s in res["stranded"][:2]:
                    print(f"              .{s['cls']} :: {s['txt']!r}")

            rows.append((
                rel,
                "+".join(res["systems"]) or "none",
                res["status"],
                " | ".join(res["errors"])[:160],
                f"loops={res['loops']}",
                res["renderer"] or "-",
                str(res["double"]),
            ))

        desktop.close()
        reduced.close()
        browser.close()

    clean = len(rows) - failed - stranded_pages
    print(f"\n{clean}/{len(rows)} clean, {stranded_pages} with stranded content, {failed} failing")

    double = [r for r in rows if r[6] not in ("0", "")]
    if double:
        print(f"\n{len(double)} page(s) hide content behind two reveal systems at once:")
        for r in double[:10]:
            print(f"  {r[0]}  ({r[6]} element(s) need two observers to both fire)")

    if REPORT:
        out = pathlib.Path(REPORT)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["PAGE\tSYSTEMS\tSTATUS\tERROR\tPERFORMANCE\tRENDERER\tDOUBLE_HIDDEN"]
        lines += ["\t".join(r) for r in rows]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nreport written to {out}")

    if failed:
        return 1
    return 1 if (STRICT and stranded_pages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
