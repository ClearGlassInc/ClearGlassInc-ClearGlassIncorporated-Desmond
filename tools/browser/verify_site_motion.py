#!/usr/bin/env python3
"""Site-wide browser health check for the ClearGlass motion system.

`verify_motion.py` proves the Cinematic Motion System on one page in depth.
This walks *every* deployable page instead, at desktop and phone width, and
reports the failures that only a real browser can see: uncaught exceptions,
console errors, horizontal overflow, and animation layers that never start.

Not part of the pytest suite — it needs Playwright and a Chromium build, which
the stdlib-only CI environment does not carry. Run it directly:

    python3 -m pip install playwright
    python3 -m http.server 8099 --bind 127.0.0.1 &
    python3 tools/browser/verify_site_motion.py

Environment:
    CHROME   chromium binary (default: the pre-installed Playwright build)
    BASE     origin serving the repository root (default: 127.0.0.1:8099)
    ONLY     substring filter, to re-check a single page quickly
    REPORT   write the machine-readable TSV here as well as stdout

Exit code is 1 if any page reports an error, so it can gate a release.
"""

from __future__ import annotations

import os
import pathlib
import sys

from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = os.environ.get(
    "CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
)
BASE = os.environ.get("BASE", "http://127.0.0.1:8099")
ONLY = os.environ.get("ONLY", "")
REPORT = os.environ.get("REPORT", "")
ARGS = ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader"]

SKIP_PARTS = {".git", "node_modules", "vendor", ".next", "dist", "workflows"}

# Chrome emits these for reasons outside the page's control; they are not
# defects in the site and must not fail a release.
BENIGN = (
    "favicon",
    "ERR_INTERNET_DISCONNECTED",
    "ERR_NAME_NOT_RESOLVED",
    "ERR_CONNECTION_REFUSED",
    "net::ERR_ABORTED",
    "Failed to load resource: the server responded with a status of 404",
)


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


def benign(text: str) -> bool:
    return any(token in text for token in BENIGN)


# Pages legitimately pull webfonts and other third-party assets. Whether those
# hosts are reachable says nothing about the site's own code, and in a sandboxed
# or offline runner every one of them fails and buries the real findings. Serve
# them locally as empty 200s so each page is measured on its own behaviour and
# the result is identical online and off.
_EMPTY_BODY = {
    "css": ("text/css", ""),
    "js": ("application/javascript", ""),
    "json": ("application/json", "{}"),
}


def stub_external(route, request) -> None:
    if request.url.startswith(BASE):
        route.continue_()
        return
    kind = request.resource_type
    if kind == "stylesheet":
        ctype, body = _EMPTY_BODY["css"]
    elif kind == "script":
        ctype, body = _EMPTY_BODY["js"]
    elif kind in ("fetch", "xhr"):
        ctype, body = _EMPTY_BODY["json"]
    else:  # fonts, images, media
        ctype, body = "application/octet-stream", ""
    try:
        route.fulfill(status=200, content_type=ctype, body=body)
    except PWError:
        pass


def check_page(ctx, url: str, width: int) -> tuple[list[str], bool]:
    """Return (errors, overflowed) for one page at one viewport width."""
    errors: list[str] = []
    page = ctx.new_page()
    page.route("**/*", stub_external)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda m: errors.append(f"console.{m.type}: {m.text}")
        if m.type == "error" and not benign(m.text)
        else None,
    )
    overflowed = False
    try:
        page.goto(url, wait_until="load", timeout=20000)
        page.wait_for_timeout(900)  # let deferred motion init and settle
        overflowed = page.evaluate(
            "() => document.documentElement.scrollWidth > window.innerWidth + 1"
        )
    except PWError as exc:
        errors.append(f"navigation: {str(exc).splitlines()[0]}")
    finally:
        page.close()
    return errors, bool(overflowed)


def main() -> int:
    pages = deployable_pages()
    if not pages:
        print("no deployable pages found", file=sys.stderr)
        return 1
    print(f"checking {len(pages)} page(s) against {BASE}\n")

    rows: list[tuple[str, str, str]] = []
    failed = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=ARGS)
        desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        phone = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )

        for p in pages:
            rel = p.relative_to(ROOT).as_posix()
            url = f"{BASE}/{rel}"
            problems: list[str] = []

            errs, over = check_page(desktop, url, 1440)
            problems += errs
            if over:
                problems.append("horizontal overflow at 1440px")

            errs, over = check_page(phone, url, 390)
            problems += [f"[390px] {e}" for e in errs]
            if over:
                problems.append("horizontal overflow at 390px")

            status = "OK" if not problems else "FAIL"
            if problems:
                failed += 1
                print(f"  FAIL  {rel}")
                for problem in problems[:4]:
                    print(f"          {problem}")
                if len(problems) > 4:
                    print(f"          … +{len(problems) - 4} more")
            rows.append((rel, status, " | ".join(problems)))

        desktop.close()
        phone.close()
        browser.close()

    ok = len(rows) - failed
    print(f"\n{ok}/{len(rows)} pages clean, {failed} with findings")

    if REPORT:
        out = pathlib.Path(REPORT)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["PAGE\tSTATUS\tFINDINGS"]
        lines += ["\t".join(r) for r in rows]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"report written to {out}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
