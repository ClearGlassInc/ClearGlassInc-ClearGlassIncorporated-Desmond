#!/usr/bin/env python3
"""Verify internal links, referenced assets, and exposed secrets before deploy.

Why this exists
---------------
``.github/workflows/pages.yml`` and ``site-integrity-and-deploy.yml`` both run
this script as their first gate, but the repository's opening
``Add files via upload`` commits flattened the tree and dropped it
(``PRODUCTION-RECOVERY.md``). With the script absent, both workflows fail at
step one, which is why Pages has to stay on "Deploy from a branch": switching
the source to "GitHub Actions" would route publishing through a workflow that
cannot get past its first step.

What it checks
--------------
1. **Internal links** - every ``href``/``src`` in a published HTML page
   resolves to a file that exists. External, anchor, ``mailto:``, ``tel:``,
   ``data:`` and ``javascript:`` targets are out of scope.
2. **Referenced assets** - the CSS/JS/image targets of those references are
   checked by the same resolver, so a renamed asset fails the gate.
3. **Exposed secrets** - live credential shapes (Stripe live keys, AWS access
   key ids, GitHub tokens, PEM private key blocks) in anything publishable.

Fail-closed: any finding in a category marked blocking exits non-zero, so a
broken deploy is caught before it publishes rather than after.

The report is always written to ``operations/reports/site-integrity.json``,
including on failure - ``site-integrity-and-deploy.yml`` uploads it with
``if-no-files-found: error``, so a missing report would fail the job on its
own and hide the real finding.

Usage
-----
    python3 scripts/verify_site.py              # full gate
    python3 scripts/verify_site.py --json       # report to stdout too
    python3 scripts/verify_site.py --no-fail    # report only, always exit 0

Stdlib only: it runs in the minimal CI images these workflows use, with no
install step ahead of it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "operations" / "reports" / "site-integrity.json"

# Directories that never ship to Pages. Kept deliberately in step with
# tools/build_pages.py's DENIED_TOP_LEVEL - scanning them would flag fixtures
# and internal docs that are not published and cannot break the site.
SKIP_DIRS = {
    ".git", ".github", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".next", "dist", "build", "venv", ".venv",
    "agent_army", "agents", "bots", "control-plane", "storefront", "admin",
    "deployment", "docs", "operations", "scripts", "sentinel", "tests",
    "tools", "workflows", "clearglass_marketing_os_v2",
}

# Inline <script>/<style> bodies are stripped before attribute extraction.
# Without this, a JavaScript assignment like `src='FRANKFURTER'` (a source
# label in clearglass-nexus.html, not a URL) parses as an HTML src attribute
# and is reported as a missing file.
SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Reference-bearing attributes. srcset/imagesrcset carry comma-separated
# candidate lists and are split before resolution.
ATTR_RE = re.compile(
    r"""\b(?:href|src|poster|data-src)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
SRCSET_RE = re.compile(
    r"""\b(?:srcset|imagesrcset)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Schemes and prefixes that are not local files.
EXTERNAL_PREFIXES = (
    "http://", "https://", "//", "mailto:", "tel:", "data:", "javascript:",
    "sms:", "ftp:", "blob:", "#", "{{", "${",
)

# Live-credential shapes only. Test/publishable keys (pk_test_, pk_live_) are
# public by design and are not flagged - the store ships a publishable key.
SECRET_PATTERNS = (
    ("stripe_secret_key", re.compile(r"\bsk_live_[0-9A-Za-z]{16,}")),
    ("stripe_restricted_key", re.compile(r"\brk_live_[0-9A-Za-z]{16,}")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b gh[pousr]_[0-9A-Za-z]{36,}".replace(" ", ""))),
    ("slack_token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
)

# Extensions worth scanning for credentials: everything that can reach a
# browser or a published artifact.
SECRET_SCAN_SUFFIXES = {
    ".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".xml",
    ".webmanifest", ".yml", ".yaml",
}

MAX_SECRET_BYTES = 4_000_000  # skip oversized generated blobs


def iter_files(suffixes: set[str]) -> list[Path]:
    """Every publishable file under ROOT with one of ``suffixes``."""
    out: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        if path.suffix.lower() in suffixes:
            out.append(path)
    return out


def is_external(target: str) -> bool:
    stripped = target.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    return lowered.startswith(EXTERNAL_PREFIXES)


def resolve(target: str, page: Path) -> Path | None:
    """Map an href/src to a path on disk, or None when it is out of scope."""
    if is_external(target):
        return None
    # Drop query string and fragment: they are not part of the filename.
    parsed = urlparse(target)
    raw = unquote(parsed.path)
    if not raw:
        return None
    if raw.startswith("/"):
        candidate = ROOT / raw.lstrip("/")
    else:
        candidate = page.parent / raw
    try:
        return candidate.resolve()
    except (OSError, RuntimeError):
        return None


def exists(candidate: Path) -> bool:
    """True when the target resolves to a real file or directory index."""
    if candidate.is_file():
        return True
    if candidate.is_dir():
        # A directory link is served by its index.html.
        return (candidate / "index.html").is_file()
    # Extensionless pretty URLs are served by the matching .html file.
    if not candidate.suffix and candidate.with_suffix(".html").is_file():
        return True
    return False


def inside_root(candidate: Path) -> bool:
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return False
    return True


def check_links() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for page in iter_files({".html", ".htm"}):
        try:
            text = page.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # unreadable file is itself a deploy problem
            findings.append(
                {"page": str(page.relative_to(ROOT)), "target": "", "reason": f"unreadable: {exc}"}
            )
            continue

        markup = COMMENT_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", text))

        targets = list(ATTR_RE.findall(markup))
        for srcset in SRCSET_RE.findall(markup):
            for candidate_desc in srcset.split(","):
                url = candidate_desc.strip().split(" ")[0].strip()
                if url:
                    targets.append(url)

        rel_page = str(page.relative_to(ROOT))
        for target in targets:
            resolved = resolve(target, page)
            if resolved is None:
                continue
            if not inside_root(resolved):
                findings.append(
                    {"page": rel_page, "target": target, "reason": "escapes repository root"}
                )
                continue
            if not exists(resolved):
                findings.append(
                    {"page": rel_page, "target": target, "reason": "missing target"}
                )
    return findings


def check_secrets() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in iter_files(SECRET_SCAN_SUFFIXES):
        try:
            if path.stat().st_size > MAX_SECRET_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(ROOT))
        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append({"file": rel, "kind": label, "line": str(line)})
    return findings


def write_report(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the report to stdout")
    parser.add_argument(
        "--no-fail", action="store_true", help="always exit 0 (report-only mode)"
    )
    args = parser.parse_args()

    broken_links = check_links()
    secrets = check_secrets()
    pages_scanned = len(iter_files({".html", ".htm"}))

    report = {
        "pages_scanned": pages_scanned,
        "broken_links": broken_links,
        "exposed_secrets": secrets,
        "counts": {
            "broken_links": len(broken_links),
            "exposed_secrets": len(secrets),
        },
        "ok": not broken_links and not secrets,
    }
    write_report(report)

    print(f"verify_site: scanned {pages_scanned} pages")
    for finding in broken_links:
        # GitHub Actions annotation: surfaces the finding on the file itself.
        print(
            f"::error file={finding['page']}::{finding['reason']}: {finding['target']}"
            if finding["target"]
            else f"::error file={finding['page']}::{finding['reason']}"
        )
    for finding in secrets:
        print(
            f"::error file={finding['file']},line={finding['line']}::"
            f"possible exposed secret ({finding['kind']})"
        )

    print(
        f"verify_site: {len(broken_links)} broken link(s), "
        f"{len(secrets)} possible exposed secret(s)"
    )
    print(f"verify_site: report written to {REPORT_PATH.relative_to(ROOT)}")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))

    if args.no_fail:
        return 0
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
