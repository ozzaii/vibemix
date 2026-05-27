"""Tests for the local Tauri sidecar bundle readiness gate."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from scripts.dist import check_sidecar_bundle_ready as gate

MAC_TRIPLE = "aarch64-apple-darwin"
WIN_TRIPLE = "x86_64-pc-windows-msvc"


def _bundle_dir(root: Path, triple: str) -> Path:
    return root / gate.BINARIES_REL / f"vibemix-core-{triple}"


def _write_bundle(
    root: Path,
    triple: str,
    *,
    size: int = 8192,
    executable: bool = True,
) -> Path:
    bundle = _bundle_dir(root, triple)
    bundle.mkdir(parents=True)
    (bundle / "_internal").mkdir()
    suffix = gate.exe_suffix_for_triple(triple)
    binary = bundle / f"vibemix-core-{triple}{suffix}"
    binary.write_bytes(b"x" * size)
    if suffix == "":
        mode = binary.stat().st_mode
        if executable:
            binary.chmod(mode | stat.S_IXUSR)
        else:
            binary.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    return binary


def test_ready_macos_bundle_passes(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is True
    assert status.binary == binary


def test_placeholder_only_bundle_fails_with_action(tmp_path: Path) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / ".placeholder").write_text("build the sidecar first\n", encoding="utf-8")

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "placeholder-only" in status.message
    assert "scripts/build_sidecar.py" in status.message


def test_missing_binary_fails(tmp_path: Path) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / "_internal").mkdir()

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "binary missing" in status.message


def test_tiny_binary_fails(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, size=16)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "too small" in status.message


def test_posix_binary_must_be_executable(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, executable=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "not executable" in status.message


def test_windows_bundle_does_not_require_posix_execute_bit(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, WIN_TRIPLE, executable=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=WIN_TRIPLE)

    assert status.ok is True
    assert status.binary == binary
    assert not os.access(binary, os.X_OK)


def test_missing_pyinstaller_internal_dir_fails(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    (binary.parent / "_internal").rmdir()

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "_internal" in status.message


def test_main_returns_zero_for_ready_explicit_triple(tmp_path: Path, capsys) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)

    rc = gate.main(["--root", str(tmp_path), "--triple", MAC_TRIPLE])

    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_for_placeholder_bundle(tmp_path: Path, capsys) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / ".placeholder").write_text("placeholder\n", encoding="utf-8")

    rc = gate.main(["--root", str(tmp_path), "--triple", MAC_TRIPLE])

    assert rc == 1
    assert "placeholder-only" in capsys.readouterr().err
