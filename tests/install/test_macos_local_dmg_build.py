# SPDX-License-Identifier: Apache-2.0
"""Static contract for the local unsigned macOS DMG rehearsal wrapper."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dist" / "build_macos_local_dmg.sh"
DEV_LOOP = ROOT / "docs" / "dev-loop.md"
RELEASE_PROCESS = ROOT / "docs" / "release-process.md"


def test_local_dmg_wrapper_repairs_before_creating_dmg() -> None:
    body = SCRIPT.read_text(encoding="utf-8")
    executable_body = "\n".join(
        line for line in body.splitlines() if not line.lstrip().startswith("#")
    )
    repair = body.index("repair_macos_app_sidecar_symlinks.py")
    app_check = body.index("check_macos_app_bundle_ready.py")
    create = body.index("create-dmg")
    dmg_check = body.index("check_macos_dmg_artifact_ready.py")

    assert "cargo tauri build --bundles app --no-sign --ci" in body
    assert "VIBEMIX_FORCE_SIDECAR=1 cargo tauri build" in body
    assert repair < app_check < create < dmg_check
    assert "cargo tauri build --bundles dmg --no-sign" not in executable_body


def test_docs_point_local_dmg_rehearsal_at_wrapper() -> None:
    dev_loop = DEV_LOOP.read_text(encoding="utf-8")
    release_process = RELEASE_PROCESS.read_text(encoding="utf-8")

    assert "bash scripts/dist/build_macos_local_dmg.sh" in dev_loop
    assert "bash scripts/dist/build_macos_local_dmg.sh" in release_process
    assert "cargo tauri build --bundles dmg --no-sign` directly" in dev_loop
