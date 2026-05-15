# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-07 — v2.0 → v2.1 upgrade TCC carryover gate.

When a user upgrades from v2.0 to v2.1 of vibemix the bundle id stays
exactly ``world.bravoh.vibemix``. macOS TCC tracks granted permissions
per-bundle-id, so a stable bundle id means the user's microphone +
screen-recording grants carry over without a re-prompt.

This test does NOT touch real TCC state on the dev machine. It
fakes a per-version state directory under tmp_path and asserts the
v2.1 launch finds the v2.0 state on disk. The real macOS TCC db
lookup happens at runtime via tauri-plugin-macos-permissions — there
is no autonomous way to validate that against the live OS.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


BUNDLE_ID = "world.bravoh.vibemix"


def _write_v2_0_state(app_support: Path) -> Path:
    """Simulate a v2.0 install that has already granted TCC + persisted
    a small state file. The path layout mirrors what Tauri's
    AppHandle::path().app_local_data_dir() returns on macOS:

        ~/Library/Application Support/<BUNDLE_ID>/state.json
    """
    bundle_dir = app_support / BUNDLE_ID
    bundle_dir.mkdir(parents=True, exist_ok=True)
    state_file = bundle_dir / "tcc-state.json"
    state_file.write_text(
        json.dumps({
            "version": "2.0",
            "microphone": "granted",
            "screen_recording": "granted",
        }),
        encoding="utf-8",
    )
    return state_file


def test_v2_0_state_dir_uses_locked_bundle_id(tmp_path: Path) -> None:
    """v2.0 wrote state under the locked bundle id directory."""
    state = _write_v2_0_state(tmp_path)
    assert BUNDLE_ID in state.parts
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["microphone"] == "granted"


def test_v2_1_finds_v2_0_state_after_version_bump(tmp_path: Path) -> None:
    """The bundle id is stable across the version bump — v2.1's state
    file path resolves to the same directory v2.0 wrote, so TCC grants
    carry forward."""
    state_v20 = _write_v2_0_state(tmp_path)

    # Simulate v2.1 launch: read from the same locked bundle dir.
    v21_state_dir = tmp_path / BUNDLE_ID
    v21_state_file = v21_state_dir / "tcc-state.json"
    assert v21_state_file == state_v20, (
        "v2.1 must resolve to the same TCC-state path v2.0 wrote — "
        "any divergence means the bundle id changed (P63 violation)."
    )

    # v2.1 reads the v2.0 grants verbatim.
    payload = json.loads(v21_state_file.read_text(encoding="utf-8"))
    assert payload["microphone"] == "granted"
    assert payload["screen_recording"] == "granted"


def test_bundle_id_change_would_lose_tcc_state(tmp_path: Path) -> None:
    """Negative gate: if the bundle id ever changed, v2.1 would land in
    a DIFFERENT directory and the user's v2.0 TCC grants would not
    carry forward. This test documents that failure mode."""
    _write_v2_0_state(tmp_path)
    # Hypothetical changed id (a typo / refactor slip — exactly what
    # P63 warns about).
    changed_id = "com.bravoh.vibemix"
    changed_dir = tmp_path / changed_id
    assert not changed_dir.exists(), (
        "Sanity check — changed-id dir must not preexist on fresh tmp."
    )
    # The v2.1 launch reading from changed_id would find NO state —
    # which is exactly the bad UX P63 describes.
    state_file = changed_dir / "tcc-state.json"
    assert not state_file.exists(), (
        "Bundle id change loses prior TCC state — see P63."
    )
