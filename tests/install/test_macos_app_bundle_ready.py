# SPDX-License-Identifier: Apache-2.0
"""Tests for the packaged macOS app bundle readiness gate."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from scripts.dist import check_macos_app_bundle_ready as gate

MAC_TRIPLE = "aarch64-apple-darwin"


def _fake_app(tmp_path: Path, *, repaired_links: bool = True) -> Path:
    app = tmp_path / "vibemix.app"
    macos = app / "Contents" / "MacOS"
    internal = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / f"vibemix-core-{MAC_TRIPLE}"
        / "_internal"
    )
    sidecar_dir = internal.parent
    av_dylibs = internal / "av" / ".dylibs"

    macos.mkdir(parents=True)
    av_dylibs.mkdir(parents=True)
    (app / "Contents" / "Info.plist").write_text("<plist />\n", encoding="utf-8")

    main = macos / "vibemix"
    main.write_bytes(b"x" * 8192)
    main.chmod(main.stat().st_mode | stat.S_IXUSR)

    sidecar = sidecar_dir / f"vibemix-core-{MAC_TRIPLE}"
    sidecar.write_text("#!/usr/bin/env sh\necho vibemix-core 0.0.1\n", encoding="utf-8")
    sidecar.chmod(sidecar.stat().st_mode | stat.S_IXUSR)

    target = av_dylibs / "libavcodec.62.dylib"
    target.write_bytes(b"av")
    top_level = internal / target.name
    if repaired_links:
        os.symlink("av/.dylibs/libavcodec.62.dylib", top_level)
    else:
        top_level.write_bytes(b"av")

    return app


def test_ready_app_bundle_passes_with_sidecar_smoke(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="version",
    )

    assert status.ok is True
    assert status.smoke_stdout == "vibemix-core 0.0.1"
    assert status.sidecar_binary.endswith(f"vibemix-core-{MAC_TRIPLE}")


def test_flattened_dylib_copy_fails_until_repaired(tmp_path: Path) -> None:
    app = _fake_app(tmp_path, repaired_links=False)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="none",
    )

    assert status.ok is False
    assert "flattened dylib copy" in status.errors[0]


def test_missing_sidecar_binary_fails(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)
    sidecar = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / f"vibemix-core-{MAC_TRIPLE}"
        / f"vibemix-core-{MAC_TRIPLE}"
    )
    sidecar.unlink()

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="none",
    )

    assert status.ok is False
    assert "sidecar binary" in status.errors[0]


def test_bundled_test_fixture_payloads_fail(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)
    fixture = (
        app
        / "Contents"
        / "Resources"
        / "binaries"
        / f"vibemix-core-{MAC_TRIPLE}"
        / "_internal"
        / "tests"
        / "library"
        / "fixtures"
        / "synthetic_collection.xml"
    )
    fixture.parent.mkdir(parents=True)
    fixture.write_text("<DJ_PLAYLISTS />\n", encoding="utf-8")

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="none",
    )

    assert status.ok is False
    assert any("test fixture payloads bundled" in error for error in status.errors)
    assert any("synthetic_collection.xml" in error for error in status.errors)


def test_main_returns_one_for_flattened_links(tmp_path: Path, capsys) -> None:
    app = _fake_app(tmp_path, repaired_links=False)

    rc = gate.main(
        [
            str(app),
            "--triple",
            MAC_TRIPLE,
            "--min-bytes",
            "1",
            "--smoke",
            "none",
        ]
    )

    assert rc == 1
    assert "flattened dylib copy" in capsys.readouterr().err
