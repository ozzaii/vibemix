# SPDX-License-Identifier: Apache-2.0
"""Tests for the final GitHub Release upload-directory gate."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.dist import check_release_upload_dir_ready as gate


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_upload_dir(tmp_path: Path) -> Path:
    upload = tmp_path / "upload"
    upload.mkdir()
    for name in (
        "vibemix-v0.1.0-arm64.dmg",
        "vibemix-v0.1.0-x86_64.dmg",
        "vibemix-installer.exe",
        "vibemix-0.1.0-arm64.app.tar.gz",
        "vibemix-0.1.0-x86_64.app.tar.gz",
        "vibemix_0.1.0_x64-setup.exe",
    ):
        (upload / name).write_bytes(b"artifact")
    _write_json(
        upload / "latest.json",
        {
            "version": "0.1.0",
            "notes": "Release v0.1.0",
            "pub_date": "2026-06-04T12:00:00Z",
            "platforms": {
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
            },
        },
    )
    for name in (
        "verify-report-macos-arm64.json",
        "verify-report-macos-x86_64.json",
        "verify-report-windows.json",
    ):
        _write_json(upload / name, {"status": "clean", "hits": [], "scanned": 42})
    return upload


def test_complete_upload_dir_passes(tmp_path: Path) -> None:
    upload = _write_upload_dir(tmp_path)

    status = gate.check_release_upload_dir_ready(upload, tag="v0.1.0")

    assert status.ok is True
    assert "latest.json" in status.files


def test_missing_updater_archive_fails(tmp_path: Path) -> None:
    upload = _write_upload_dir(tmp_path)
    (upload / "vibemix-0.1.0-x86_64.app.tar.gz").unlink()

    status = gate.check_release_upload_dir_ready(upload, tag="v0.1.0")

    assert status.ok is False
    assert any("macOS x86_64 updater archive" in error for error in status.errors)


def test_dirty_verify_report_fails(tmp_path: Path) -> None:
    upload = _write_upload_dir(tmp_path)
    _write_json(
        upload / "verify-report-windows.json",
        {"status": "flagged", "hits": [{"kind": "secret"}], "scanned": 42},
    )

    status = gate.check_release_upload_dir_ready(upload, tag="v0.1.0")

    assert status.ok is False
    assert any("verify report status is not clean" in error for error in status.errors)
    assert any("verify report contains hits" in error for error in status.errors)


def test_broken_latest_json_fails(tmp_path: Path) -> None:
    upload = _write_upload_dir(tmp_path)
    data = json.loads((upload / "latest.json").read_text(encoding="utf-8"))
    data["platforms"]["darwin-aarch64"]["url"] = (
        "https://example.test/vibemix-v0.1.0-arm64.dmg"
    )
    _write_json(upload / "latest.json", data)

    status = gate.check_release_upload_dir_ready(upload, tag="v0.1.0")

    assert status.ok is False
    assert "latest.json failed updater manifest readiness" in status.errors
    assert any("first-install DMG" in error for error in status.errors)


def test_forbidden_upload_asset_fails(tmp_path: Path) -> None:
    upload = _write_upload_dir(tmp_path)
    (upload / "vibemix-v0.1.0.pkg").write_bytes(b"pkg")

    status = gate.check_release_upload_dir_ready(upload, tag="v0.1.0")

    assert status.ok is False
    assert any("forbidden upload asset" in error for error in status.errors)
