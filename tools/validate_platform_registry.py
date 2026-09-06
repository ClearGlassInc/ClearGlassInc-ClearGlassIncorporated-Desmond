# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validate data/platform/registry.json against the ClearGlass naming standard.

Stdlib-only and fail-closed, matching the sentinel/ agent conventions: any
structural or naming violation returns a nonzero exit code so CI blocks the
change. The registry is the canonical source for platform/product/agent names;
this validator is what keeps it internally consistent as it grows.

Usage:
    python tools/validate_platform_registry.py [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "platform" / "registry.json"

REQUIRED_TOP_LEVEL = (
    "platform",
    "version",
    "status",
    "naming_standard",
    "executive_layer",
    "agent_framework",
    "hierarchy",
    "products",
)

EXPECTED_DOMAINS = (
    "executive_ai",
    "intelligence",
    "cybersecurity",
    "threat_intelligence",
    "osint",
    "digital_forensics",
    "ai_automation",
    "business_intelligence",
    "development",
)


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(registry: dict) -> list[str]:
    """Return a list of violations. Empty list means the registry is valid."""
    errors: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in registry:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors  # structure is broken; downstream checks would mislead

    # ── naming standard ──────────────────────────────────────────────────
    tiers = registry["naming_standard"].get("tiers", [])
    tier_patterns: dict[str, re.Pattern[str]] = {}
    for tier in tiers:
        name = tier.get("tier", "<unnamed>")
        try:
            compiled = re.compile(tier["pattern"])
        except (KeyError, re.error) as exc:
            errors.append(f"tier {name}: invalid pattern ({exc})")
            continue
        tier_patterns[name] = compiled
        example = tier.get("example", "")
        if not compiled.fullmatch(example):
            errors.append(
                f"tier {name}: example {example!r} does not match its own pattern"
            )
        prefix = tier.get("prefix", "")
        if not prefix:
            errors.append(f"tier {name}: missing prefix")
        elif not example.startswith(prefix):
            errors.append(f"tier {name}: example {example!r} does not start with prefix {prefix!r}")

    prefixes = [t.get("prefix") for t in tiers]
    if len(prefixes) != len(set(prefixes)):
        errors.append("tier prefixes are not unique")

    platform_pattern = tier_patterns.get("platform")
    agent_pattern = tier_patterns.get("agent")
    if platform_pattern is None or agent_pattern is None:
        errors.append("naming standard must define 'platform' and 'agent' tiers")
        return errors

    # ── executive layer ──────────────────────────────────────────────────
    executive_names = set()
    for entry in registry["executive_layer"]:
        name = entry.get("name", "")
        executive_names.add(name)
        if not platform_pattern.fullmatch(name):
            errors.append(f"executive layer: {name!r} violates the platform tier pattern")
        if not entry.get("role"):
            errors.append(f"executive layer: {name!r} has no role")
    if len(executive_names) != len(registry["executive_layer"]):
        errors.append("executive layer names are not unique")

    # ── agent framework ──────────────────────────────────────────────────
    framework = registry["agent_framework"]
    for domain in EXPECTED_DOMAINS:
        if domain not in framework:
            errors.append(f"agent framework: missing domain {domain}")
    framework_names: set[str] = set()
    for domain, names in framework.items():
        if len(names) != len(set(names)):
            errors.append(f"agent framework: duplicate names within domain {domain}")
        for name in names:
            if not re.fullmatch(r"[A-Z][A-Za-z0-9]+", name):
                errors.append(f"agent framework: {domain}/{name!r} is not a valid codename")
        framework_names.update(names)

    # ── hierarchy ────────────────────────────────────────────────────────
    hierarchy = registry["hierarchy"]
    if hierarchy.get("root") not in executive_names:
        errors.append(f"hierarchy root {hierarchy.get('root')!r} is not an executive layer platform")
    product_anchors = {p.get("anchor") for p in registry["products"]}
    seen_agent_ids: set[str] = set()
    for node in hierarchy.get("nodes", []):
        name = node.get("name", "")
        agent_id = node.get("agent_id", "")
        if not node.get("role"):
            errors.append(f"hierarchy node {name!r} has no role")
        if not agent_pattern.fullmatch(agent_id):
            errors.append(f"hierarchy node {name!r}: agent_id {agent_id!r} violates the agent tier pattern")
        if agent_id in seen_agent_ids:
            errors.append(f"hierarchy node {name!r}: duplicate agent_id {agent_id!r}")
        seen_agent_ids.add(agent_id)
        expected_id = f"CGA-{name}-01"
        if agent_id != expected_id:
            errors.append(f"hierarchy node {name!r}: agent_id should be {expected_id!r}, got {agent_id!r}")
        resolves = (
            name in framework_names
            or f"ClearGlass {name}" in executive_names
            or name in product_anchors
        )
        if not resolves:
            errors.append(
                f"hierarchy node {name!r} does not resolve to an agent codename, "
                "executive platform, or product anchor"
            )

    # ── products ─────────────────────────────────────────────────────────
    hierarchy_names = {n.get("name") for n in hierarchy.get("nodes", [])}
    product_names = set()
    for product in registry["products"]:
        name = product.get("name", "")
        product_names.add(name)
        if not platform_pattern.fullmatch(name):
            errors.append(f"product {name!r} violates the platform tier pattern")
        anchor = product.get("anchor", "")
        if name != f"ClearGlass {anchor}":
            errors.append(f"product {name!r}: anchor {anchor!r} does not match the product name")
        if anchor not in hierarchy_names:
            errors.append(f"product {name!r}: anchor {anchor!r} has no hierarchy node under Nexus")
        if not product.get("domain"):
            errors.append(f"product {name!r} has no domain")
    if len(product_names) != len(registry["products"]):
        errors.append("product names are not unique")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    try:
        registry = load_registry()
    except (OSError, json.JSONDecodeError) as exc:
        report = {"ok": False, "errors": [f"cannot load registry: {exc}"]}
        print(json.dumps(report) if args.json else report["errors"][0], file=sys.stderr)
        return 1

    errors = validate(registry)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "version": registry.get("version")}, indent=2))
    elif errors:
        for error in errors:
            print(f"VIOLATION: {error}", file=sys.stderr)
    else:
        counts = {domain: len(names) for domain, names in registry["agent_framework"].items()}
        total = sum(counts.values())
        print(
            f"registry OK — v{registry.get('version')}: "
            f"{len(registry['executive_layer'])} platforms, {total} agent codenames, "
            f"{len(registry['hierarchy']['nodes'])} hierarchy nodes, {len(registry['products'])} products"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
