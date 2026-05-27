# SPDX-License-Identifier: Apache-2.0
"""Tests for repairing Tauri-flattened macOS sidecar dylib links."""

from __future__ import annotations

import os
from pathlib import Path

from scripts.dist.repair_macos_app_sidecar_symlinks import repair_bundle


def _fake_app(tmp_path: Path) -> Path:
    app = tmp_path / "vibemix.app"
    internal = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / "vibemix-core-aarch64-apple-darwin"
        / "_internal"
    )
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "Info.plist").write_text("<plist />\n", encoding="utf-8")
    (internal / "av" / ".dylibs").mkdir(parents=True)
    (internal / "PIL" / ".dylibs").mkdir(parents=True)
    return app


def test_repair_bundle_relinks_flattened_av_and_pil_dylibs(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)
    internal = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / "vibemix-core-aarch64-apple-darwin"
        / "_internal"
    )

    av_target = internal / "av" / ".dylibs" / "libavcodec.62.dylib"
    pil_target = internal / "PIL" / ".dylibs" / "libjpeg.62.dylib"
    av_target.write_bytes(b"av")
    pil_target.write_bytes(b"pil")
    (internal / av_target.name).write_bytes(b"av")
    (internal / pil_target.name).write_bytes(b"pil")

    summary = repair_bundle(app)

    assert summary.ok
    assert summary.scanned_internal_dirs == 1
    assert summary.relinked == 2
    assert os.readlink(internal / av_target.name) == "av/.dylibs/libavcodec.62.dylib"
    assert os.readlink(internal / pil_target.name) == "PIL/.dylibs/libjpeg.62.dylib"


def test_repair_bundle_keeps_correct_symlink(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)
    internal = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / "vibemix-core-aarch64-apple-darwin"
        / "_internal"
    )
    target = internal / "av" / ".dylibs" / "libavutil.60.dylib"
    target.write_bytes(b"avutil")
    os.symlink("av/.dylibs/libavutil.60.dylib", internal / target.name)

    summary = repair_bundle(app)

    assert summary.ok
    assert summary.already_linked == 1
    assert summary.relinked == 0
    assert os.readlink(internal / target.name) == "av/.dylibs/libavutil.60.dylib"


def test_repair_bundle_reports_mismatch_without_replacing(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)
    internal = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / "vibemix-core-aarch64-apple-darwin"
        / "_internal"
    )
    target = internal / "av" / ".dylibs" / "libswscale.9.dylib"
    top_level = internal / target.name
    target.write_bytes(b"expected")
    top_level.write_bytes(b"different")

    summary = repair_bundle(app)

    assert not summary.ok
    assert summary.relinked == 0
    assert not top_level.is_symlink()
    assert "content differs" in summary.mismatches[0]
