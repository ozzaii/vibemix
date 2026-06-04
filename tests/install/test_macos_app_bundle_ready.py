# SPDX-License-Identifier: Apache-2.0
"""Tests for the packaged macOS app bundle readiness gate."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from scripts.dist import check_macos_app_bundle_ready as gate
from scripts.dist.check_sidecar_bundle_ready import LEARN_EXEMPLAR_WAVS

MAC_TRIPLE = "aarch64-apple-darwin"


@pytest.fixture(autouse=True)
def _ready_source_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gate,
        "sidecar_build_manifest_ready",
        lambda *_args, **_kwargs: (True, "sidecar source manifest ready"),
    )


def _write_learn_exemplar_wavs(sidecar_dir: Path) -> None:
    for rel in LEARN_EXEMPLAR_WAVS:
        path = sidecar_dir / "_internal" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wav")


def _write_codesign_resource_seal(app: Path) -> None:
    seal = app / "Contents" / "_CodeSignature" / "CodeResources"
    seal.parent.mkdir(parents=True, exist_ok=True)
    seal.write_text("<plist />\n", encoding="utf-8")


def _fake_app(
    tmp_path: Path,
    *,
    repaired_links: bool = True,
    learn_wavs: bool = True,
) -> Path:
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
    if learn_wavs:
        _write_learn_exemplar_wavs(sidecar_dir)

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


def test_missing_learn_exemplar_wavs_fail(tmp_path: Path) -> None:
    app = _fake_app(tmp_path, learn_wavs=False)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="none",
    )

    assert status.ok is False
    assert any("Learn exemplar WAV bank missing" in error for error in status.errors)


def test_stale_source_manifest_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _fake_app(tmp_path)
    monkeypatch.setattr(
        gate,
        "sidecar_build_manifest_ready",
        lambda *_args, **_kwargs: (False, "sidecar source manifest fingerprint is stale"),
    )

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        smoke="none",
    )

    assert status.ok is False
    assert any("source manifest fingerprint is stale" in error for error in status.errors)


def test_require_moss_source_fails_without_bundle_or_archive(
    tmp_path: Path, monkeypatch
) -> None:
    app = _fake_app(tmp_path)
    monkeypatch.delenv("VIBEMIX_MOSS_TTS_ARCHIVE_URL", raising=False)
    monkeypatch.delenv("VIBEMIX_MOSS_TTS_ARCHIVE_SHA256", raising=False)
    monkeypatch.delenv("VIBEMIX_MOSS_TTS_ARCHIVE_SIZE", raising=False)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        require_moss_source=True,
        smoke="none",
    )

    assert status.ok is False
    assert any("MOSS-only release has no model source" in error for error in status.errors)
    assert "VIBEMIX_MOSS_TTS_ARCHIVE_URL is not set" in status.moss_source


def test_require_moss_source_accepts_release_archive_pins(
    tmp_path: Path, monkeypatch
) -> None:
    app = _fake_app(tmp_path)
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_ARCHIVE_URL", "https://models.example/moss.zip")
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_ARCHIVE_SHA256", "b" * 64)
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_ARCHIVE_SIZE", "123")

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        require_moss_source=True,
        smoke="none",
    )

    assert status.ok is True
    assert "MOSS archive pins configured" in status.moss_source


def test_require_developer_id_fails_without_resource_seal(tmp_path: Path) -> None:
    app = _fake_app(tmp_path)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        require_developer_id=True,
        smoke="none",
    )

    assert status.ok is False
    assert any("Developer ID resource seal missing" in error for error in status.errors)


def test_require_developer_id_accepts_signed_resource_seal(
    tmp_path: Path, monkeypatch
) -> None:
    app = _fake_app(tmp_path)
    _write_codesign_resource_seal(app)

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "codesign"
        if "--verify" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="",
                stderr=f"{app}: valid on disk\n{app}: satisfies its Designated Requirement\n",
            )
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="",
            stderr="\n".join(
                [
                    "Executable=/fake/vibemix.app/Contents/MacOS/vibemix",
                    "Authority=Developer ID Application: BravoH Labs (TEAM123)",
                    "Authority=Developer ID Certification Authority",
                    "Authority=Apple Root CA",
                    "TeamIdentifier=TEAM123",
                    "Sealed Resources version=2 rules=13 files=7",
                ]
            ),
        )

    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    status = gate.check_macos_app_bundle_ready(
        app,
        triple=MAC_TRIPLE,
        min_bytes=1,
        require_developer_id=True,
        developer_team_id="TEAM123",
        smoke="none",
    )

    assert status.ok is True
    assert status.developer_id == "Developer ID signature ready: TeamIdentifier=TEAM123"


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
