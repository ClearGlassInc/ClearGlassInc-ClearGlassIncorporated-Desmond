#!/usr/bin/env python3
"""ClearGlass Inc. marketing audit: validate SEO title and metadata coverage."""

import sys
from pathlib import Path

LOG_PATH = Path("docs/audit_logs/marketing_audit.log")


def emit(message: str) -> None:
    """Print a line and append it to the marketing audit log."""
    print(message)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.write_text("", encoding="utf-8")

emit("Executing ClearGlass SEO Audit: Validating semantic architecture...")

html_files = sorted(
    file
    for file in Path(".").rglob("*.html")
    if "node_modules" not in file.parts
    and ".git" not in file.parts
    and not file.name.startswith("google")
)
critical_failures = 0

for file in html_files:
    content = file.read_text(encoding="utf-8").lower()
    if "<title>" not in content or "</title>" not in content:
        emit(f"[FAIL] Missing <title> tag in {file}")
        critical_failures += 1
    if '<meta name="description"' not in content:
        emit(f"[WARN] Missing meta description in {file}")

if critical_failures > 0:
    emit(f"Audit Failed: {critical_failures} critical SEO violations detected.")
    sys.exit(1)  # Halt the pipeline if structural SEO is missing.

emit("Audit Complete: Semantic architecture and metadata verified.")
sys.exit(0)
