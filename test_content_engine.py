# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
from datetime import datetime, timezone


from bots.content_engine import (
    CONTENT,
    PILLARS,
    PLATFORM_LIMITS,
    URLS,
    build_bundle,
    choose_pillar,
    choose_variant,
    render_summary_markdown,
    write_outputs,
    _resolve_urls,
)


# ── Pillar selection ──────────────────────────────────────────────────────────

def test_choose_pillar_rotates_through_all():
    seen = set()
    for day in range(1, len(PILLARS) * 3 + 1):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc).replace(
            tzinfo=timezone.utc
        )
        # Simulate day-of-year offset
        now = datetime(2026, 1, day % 365 + 1, tzinfo=timezone.utc)
        seen.add(choose_pillar(now))
    assert seen == set(PILLARS)


def test_choose_pillar_force_override(monkeypatch):
    monkeypatch.setenv("FORCE_PILLAR", "artemis")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert choose_pillar(now) == "artemis"


def test_choose_pillar_ignores_invalid_override(monkeypatch):
    monkeypatch.setenv("FORCE_PILLAR", "nonexistent")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Falls back to day-based selection, must return a valid pillar
    assert choose_pillar(now) in PILLARS


# ── Variant selection ─────────────────────────────────────────────────────────

def test_choose_variant_cycles():
    from datetime import timedelta
    variants = ["a", "b"]
    weeks_seen = set()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for week in range(52):
        now = base + timedelta(weeks=week)
        v, idx = choose_variant(variants, now)
        weeks_seen.add(v)
    assert "a" in weeks_seen and "b" in weeks_seen


def test_choose_variant_index_in_bounds():
    for pillar in PILLARS:
        for platform, variants in CONTENT[pillar].items():
            now = datetime(2026, 5, 8, tzinfo=timezone.utc)
            _, idx = choose_variant(variants, now)
            assert 0 <= idx < len(variants)


# ── URL resolution ────────────────────────────────────────────────────────────

def test_resolve_urls_substitutes_all_keys():
    text = "Home: {home}  Artemis: {artemis}  Guardian: {guardian}"
    resolved = _resolve_urls(text)
    for key, url in URLS.items():
        assert url in resolved or "{" + key + "}" not in resolved


def test_resolve_urls_no_leftover_placeholders():
    # Build a string with all known keys
    all_keys = " ".join("{" + k + "}" for k in URLS)
    resolved = _resolve_urls(all_keys)
    assert "{" not in resolved and "}" not in resolved


# ── Bundle construction ───────────────────────────────────────────────────────

def test_build_bundle_returns_all_platforms(monkeypatch):
    monkeypatch.delenv("FORCE_PILLAR", raising=False)
    bundle = build_bundle()
    platform_names = {pc.platform for pc in bundle.platforms}
    assert platform_names == {"linkedin", "threads", "x", "email", "website"}


def test_build_bundle_pillar_valid(monkeypatch):
    monkeypatch.delenv("FORCE_PILLAR", raising=False)
    bundle = build_bundle()
    assert bundle.pillar in PILLARS


def test_build_bundle_content_hash_stable_same_inputs(monkeypatch):
    monkeypatch.setenv("FORCE_PILLAR", "brand")
    now = datetime(2026, 5, 8, tzinfo=timezone.utc)
    b1 = build_bundle(now)
    b2 = build_bundle(now)
    assert b1.content_hash == b2.content_hash


def test_build_bundle_char_counts_positive():
    bundle = build_bundle()
    for pc in bundle.platforms:
        assert pc.char_count > 0, f"Zero char count on {pc.platform}"


def test_build_bundle_each_pillar_via_force(monkeypatch):
    for pillar in PILLARS:
        monkeypatch.setenv("FORCE_PILLAR", pillar)
        bundle = build_bundle()
        assert bundle.pillar == pillar


# ── Markdown rendering ────────────────────────────────────────────────────────

def test_render_summary_markdown_contains_pillar():
    bundle = build_bundle()
    md = render_summary_markdown(bundle)
    assert bundle.pillar in md


def test_render_summary_markdown_contains_all_platform_headers():
    bundle = build_bundle()
    md = render_summary_markdown(bundle)
    for pc in bundle.platforms:
        assert pc.platform.title() in md


# ── File output ───────────────────────────────────────────────────────────────

def test_write_outputs_creates_expected_files(monkeypatch, tmp_path):
    # Redirect output to a temp directory
    monkeypatch.setattr("bots.content_engine.OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr("bots.content_engine.PLATFORMS_DIR", tmp_path / "output" / "platforms")
    monkeypatch.setattr("bots.content_engine.ARCHIVE_DIR", tmp_path / "output" / "archive")
    monkeypatch.setattr("bots.content_engine.METRICS_DIR", tmp_path / "output" / "metrics")

    bundle = build_bundle()
    write_outputs(bundle)

    output = tmp_path / "output"
    assert (output / "latest.md").exists()
    assert (output / "latest.json").exists()

    for pc in bundle.platforms:
        assert (output / "platforms" / pc.platform / "latest.md").exists()

    archive_files = list((output / "archive").glob("*.json"))
    assert len(archive_files) == 1

    metrics_files = list((output / "metrics").glob("runs.json"))
    assert len(metrics_files) == 1


def test_write_outputs_metrics_json_appends(monkeypatch, tmp_path):
    monkeypatch.setattr("bots.content_engine.OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr("bots.content_engine.PLATFORMS_DIR", tmp_path / "output" / "platforms")
    monkeypatch.setattr("bots.content_engine.ARCHIVE_DIR", tmp_path / "output" / "archive")
    monkeypatch.setattr("bots.content_engine.METRICS_DIR", tmp_path / "output" / "metrics")

    for pillar in ["brand", "artemis"]:
        monkeypatch.setenv("FORCE_PILLAR", pillar)
        bundle = build_bundle()
        write_outputs(bundle)

    runs = json.loads((tmp_path / "output" / "metrics" / "runs.json").read_text())
    assert len(runs) == 2
    assert {r["pillar"] for r in runs} == {"brand", "artemis"}


# ── Content quality ───────────────────────────────────────────────────────────

def test_all_external_content_has_site_url():
    """Every external-facing piece of content must contain the ClearGlass URL.
    Website copy is exempt — it IS the site and CMS snippets don't self-link."""
    EXEMPT = {"website"}
    for pillar, platforms in CONTENT.items():
        for platform, variants in platforms.items():
            if platform in EXEMPT:
                continue
            for variant in variants:
                if platform == "threads":
                    text = " ".join(variant.get("posts", []))
                elif platform == "x":
                    text = variant.get("text", "")
                elif platform == "email":
                    text = variant.get("body", "")
                else:
                    text = variant.get("body", "")

                resolved = _resolve_urls(text)
                assert "www.clearglassinc.com" in resolved, (
                    f"Missing URL in {pillar}/{platform} variant"
                )


def test_linkedin_content_meets_minimum_length():
    for pillar in PILLARS:
        for variant in CONTENT[pillar]["linkedin"]:
            body = _resolve_urls(variant.get("headline", "") + " " + variant.get("body", ""))
            assert len(body) >= PLATFORM_LIMITS["linkedin"]["min"], (
                f"LinkedIn body too short for pillar={pillar}: {len(body)} chars"
            )
