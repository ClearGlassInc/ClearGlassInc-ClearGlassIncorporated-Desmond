from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("indexnow_submit", ROOT / "tools/indexnow_submit.py")
indexnow = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(indexnow)


def test_accepts_canonical_production_url() -> None:
    assert indexnow.canonical_url("https://www.clearglassinc.com/blog/").endswith("/blog/")


@pytest.mark.parametrize("url", [
    "http://www.clearglassinc.com/", "https://evil.example/", "https://user@www.clearglassinc.com/",
    "https://www.clearglassinc.com:8443/", "https://www.clearglassinc.com/#fragment",
])
def test_rejects_noncanonical_or_ambiguous_url(url: str) -> None:
    with pytest.raises(ValueError):
        indexnow.canonical_url(url)
