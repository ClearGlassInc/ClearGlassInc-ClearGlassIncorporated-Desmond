"""Security and evidence-regression tests for the Auto Heal diagnostic path."""
from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTO_HEAL_PATH = ROOT / ".github" / "auto-heal" / "auto_heal.py"
SPEC = importlib.util.spec_from_file_location("clearglass_auto_heal_test", AUTO_HEAL_PATH)
assert SPEC and SPEC.loader
auto_heal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auto_heal)


@pytest.mark.parametrize(
    "secret",
    [
        "ghp_" + "a" * 36,
        "github_pat_" + "b" * 48,
        "sk_" + "live_" + "c" * 32,
        "rk_" + "test_" + "d" * 32,
        "AKIA" + "E" * 16,
        "xoxb-" + "f" * 24,
        "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
    ],
)
def test_redact_sensitive_text_masks_common_token_shapes(secret: str) -> None:
    cleaned = auto_heal.redact_sensitive_text(f"failure: {secret}")
    assert secret not in cleaned
    assert "[REDACTED]" in cleaned


def test_redact_sensitive_text_masks_credentials_and_cookie_headers() -> None:
    password = "pw-" + "v" * 24
    bearer = "bearer-" + "w" * 24
    text = (
        f'password="{password}" Authorization: Bearer {bearer}\n'
        f"Cookie: session={password}; other=value"
    )
    cleaned = auto_heal.redact_sensitive_text(text)
    assert password not in cleaned
    assert bearer not in cleaned
    assert "session=" not in cleaned
    assert cleaned.count("[REDACTED]") >= 2


def test_signature_redacts_before_persistable_diagnostic_is_created() -> None:
    token = "ghs_" + "q" * 36
    result = auto_heal.signature(f"ERROR request failed with token {token}")
    assert token not in result
    assert "[REDACTED]" in result


def test_api_unzips_and_redacts_github_actions_job_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "ghs_" + "r" * 36
    content = f"##[error] Request failed: Authorization: Bearer {token}\n"
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("0_job.txt", content)

    class FakeResponse:
        headers = {"content-type": "application/zip"}

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def read(self) -> bytes:
            return archive_bytes.getvalue()

    monkeypatch.setattr(auto_heal, "TOKEN", "test-token")
    monkeypatch.setattr(auto_heal, "REPOSITORY", "example/repository")
    monkeypatch.setattr(
        auto_heal.urllib.request,
        "urlopen",
        lambda _request, timeout: FakeResponse(),
    )

    result = auto_heal.api("GET", "/repos/example/repository/actions/jobs/123/logs")
    assert "Request failed" in result
    assert token not in result
    assert "[REDACTED]" in result
