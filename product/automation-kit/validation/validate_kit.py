"""Static validation for the internal automation kit."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

NOTICE = (
    "Outputs are estimates based on user-entered assumptions. They are planning aids "
    "only and do not guarantee savings, financial results, return on investment, "
    "operational performance, or business outcomes."
)

REQUIRED_ASSET_FIELDS = {
    "asset_id",
    "path",
    "title",
    "origin",
    "author",
    "license_status",
    "source_location",
    "version",
    "review_status",
    "release_status",
}

FORBIDDEN_PATTERNS = (
    re.compile(r"\bguarantees?\s+(?:savings|revenue|roi|return|security|compliance)", re.I),
    re.compile(r"\bguaranteed\s+(?:savings|revenue|roi|return|security|compliance)", re.I),
    re.compile(r"\bcertif(?:y|ied|ication)\b", re.I),
    re.compile(r"\bformal\s+(?:compliance|security)\s+(?:assessment|assurance)\b", re.I),
)


def validate_asset_register(path: str) -> list[str]:
    register_path = Path(path)
    findings: list[str] = []
    try:
        data: dict[str, Any] = json.loads(register_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"asset register unreadable: {exc}"]

    assets = data.get("assets")
    if not isinstance(assets, list):
        return ["asset register must contain an assets list"]

    root = register_path.parent
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            findings.append(f"asset {index} is not an object")
            continue
        missing = sorted(REQUIRED_ASSET_FIELDS - asset.keys())
        for field in missing:
            findings.append(f"asset {index} missing {field}")
        relative_path = asset.get("path")
        if isinstance(relative_path, str) and not (root / relative_path).exists():
            # Paths in the register may be repository-relative, so also check two levels up.
            repository_root = root.parent.parent
            if not (repository_root / relative_path).exists():
                findings.append(f"asset {asset.get('asset_id', index)} path missing: {relative_path}")
        if asset.get("release_status") not in {"INTERNAL_ONLY", "NOT_RELEASE_APPROVED"}:
            findings.append(f"asset {asset.get('asset_id', index)} has unsafe release status")
    return findings


def _markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def validate_text_policy(root: str) -> list[str]:
    findings: list[str] = []
    for path in _markdown_files(Path(root)):
        text = path.read_text(errors="replace")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                findings.append(f"policy review required: {path}: {pattern.pattern}")
    return findings


def validate_required_notice(root: str) -> list[str]:
    findings: list[str] = []
    root_path = Path(root)
    combined = "\n".join(path.read_text(errors="replace") for path in _markdown_files(root_path))
    if NOTICE not in combined:
        findings.append("mandatory calculator estimate notice is missing")
    return findings


def run_validation(root: str) -> dict[str, object]:
    root_path = Path(root)
    register = root_path / "asset-register.json"
    findings = []
    findings.extend(validate_asset_register(str(register)))
    findings.extend(validate_text_policy(str(root_path)))
    findings.extend(validate_required_notice(str(root_path)))
    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "root": str(root_path),
    }


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parents[1]
    result = run_validation(str(package_root))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
