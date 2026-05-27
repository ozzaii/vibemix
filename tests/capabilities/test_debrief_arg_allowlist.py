# SPDX-License-Identifier: Apache-2.0
"""Debrief capability contract.

The debrief window used to launch `binaries/vibemix-core` through Tauri's
named sidecar permission. The product now ships the PyInstaller onedir bundle
as `bundle.resources` and Rust resolves it from `resource_dir()` just like the
watchdog/library paths. Pin both sides: the window label remains in capability
scope, and the stale named sidecar allow entry stays removed.
"""

from __future__ import annotations

import json
from pathlib import Path

CAPABILITY_PATH = (
    Path(__file__).resolve().parents[2]
    / "tauri"
    / "src-tauri"
    / "capabilities"
    / "default.json"
)


def _load_capability() -> dict:
    return json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))


def _shell_execute_allows(cap: dict) -> list[dict]:
    for perm in cap.get("permissions", []):
        if not isinstance(perm, dict):
            continue
        if perm.get("identifier") != "shell:allow-execute":
            continue
        allows = perm.get("allow")
        assert isinstance(allows, list), "shell:allow-execute allow must be a list"
        return allows
    raise AssertionError("shell:allow-execute permission not found")


def test_named_vibemix_core_sidecar_permission_removed():
    cap = _load_capability()
    stale = [
        allow
        for allow in _shell_execute_allows(cap)
        if allow.get("name") == "binaries/vibemix-core" or allow.get("sidecar") is True
    ]
    assert stale == [], (
        "debrief/watchdog/library must use the resource_dir resolver, not a "
        "stale Tauri externalBin sidecar permission"
    )


def test_windows_array_includes_debrief():
    cap = _load_capability()
    windows = cap.get("windows", [])
    assert "debrief" in windows, (
        f"windows array should include 'debrief', got {windows!r}"
    )
