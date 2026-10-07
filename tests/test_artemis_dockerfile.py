# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The ARTEMIS service image must contain every first-party module main.py imports.

691fb55 made deployment/artemis/app/main.py import artemis.osint, but the image
was built from deployment/artemis/ and copied only app/, so the container died
at boot with ModuleNotFoundError. There is no Docker in CI, so these checks
rebuild the image's file layout from the Dockerfile's COPY lines instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "deployment" / "artemis" / "Dockerfile"
MAIN = ROOT / "deployment" / "artemis" / "app" / "main.py"


def _copies() -> list[tuple[str, str]]:
    """(source, destination) for every COPY from the build context."""
    pairs = []
    for line in DOCKERFILE.read_text().splitlines():
        parts = line.split()
        if not parts or parts[0] != "COPY" or any(p.startswith("--") for p in parts[1:]):
            continue
        *sources, dest = parts[1:]
        pairs.extend((src, dest.rstrip("/")) for src in sources)
    return pairs


def _image_has(image_path: str) -> bool:
    """True when some COPY puts a file from the repository at image_path."""
    for src, dest in _copies():
        if image_path == dest:
            return (ROOT / src).exists()
        if image_path.startswith(dest + "/") and (ROOT / src).is_dir():
            if (ROOT / src / image_path[len(dest) + 1 :]).exists():
                return True
    return False


def _first_party_imports() -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(MAIN.read_text())):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return {m for m in modules if (ROOT / m.split(".")[0] / "__init__.py").is_file()}


def test_every_copy_source_exists_from_the_repo_root() -> None:
    # The Dockerfile header says to build from the repository root.
    missing = [src for src, _ in _copies() if not (ROOT / src).exists()]
    assert not missing, f"COPY sources missing relative to the repo root: {missing}"


def test_main_imports_first_party_code() -> None:
    # Guards the test below against passing vacuously if main.py's imports change.
    assert "artemis.osint.api" in _first_party_imports()


def test_image_carries_every_first_party_module_main_imports() -> None:
    for module in sorted(_first_party_imports()):
        parts = module.split(".")
        for depth in range(1, len(parts)):
            package = "/".join(parts[:depth])
            assert _image_has(f"/app/{package}/__init__.py"), f"image lacks package {package}"
        leaf = "/".join(parts)
        assert _image_has(f"/app/{leaf}.py") or _image_has(f"/app/{leaf}/__init__.py"), (
            f"image lacks {module}, which main.py imports"
        )
