"""Regression tests for the repository secret scanner."""
from pathlib import Path

from scripts.secret_scan import scan


def test_scan_reports_unreadable_candidate_file(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / "config.py"
    candidate.write_text("SAFE = True", encoding="utf-8")
    original_read_text = Path.read_text

    def unreadable(self: Path, *args, **kwargs) -> str:
        if self == candidate:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    findings = scan(tmp_path)

    assert findings == [f"{candidate}: unreadable file"]


def test_scan_reports_credential_pattern_without_exposing_value(tmp_path: Path) -> None:
    candidate = tmp_path / "config.py"
    candidate.write_text('TOKEN = "sk_live_' + "A" * 24 + '"', encoding="utf-8")

    findings = scan(tmp_path)

    assert len(findings) == 1
    assert "Stripe live secret key" in findings[0]
    assert "sk_live_" not in findings[0]
