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

PROJECT_ROOT = Path(__file__).parents[2]


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

    def fake_check_output(*args, **kwargs):
        raise FileNotFoundError("rustc not found")

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    with pytest.raises(RuntimeError, match=r"rustc not on PATH"):
        build_sidecar.detect_target_triple()


def test_exe_suffix_for_triple() -> None:
    """The suffix helper is platform-aware."""
    assert build_sidecar.exe_suffix_for_triple("x86_64-pc-windows-msvc") == ".exe"
    assert build_sidecar.exe_suffix_for_triple("aarch64-apple-darwin") == ""
    assert build_sidecar.exe_suffix_for_triple("x86_64-unknown-linux-gnu") == ""


def test_run_pyinstaller_installs_local_ai_extra(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The frozen sidecar build must include the local CLAP/CUE runtime deps."""
    monkeypatch.setattr(build_sidecar, "_PROJECT_ROOT", tmp_path)
    spec = tmp_path / "vibemix-core.macos.spec"
    spec.write_text("# fake spec\n", encoding="utf-8")

    captured: list[str] = []

    def fake_run(cmd, **kwargs):
        captured.extend(cmd)
        out = tmp_path / "dist" / "vibemix-core"
        out.mkdir(parents=True)
        (out / "vibemix-core").write_bytes(b"fake")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = build_sidecar.run_pyinstaller(spec)

    assert out == tmp_path / "dist" / "vibemix-core"
    assert captured[:5] == ["uv", "run", "--extra", "ai-local", "pyinstaller"]


def test_pyav_is_a_direct_runtime_dependency() -> None:
    """Local model/debrief audio paths import PyAV directly, not via LiveKit."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"av>=17.0.1"' in text


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
    (onedir / "internal" / "runtime").mkdir(parents=True)
    (onedir / "internal" / "runtime" / "module.py").write_text("# fake module\n")

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
    assert (expected_dir / "internal" / "runtime" / "module.py").is_file()
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


def test_install_into_tauri_binaries_preserves_pyinstaller_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PyInstaller's macOS onedir uses symlinks for duplicated native libs."""
    if os.name == "nt":
        pytest.skip("symlink privileges vary on Windows runners")

    onedir = tmp_path / "dist" / "vibemix-core"
    onedir.mkdir(parents=True)
    binary = onedir / "vibemix-core"
    binary.write_bytes(b"#!/usr/bin/env python3\nprint('hi')\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

    dylib_dir = onedir / "_internal" / "av" / ".dylibs"
    dylib_dir.mkdir(parents=True)
    real_lib = dylib_dir / "libavcodec.62.11.100.dylib"
    real_lib.write_bytes(b"fake-avcodec")
    link = onedir / "_internal" / "libavcodec.62.11.100.dylib"
    link.symlink_to("av/.dylibs/libavcodec.62.11.100.dylib")

    fake_target_root = tmp_path / "tauri" / "src-tauri" / "binaries"
    monkeypatch.setattr(build_sidecar, "_TAURI_BINARIES_DIR", fake_target_root)

    build_sidecar.install_into_tauri_binaries(
        onedir, "aarch64-apple-darwin", exe_suffix=""
    )

    copied_link = (
        fake_target_root
        / "vibemix-core-aarch64-apple-darwin"
        / "_internal"
        / "libavcodec.62.11.100.dylib"
    )
    assert copied_link.is_symlink()
    assert os.readlink(copied_link) == "av/.dylibs/libavcodec.62.11.100.dylib"
    assert copied_link.exists()


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


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_collect_local_ai_runtime(spec_name: str) -> None:
    """Lazy CLAP/CUE deps must be explicit in the frozen sidecar specs."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        "_LOCAL_AI_SUBMODULES",
        "av",
        "onnxruntime",
        "onnxruntime.capi",
        "tokenizers",
        "collect_dynamic_libs",
        '"transformers"',
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"
    assert "transformers.audio_utils" not in text
    assert "transformers.models.roberta" not in text
    assert "transformers.models.detr" not in text
    assert '    "transformers.models.detr",\n' not in text
    assert '    "transformers.models.roberta",\n' not in text
    assert '"hf_xet"' in text
    assert '"hf_xet.hf_xet"' in text


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_use_slim_livekit_google_collection(spec_name: str) -> None:
    """Gemini LLM/TTS leaves are bundled without Google Cloud STT/TTS."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    dynamic_block = text.split("_DYNAMIC_PKGS = (", 1)[1].split(")", 1)[0]
    assert '"livekit.plugins.google",' not in dynamic_block
    assert '"google.cloud",' not in dynamic_block
    required = [
        "_livekit_google_slim",
        '"livekit.plugins.google.llm"',
        '"livekit.plugins.google.beta.gemini_tts"',
        '"livekit.plugins.google.stt"',
        '"livekit.plugins.google.tts"',
        '"google.cloud"',
        '"grpc"',
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_narrow_pillow_collection(spec_name: str) -> None:
    """Screen/CUE need Pillow, but frozen builds should not collect all PIL tools."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        "_PIL_MODULES",
        '"PIL.Image"',
        '"PIL.ImageFile"',
        '"PIL.ImageOps"',
        '"PIL.JpegImagePlugin"',
        '"PIL.PngImagePlugin"',
        '"PIL._imagingtk"',
        '"PIL._avif"',
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"
    assert '    "PIL",\n' not in text


def test_macos_pyinstaller_spec_excludes_livekit_demo_resources() -> None:
    """The cohost needs LiveKit FFI, not bundled ambience/Jupyter demo assets."""
    text = (PROJECT_ROOT / "vibemix-core.macos.spec").read_text(encoding="utf-8")
    required = [
        'collect_dynamic_libs("livekit")',
        'collect_data_files(\n            "livekit"',
        '"**/*.ogg"',
        '"**/jupyter-html/**"',
    ]
    for token in required:
        assert token in text, f"macOS spec missing {token}"


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_collect_sqlite_vec_extension(spec_name: str) -> None:
    """sqlite_vec.load() needs vec0.* next to the package in frozen builds."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        '_collect_runtime_submodules("sqlite_vec")',
        'collect_dynamic_libs("sqlite_vec")',
        'collect_data_files("sqlite_vec", includes=["vec0.*"])',
        "_sqlite_vec_bin_srcs",
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_filter_test_submodules(spec_name: str) -> None:
    """Frozen bundles must not force-include package test/demo trees."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        "def _runtime_submodule",
        "filter=_runtime_submodule",
        '"tests"',
        '"doc_examples"',
        '"benchmarks"',
        '"scripts"',
        '"tools"',
        # '"cli"' is intentionally NOT required: the spec keeps livekit.agents.cli,
        # a runtime import (agent_session.py). Blocking it reintroduced the frozen
        # "cannot import name 'cli'" sidecar crash. The filter targets test/demo/tool
        # trees, not this runtime CLI leaf.
        '"jupyter"',
        '"vibemix.bench"',
        '"__main__"',
        "_collect_runtime_submodules(_pkg)",
        "def _runtime_data_file",
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_exclude_transformers(spec_name: str) -> None:
    """CLAP/CUE preprocessing is local; frozen builds should exclude Transformers."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        '_ANALYSIS_EXCLUDES = [',
        '"transformers"',
        '"onnxruntime.backend"',
        '"onnxruntime.capi.convert_npz_to_onnx_adapter"',
        '"onnxruntime.datasets"',
        '"onnxruntime.transformers"',
        '"onnxruntime.tools"',
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"
    assert "_transformers_model_excludes" not in text


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_pyinstaller_specs_exclude_dev_cli_and_otlp_grpc(spec_name: str) -> None:
    """Frozen sidecars should not carry dev tools or unusable grpc exporters."""
    text = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
    required = [
        '"livekit.agents.jupyter"',
        '"telegram"',
        '"telegram.ext"',
        '"vibemix.bench.run"',
        '"jsonschema.cli"',
        '"opentelemetry.exporter.otlp.proto.grpc"',
        '"opentelemetry.exporter.otlp.proto.grpc.trace_exporter"',
        '"grpc"',
    ]
    for token in required:
        assert token in text, f"{spec_name} missing {token}"
    # livekit.agents.cli is a RUNTIME dependency (agent_session.py::start() does
    # ``from .. import cli; AgentsConsole.get_instance()`` on every session start).
    # Excluding it boot-crashed the frozen sidecar with a ModuleNotFoundError at
    # start() (2026-05-30). It must NOT be in the analysis exclude list — guard
    # against a future size-sweep re-adding it.
    excludes_body = re.search(
        r"_ANALYSIS_EXCLUDES = \[(.*?)\n\]", text, re.DOTALL
    )
    assert excludes_body is not None, f"{spec_name}: cannot locate _ANALYSIS_EXCLUDES"
    assert '"livekit.agents.cli"' not in excludes_body.group(1), (
        f"{spec_name}: livekit.agents.cli is excluded from the frozen bundle, but "
        "it is a runtime dependency of AgentSession.start(). Re-excluding it "
        "reintroduces the ModuleNotFoundError boot crash."
    )


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
