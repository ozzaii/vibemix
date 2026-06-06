"""Tauri dev-loop config guards."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONF = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"


def test_before_dev_command_resolves_tauri_cli_cwd() -> None:
    body = TAURI_CONF.read_text(encoding="utf-8")

    assert (
        '"beforeDevCommand": "sh -c \'if [ -f ui/package.json ]; then '
        "npm --prefix ui run dev; else npm run dev; fi'\""
    ) in body
    assert "double-prefix `ui/ui`" in body
    assert '"beforeDevCommand": "npm --prefix ui run dev"' not in body
    assert '"beforeDevCommand": "npm --prefix tauri/ui run dev"' not in body
    assert '"beforeDevCommand": "npm run dev"' not in body


def test_before_build_command_prepares_frontend_and_sidecar() -> None:
    body = TAURI_CONF.read_text(encoding="utf-8")

    assert '"beforeBuildCommand": ' in body
    assert "prepare_tauri_build.py --require-chatterbox-ref" in body
    assert "`.placeholder` sidecar directories" in body
    assert "bundled production reference" in body
