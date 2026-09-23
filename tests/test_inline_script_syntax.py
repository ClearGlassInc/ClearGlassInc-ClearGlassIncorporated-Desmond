"""Every inline <script> on every shipped page must parse.

A single syntax error aborts the whole script block, so the page renders but
nothing on it works. Three pages shipped that way at once: ``artemis-iv.html``
(a duplicated ``const``), ``counter-uas-commercialization-os.html`` (a stray
``)``) and ``revenue-command.html``, whose regex ``//$/`` parsed as a comment.
On that last page the submit handler never attached, so the browser fell back
to a native GET and wrote each prospect's name, email and business problem into
the URL. None of the existing tests executes page JavaScript, so none caught it.

V8 compiles each block without running it, which reports the same early errors
as ``node --check``. One Node process checks the whole site.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".next", "node_modules", "vendor"}
# Script types the browser executes as JavaScript. JSON-LD, templates and
# importmaps are data, not code.
CLASSIC_TYPES = {"", "text/javascript", "application/javascript"}

CHECKER = r"""
const fs = require("fs"), os = require("os"), path = require("path");
const vm = require("vm"), { spawnSync } = require("child_process");
const blocks = JSON.parse(fs.readFileSync(0, "utf8"));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cg-inline-"));
const failures = [];
blocks.forEach((b, i) => {
  if (b.module) {
    // Module grammar (import/export, top-level await) needs the module parser.
    const file = path.join(tmp, i + ".mjs");
    fs.writeFileSync(file, b.code);
    const r = spawnSync(process.execPath, ["--check", file], { encoding: "utf8" });
    if (r.status !== 0) {
      const line = (r.stderr.split("\n").find((l) => /Error/.test(l)) || r.stderr).trim();
      failures.push(b.where + ": " + line);
    }
    return;
  }
  try {
    new vm.Script(b.code, { filename: b.where });
  } catch (e) {
    failures.push(b.where + ": " + e.name + ": " + e.message);
  }
});
fs.rmSync(tmp, { recursive: true, force: true });
process.stdout.write(JSON.stringify(failures));
"""


class _InlineScripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.blocks: list[tuple[int, bool, str]] = []
        self._open: tuple[int, bool, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attributes = dict(attrs)
        kind = (attributes.get("type") or "").strip().lower()
        if "src" in attributes or (kind not in CLASSIC_TYPES and kind != "module"):
            self._open = None
            return
        self._open = (self.getpos()[0], kind == "module", [])

    def handle_data(self, data: str) -> None:
        if self._open is not None:
            self._open[2].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._open is not None:
            line, is_module, parts = self._open
            self.blocks.append((line, is_module, "".join(parts)))
            self._open = None


def inline_script_blocks() -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for path in sorted(ROOT.rglob("*.html")):
        relative = path.relative_to(ROOT)
        if EXCLUDED_PARTS.intersection(relative.parts):
            continue
        parser = _InlineScripts()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        for line, is_module, code in parser.blocks:
            if code.strip():
                blocks.append({"where": f"{relative}:{line}", "module": is_module, "code": code})
    return blocks


def test_inline_scripts_are_discovered() -> None:
    # Guards the guard: a parser regression that finds nothing would pass vacuously.
    assert len(inline_script_blocks()) > 100


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to parse page JavaScript")
def test_every_inline_script_parses() -> None:
    blocks = inline_script_blocks()
    result = subprocess.run(
        ["node", "-e", CHECKER],
        input=json.dumps(blocks),
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    failures = json.loads(result.stdout)
    assert not failures, "Inline scripts that will not parse:\n" + "\n".join(failures)


def test_lead_form_never_falls_back_to_get() -> None:
    # If the page script ever fails again, a POST keeps personal data out of
    # the URL, browser history, server logs and Referer headers.
    markup = (ROOT / "revenue-command.html").read_text(encoding="utf-8")
    assert '<form id="lead-form" method="post">' in markup
