from pathlib import Path

SCRIPT = Path("ThreadsGrowthCommandCenter.ps1")


def test_threads_script_is_manual_and_ethical():
    text = SCRIPT.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "manual-only" in lowered
    assert "does not log in" in lowered
    assert "scrape" in lowered
    assert "fake engagement" in lowered
    assert "mass dms" in lowered or "mass-message" in lowered


def test_threads_script_creates_required_command_center_assets():
    text = SCRIPT.read_text(encoding="utf-8")
    for folder in ["Drafts", "Calendars", "Analytics", "Engagement", "DailyPlans", "Reports"]:
        assert folder in text
    for filename in [
        "ContentCalendar.csv",
        "ThreadsKPITracker.csv",
        "EngagementTracker.csv",
        "ThreadsGrowthDashboard.html",
    ]:
        assert filename in text
    assert "THREADS-DRAFT-{0:D2}.txt" in text
    assert "$i -le 10" in text


def test_threads_script_is_parameterized_and_idempotent():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "[string]$BrandName" in text
    assert "[string]$Niche" in text
    assert "[string]$RootPath" in text
    assert "Write-FileIfMissing" in text
    assert "Test-Path -LiteralPath $Path" in text
