# ARTEMIS // CLEARGLASS INC.
#
# Copyright (c) 2026 ClearGlass Inc. All rights reserved.
# Original Author and Systems Architect: Desmond Otieno Odhiambo.
#
# This source code is proprietary and confidential to ClearGlass Inc.
# Unauthorized copying, modification, distribution, publication, sublicensing,
# reverse engineering, commercial use, or removal of attribution is prohibited
# except where expressly authorized in writing by ClearGlass Inc.
#
# System: ARTEMIS | Organization: ClearGlass Inc. | Classification: Proprietary
"""ARTEMIS provenance bot.

Generates a machine-readable provenance manifest for ARTEMIS artifacts:
SHA-256 checksum, byte size, and last-commit reference for each tracked
artifact, plus the repository HEAD commit at generation time. Every value is
derived from the actual working tree and git history — nothing is fabricated.
If git metadata is unavailable the commit fields are recorded as ``null``
rather than invented.

Output: ``operations/artemis/provenance_manifest.json``
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "artemis"

ARTIFACT_GLOBS = [
    "agents/artemis_command_system/*",
    "agents/artemis_ip_guardian/*",
    "bots/artemis_ip_guardian_bot.py",
    "bots/artemis_provenance_bot.py",
    ".github/workflows/artemis-deploy.yml",
    "prompts/general_assistant_system_prompt.md",
    "NOTICE",
    "TRADEMARKS.md",
    "docs/PROVENANCE.md",
    "docs/IP-POLICY.md",
]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict:
    entries = []
    for pattern in ARTIFACT_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(ROOT))
            entries.append(
                {
                    "artifact": rel,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                    "last_commit": _git("log", "-1", "--format=%H", "--", rel),
                    "last_commit_date": _git("log", "-1", "--format=%cI", "--", rel),
                }
            )
    return {
        "system": "ARTEMIS",
        "organization": "ClearGlass Inc.",
        "original_author": "Desmond Otieno Odhiambo",
        "classification": "CONFIDENTIAL",
        "bot": "artemis_provenance_bot",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository_head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "artifact_count": len(entries),
        "artifacts": entries,
    }


def main() -> int:
    manifest = build_manifest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "provenance_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"ARTEMIS provenance: {manifest['artifact_count']} artifacts recorded "
        f"at {manifest['generated_utc']} → {out_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
