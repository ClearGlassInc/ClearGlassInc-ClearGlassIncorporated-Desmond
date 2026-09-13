#!/usr/bin/env python3
"""ClearGlass assurance-engagement scaffolder and no-fabrication checker.

The AI Agent Attack-Surface and Control Assurance assessment
(``operations/assurance/``) ships empty on purpose: every field in the template
is a bracketed placeholder, and the deliverable is only defensible if none of
those placeholders survives to the client. Convention does not enforce that,
because convention is what fails silently at 11pm the night before delivery.
This tool enforces it mechanically.

Usage::

    python3 tools/assurance_pack.py --new acme-credit-union   # scaffold
    python3 tools/assurance_pack.py --check <path>            # pre-delivery gate
    python3 tools/assurance_pack.py --summary <path>          # evidence quality
    python3 tools/assurance_pack.py --list                    # engagements

``--check`` fails (exit 1) while any bracketed placeholder marker remains, and
prints the line number and marker for each one. ``<path>`` may be a single file
or a directory, in which case every ``*.md`` under it is checked.

Note on ``UNKNOWN``: a bare ``UNKNOWN`` in a Confidence table cell is a
**legitimate confidence value** under the assessment's evidence standard - an
unknown is a finding, not a gap - and must never fail ``--check``. Only the
bracketed markers in ``MARKERS`` fail, so ``[UNKNOWN - NOT YET VALIDATED]``
fails while ``UNKNOWN`` passes. ``--summary`` counts the bare values so the
assessor can see the VERIFIED / REPORTED / UNKNOWN ratio before delivery.

Stdlib only, so it runs in the minimal CI images.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSURANCE_DIR = REPO_ROOT / "operations" / "assurance"
TEMPLATE = ASSURANCE_DIR / "ASSESSMENT_TEMPLATE.md"
INTAKE = ASSURANCE_DIR / "INTAKE.md"
ENGAGEMENTS = ASSURANCE_DIR / "engagements"

# Every bracketed placeholder used anywhere in the assurance pack. A delivered
# document must contain none of them. Matching is on these exact literals rather
# than on a general "[SOMETHING]" pattern so that ordinary bracketed prose and
# markdown links are never flagged.
MARKERS: tuple[str, ...] = (
    "[EVIDENCE REQUIRED]",
    "[UNKNOWN - NOT YET VALIDATED]",
    "[ASSUMPTION - REQUIRES CONFIRMATION]",
    "[EXAMPLE - DELETE BEFORE DELIVERY]",
    "[EXAMPLE - DELETE BEFORE USE]",
    "[PROPOSED - CONFIRM BEFORE SENDING]",
    "[TBD]",
    "[CLIENT]",
    "[DATE]",
    "[ENGAGEMENT ID]",
    "[TIER]",
    "[ASSESSOR]",
    "[SCOPE]",
)

# The only confidence labels the evidence standard permits.
CONFIDENCE_VALUES: tuple[str, ...] = ("VERIFIED", "REPORTED", "UNKNOWN")

# Header rows whose date cell is stamped with today's date at scaffold time.
DATE_STAMP_ROWS: frozenset[str] = frozenset({
    "Engagement start date",
    "Target engagement start",
})

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

FILES_TO_SCAFFOLD: tuple[pathlib.Path, ...] = (TEMPLATE, INTAKE)


class ScaffoldError(RuntimeError):
    """An engagement could not be scaffolded, and nothing was written."""


def find_markers(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, marker)`` for every placeholder marker in ``text``."""
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for marker in MARKERS:
            if marker in line:
                hits.append((number, marker))
    return hits


def table_cells(line: str) -> list[str]:
    """Return the stripped cells of a markdown table row, or ``[]`` if not one."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def count_confidence(text: str) -> dict[str, int]:
    """Count bare confidence values appearing as markdown table cells.

    Only whole-cell matches count, so the rubric table's ``` `VERIFIED` ```
    definitions and any prose mention are excluded, and only values an assessor
    actually recorded in a row are counted.
    """
    counts = dict.fromkeys(CONFIDENCE_VALUES, 0)
    for line in text.splitlines():
        for cell in table_cells(line):
            if cell in counts:
                counts[cell] += 1
    return counts


def row_label(line: str) -> str:
    """Return the first cell of a markdown table row, or ``""`` if not one."""
    cells = table_cells(line)
    return cells[0] if cells else ""


def stamp(text: str, slug: str, engagement_id: str, today: str) -> str:
    """Pre-fill the header placeholders a new engagement already knows."""
    text = text.replace("[CLIENT]", slug).replace("[ENGAGEMENT ID]", engagement_id)
    lines = []
    for line in text.splitlines(keepends=True):
        if row_label(line) in DATE_STAMP_ROWS:
            line = line.replace("[DATE]", today)
        lines.append(line)
    return "".join(lines)


def markdown_files(path: pathlib.Path) -> list[pathlib.Path]:
    """Return the markdown files ``path`` refers to, directly or by containing them."""
    if path.is_dir():
        return sorted(p for p in path.rglob("*.md") if p.is_file())
    return [path]


def new_engagement(slug: str, today: str) -> pathlib.Path:
    """Scaffold ``engagements/<slug>/``. Never overwrites an existing directory."""
    if not SLUG_RE.match(slug):
        raise ScaffoldError(
            f"invalid client slug {slug!r}: use lowercase letters, digits and hyphens"
        )

    destination = ENGAGEMENTS / slug
    if destination.exists():
        raise ScaffoldError(
            f"engagement {slug!r} already exists at "
            f"{_display(destination)}; refusing to overwrite"
        )

    for source in FILES_TO_SCAFFOLD:
        if not source.is_file():
            raise ScaffoldError(f"missing source document: {_display(source)}")

    engagement_id = f"{slug}-{today}"
    destination.mkdir(parents=True)
    for source in FILES_TO_SCAFFOLD:
        body = stamp(source.read_text(encoding="utf-8"), slug, engagement_id, today)
        (destination / source.name).write_text(body, encoding="utf-8")
    return destination


def list_engagements() -> list[pathlib.Path]:
    if not ENGAGEMENTS.is_dir():
        return []
    return sorted(p for p in ENGAGEMENTS.iterdir() if p.is_dir())


def _display(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_new(slug: str) -> int:
    today = dt.date.today().isoformat()
    try:
        destination = new_engagement(slug, today)
    except ScaffoldError as exc:
        print(f"assurance_pack: {exc}", file=sys.stderr)
        return 1
    print(f"scaffolded {_display(destination)}")
    for source in FILES_TO_SCAFFOLD:
        print(f"  {source.name}")
    print("Engagement directories hold client data and are gitignored. Do not commit them.")
    return 0


def run_check(target: pathlib.Path) -> int:
    if not target.exists():
        print(f"assurance_pack: no such path: {_display(target)}", file=sys.stderr)
        return 1

    files = markdown_files(target)
    if not files:
        print(f"assurance_pack: no markdown files under {_display(target)}", file=sys.stderr)
        return 1

    total = 0
    for path in files:
        hits = find_markers(path.read_text(encoding="utf-8"))
        total += len(hits)
        for number, marker in hits:
            print(f"{_display(path)}:{number}: unresolved placeholder {marker}")

    if total:
        noun = "placeholder" if total == 1 else "placeholders"
        print(
            f"\nFAIL: {total} unresolved {noun} across {len(files)} file(s). "
            f"Not deliverable.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: no unresolved placeholders in {len(files)} file(s).")
    return 0


def run_summary(target: pathlib.Path) -> int:
    if not target.exists():
        print(f"assurance_pack: no such path: {_display(target)}", file=sys.stderr)
        return 1

    files = markdown_files(target)
    if not files:
        print(f"assurance_pack: no markdown files under {_display(target)}", file=sys.stderr)
        return 1

    counts = dict.fromkeys(CONFIDENCE_VALUES, 0)
    for path in files:
        for label, count in count_confidence(path.read_text(encoding="utf-8")).items():
            counts[label] += count

    total = sum(counts.values())
    print(f"confidence values in {_display(target)} ({len(files)} file(s)):")
    for label in CONFIDENCE_VALUES:
        share = (counts[label] / total * 100) if total else 0.0
        print(f"  {label:<9} {counts[label]:>5}  {share:5.1f}%")
    print(f"  {'TOTAL':<9} {total:>5}")

    if total == 0:
        print("no confidence-labelled rows found; the assessment is not yet filled in")
    elif counts["UNKNOWN"] == 0:
        print("no UNKNOWN rows: review before delivery, a fully known estate is unusual")
    return 0


def run_list() -> int:
    engagements = list_engagements()
    if not engagements:
        print("no engagements under operations/assurance/engagements/")
        return 0
    print(f"{len(engagements)} engagement(s):")
    for path in engagements:
        print(f"  {path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="assurance_pack.py",
        description="Scaffold and validate ClearGlass assurance engagements.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--new", metavar="CLIENT_SLUG",
                      help="Scaffold a new engagement directory from the templates.")
    mode.add_argument("--check", metavar="PATH",
                      help="Exit 1 if any unresolved placeholder marker remains.")
    mode.add_argument("--summary", metavar="PATH",
                      help="Count VERIFIED / REPORTED / UNKNOWN confidence values.")
    mode.add_argument("--list", action="store_true",
                      help="List existing engagements.")
    args = parser.parse_args(argv)

    if args.new:
        return run_new(args.new)
    if args.check:
        return run_check(pathlib.Path(args.check))
    if args.summary:
        return run_summary(pathlib.Path(args.summary))
    return run_list()


if __name__ == "__main__":
    raise SystemExit(main())
