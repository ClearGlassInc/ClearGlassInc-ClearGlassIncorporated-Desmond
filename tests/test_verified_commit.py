"""Offline regressions for the shared signing action's GitHub request boundary."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github/actions/verified-commit"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Offline fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "reports").mkdir()
    (repo / "reports/report.txt").write_text("original\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Initial fixture")
    return repo


def run_action(repo: Path, tmp_path: Path, *, api_fails: bool = False):
    """Run the real Bash action, replacing only remote Git/GitHub operations."""
    tool_dir = tmp_path / "bin"
    tool_dir.mkdir()
    requests = tmp_path / "requests.jsonl"
    pushes = tmp_path / "pushes.jsonl"
    output = tmp_path / "output"
    real_git = shutil.which("git")
    assert real_git
    (tool_dir / "git").write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "if args[0] in {'fetch', 'reset'}: sys.exit(0)\n"
        "if args[0] == 'push':\n"
        "    with open(os.environ['PUSHES'], 'a') as handle:\n"
        "        handle.write(json.dumps(args) + '\\n')\n"
        "    sys.exit(0)\n"
        "if args[0] == 'pull': sys.exit(0)\n"
        "os.execv(os.environ['REAL_GIT'], [os.environ['REAL_GIT'], *args])\n"
    )
    (tool_dir / "gh").write_text(
        f"#!{sys.executable}\n"
        "import json, os, re, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] != ['api', 'graphql']: sys.exit(2)\n"
        "if '--input' in args:\n"
        "    source = args[args.index('--input') + 1]\n"
        "    request = json.load(sys.stdin if source == '-' else open(source))\n"
        "else:\n"
        "    fields = {}\n"
        "    for index, arg in enumerate(args[:-1]):\n"
        "        if arg != '-f': continue\n"
        "        key, value = args[index + 1].split('=', 1)\n"
        "        keys = re.findall(r'[^\\[\\]]+', key)\n"
        "        target = fields\n"
        "        for key in keys[:-1]: target = target.setdefault(key, {})\n"
        "        target[keys[-1]] = value\n"
        "    request = {'query': fields.pop('query'), 'variables': fields}\n"
        "with open(os.environ['REQUESTS'], 'a') as handle:\n"
        "    handle.write(json.dumps(request) + '\\n')\n"
        "changes = request.get('variables', {}).get('input', {}).get('fileChanges')\n"
        "if os.environ['API_FAILS'] == '1' or not isinstance(changes, dict): sys.exit(1)\n"
        "print(json.dumps({'data': {'createCommitOnBranch': {'commit': {'oid': 'a' * 40}}}}))\n"
    )
    (tool_dir / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for tool in tool_dir.iterdir():
        tool.chmod(0o755)
    branch = "repair/verified-commit-test"
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", f"refs/remotes/origin/{branch}", head)
    marker = tmp_path / "injection-must-not-run"
    message = f'Fix "quoted" report\nλ literal $(touch {marker}) and `false`'
    env = dict(
        os.environ,
        PATH=f"{tool_dir}{os.pathsep}{os.environ['PATH']}",
        REAL_GIT=real_git,
        REQUESTS=str(requests),
        PUSHES=str(pushes),
        API_FAILS="1" if api_fails else "0",
        GITHUB_ACTION_PATH=str(ACTION),
        GITHUB_OUTPUT=str(output),
        CG_PATHS="reports",
        CG_MESSAGE=message,
        CG_BRANCH=branch,
        GH_REPO="example/repository",
        GH_TOKEN="offline-fixture",
    )
    script = yaml.safe_load((ACTION / "action.yml").read_text())["runs"]["steps"][0]["run"]
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", script],
        cwd=repo, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "commit metadata was executed as shell source"
    records = [json.loads(line) for line in requests.read_text().splitlines()] if requests.exists() else []
    return records, output.read_text(), pushes, message, head


def test_signing_request_uses_structured_file_changes_and_preserves_metadata(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    (repo / "reports/report.txt").write_text('New "quoted" content\nλ\n')

    records, output, pushes, message, head = run_action(repo, tmp_path)

    request = records[0]
    assert request["variables"]["input"] == {
        "branch": {"repositoryNameWithOwner": "example/repository", "branchName": "repair/verified-commit-test"},
        "message": {"headline": message},
        "expectedHeadOid": head,
        "fileChanges": {
            "additions": [{"path": "reports/report.txt", "contents": "TmV3ICJxdW90ZWQiIGNvbnRlbnQKzrsK"}],
            "deletions": [],
        },
    }
    assert "createCommitOnBranch" in request["query"]
    assert len(records) == 1
    assert output.splitlines() == ["committed=true", "verified=true"]
    assert not pushes.exists(), "successful signing unexpectedly fell back to git push"


def test_staged_rename_deletes_old_path_from_the_signed_commit(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    git(repo, "mv", "reports/report.txt", "reports/renamed report.txt")

    result = subprocess.run(
        [sys.executable, str(ACTION / "build_file_changes.py")],
        cwd=repo, check=True, capture_output=True, text=True,
    )

    assert json.loads(result.stdout) == {
        "additions": [{"path": "reports/renamed report.txt", "contents": base64.b64encode(b"original\n").decode()}],
        "deletions": [{"path": "reports/report.txt"}],
    }


def test_unavailable_signing_api_preserves_git_push_fallback(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    (repo / "reports/report.txt").write_text("changed\n")

    records, output, pushes, _, _ = run_action(repo, tmp_path, api_fails=True)

    assert len(records) == 5
    assert output.splitlines() == ["committed=true", "verified=false"]
    assert json.loads(pushes.read_text()) == ["push", "origin", "HEAD:repair/verified-commit-test"]
    assert git(repo, "show", "HEAD:reports/report.txt") == "changed"


def test_unchanged_tree_does_not_call_the_signing_api(tmp_path: Path) -> None:
    repo = repository(tmp_path)

    records, output, pushes, _, _ = run_action(repo, tmp_path)

    assert records == []
    assert output.splitlines() == ["committed=false", "verified=false"]
    assert not pushes.exists()
