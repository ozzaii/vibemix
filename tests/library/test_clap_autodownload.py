# SPDX-License-Identifier: Apache-2.0
"""First library use must auto-download the CLAP ONNX snapshot, not dead-end with
a raw FileNotFoundError.

The README promises a "one-time ~785 MB model download on first Library open".
The installer (``vibemix library models --install clap``) already exists, but a
GUI-only user never runs it — so ``_ensure_onnx_assets`` reuses that installer on
first use (zero-config default). It stays honest: if the snapshot is absent AND
can't be fetched (offline opt-out, or a failed download), it raises an ACTIONABLE
error — never a silent mis-grounding, never a bare missing-file the user who never
opened a terminal can't act on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import vibemix.library.model_assets as model_assets
from vibemix.library import clap_engine

_AUDIO_REL = "onnx/audio_model.onnx"
_TEXT_REL = "onnx/text_model.onnx"


def _write_snapshot(mdir: Path) -> None:
    """Create the two ONNX files ``_ensure_onnx_assets`` checks for."""
    for rel in (_AUDIO_REL, _TEXT_REL):
        p = mdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"onnx")


def test_present_snapshot_skips_download(tmp_path, monkeypatch):
    """Model already on disk → no download attempt, no raise."""
    _write_snapshot(tmp_path)
    calls: list[dict] = []
    monkeypatch.setattr(
        model_assets,
        "install_clap_model",
        lambda **kw: calls.append(kw) or {"installed": True, "errors": []},
    )
    clap_engine._ensure_onnx_assets(tmp_path)
    assert calls == [], "must not download when the snapshot is already present"


def test_absent_snapshot_autodownloads_then_proceeds(tmp_path, monkeypatch):
    """Absent model → calls the shared installer, which fetches it, then returns."""
    calls: list[dict] = []

    def fake_install(**kw):
        calls.append(kw)
        _write_snapshot(tmp_path)  # the "download" lands the files
        return {"installed": True, "errors": []}

    monkeypatch.setattr(model_assets, "install_clap_model", fake_install)
    clap_engine._ensure_onnx_assets(tmp_path)  # must not raise
    assert len(calls) == 1, "first use must trigger exactly one install"


def test_optout_env_skips_download_and_raises(tmp_path, monkeypatch):
    """VIBEMIX_CLAP_NO_AUTODOWNLOAD=1 (offline/air-gapped) → raise without fetching."""
    calls: list[dict] = []
    monkeypatch.setattr(
        model_assets,
        "install_clap_model",
        lambda **kw: calls.append(kw) or {"installed": True, "errors": []},
    )
    monkeypatch.setenv("VIBEMIX_CLAP_NO_AUTODOWNLOAD", "1")
    with pytest.raises(FileNotFoundError):
        clap_engine._ensure_onnx_assets(tmp_path)
    assert calls == [], "opt-out must not hit the network"


def test_failed_download_raises_actionable(tmp_path, monkeypatch):
    """Download runs but the snapshot is still absent → actionable error naming the
    manual install fallback, never a silent partial state."""

    def fake_install(**kw):
        return {
            "installed": False,
            "errors": ["download failed for onnx/audio_model.onnx: timeout"],
        }

    monkeypatch.setattr(model_assets, "install_clap_model", fake_install)
    with pytest.raises(FileNotFoundError) as excinfo:
        clap_engine._ensure_onnx_assets(tmp_path)
    assert "models --install clap" in str(excinfo.value), excinfo.value


def test_progress_logs_downloading_line(capsys):
    """The first-run progress hook prints a human MB line and never raises on
    odd/partial frames (progress is telemetry — it must not break model setup)."""
    clap_engine._stderr_clap_progress(
        {
            "status": "downloading",
            "rel_path": "onnx/audio_model.onnx",
            "n": 1,
            "total": 6,
            "downloaded": 8 << 20,
            "size": 281 << 20,
        }
    )
    clap_engine._stderr_clap_progress({"status": "weird"})  # ignored, no raise
    clap_engine._stderr_clap_progress({"status": "downloaded", "rel_path": "x"})
    err = capsys.readouterr().err
    assert "downloading onnx/audio_model.onnx" in err
    assert "8/281 MB" in err
    assert "downloaded x" in err
