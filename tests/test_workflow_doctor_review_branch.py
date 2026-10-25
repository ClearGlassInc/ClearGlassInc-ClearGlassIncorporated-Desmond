"""Exercise the repair branch step against a local remote, without GitHub access."""
import os
import subprocess
from pathlib import Path

import yaml

from scripts.audit_github_actions import GitHubLoader


ROOT = Path(__file__).resolve().parents[1]


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def test_each_repair_attempt_preserves_existing_review_branch(tmp_path):
    document = yaml.load(
        (ROOT / ".github/workflows/workflow-doctor.yml").read_text(), Loader=GitHubLoader
    )
    repair = document["jobs"]["repair"]
    branch_step = next(s for s in repair["steps"] if s.get("name") == "Establish repair branch")
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "init", "-b", "main", str(work))
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.invalid")
    (work / ".github/workflows").mkdir(parents=True)
    tracked = work / ".github/workflows/check.yml"
    tracked.write_text("baseline\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "baseline")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "origin", "main")
    baseline = git(work, "rev-parse", "HEAD")
    # Simulate review work on the branch that the old implementation resets.
    tracked.write_text("review work\n")
    git(work, "commit", "-am", "review work")
    review = git(work, "rev-parse", "HEAD")
    git(work, "push", "origin", "HEAD:refs/heads/bot/workflow-doctor-repair")
    git(work, "reset", "--hard", baseline)
    tracked.write_text("proposed repair\n")

    branches = []
    for attempt in ("1", "2"):
        output = tmp_path / f"output-{attempt}"
        output.touch()
        subprocess.run(
            ["bash", "-euo", "pipefail", "-c", branch_step["run"]], cwd=work, check=True,
            env={**os.environ, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": attempt,
                 "GITHUB_OUTPUT": str(output)},
        )
        assert git(remote, "rev-parse", "refs/heads/bot/workflow-doctor-repair") == review
        branch = dict(line.split("=", 1) for line in output.read_text().splitlines())["branch"]
        branches.append(branch)
        assert git(remote, "rev-parse", f"refs/heads/{branch}") == baseline
        assert tracked.read_text() == "proposed repair\n"
        assert git(work, "diff", "--cached", "--name-only") == ".github/workflows/check.yml"
    assert len(set(branches)) == 2
    assert branch_step["id"] == "branch"
    signing = next(s for s in repair["steps"] if s.get("name") == "Commit repairs (Verified)")
    pr = next(s for s in repair["steps"] if s.get("name") == "Open repair PR")
    assert signing["with"]["branch"] == "${{ steps.branch.outputs.branch }}"
    assert pr["env"]["REPAIR_BRANCH"] == "${{ steps.branch.outputs.branch }}"
