# SPDX-License-Identifier: Apache-2.0
"""Tests for extracting and validating macOS updater artifacts."""

from __future__ import annotations

import os
import stat
import tarfile
from pathlib import Path

from scripts.dist import check_macos_updater_artifact_ready as gate
from scripts.dist.check_sidecar_bundle_ready import LEARN_EXEMPLAR_WAVS

MAC_TRIPLE = "aarch64-apple-darwin"


def _write_learn_exemplar_wavs(sidecar_dir: Path) -> None:
    for rel in LEARN_EXEMPLAR_WAVS:
        path = sidecar_dir / "_internal" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wav")


def _fake_app(root: Path, *, repaired_links: bool = True) -> Path:
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
    top_level = internal / target.name
    if repaired_links:
        os.symlink("av/.dylibs/libavcodec.62.dylib", top_level)
    else:
        top_level.write_bytes(b"av")
    return app


def _tar_app(tmp_path: Path, app: Path, name: str = "vibemix-0.1.0-arm64.app.tar.gz") -> Path:
    artifact = tmp_path / name
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(app, arcname=app.name, recursive=True)
    return artifact


def test_ready_updater_artifact_extracts_and_smokes_sidecar(tmp_path: Path) -> None:
    app = _fake_app(tmp_path / "src")
    artifact = _tar_app(tmp_path, app)
    install_dir = tmp_path / "install"

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        install_dir=install_dir,
        smoke="version",
    )

    assert status.ok is True
    assert status.app == str(install_dir / "vibemix.app")
    assert status.app_status is not None
    assert status.app_status.smoke_stdout == "vibemix-core 0.0.1"
    assert (install_dir / "vibemix.app" / "Contents" / "Info.plist").is_file()


def test_flattened_app_inside_artifact_fails(tmp_path: Path) -> None:
    app = _fake_app(tmp_path / "src", repaired_links=False)
    artifact = _tar_app(tmp_path, app)

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        smoke="none",
    )

    assert status.ok is False
    assert any("flattened dylib copy" in error for error in status.errors)


def test_appledouble_metadata_is_ignored(tmp_path: Path) -> None:
    app = _fake_app(tmp_path / "src")
    artifact = tmp_path / "vibemix-0.1.0-arm64.app.tar.gz"
    metadata = tmp_path / "._vibemix.app"
    metadata.write_bytes(b"appledouble")
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(app, arcname=app.name, recursive=True)
        archive.add(metadata, arcname="._vibemix.app")

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        smoke="version",
    )

    assert status.ok is True


def test_rehearsal_refuses_non_empty_install_dir(tmp_path: Path) -> None:
    app = _fake_app(tmp_path / "src")
    artifact = _tar_app(tmp_path, app)
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        install_dir=install_dir,
        smoke="none",
    )

    assert status.ok is False
    assert "not empty" in status.errors[0]
    assert (install_dir / "keep.txt").read_text(encoding="utf-8") == "do not overwrite\n"


def test_unsafe_tar_member_path_fails(tmp_path: Path) -> None:
    artifact = tmp_path / "vibemix-0.1.0-arm64.app.tar.gz"
    payload = tmp_path / "payload.txt"
    payload.write_text("bad\n", encoding="utf-8")
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(payload, arcname="../evil.txt")

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        smoke="none",
    )

    assert status.ok is False
    assert "unsafe tar member path" in status.errors[0]


def test_require_developer_id_is_passed_to_extracted_app_checker(
    tmp_path: Path, monkeypatch
) -> None:
    app = _fake_app(tmp_path / "src")
    artifact = _tar_app(tmp_path, app)
    seen = {}

    def fake_app_check(app_path, **kwargs):
        seen.update(kwargs)
        return gate.MacOSAppBundleStatus(
            app=str(app_path),
            triple=kwargs["triple"],
            developer_id="Developer ID signature ready: TeamIdentifier=TEAM123",
        )

    monkeypatch.setattr(gate, "check_macos_app_bundle_ready", fake_app_check)

    status = gate.check_macos_updater_artifact_ready(
        artifact,
        triple=MAC_TRIPLE,
        require_developer_id=True,
        developer_team_id="TEAM123",
        smoke="none",
    )

    assert status.ok is True
    assert seen["require_developer_id"] is True
    assert seen["developer_team_id"] == "TEAM123"


def test_main_returns_zero_for_ready_artifact(tmp_path: Path, capsys) -> None:
    app = _fake_app(tmp_path / "src")
    artifact = _tar_app(tmp_path, app)

    rc = gate.main(
        [
            str(artifact),
            "--triple",
            MAC_TRIPLE,
            "--smoke",
            "version",
        ]
    )

    assert rc == 0
    assert "OK" in capsys.readouterr().out
