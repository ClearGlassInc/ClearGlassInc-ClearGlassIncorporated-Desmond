"""Shared policy for HTML pages intentionally excluded from deployable-page automation.

These paths are source-controlled design prototypes: noindex/nofollow, offline-only
surfaces that intentionally do not carry the site's deployable shared layers.
Keep this inventory small and explicit so a new HTML page remains covered by the
normal site-wide gates until an owner deliberately classifies it here.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

NON_DEPLOYABLE_HTML_PAGES: frozenset[str] = frozenset(
    {
        "clearglass-legal-assistance/prototype/index.html",
        "clearglass-legal-assistance/prototype/security-prototype.html",
    }
)


def is_non_deployable_html(path: Path, root: Path = REPO_ROOT) -> bool:
    return path.relative_to(root).as_posix() in NON_DEPLOYABLE_HTML_PAGES
