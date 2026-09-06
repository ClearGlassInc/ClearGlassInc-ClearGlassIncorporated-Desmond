import re

from tools.build_pages import build


SECRET_PATTERNS = {
    "Stripe secret/restricted key": re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[psoru]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
}

TEXT_SUFFIXES = {".html", ".js", ".json", ".txt", ".xml", ".svg", ".css", ".webmanifest"}


def test_public_artifact_contains_no_secret_material(tmp_path) -> None:
    """Fail closed if credential-like material is about to reach GitHub Pages."""
    destination = tmp_path / "dist"
    build(destination)

    findings: list[str] = []
    for path in destination.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(destination)}: {label}")

    assert findings == [], "public credential exposure detected: " + "; ".join(findings)
