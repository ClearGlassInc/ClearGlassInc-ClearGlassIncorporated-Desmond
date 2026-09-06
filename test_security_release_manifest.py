from tools.security_release_manifest import IMPORTANT_FILES, build_manifest, digest


def test_manifest_is_complete_and_uses_sha256() -> None:
    manifest = build_manifest()
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    assert [artifact["path"] for artifact in artifacts] == list(IMPORTANT_FILES)
    assert all(len(artifact["sha256"]) == 64 for artifact in artifacts)


def test_digest_changes_when_content_changes(tmp_path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("first", encoding="utf-8")
    first = digest(artifact)
    artifact.write_text("second", encoding="utf-8")
    assert digest(artifact) != first
