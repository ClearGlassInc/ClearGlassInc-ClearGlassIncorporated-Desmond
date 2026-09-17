import json
from pathlib import Path

from product.automation_kit.validation.validate_kit import (
    validate_asset_register,
    validate_required_notice,
    validate_text_policy,
)


def test_valid_package_has_no_policy_findings(tmp_path: Path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "asset-register.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "assets": [
                    {
                        "asset_id": "a1",
                        "path": "content/example.md",
                        "title": "Example",
                        "origin": "ClearGlass internal original",
                        "author": "ClearGlass internal development",
                        "license_status": "Owner-authorship declared; legal review not asserted",
                        "source_location": "content/example.md",
                        "version": "0.1.0",
                        "review_status": "INTERNAL_REVIEW_REQUIRED",
                        "release_status": "INTERNAL_ONLY",
                    }
                ],
            }
        )
    )
    (package / "content").mkdir()
    (package / "content/example.md").write_text(
        "Planning example.\n\n"
        "Outputs are estimates based on user-entered assumptions. They are planning aids "
        "only and do not guarantee savings, financial results, return on investment, "
        "operational performance, or business outcomes."
    )

    assert validate_asset_register(str(package / "asset-register.json")) == []
    assert validate_text_policy(str(package)) == []
    assert validate_required_notice(str(package)) == []


def test_missing_asset_field_is_reported(tmp_path: Path):
    register = tmp_path / "asset-register.json"
    register.write_text(json.dumps({"schema_version": "1.0", "assets": [{"asset_id": "a1"}]}))

    findings = validate_asset_register(str(register))

    assert any("path" in finding for finding in findings)


def test_forbidden_guarantee_language_is_reported(tmp_path: Path):
    (tmp_path / "bad.md").write_text("This guarantees savings.")

    findings = validate_text_policy(str(tmp_path))

    assert findings


def test_missing_notice_is_reported(tmp_path: Path):
    (tmp_path / "example.md").write_text("Planning aid only.")

    findings = validate_required_notice(str(tmp_path))

    assert findings
