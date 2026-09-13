# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for tools/assurance_pack.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("assurance_pack", ROOT / "tools/assurance_pack.py")
assert SPEC and SPEC.loader
assurance_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assurance_pack)


CLEAN_ASSESSMENT = """# Assessment

| Field | Value |
|---|---|
| Client | Placeholder Org |
| Engagement ID | placeholder-org-2026-01-01 |

| ID | Agent Name | Confidence | Evidence Ref |
|---|---|---|---|
| A-001 | Deploy bot | VERIFIED | EV-001 |
| A-002 | Ticket triage | REPORTED | EV-002 |
| A-003 | Inbox summariser | UNKNOWN | EV-003 |
| A-004 | Report writer | VERIFIED | EV-004 |

An UNKNOWN is a finding, not a gap in the report.
"""


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


class TestFindMarkers:
    def test_clean_text_has_no_markers(self) -> None:
        assert assurance_pack.find_markers(CLEAN_ASSESSMENT) == []

    def test_marker_is_reported_with_line_number(self) -> None:
        body = "line one\n| Client | [CLIENT] |\n"
        assert assurance_pack.find_markers(body) == [(2, "[CLIENT]")]

    def test_every_declared_marker_is_detected(self) -> None:
        for marker in assurance_pack.MARKERS:
            assert assurance_pack.find_markers(f"value: {marker}\n") == [(1, marker)]

    def test_bare_unknown_is_not_a_marker(self) -> None:
        assert assurance_pack.find_markers("| A-001 | UNKNOWN | EV-001 |\n") == []


class TestCheck:
    def test_check_fails_on_a_file_containing_a_marker(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "report.md", "| Owner | [EVIDENCE REQUIRED] |\n")
        assert assurance_pack.main(["--check", str(path)]) == 1

    def test_check_passes_on_a_clean_file(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "report.md", CLEAN_ASSESSMENT)
        assert assurance_pack.main(["--check", str(path)]) == 0

    def test_check_does_not_fail_on_a_bare_unknown_confidence_value(
        self, tmp_path: Path
    ) -> None:
        body = (
            "| Agent ID | Confidence | Evidence Ref |\n"
            "|---|---|---|\n"
            "| A-001 | UNKNOWN | EV-001 |\n"
            "| A-002 | UNKNOWN | EV-002 |\n"
        )
        path = _write(tmp_path / "report.md", body)
        assert assurance_pack.main(["--check", str(path)]) == 0

    def test_check_reports_line_numbers_and_markers(self, tmp_path: Path, capsys) -> None:
        body = "ok\n| Client | [CLIENT] |\nok\n| Owner | [TBD] |\n"
        path = _write(tmp_path / "report.md", body)
        assert assurance_pack.main(["--check", str(path)]) == 1
        out = capsys.readouterr().out
        assert "report.md:2: unresolved placeholder [CLIENT]" in out
        assert "report.md:4: unresolved placeholder [TBD]" in out

    def test_check_walks_a_directory(self, tmp_path: Path) -> None:
        _write(tmp_path / "clean.md", CLEAN_ASSESSMENT)
        _write(tmp_path / "dirty.md", "| Owner | [TBD] |\n")
        assert assurance_pack.main(["--check", str(tmp_path)]) == 1

    def test_check_fails_on_a_missing_path(self, tmp_path: Path) -> None:
        assert assurance_pack.main(["--check", str(tmp_path / "nope.md")]) == 1

    def test_shipped_template_still_carries_its_placeholders(self) -> None:
        # The template ships empty by design; if it ever passes --check, someone
        # has filled it in in the repository.
        assert assurance_pack.main(["--check", str(assurance_pack.TEMPLATE)]) == 1


class TestCountConfidence:
    def test_counts_each_label(self) -> None:
        counts = assurance_pack.count_confidence(CLEAN_ASSESSMENT)
        assert counts == {"VERIFIED": 2, "REPORTED": 1, "UNKNOWN": 1}

    def test_prose_mentions_are_not_counted(self) -> None:
        body = "An UNKNOWN is a finding. VERIFIED means observed.\n"
        assert assurance_pack.count_confidence(body) == {
            "VERIFIED": 0, "REPORTED": 0, "UNKNOWN": 0,
        }

    def test_backticked_rubric_cells_are_not_counted(self) -> None:
        body = "| `VERIFIED` | Observed directly by the assessor. |\n"
        assert assurance_pack.count_confidence(body)["VERIFIED"] == 0

    def test_summary_prints_counts_and_exits_zero(self, tmp_path: Path, capsys) -> None:
        path = _write(tmp_path / "report.md", CLEAN_ASSESSMENT)
        assert assurance_pack.main(["--summary", str(path)]) == 0
        out = capsys.readouterr().out
        assert "VERIFIED      2" in out
        assert "REPORTED      1" in out
        assert "UNKNOWN       1" in out
        assert "TOTAL         4" in out

    def test_summary_flags_an_assessment_with_no_unknowns(
        self, tmp_path: Path, capsys
    ) -> None:
        body = "| A-001 | VERIFIED | EV-001 |\n"
        path = _write(tmp_path / "report.md", body)
        assert assurance_pack.main(["--summary", str(path)]) == 0
        assert "no UNKNOWN rows" in capsys.readouterr().out


class TestTableCells:
    def test_non_table_lines_yield_no_cells(self) -> None:
        assert assurance_pack.table_cells("just prose") == []

    def test_row_label_is_the_first_cell(self) -> None:
        assert assurance_pack.row_label("| Engagement start date | [DATE] |") == (
            "Engagement start date"
        )


class TestStamp:
    def test_client_and_engagement_id_are_filled(self) -> None:
        body = "| Client | [CLIENT] |\n| Engagement ID | [ENGAGEMENT ID] |\n"
        stamped = assurance_pack.stamp(body, "acme-co", "acme-co-2026-01-02", "2026-01-02")
        assert "| Client | acme-co |" in stamped
        assert "| Engagement ID | acme-co-2026-01-02 |" in stamped

    def test_only_the_named_date_rows_are_stamped(self) -> None:
        body = (
            "| Engagement start date | [DATE] |\n"
            "| Report issued | [DATE] |\n"
        )
        stamped = assurance_pack.stamp(body, "acme-co", "acme-co-2026-01-02", "2026-01-02")
        assert "| Engagement start date | 2026-01-02 |" in stamped
        assert "| Report issued | [DATE] |" in stamped


class TestNewEngagement:
    def test_scaffolds_both_documents(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        destination = assurance_pack.new_engagement("acme-co", "2026-01-02")
        assert (destination / "ASSESSMENT_TEMPLATE.md").is_file()
        assert (destination / "INTAKE.md").is_file()
        assessment = (destination / "ASSESSMENT_TEMPLATE.md").read_text(encoding="utf-8")
        assert "| Client | acme-co |" in assessment
        assert "| Engagement ID | acme-co-2026-01-02 |" in assessment
        assert "[CLIENT]" not in assessment

    def test_refuses_to_overwrite_an_existing_engagement(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        assurance_pack.new_engagement("acme-co", "2026-01-02")
        try:
            assurance_pack.new_engagement("acme-co", "2026-01-03")
        except assurance_pack.ScaffoldError as exc:
            assert "refusing to overwrite" in str(exc)
        else:
            raise AssertionError("a second scaffold of the same slug must raise")

    def test_cli_returns_non_zero_on_overwrite(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        assert assurance_pack.main(["--new", "acme-co"]) == 0
        assert assurance_pack.main(["--new", "acme-co"]) == 1

    def test_rejects_a_slug_that_could_escape_the_directory(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        for slug in ("../escape", "Acme Co", "/absolute"):
            assert assurance_pack.main(["--new", slug]) == 1
        assert not (tmp_path / "engagements").exists()


class TestList:
    def test_lists_nothing_when_there_are_no_engagements(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        assert assurance_pack.main(["--list"]) == 0
        assert "no engagements" in capsys.readouterr().out

    def test_lists_scaffolded_engagements(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(assurance_pack, "ENGAGEMENTS", tmp_path / "engagements")
        assurance_pack.new_engagement("acme-co", "2026-01-02")
        assurance_pack.new_engagement("beta-corp", "2026-01-02")
        assert assurance_pack.main(["--list"]) == 0
        out = capsys.readouterr().out
        assert "acme-co" in out
        assert "beta-corp" in out


class TestShippedPack:
    def test_engagements_directory_is_gitignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "operations/assurance/engagements/*/" in ignore

    def test_pack_documents_exist(self) -> None:
        directory = ROOT / "operations/assurance"
        for name in ("OFFER.md", "OUTREACH.md", "INTAKE.md",
                     "ASSESSMENT_TEMPLATE.md", "README.md"):
            assert (directory / name).is_file(), name
