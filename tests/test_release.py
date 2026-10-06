"""scripts/ci/release.py: what moves traffic, what moves it back, and what never runs.

Cloud Run is the stateful fake in tests/fixtures/fake_gcloud.py; docker and the
smoke script are stubs whose results the test controls. The assertions are about
the traffic table, because that is what users experience.
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
RELEASE = ROOT / "scripts" / "ci" / "release.py"
FAKE_GCLOUD = Path(__file__).resolve().parent / "fixtures" / "fake_gcloud.py"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None, reason="needs bash and jq"
)

FAKE_DOCKER = """#!/bin/sh
# build/push succeed and register the image; imagetools inspect resolves only
# images that were pushed or pre-seeded in $FAKE_DOCKER_IMAGES.
echo "$*" >> "$FAKE_DOCKER_LOG"
case "$1" in
  build) exit 0 ;;
  push) echo "$2" >> "$FAKE_DOCKER_IMAGES"; exit 0 ;;
  buildx)
    if grep -qxF "$4" "$FAKE_DOCKER_IMAGES" 2>/dev/null; then
      printf '{"digest":"sha256:%064d"}' 7
      exit 0
    fi
    echo "not found: $4" >&2; exit 1 ;;
esac
exit 2
"""

# Fails when the URL contains $FAKE_SMOKE_FAIL (if set); records every URL.
FAKE_SMOKE = """#!/bin/sh
echo "$SMOKE_BASE_URL" >> "$FAKE_SMOKE_LOG"
if [ -n "$FAKE_SMOKE_FAIL" ]; then
  case "$SMOKE_BASE_URL" in *"$FAKE_SMOKE_FAIL"*) echo "smoke failed"; exit 1 ;; esac
fi
exit 0
"""

SHA = "abc1234" + "0" * 33
REPO = "northamerica-northeast2-docker.pkg.dev/cg-artifacts/releases"


def executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def service(name: str) -> dict:
    return {
        "revisions": [{"name": f"{name}-00001", "image": "old", "env": None}],
        "status": {
            "url": f"https://{name}-x.a.run.app",
            "latestCreatedRevisionName": f"{name}-00001",
            "traffic": [{"revisionName": f"{name}-00001", "percent": 100}],
        },
    }


@pytest.fixture
def world(tmp_path: Path) -> dict:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable(bin_dir / "gcloud", f'#!/bin/sh\nexec {sys.executable} {FAKE_GCLOUD} "$@"\n')
    executable(bin_dir / "docker", FAKE_DOCKER)
    smoke = tmp_path / "smoke.sh"
    executable(smoke, FAKE_SMOKE)
    state = tmp_path / "state.json"
    names = [f"cg-{svc}-{env}" for svc in ("control-plane", "storefront") for env in ("preview", "staging", "production")]
    state.write_text(json.dumps({name: service(name) for name in names}))
    images = tmp_path / "images.txt"
    images.write_text("")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GCLOUD_STATE": str(state),
        "FAKE_GCLOUD_LOG": str(tmp_path / "gcloud.log"),
        "FAKE_DOCKER_LOG": str(tmp_path / "docker.log"),
        "FAKE_DOCKER_IMAGES": str(images),
        "FAKE_SMOKE_LOG": str(tmp_path / "smoke.log"),
        "CG_SMOKE_SCRIPT": str(smoke),
        "DEPLOY_PROVIDER": "cloudrun",
        "DEPLOY_PROJECT": "cg-test",
        "DEPLOY_REGION": "northamerica-northeast2",
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }
    return {"env": env, "tmp": tmp_path, "state": state, "images": images}


def release(world: dict, *args: str, **env: str) -> tuple[int, dict, dict]:
    out = world["tmp"] / "result.json"
    proc = subprocess.run(
        [sys.executable, str(RELEASE), "--sha", SHA, "--image-repository", REPO, "--out", str(out), *args],
        env={**world["env"], **env},
        capture_output=True,
        text=True,
    )
    outputs = {}
    output_file = Path(world["env"]["GITHUB_OUTPUT"])
    if output_file.exists():
        outputs = dict(line.split("=", 1) for line in output_file.read_text().splitlines() if "=" in line)
    result = json.loads(out.read_text()) if out.exists() else {}
    result["_stdout"], result["_stderr"] = proc.stdout, proc.stderr
    return proc.returncode, outputs, result


def serving(world: dict, name: str) -> str:
    state = json.loads(world["state"].read_text())
    return next(t["revisionName"] for t in state[name]["status"]["traffic"] if t["percent"] == 100)


def tags(world: dict, name: str) -> set[str]:
    state = json.loads(world["state"].read_text())
    return {t["tag"] for t in state[name]["status"]["traffic"] if t.get("tag")}


def seed_image(world: dict, svc: str) -> None:
    with world["images"].open("a") as handle:
        handle.write(f"{REPO}/{svc}:{SHA}\n")


def test_preview_builds_deploys_a_tagged_revision_and_never_moves_traffic(world):
    code, outputs, result = release(
        world, "--environment", "preview", "--services", "control-plane", "--tag", "pr-12", "--build"
    )
    assert code == 0, result["_stderr"]
    assert outputs["outcome"] == "success"
    assert json.loads(outputs["urls"]) == {"control-plane": "https://pr-12---cg-control-plane-preview-x.a.run.app"}
    assert serving(world, "cg-control-plane-preview") == "cg-control-plane-preview-00001"
    assert tags(world, "cg-control-plane-preview") == {"pr-12"}  # the preview URL stays

    state = json.loads(world["state"].read_text())
    env = state["cg-control-plane-preview"]["revisions"][-1]["env"]
    assert "APP_ENV=preview" in env and "DATABASE_URL=sqlite:////tmp/preview.db" in env
    admin_key = next(p.split("=", 1)[1] for p in env.split(",") if p.startswith("ADMIN_API_KEY="))
    assert admin_key != "@random" and len(admin_key) == 48
    assert f"::add-mask::{admin_key}" in result["_stdout"]
    # Deployed by digest, never by the mutable tag.
    assert state["cg-control-plane-preview"]["revisions"][-1]["image"] == f"{REPO}/control-plane@sha256:{7:064d}"


def test_staging_promotes_then_removes_the_candidate_tag(world):
    code, outputs, _ = release(
        world, "--environment", "staging", "--services", "control-plane", "--tag", "sha-abc1234",
        "--build", "--promote", "--auto-rollback",
    )
    assert code == 0 and outputs["outcome"] == "success"
    assert serving(world, "cg-control-plane-staging") == "cg-control-plane-staging-00002"
    assert tags(world, "cg-control-plane-staging") == set()
    assert outputs["primary_url"] == "https://cg-control-plane-staging-x.a.run.app"


def test_production_refuses_an_image_staging_never_built(world):
    code, outputs, result = release(
        world, "--environment", "production", "--services", "control-plane", "--tag", "sha-abc1234",
        "--promote", "--auto-rollback",
    )
    assert code == 1 and outputs["outcome"] == "failed"
    assert result["services"][0]["status"] == "failed"
    gcloud_calls = Path(world["env"]["FAKE_GCLOUD_LOG"]).read_text() if Path(world["env"]["FAKE_GCLOUD_LOG"]).exists() else ""
    assert '"deploy"' not in gcloud_calls
    assert serving(world, "cg-control-plane-production") == "cg-control-plane-production-00001"


def test_production_never_builds():
    proc = subprocess.run(
        [sys.executable, str(RELEASE), "--environment", "production", "--services", "control-plane",
         "--sha", SHA, "--tag", "t", "--image-repository", REPO, "--build"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2 and "never builds" in proc.stderr


def test_previews_never_promote():
    proc = subprocess.run(
        [sys.executable, str(RELEASE), "--environment", "preview", "--services", "control-plane",
         "--sha", SHA, "--tag", "t", "--image-repository", REPO, "--promote"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2 and "never take traffic" in proc.stderr


def test_a_failing_candidate_never_receives_traffic(world):
    seed_image(world, "control-plane")
    code, outputs, result = release(
        world, "--environment", "production", "--services", "control-plane", "--tag", "sha-abc1234",
        "--promote", "--auto-rollback", FAKE_SMOKE_FAIL="sha-abc1234---",
    )
    assert code == 1 and outputs["outcome"] == "failed"
    assert serving(world, "cg-control-plane-production") == "cg-control-plane-production-00001"
    assert "update-traffic" in Path(world["env"]["FAKE_GCLOUD_LOG"]).read_text()  # only the tag cleanup
    assert "--to-revisions" not in Path(world["env"]["FAKE_GCLOUD_LOG"]).read_text()


def test_a_release_that_fails_live_is_rolled_back_in_reverse_order(world):
    seed_image(world, "control-plane")
    seed_image(world, "storefront")
    code, outputs, result = release(
        world, "--environment", "production", "--services", "storefront,control-plane", "--tag", "sha-abc1234",
        "--promote", "--auto-rollback", FAKE_SMOKE_FAIL="https://cg-storefront-production-x",
    )
    assert code == 1 and outputs["outcome"] == "rolled-back"
    # Both services were promoted; both serve their previous revision again.
    assert serving(world, "cg-control-plane-production") == "cg-control-plane-production-00001"
    assert serving(world, "cg-storefront-production") == "cg-storefront-production-00001"
    statuses = {s["service"]: s["status"] for s in result["services"]}
    assert statuses == {"control-plane": "rolled-back", "storefront": "rolled-back"}
    # Dependency order: the API went first, so it is restored last.
    log = [json.loads(line) for line in Path(world["env"]["FAKE_GCLOUD_LOG"]).read_text().splitlines()]
    rollbacks = [c[3] for c in log if "--to-revisions" in c and c[c.index("--to-revisions") + 1].endswith("-00001=100")]
    assert rollbacks == ["cg-storefront-production", "cg-control-plane-production"]


def test_rollback_is_withheld_when_migrations_ship(world):
    seed_image(world, "control-plane")
    code, outputs, result = release(
        world, "--environment", "production", "--services", "control-plane", "--tag", "sha-abc1234",
        "--promote", FAKE_SMOKE_FAIL="https://cg-control-plane-production-x",
    )
    assert code == 1 and outputs["outcome"] == "failed"
    assert serving(world, "cg-control-plane-production") == "cg-control-plane-production-00002"
    assert "Rollback withheld" in result["_stdout"]


def test_unknown_services_are_refused(world):
    code, _, result = release(world, "--environment", "staging", "--services", "control-plane,../etc",
                              "--tag", "t", "--build")
    assert code == 2 and "not deployable" in result["_stdout"]
