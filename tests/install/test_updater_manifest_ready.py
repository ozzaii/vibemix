# SPDX-License-Identifier: Apache-2.0
"""Tests for the signed updater manifest readiness gate."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.dist import check_updater_manifest_ready as gate


def _manifest(**platform_overrides) -> dict:
    platforms = {
        "darwin-aarch64": {
            "url": "https://example.test/vibemix-0.1.0-arm64.app.tar.gz",
            "signature": "sig-arm64",
        },
        "darwin-x86_64": {
            "url": "https://example.test/vibemix-0.1.0-x86_64.app.tar.gz",
            "signature": "sig-x86_64",
        },
        "windows-x86_64": {
            "url": "https://example.test/vibemix_0.1.0_x64-setup.exe",
            "signature": "sig-windows",
        },
    }
    platforms.update(platform_overrides)
    return {
        "version": "0.1.0",
        "notes": "Release v0.1.0",
        "pub_date": "2026-06-04T12:00:00Z",
        "platforms": platforms,
    }


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_complete_manifest_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _manifest())

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is True
    assert status.version == "0.1.0"
    assert status.platforms == ["darwin-aarch64", "darwin-x86_64", "windows-x86_64"]


def test_missing_platform_fails(tmp_path: Path) -> None:
    data = _manifest()
    del data["platforms"]["darwin-x86_64"]
    path = _write(tmp_path, data)

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is False
    assert "missing platform entries: darwin-x86_64" in status.errors


def test_semver_prerelease_with_build_metadata_passes(tmp_path: Path) -> None:
    data = _manifest()
    data["version"] = "0.1.0-beta.1+build.5"
    path = _write(tmp_path, data)

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is True
    assert status.version == "0.1.0-beta.1+build.5"


def test_macos_manifest_must_not_point_at_dmg(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _manifest(
            **{
                "darwin-aarch64": {
                    "url": "https://example.test/vibemix-0.1.0-arm64.dmg",
                    "signature": "sig-arm64",
                }
            }
        ),
    )

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is False
    assert any("url must end with .app.tar.gz" in error for error in status.errors)
    assert any("first-install DMG" in error for error in status.errors)


def test_windows_manifest_must_not_point_at_first_install_inno(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _manifest(
            **{
                "windows-x86_64": {
                    "url": "https://example.test/vibemix-installer.exe",
                    "signature": "sig-windows",
                }
            }
        ),
    )

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is False
    assert any("Inno first-install" in error for error in status.errors)
    assert any("NSIS *setup*.exe" in error for error in status.errors)


def test_empty_signature_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _manifest(
            **{
                "darwin-x86_64": {
                    "url": "https://example.test/vibemix-0.1.0-x86_64.app.tar.gz",
                    "signature": "",
                }
            }
        ),
    )

    status = gate.check_updater_manifest_ready(path)

    assert status.ok is False
    assert "darwin-x86_64: signature must be non-empty" in status.errors
