# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 02 — production recordings root resolves to app_data_dir()/recordings.

The `_resolve_recordings_root()` helper in `vibemix.__main__` is the single
wire-site the live runtime uses to construct `VoiceRecorder(root=...)`. The
helper MUST forward to `vibemix.runtime.config_store.app_data_dir()` so the
Tauri assetProtocol scope ($APPDATA/vibemix/recordings/**) matches what the
sidecar writes to.

This test directly invokes the helper with a patched _app_data_dir — no
full main() run needed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from vibemix.__main__ import _resolve_recordings_root


def test_resolve_recordings_root_uses_app_data_dir(tmp_path: Path) -> None:
    """_resolve_recordings_root() returns app_data_dir() / "recordings"."""
    fake_app_dir = tmp_path / "fake-app-data"

    with patch("vibemix.__main__.app_data_dir", return_value=fake_app_dir):
        resolved = _resolve_recordings_root()

    assert Path(resolved) == fake_app_dir / "recordings", (
        f"expected {fake_app_dir / 'recordings'!s}, got {resolved!s}"
    )


def test_resolve_recordings_root_is_pure_no_mkdir(tmp_path: Path) -> None:
    """The helper must not mkdir — VoiceRecorder.__init__ owns the create
    (with mode=0o700 per RESEARCH Security V8)."""
    fake_app_dir = tmp_path / "untouched-app-data"

    with patch("vibemix.__main__.app_data_dir", return_value=fake_app_dir):
        _resolve_recordings_root()

    assert not fake_app_dir.exists(), (
        "resolver leaked an mkdir — VoiceRecorder must own dir creation"
    )
