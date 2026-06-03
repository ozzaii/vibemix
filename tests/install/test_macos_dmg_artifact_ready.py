# SPDX-License-Identifier: Apache-2.0
"""Tests for the macOS first-install DMG readiness gate."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from scripts.dist import check_macos_dmg_artifact_ready as gate
from scripts.dist.check_sidecar_bundle_ready import LEARN_EXEMPLAR_WAVS

MAC_TRIPLE = "aarch64-apple-darwin"
HDIUTIL = shutil.which("hdiutil")


def _write_learn_exemplar_wavs(sidecar_dir: Path) -> None:
    for rel in LEARN_EXEMPLAR_WAVS:
        path = sidecar_dir / "_internal" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wav")


def _fake_app(root: Path) -> Path:
    app = root / "vibemix.app"
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
    sidecar.write_text(
        "#!/usr/bin/env sh\necho vibemix-core 0.0.1\n" + ("# pad\n" * 2048),
        encoding="utf-8",
    )
    sidecar.chmod(sidecar.stat().st_mode | stat.S_IXUSR)
    _write_learn_exemplar_wavs(sidecar_dir)

    target = av_dylibs / "libavcodec.62.dylib"
    target.write_bytes(b"av")
    os.symlink("av/.dylibs/libavcodec.62.dylib", internal / target.name)
    return app


def _create_dmg(tmp_path: Path, app: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    shutil.copytree(app, source / app.name, symlinks=True)
    artifact = tmp_path / "vibemix-0.1.0-arm64.dmg"
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            "vibemix",
            "-srcfolder",
            str(source),
            "-format",
            "UDZO",
            "-ov",
            str(artifact),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return artifact


@pytest.mark.skipif(HDIUTIL is None, reason="hdiutil is macOS-only")
def test_ready_dmg_drag_installs_and_smokes_sidecar(tmp_path: Path) -> None:
    artifact = _create_dmg(tmp_path, _fake_app(tmp_path / "app-src"))
    install_dir = tmp_path / "install"

    status = gate.check_macos_dmg_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        install_dir=install_dir,
        smoke="version",
    )

    assert status.ok is True
    assert status.installed_app == str(install_dir / "vibemix.app")
    assert status.app_status is not None
    assert status.app_status.smoke_stdout == "vibemix-core 0.0.1"
    copied_link = (
        install_dir
        / "vibemix.app"
        / "Contents"
        / "Resources"
        / "binaries"
        / f"vibemix-core-{MAC_TRIPLE}"
        / "_internal"
        / "libavcodec.62.dylib"
    )
    assert copied_link.is_symlink()


@pytest.mark.skipif(HDIUTIL is None, reason="hdiutil is macOS-only")
def test_rehearsal_refuses_non_empty_install_dir(tmp_path: Path) -> None:
    artifact = _create_dmg(tmp_path, _fake_app(tmp_path / "app-src"))
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")

    status = gate.check_macos_dmg_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        install_dir=install_dir,
        smoke="none",
    )

    assert status.ok is False
    assert "not empty" in status.errors[0]
    assert (install_dir / "keep.txt").read_text(encoding="utf-8") == "do not overwrite\n"


def test_non_dmg_artifact_fails(tmp_path: Path) -> None:
    artifact = tmp_path / "vibemix.zip"
    artifact.write_bytes(b"not a dmg")

    status = gate.check_macos_dmg_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        smoke="none",
    )

    assert status.ok is False
    assert ".dmg" in status.errors[0]


@pytest.mark.skipif(HDIUTIL is None, reason="hdiutil is macOS-only")
def test_require_developer_id_is_passed_to_drag_installed_app_checker(
    tmp_path: Path, monkeypatch
) -> None:
    artifact = _create_dmg(tmp_path, _fake_app(tmp_path / "app-src"))
    seen = {}

    def fake_app_check(app_path, **kwargs):
        seen.update(kwargs)
        return gate.MacOSAppBundleStatus(
            app=str(app_path),
            triple=kwargs["triple"],
            developer_id="Developer ID signature ready: TeamIdentifier=TEAM123",
        )

    monkeypatch.setattr(gate, "check_macos_app_bundle_ready", fake_app_check)

    status = gate.check_macos_dmg_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        require_developer_id=True,
        developer_team_id="TEAM123",
        smoke="none",
    )

    assert status.ok is True
    assert seen["require_developer_id"] is True
    assert seen["developer_team_id"] == "TEAM123"
