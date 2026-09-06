from marketing.content_engine.strategic_viral_engine import (
    Concept,
    asset_pack,
    dashboard,
)


def test_asset_pack_contains_required_weekly_formats() -> None:
    pack = asset_pack(
        Concept(
            1,
            "The AI Lie Nobody Tells You",
            "ai_risk",
            "95% of AI pilots fail when nobody can audit the decision trail.",
        )
    )

    assert pack["seo_blog_outline"]["target_keyword"] == "auditable AI systems"
    assert "utm_source=linkedin" in pack["conversion_urls"]["linkedin"]
    assert len(pack["x_thread"]) == 15
    assert len(pack["linkedin_carousel"]) == 5
    assert len(pack["video_script_60s"]) == 6
    assert "Last week at ClearGlassInc" in pack["linkedin_post"]


def test_dashboard_counts_five_primary_formats_per_concept() -> None:
    packs = [{"concept": {"id": i}} for i in range(7)]
    report = dashboard(packs)

    assert report["weekly_pack"]["concept_count"] == 7
    assert report["weekly_pack"]["asset_count"] == 35
    assert "form_submit" in report["events_to_track"]
