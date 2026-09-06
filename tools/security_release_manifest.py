#!/usr/bin/env python3
"""Create or verify deterministic SHA-256 provenance for public policy artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "provenance" / "release-manifest.json"
IMPORTANT_FILES = (
    ".github/workflows/pages.yml",
    ".github/workflows/security.yml",
    ".well-known/security.txt",
    "LICENSE",
    "NOTICE",
    "SECURITY.md",
    "_headers",
    "asset-protection.js",
    "legal/WEBSITE_POLICY_TEMPLATES.md",
    "legal/privacy.html",
    "legal/terms.html",
    "security/HARDENING_AND_THREAT_MODEL.md",
    "tools/build_pages.py",
    "tools/security_release_manifest.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict[str, object]:
    artifacts = []
    for relative in IMPORTANT_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required provenance artifact missing: {relative}")
        artifacts.append({"path": relative, "sha256": digest(path)})
    return {
        "schema": "https://www.clearglassinc.com/provenance/manifest-v1.schema.json",
        "organization": "ClearGlassInc Artemis",
        "algorithm": "SHA-256",
        "artifacts": artifacts,
    }


def serialize(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed manifest is stale")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    expected = serialize(build_manifest())
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != expected:
            print(f"stale provenance manifest: {args.output}")
            return 1
        print(f"verified {len(IMPORTANT_FILES)} SHA-256 artifact hashes")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(expected, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
