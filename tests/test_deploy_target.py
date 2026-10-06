"""scripts/ci/deploy_target.sh against a stateful fake gcloud.

The fake keeps a Cloud Run service's traffic table in a JSON file and implements
only the four gcloud calls the adapter makes, so these tests prove the sequence
the deploy workflows depend on: a new revision gets no traffic, promotion moves
100% to it, rollback moves it back, teardown removes only the named tag, and
production configuration is merged rather than replaced.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "deploy_target.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None, reason="needs bash and jq"
)

FAKE_GCLOUD = Path(__file__).resolve().parent / "fixtures" / "fake_gcloud.py"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gcloud"
    fake.write_text(f"#!/bin/sh\nexec {sys.executable} {FAKE_GCLOUD} \"$@\"\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "cg-api": {
                    "revisions": [{"name": "cg-api-00001", "image": "old", "env": None}],
                    "status": {
                        "url": "https://cg-api-x.a.run.app",
                        "latestCreatedRevisionName": "cg-api-00001",
                        "traffic": [{"revisionName": "cg-api-00001", "percent": 100}],
                    },
                }
            }
        )
    )
    return {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GCLOUD_STATE": str(state),
        "FAKE_GCLOUD_LOG": str(tmp_path / "calls.log"),
        "DEPLOY_PROVIDER": "cloudrun",
        "DEPLOY_PROJECT": "cg-staging",
        "DEPLOY_REGION": "northamerica-northeast2",
        "SERVICE": "cg-api",
        "COMMIT_SHA": "a" * 40,
    }


def run(action: str, env: dict[str, str], **extra: str) -> tuple[int, dict[str, str], str]:
    proc = subprocess.run(
        ["bash", str(SCRIPT), action],
        env={**env, **extra},
        capture_output=True,
        text=True,
    )
    outputs = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
    return proc.returncode, outputs, proc.stderr


def calls(env: dict[str, str]) -> list[list[str]]:
    log = Path(env["FAKE_GCLOUD_LOG"])
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def test_describe_reports_the_serving_revision(env):
    code, out, _ = run("describe", env)
    assert code == 0
    assert out == {"exists": "true", "url": "https://cg-api-x.a.run.app", "serving_revision": "cg-api-00001"}


def test_describe_a_missing_service(env):
    code, out, _ = run("describe", env, SERVICE="nope")
    assert code == 0 and out["exists"] == "false"


def test_deploy_refuses_to_create_a_service(env):
    code, _, err = run("deploy", env, SERVICE="nope", IMAGE="img@sha256:1", TAG="pr-1", PORT="8000")
    assert code != 0 and "does not exist" in err
    assert not any(c[:2] == ["run", "deploy"] for c in calls(env))


def test_deploy_promote_rollback_untag(env):
    code, out, _ = run("deploy", env, IMAGE="img@sha256:2", TAG="sha-abc1234", PORT="8000", ENV_VARS="A=1,B=2")
    assert code == 0
    assert out["revision"] == "cg-api-00002"
    assert out["candidate_url"] == "https://sha-abc1234---cg-api-x.a.run.app"
    # The candidate takes no traffic until promoted.
    assert run("describe", env)[1]["serving_revision"] == "cg-api-00001"

    deploy_call = next(c for c in calls(env) if c[:2] == ["run", "deploy"])
    assert "--no-traffic" in deploy_call
    assert "--update-env-vars" in deploy_call and "--set-env-vars" not in deploy_call
    assert "commit-sha=" + "a" * 40 in " ".join(deploy_call)

    assert run("promote", env, REVISION="cg-api-00002")[0] == 0
    assert run("describe", env)[1]["serving_revision"] == "cg-api-00002"

    assert run("rollback", env, REVISION="cg-api-00001")[0] == 0
    assert run("describe", env)[1]["serving_revision"] == "cg-api-00001"

    assert run("untag", env, TAG="sha-abc1234")[0] == 0
    state = json.loads(Path(env["FAKE_GCLOUD_STATE"]).read_text())
    assert all(t.get("tag") != "sha-abc1234" for t in state["cg-api"]["status"]["traffic"])


def test_no_env_vars_means_no_env_flag(env):
    run("deploy", env, IMAGE="img@sha256:2", TAG="pr-7", PORT="8000")
    deploy_call = next(c for c in calls(env) if c[:2] == ["run", "deploy"])
    assert "--update-env-vars" not in deploy_call


def test_untagging_an_absent_tag_is_a_no_op(env):
    code, _, _ = run("untag", env, TAG="pr-404")
    assert code == 0
    assert not any("update-traffic" in c for c in calls(env))


@pytest.mark.parametrize("tag", ["PR-1", "1abc", "pr_1", "pr 1; rm -rf /", ""])
def test_invalid_tags_are_refused_before_any_call(env, tag):
    code, _, _ = run("deploy", env, IMAGE="img", TAG=tag, PORT="8000")
    assert code != 0
    assert not any(c[:2] == ["run", "deploy"] for c in calls(env))


@pytest.mark.parametrize("provider, message", [("ecs", "not implemented"), ("kubernetes", "not implemented"),
                                               ("", "not set"), ("azure", "unknown provider")])
def test_other_providers_fail_closed(env, provider, message):
    code, _, err = run("describe", env, DEPLOY_PROVIDER=provider)
    assert code != 0 and message in err
