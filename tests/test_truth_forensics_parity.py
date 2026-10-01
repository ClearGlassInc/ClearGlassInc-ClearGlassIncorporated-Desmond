# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The browser engine must produce exactly what the Python engine produces.

`assets/js/truth-forensics-engine.js` is run in Node against the committed
demonstration corpus, with and without the demonstration reviews. Its full
result (telemetry aside) and its report must be byte-identical canonical JSON
to the Python engine's. A difference is reported as the first diverging path.

Also asserted here: the vocabulary tables match, the JS SSRF guard refuses
the same URLs, and the console never writes untrusted text with innerHTML.

Needs `node` on PATH (ubuntu-latest provides it, as tests/test_inline_script_syntax.py
already requires).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from truth_forensics import case, demo, report, vocab
from truth_forensics.canonical import canonical_json

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "assets" / "js" / "truth-forensics-engine.js"
CONSOLE = ROOT / "assets" / "js" / "truth-forensics-console.js"
CASE_PATH = ROOT / "data" / "truth-forensics" / "demo-case.json"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

RUNNER = r"""
const E = require(process.argv[1]);
const fs = require('fs'), path = require('path');
(async () => {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  const out = {};
  if (input.mode === 'case') {
    const kase = JSON.parse(fs.readFileSync(input.case, 'utf8'));
    const base = path.dirname(input.case), files = {};
    for (const it of kase.evidence) files[it.evidence_id] = new Uint8Array(fs.readFileSync(path.join(base, it.file)));
    const res = await E.runCase(kase, files, input.reviews || []);
    delete res.telemetry;
    out.result = E.canonicalJson(res);
    out.report = E.canonicalJson(await E.buildReport(res));
    out.markdown = E.renderMarkdown(await E.buildReport(res));
  } else if (input.mode === 'vocab') {
    out.vocab = E.vocab;
  } else if (input.mode === 'urls') {
    out.urls = input.urls.map((u) => E.validateUrl(u)[0]);
  } else if (input.mode === 'decompose') {
    out.props = input.claims.map((c) => E.decompose(c));
  }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def run_node(payload: dict) -> dict:
    proc = subprocess.run([NODE, "-e", RUNNER, str(ENGINE)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=120, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def first_difference(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: python {type(a).__name__} {a!r:.120} != js {type(b).__name__} {b!r:.120}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{path}.{k}: present only in {'python' if k in a else 'js'}"
            d = first_difference(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length python {len(a)} != js {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: python {a!r:.200} != js {b!r:.200}"


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def files(spec) -> dict:
    return demo.load_files(spec, CASE_PATH.parent)


@pytest.mark.parametrize("reviewed", [False, True], ids=["unreviewed", "reviewed"])
def test_js_engine_matches_python_byte_for_byte(spec, files, reviewed: bool) -> None:
    reviews = spec["suggested_reviews"] if reviewed else []
    py = case.run_case(spec, files, reviews=reviews)
    py.pop("telemetry")
    js = run_node({"mode": "case", "case": str(CASE_PATH), "reviews": reviews})
    py_json = canonical_json(py)
    if py_json != js["result"]:
        pytest.fail("result differs: " + str(first_difference(json.loads(py_json),
                                                              json.loads(js["result"]))))
    py_report = report.build_report(py)
    if canonical_json(py_report) != js["report"]:
        pytest.fail("report differs: " + str(first_difference(py_report, json.loads(js["report"]))))
    assert report.render_markdown(py_report) == js["markdown"]


def test_vocabulary_tables_match() -> None:
    js = run_node({"mode": "vocab"})["vocab"]
    for name in ("ENGINE_NAME", "ENGINE_VERSION", "CASE_SCHEMA", "RESULT_SCHEMA", "DISCLAIMER",
                 "BIFOCAL_DISCLAIMER", "CRYPTO_NOTE", "INDICATORS_FOUND", "NO_INDICATORS",
                 "DEMO_LABEL"):
        assert js[name] == getattr(vocab, name), name
    for name in ("EVIDENCE_STATUSES", "CLAIM_VERDICTS", "STATES", "JOB_STATES", "CONFIDENCE",
                 "CATEGORIES", "STATEMENT_KINDS", "PIPELINE"):
        assert tuple(js[name]) == getattr(vocab, name), name


def test_claim_decomposition_matches() -> None:
    from truth_forensics import claims

    samples = [
        demo.CLAIM,
        "Photo B shows Émile Côté outside Café Olé in Montréal at 09:15",
        "The gate opened before the truck left",
        "Audio C was recorded on 2026-03-14 near Dock 9 then EV-K was issued",
        "Screenshot 7 shows the Harbour Office at 7:05:09 on March 3, 2026",
    ]
    js = run_node({"mode": "decompose", "claims": samples})["props"]
    assert json.loads(json.dumps([claims.decompose(c) for c in samples])) == js


def test_js_url_guard_refuses_what_python_refuses() -> None:
    from truth_forensics import intake

    urls = ["http://example.com/a", "https://localhost/admin", "https://127.0.0.1/",
            "https://10.0.0.5/", "https://192.168.1.1/", "https://169.254.169.254/latest/",
            "https://[::1]/", "https://[::ffff:127.0.0.1]/", "https://0x7f000001/",
            "https://2130706433/", "https://0177.0.0.1/", "https://user:pass@example.com/",
            "https://example.com:8443/", "https://metadata.internal/", "https://printer.local/",
            "file:///etc/passwd", "https://exa mple.com/", "",
            "https://www.clearglassinc.com/blog/", "https://example.org:443/x"]
    js = run_node({"mode": "urls", "urls": urls})["urls"]
    assert js == [intake.validate_url(u)[0] for u in urls]


def test_console_never_assigns_untrusted_html() -> None:
    """The console renders evidence metadata, filenames, claims and notes, all
    attacker-controlled. It must build DOM nodes, never parse strings as HTML."""
    if not CONSOLE.exists():
        pytest.skip("console not present")
    src = CONSOLE.read_text(encoding="utf-8")
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                 "new Function"):
        assert sink not in src, f"{CONSOLE.name} uses {sink}"
    assert re.search(r"\.textContent\s*=", src)
