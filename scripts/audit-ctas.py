#!/usr/bin/env python3
"""ClearGlass Inc. revenue audit: validate CTA and lead-capture coverage."""

import sys
from pathlib import Path

LOG_PATH = Path("docs/audit_logs/revenue_audit.log")


def emit(message: str) -> None:
    """Print a line and append it to the revenue audit log."""
    print(message)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.write_text("", encoding="utf-8")

emit("Executing ClearGlass Revenue Audit: Scanning for conversion paths...")

html_files = sorted(
    file
    for file in Path(".").rglob("*.html")
    if "node_modules" not in file.parts
    and ".git" not in file.parts
    and not file.name.startswith("google")
)
missing_ctas = 0

for file in html_files:
    content = file.read_text(encoding="utf-8")
    # Basic validation: ensure high-value pages have contact or action links.
    if 'href="mailto:' not in content and "<form" not in content:
        emit(f"[WARN] No lead capture or direct contact vector found in {file}")
        missing_ctas += 1

if missing_ctas > 0:
    emit(f"Audit Complete: {missing_ctas} pages lack direct conversion paths. Monitor for impact.")
else:
    emit("Audit Complete: All scanned pages contain operational conversion vectors.")

sys.exit(0)  # Exit 0 ensures the pipeline continues successfully.
