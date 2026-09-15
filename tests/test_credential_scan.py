# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The credential scan gates merges and halts automation, so it must actually catch things.

Covers ``scripts/secret_scan.py``. Extracting that out of the Security
workflow's heredoc made it testable for the first time. What is asserted here is
both halves of the contract: it finds real credential shapes, and it does not cry
wolf on the placeholders this repository legitimately contains — a gate that
fires on every run gets switched off.

Named ``test_credential_scan`` rather than ``test_secret_scan`` because
``.gitignore`` excludes ``*_secret*``, which would have silently left this file
untracked — a test that is not in the repository is not a test.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.secret_scan import PATTERNS, main, scan


# Credential-shaped fixtures are assembled at runtime rather than written out
# literally. A test file containing a real-looking AKIA key would be found by the
# very scan it is testing, and `scripts/secret_scan.py` runs over this whole
# repository in CI — so a literal fixture here would turn the Security workflow
# permanently red and invite someone to add an exemption to make it stop.
AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
PRIVATE_KEY_HEADER = "-----BEGIN RSA " + "PRIVATE KEY-----"
GENERIC_API_KEY = "api_key = '" + "a" * 30 + "'"
AWS_LEAK = f"AWS_KEY = '{AWS_KEY}'"


def tree(root: Path, **files: str) -> Path:
    for name, content in files.items():
        path = root / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_a_clean_tree_reports_nothing(tmp_path: Path) -> None:
    tree(tmp_path, **{"app.py": "print('hello')", "config.yml": "log_level: info"})
    assert scan(tmp_path) == []


@pytest.mark.parametrize(
    "content",
    [
        AWS_LEAK,
        "token = 'ghp_" + "a" * 36 + "'",
        "token = 'ghs_" + "b" * 36 + "'",
        "gitlab = 'glpat-" + "c" * 20 + "'",
        GENERIC_API_KEY,
        PRIVATE_KEY_HEADER,
        "STRIPE = 'sk_live_" + "d" * 24 + "'",
        "STRIPE = 'rk_live_" + "e" * 24 + "'",
    ],
)
def test_credential_shapes_are_caught(tmp_path: Path, content: str) -> None:
    tree(tmp_path, **{"leaked.py": content})
    findings = scan(tmp_path)
    assert findings, f"nothing flagged for: {content[:40]}"


def test_a_stripe_test_key_is_not_a_finding(tmp_path: Path) -> None:
    """Test keys are documented all over this repository and are harmless."""
    tree(tmp_path, **{"docs.py": "STRIPE_SECRET_KEY = 'sk_test_" + "f" * 24 + "'"})
    assert scan(tmp_path) == []


def test_vendored_and_generated_trees_are_skipped(tmp_path: Path) -> None:
    """Otherwise every run drowns in findings from code that is not ours to fix."""
    leak = AWS_LEAK
    tree(
        tmp_path,
        **{
            "node_modules__pkg__index.js": leak,
            "dist__bundle.js": leak,
            "build__out.js": leak,
            ".venv__lib__thing.py": leak,
        },
    )
    assert scan(tmp_path) == []


def test_binary_and_unlisted_file_types_are_not_read(tmp_path: Path) -> None:
    tree(tmp_path, **{"image.png": AWS_KEY, "notes.txt": AWS_KEY})
    assert scan(tmp_path) == []


def test_the_finding_names_the_file_and_what_was_found(tmp_path: Path) -> None:
    tree(tmp_path, **{"src__leak.py": AWS_LEAK})
    finding = scan(tmp_path)[0]
    assert "leak.py" in finding
    assert "AWS access key" in finding


def test_every_pattern_is_a_valid_regex() -> None:
    """A pattern that fails to compile would take the whole gate down with it."""
    import re

    for label, pattern in PATTERNS.items():
        re.compile(pattern)  # raises on a bad pattern, naming it via the loop
        assert label.strip(), "every pattern needs a human-readable label"


def test_findings_exit_non_zero(tmp_path: Path, capsys) -> None:
    """Workflows read the exit code; a finding that exits 0 is a gate that passed."""
    tree(tmp_path, **{"leak.py": AWS_LEAK})
    assert main(["--root", str(tmp_path)]) == 1
    assert "::error::" in capsys.readouterr().out


def test_a_clean_tree_exits_zero(tmp_path: Path) -> None:
    tree(tmp_path, **{"app.py": "print('hello')"})
    assert main(["--root", str(tmp_path)]) == 0


def test_a_missing_root_exits_non_zero(tmp_path: Path) -> None:
    """An unscannable tree is not a clean tree."""
    assert main(["--root", str(tmp_path / "nope")]) == 1


def test_the_repository_itself_is_clean() -> None:
    """The gate as CI runs it. A failure here is a real finding, not a test bug."""
    root = Path(__file__).resolve().parents[1]
    assert scan(root) == []
