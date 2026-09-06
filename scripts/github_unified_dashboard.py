"""Generate a unified GitHub repository dashboard for ClearGlassInc Artemis.

Usage:
    export GITHUB_TOKEN=ghp_xxx
    python scripts/github_unified_dashboard.py
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

OWNERS = ["ClearGlassInc", "OPENWINDOW369"]
OUT_FILE = Path("clearglass_dashboard.html")
API_BASE = "https://api.github.com"


@dataclass
class RepoRecord:
    owner: str
    name: str
    description: str
    html_url: str
    language: str
    is_private: bool
    updated_at: str
    stars: int
    forks: int


def github_headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_owner_repos(owner: str, headers: dict[str, str]) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{owner}/repos"
        params = {"page": page, "per_page": 100, "sort": "updated", "direction": "desc"}
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        if not payload:
            break
        repos.extend(payload)
        page += 1
    return repos


def normalize_repos(raw_repos: Iterable[dict]) -> list[RepoRecord]:
    normalized: list[RepoRecord] = []
    for repo in raw_repos:
        normalized.append(
            RepoRecord(
                owner=repo["owner"]["login"],
                name=repo["name"],
                description=repo.get("description") or "No description",
                html_url=repo["html_url"],
                language=repo.get("language") or "N/A",
                is_private=bool(repo.get("private", False)),
                updated_at=repo["updated_at"][:10],
                stars=int(repo.get("stargazers_count", 0)),
                forks=int(repo.get("forks_count", 0)),
            )
        )
    return normalized


def render_dashboard(repos: list[RepoRecord]) -> str:
    rows = []
    for r in repos:
        visibility = "🔒 Private" if r.is_private else "🌐 Public"
        rows.append(
            f"""
            <div class=\"repo-card\">
                <div class=\"owner-badge\">{html.escape(r.owner)}</div>
                <div class=\"repo-name\"><a href=\"{html.escape(r.html_url)}\" target=\"_blank\">{html.escape(r.name)}</a></div>
                <div class=\"description\">{html.escape(r.description)}</div>
                <div class=\"lang\">{html.escape(r.language)}</div>
                <div class=\"stats\">
                    <span>{visibility}</span>
                    <span>⭐ {r.stars}</span>
                    <span>🍴 {r.forks}</span>
                    <span>🕘 {r.updated_at}</span>
                </div>
            </div>
            """
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ClearGlassInc Artemis Unified Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, monospace; background: #0d1117; color: #c9d1d9; padding: 2rem; }}
h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: #f0f6fc; }}
.sub {{ margin-bottom: 2rem; color: #8b949e; }}
.repo-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
.repo-card {{ background: #161b22; border-radius: 12px; padding: 1.25rem; border: 1px solid #30363d; transition: transform .1s ease; }}
.repo-card:hover {{ transform: translateY(-2px); border-color: #58a6ff; }}
.repo-name {{ font-size: 1.2rem; font-weight: 600; margin-bottom: .5rem; }}
.repo-name a {{ color: #58a6ff; text-decoration: none; }}
.owner-badge {{ display:inline-block; font-size:.7rem; background:#21262d; padding:.2rem .5rem; border-radius:20px; margin-bottom:.75rem; }}
.description {{ font-size:.85rem; color:#8b949e; margin-bottom:.75rem; min-height:2.5rem; }}
.lang {{ font-size:.75rem; background:#1f242e; display:inline-block; padding:.2rem .5rem; border-radius:12px; margin-right:.5rem; }}
.stats {{ margin-top:.75rem; font-size:.75rem; color:#8b949e; display:flex; gap:.8rem; flex-wrap:wrap; }}
</style>
</head>
<body>
<h1>🪟 ClearGlassInc Artemis Unified Dashboard</h1>
<div class="sub">Connected repos from ClearGlassInc + OPENWINDOW369 • {ts}</div>
<div class="repo-grid">
{''.join(rows)}
</div>
</body>
</html>
"""


def main() -> None:
    headers = github_headers()
    all_raw: list[dict] = []
    for owner in OWNERS:
        try:
            all_raw.extend(fetch_owner_repos(owner, headers))
        except requests.HTTPError as exc:
            print(f"Error fetching {owner}: {exc}")

    repos = normalize_repos(all_raw)
    repos.sort(key=lambda r: r.updated_at, reverse=True)
    OUT_FILE.write_text(render_dashboard(repos), encoding="utf-8")

    print(f"✅ Dashboard saved as {OUT_FILE}")
    if "Authorization" not in headers:
        print("🔑 Tip: set GITHUB_TOKEN to include private repositories.")


if __name__ == "__main__":
    main()
