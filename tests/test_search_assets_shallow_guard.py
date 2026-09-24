"""The search-asset generator must refuse to run in a shallow clone.

``<lastmod>`` comes from each page's last commit. In a shallow clone that
history stops at the boundary commit, so the generator rewrote ~125 dates to
that commit's day and ``scripts/ci_local.py`` reported the committed sitemap as
stale when it was correct. Committing that output, as the failure message then
advised, would have published wrong dates for every older page.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load("seo_audit")
generator = _load("generate_search_assets")


def test_refuses_before_writing_anything_in_a_shallow_clone(monkeypatch, capsys) -> None:
    monkeypatch.setattr(generator, "shallow_clone", lambda: True)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("generator touched the tree in a shallow clone")

    for name in ("indexable_pages", "write_sitemap", "write_feed", "write_intent_map"):
        monkeypatch.setattr(generator, name, must_not_run)

    assert generator.main() == 2
    assert "git fetch --unshallow" in capsys.readouterr().err


def test_shallow_clone_reads_git(tmp_path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    assert generator.shallow_clone() is False
    (tmp_path / ".git" / "shallow").write_text("0" * 40 + "\n")
    assert generator.shallow_clone() is True
