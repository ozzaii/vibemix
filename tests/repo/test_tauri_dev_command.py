"""Tauri dev-loop config guards."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONF = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"


def test_before_dev_command_targets_ui_package() -> None:
    body = TAURI_CONF.read_text(encoding="utf-8")

    assert '"beforeDevCommand": "npm --prefix ui run dev"' in body
    assert '"beforeDevCommand": "npm --prefix tauri/ui run dev"' not in body
    assert '"beforeDevCommand": "npm run dev"' not in body


def test_before_build_command_prepares_frontend_and_sidecar() -> None:
    body = TAURI_CONF.read_text(encoding="utf-8")

    assert (
        '"beforeBuildCommand": "uv run python ../scripts/dist/prepare_tauri_build.py"'
        in body
    )
    assert 'committed `.placeholder`' in body
