# SPDX-License-Identifier: Apache-2.0
"""Tests for the staged Windows app payload readiness gate."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.dist import check_windows_app_payload_ready as gate

WIN_TRIPLE = "x86_64-pc-windows-msvc"


def _write_pe(path: Path, *, size: int = 8192) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ" + (b"x" * (size - 2)))


def _fake_payload(tmp_path: Path, *, internal: bool = True, placeholder_only: bool = False) -> Path:
    payload = tmp_path / "windows-app"
    if placeholder_only:
        sidecar_dir = payload / "binaries" / f"vibemix-core-{WIN_TRIPLE}"
        sidecar_dir.mkdir(parents=True)
        (sidecar_dir / ".placeholder").write_text("build sidecar first\n", encoding="utf-8")
        _write_pe(payload / "vibemix.exe")
        return payload

    _write_pe(payload / "vibemix.exe")
    sidecar_dir = payload / "binaries" / f"vibemix-core-{WIN_TRIPLE}"
    _write_pe(sidecar_dir / f"vibemix-core-{WIN_TRIPLE}.exe")
    if internal:
        (sidecar_dir / "_internal").mkdir(parents=True)
    return payload


def test_ready_windows_payload_passes_structural_checks(tmp_path: Path) -> None:
    payload = _fake_payload(tmp_path)

    status = gate.check_windows_app_payload_ready(payload, triple=WIN_TRIPLE)

    assert status.ok is True
    assert status.app_binary.endswith("vibemix.exe")
    assert status.sidecar_binary.endswith(f"vibemix-core-{WIN_TRIPLE}.exe")


def test_missing_app_exe_fails(tmp_path: Path) -> None:
    payload = _fake_payload(tmp_path)
    (payload / "vibemix.exe").unlink()

    status = gate.check_windows_app_payload_ready(payload, triple=WIN_TRIPLE)

    assert status.ok is False
    assert any("app binary" in error for error in status.errors)


def test_non_pe_binary_fails(tmp_path: Path) -> None:
    payload = _fake_payload(tmp_path)
    (payload / "vibemix.exe").write_bytes(b"NO" + (b"x" * 8190))

    status = gate.check_windows_app_payload_ready(payload, triple=WIN_TRIPLE)

    assert status.ok is False
    assert any("PE executable" in error for error in status.errors)


def test_placeholder_only_sidecar_fails(tmp_path: Path) -> None:
    payload = _fake_payload(tmp_path, placeholder_only=True)

    status = gate.check_windows_app_payload_ready(payload, triple=WIN_TRIPLE)

    assert status.ok is False
    assert "placeholder-only" in status.errors[0]


def test_missing_internal_dir_fails(tmp_path: Path) -> None:
    payload = _fake_payload(tmp_path, internal=False)

    status = gate.check_windows_app_payload_ready(payload, triple=WIN_TRIPLE)

    assert status.ok is False
    assert "_internal" in status.errors[0]


def test_smoke_runs_sidecar_command(tmp_path: Path, monkeypatch) -> None:
    payload = _fake_payload(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="vibemix 0.1.0\n", stderr="")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    status = gate.check_windows_app_payload_ready(
        payload,
        triple=WIN_TRIPLE,
        smoke="version",
    )

    assert status.ok is True
    assert calls == [
        [
            str(
                payload
                / "binaries"
                / f"vibemix-core-{WIN_TRIPLE}"
                / f"vibemix-core-{WIN_TRIPLE}.exe"
            ),
            "--version",
        ]
    ]
    assert status.smoke_stdout == "vibemix 0.1.0"


def test_main_returns_one_for_missing_payload(tmp_path: Path, capsys) -> None:
    rc = gate.main([str(tmp_path / "missing")])

    assert rc == 1
    assert "payload directory missing" in capsys.readouterr().err
