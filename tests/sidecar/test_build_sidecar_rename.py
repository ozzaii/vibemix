# SPDX-License-Identifier: Apache-2.0
"""Phase 11 Wave 1 — unit tests for ``scripts/build_sidecar.py``.

We test the three helpers that don't require a real PyInstaller run:

1. ``detect_target_triple`` — parses ``rustc -vV`` host line.
2. ``install_into_tauri_binaries`` — copies a fake onedir + renames the
   inner binary; verifies executable bit on POSIX.
3. ``assert_no_aiza_leak`` — finds AIza-pattern strings inside any
   bundle file and aborts; passes silently on a clean bundle.

The full PyInstaller invocation (``run_pyinstaller`` + ``build_and_install``
end-to-end) runs only on Kaan's macOS dev rig as a manual checkpoint —
not in this unit test suite (per 11-02-PLAN.md task 2 item 4).
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

# Import the script module directly. We added scripts/__init__.py in Task 2.
from scripts import build_sidecar


# ---------------------------------------------------------------------------
# detect_target_triple
# ---------------------------------------------------------------------------


def test_detect_target_triple_returns_known_shape() -> None:
    """``detect_target_triple`` returns a string in one of the known
    triple shapes for v1 platforms (Linux included for CI matrix)."""
    if shutil.which("rustc") is None:
        pytest.skip("rustc not on PATH — skip on hosts without Rust")

    triple = build_sidecar.detect_target_triple()
    assert isinstance(triple, str)
    assert triple, "triple is empty"
    # Apple Silicon / Intel mac / Windows / Linux x64 / Linux arm64 — the
    # five shapes we'd ever see on Kaan's box or a CI runner.
    valid = re.compile(
        r"^(x86_64|aarch64)-(apple-darwin|pc-windows-msvc|unknown-linux-gnu)$"
    )
    assert valid.match(triple), f"unexpected triple shape: {triple!r}"


def test_detect_target_triple_raises_when_rustc_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """If rustc isn't on PATH, the helper raises RuntimeError with an
    actionable install hint — not a cryptic FileNotFoundError."""

    def fake_check_output(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise FileNotFoundError("rustc not found")

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    with pytest.raises(RuntimeError, match=r"rustc not on PATH"):
        build_sidecar.detect_target_triple()


def test_exe_suffix_for_triple() -> None:
    """The suffix helper is platform-aware."""
    assert build_sidecar.exe_suffix_for_triple("x86_64-pc-windows-msvc") == ".exe"
    assert build_sidecar.exe_suffix_for_triple("aarch64-apple-darwin") == ""
    assert build_sidecar.exe_suffix_for_triple("x86_64-unknown-linux-gnu") == ""


# ---------------------------------------------------------------------------
# install_into_tauri_binaries
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_onedir(tmp_path: Path) -> Path:
    """Create a synthetic ``dist/vibemix-core/`` mirror: an executable
    file named ``vibemix-core`` + a couple of dummy lib files so the
    copytree path is realistic."""
    onedir = tmp_path / "dist" / "vibemix-core"
    onedir.mkdir(parents=True)
    binary = onedir / "vibemix-core"
    binary.write_bytes(b"#!/usr/bin/env python3\nprint('hi')\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    # Lib files so the copytree feels real.
    (onedir / "libpython3.12.dylib").write_bytes(b"\0" * 1024)
    (onedir / "internal" / "scipy").mkdir(parents=True)
    (onedir / "internal" / "scipy" / "signal.py").write_text("# fake module\n")

    return onedir


def test_install_into_tauri_binaries_renames_and_relocates(
    tmp_path: Path,
    fake_onedir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: ``vibemix-core`` lands at
    ``tauri/src-tauri/binaries/vibemix-core-<triple>/vibemix-core-<triple>``.
    The original ``vibemix-core`` inside the target dir is gone (renamed).
    Sibling lib files are preserved.
    """
    # Redirect the module's _TAURI_BINARIES_DIR into tmp_path so we don't
    # touch the real tauri/src-tauri/binaries during tests.
    fake_target_root = tmp_path / "tauri" / "src-tauri" / "binaries"
    monkeypatch.setattr(build_sidecar, "_TAURI_BINARIES_DIR", fake_target_root)

    triple = "aarch64-apple-darwin"
    renamed = build_sidecar.install_into_tauri_binaries(
        fake_onedir, triple, exe_suffix=""
    )

    expected_dir = fake_target_root / f"vibemix-core-{triple}"
    expected_binary = expected_dir / f"vibemix-core-{triple}"

    assert renamed == expected_binary
    assert expected_binary.is_file()
    assert (expected_dir / "vibemix-core").exists() is False, "old name should be gone"
    assert (expected_dir / "libpython3.12.dylib").is_file()
    assert (expected_dir / "internal" / "scipy" / "signal.py").is_file()
    # Executable bit preserved on POSIX (Windows os.X_OK semantics differ;
    # the suffix=="" branch only runs on macOS / Linux anyway).
    assert os.access(expected_binary, os.X_OK), "executable bit not preserved"


def test_install_into_tauri_binaries_idempotent(
    tmp_path: Path,
    fake_onedir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running install on a pre-existing target dir overwrites cleanly."""
    fake_target_root = tmp_path / "tauri" / "src-tauri" / "binaries"
    monkeypatch.setattr(build_sidecar, "_TAURI_BINARIES_DIR", fake_target_root)
    triple = "aarch64-apple-darwin"

    # First install.
    build_sidecar.install_into_tauri_binaries(fake_onedir, triple, exe_suffix="")
    # Plant a stale file in the target dir; second install must wipe it.
    target_dir = fake_target_root / f"vibemix-core-{triple}"
    (target_dir / "stale.txt").write_text("delete me")

    # Second install — fresh onedir.
    build_sidecar.install_into_tauri_binaries(fake_onedir, triple, exe_suffix="")
    assert (target_dir / "stale.txt").exists() is False


def test_install_into_tauri_binaries_windows_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows path: vibemix-core.exe → vibemix-core-<triple>.exe."""
    onedir = tmp_path / "dist" / "vibemix-core"
    onedir.mkdir(parents=True)
    (onedir / "vibemix-core.exe").write_bytes(b"MZ\x90\x00fake-pe-header\n")

    fake_target_root = tmp_path / "tauri" / "src-tauri" / "binaries"
    monkeypatch.setattr(build_sidecar, "_TAURI_BINARIES_DIR", fake_target_root)
    triple = "x86_64-pc-windows-msvc"

    renamed = build_sidecar.install_into_tauri_binaries(onedir, triple, exe_suffix=".exe")

    assert renamed.name == f"vibemix-core-{triple}.exe"
    assert renamed.is_file()


def test_install_into_tauri_binaries_raises_on_missing_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the inner ``vibemix-core`` binary isn't where the spec says it
    should be, abort with a clear error."""
    onedir = tmp_path / "dist" / "vibemix-core"
    onedir.mkdir(parents=True)
    # Note: NO vibemix-core file inside

    monkeypatch.setattr(build_sidecar, "_TAURI_BINARIES_DIR", tmp_path / "binaries")
    with pytest.raises(RuntimeError, match=r"expected inner binary .* missing"):
        build_sidecar.install_into_tauri_binaries(
            onedir, "aarch64-apple-darwin", exe_suffix=""
        )


# ---------------------------------------------------------------------------
# assert_no_aiza_leak
# ---------------------------------------------------------------------------


_FAKE_AIZA = "AIza1234567890abcdefghijklmnopqrstuvwxy"  # 4 + 35 = 39 chars


def test_assert_no_aiza_leak_detects_literal_string(tmp_path: Path) -> None:
    """A file containing the literal AIza pattern must abort the build."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "config.txt").write_text(f"GEMINI_API_KEY={_FAKE_AIZA}\n")

    with pytest.raises(RuntimeError, match=r"API KEY LEAK"):
        build_sidecar.assert_no_aiza_leak(bundle)


def test_assert_no_aiza_leak_passes_on_clean_bundle(tmp_path: Path) -> None:
    """A bundle with no AIza-pattern bytes anywhere passes silently."""
    bundle = tmp_path / "bundle"
    (bundle / "nested" / "deep").mkdir(parents=True)
    (bundle / "main.py").write_text("# nothing to see here\n")
    (bundle / "lib.so").write_bytes(b"\x7fELF" + b"\x00" * 1024)
    (bundle / "nested" / "deep" / "data.json").write_text('{"answer": 42}')

    # Must return None (no raise).
    result = build_sidecar.assert_no_aiza_leak(bundle)
    assert result is None


def test_assert_no_aiza_leak_detects_inside_binary_bytes(tmp_path: Path) -> None:
    """The pattern hides inside a binary blob — still must catch it.
    This is the realistic threat: a leaked key embedded in a .pyc cache
    or PyInstaller's frozen-module zip."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "freeze.pyc").write_bytes(
        b"\x42\x0d\x0d\x0a" + b"\x00" * 64 + _FAKE_AIZA.encode("ascii") + b"\x00" * 128
    )

    with pytest.raises(RuntimeError, match=r"API KEY LEAK"):
        build_sidecar.assert_no_aiza_leak(bundle)


def test_assert_no_aiza_leak_redacts_key_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The error message + log line must NEVER print the actual key —
    that would leak the secret to CI logs."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "leak.txt").write_text(_FAKE_AIZA + "\n")

    with pytest.raises(RuntimeError):
        build_sidecar.assert_no_aiza_leak(bundle)

    captured = capsys.readouterr()
    # The key itself must NEVER land in stderr — only "values redacted".
    assert _FAKE_AIZA not in captured.err
    assert _FAKE_AIZA not in captured.out


def test_assert_no_aiza_leak_raises_on_missing_dir(tmp_path: Path) -> None:
    """Missing bundle dir is a configuration error, not silent success."""
    with pytest.raises(RuntimeError, match=r"bundle dir not found"):
        build_sidecar.assert_no_aiza_leak(tmp_path / "does-not-exist")


# ---------------------------------------------------------------------------
# main() CLI argparse + dispatch
# ---------------------------------------------------------------------------


def test_main_requires_spec_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--spec`` is mandatory; argparse aborts with non-zero exit."""
    with pytest.raises(SystemExit) as exc_info:
        build_sidecar.main([])
    assert exc_info.value.code != 0


def test_main_help_includes_no_aiza_check_warning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--help`` documents ``--no-aiza-check`` as DANGEROUS + CI-never."""
    with pytest.raises(SystemExit) as exc_info:
        build_sidecar.main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "no-aiza-check" in captured.out
    assert "DANGEROUS" in captured.out
    assert "Phase 5" in captured.out


def test_main_returns_nonzero_on_missing_spec_path(tmp_path: Path) -> None:
    """If --spec points to a file that doesn't exist, main exits non-zero
    cleanly (RuntimeError → exit 1, not unhandled stack trace)."""
    bogus_spec = tmp_path / "does-not-exist.spec"
    rc = build_sidecar.main(["--spec", str(bogus_spec)])
    assert rc == 1
