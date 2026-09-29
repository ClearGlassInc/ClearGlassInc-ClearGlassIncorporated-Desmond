"""The homepage signup must not report success for a submission FormSubmit refused.

FormSubmit's AJAX endpoint answers HTTP 200 with a JSON body whose ``success``
field says whether the submission was accepted; a relay that was never
activated answers ``success: "false"`` and an "Activate Form" message. The
handler used to check only the HTTP status, so a visitor was told "Thanks — you
are on the list" while the lead went nowhere. Through 2026-09-29 the owner's
mailbox held no FormSubmit email of any kind, in any folder, since the forms
were pointed at it on 2026-09-06.

This runs the page's own inline script in Node against a stubbed ``fetch``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)

HARNESS = r"""
const [src, response] = [process.argv[1], JSON.parse(process.argv[2])];
let onSubmit;
const status = {textContent: '', style: {}};
const form = {
  email: {value: 'visitor@example.com'},
  reportValidity: () => true,
  querySelector: () => ({disabled: false}),
  addEventListener: (_, fn) => { onSubmit = fn; },
  reset: () => { form.wasReset = true; },
};
globalThis.document = {getElementById: (id) => ({subscribeForm: form, status})[id] || null};
globalThis.window = {setTimeout: () => 0, clearTimeout: () => {}};
globalThis.FormData = class {};
globalThis.fetch = async () => ({ok: true, status: 200, json: async () => response});
new Function(src)();
onSubmit({preventDefault() {}});
setTimeout(() => console.log(JSON.stringify({text: status.textContent, reset: !!form.wasReset})), 20);
"""


def subscribe_script() -> str:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    blocks = [b for b in SCRIPT_RE.findall(html) if "subscribeForm" in b and "formsubmit.co/ajax" in b]
    assert len(blocks) == 1, "expected exactly one inline subscribe handler on index.html"
    return blocks[0]


def run(response: object) -> dict:
    out = subprocess.run(
        ["node", "-e", HARNESS, subscribe_script(), json.dumps(response)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(out.stdout)


pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


@pytest.mark.parametrize("flag", ["true", True])
def test_accepted_submission_confirms_and_resets(flag):
    result = run({"success": flag, "message": "The form was submitted successfully."})
    assert result == {"text": "Thanks — you are on the list.", "reset": True}


@pytest.mark.parametrize(
    "response",
    [
        {"success": "false", "message": "This form needs Activation."},
        {"message": "no success field"},
        None,
    ],
)
def test_refused_submission_offers_the_direct_address(response):
    result = run(response)
    assert "desmondotieno@icloud.com" in result["text"]
    assert "Thanks" not in result["text"]
    assert result["reset"] is False  # the visitor keeps what they typed
