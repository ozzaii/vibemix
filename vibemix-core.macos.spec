# SPDX-License-Identifier: Apache-2.0
# vibemix-core.macos.spec — PyInstaller --onedir spec for the macOS sidecar.
#
# [VERIFIED: PyInstaller Context7 /pyinstaller/pyinstaller]
# [VERIFIED: 11-RESEARCH.md §Pitfall 2 — hidden-import misses]
# [VERIFIED: 11-RESEARCH.md §Pitfall 5 — AIza key leak]
#
# Phase 11 Wave 1 — produces ``dist/vibemix-core/vibemix-core`` (no extension
# on macOS). ``scripts/build_sidecar.py`` then renames + moves the bundle
# into ``tauri/src-tauri/binaries/vibemix-core-<rustc target triple>/``
# with the inner binary suffixed by the target triple — that's what Tauri's
# ``externalBin`` configuration expects (RESEARCH Pitfall 4).
#
# NEVER set ``--onefile`` or ``upx=True`` (RESEARCH Pitfall 1: AV / Defender
# false positives). NEVER set ``console=True`` (Tauri spawns this headless;
# we don't want a stray terminal window during normal user runs).
#
# Run via: ``uv run pyinstaller vibemix-core.macos.spec --clean --noconfirm``.

# ruff: noqa: E402, F821  # PyInstaller injects Analysis / PYZ / EXE / COLLECT at
# spec-file exec time; the linter doesn't know about them.

import sys
from pathlib import Path

_PROJECT_ROOT = Path(globals().get("SPECPATH", Path.cwd())).resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)
from scripts.dist.chatterbox_bundle import collect_chatterbox_ref_datas

block_cipher = None

# ---------------------------------------------------------------------------
# Hidden imports — packages whose ``__import__`` is dynamic and therefore
# invisible to PyInstaller's AST walker (RESEARCH Pitfall 2).
# ---------------------------------------------------------------------------

hiddenimports: list[str] = []
binaries: list[tuple[str, str]] = []
datas: list[tuple[str, str]] = []


def _runtime_submodule(name: str) -> bool:
    """Exclude package test/demo/tool trees from frozen hiddenimports."""
    parts = name.split(".")
    blocked = {
        "__main__",
        "tests",
        "testing",
        "doc_examples",
        "benchmarks",
        "benchmark",
        "examples",
        "scripts",
        "tools",
        "jupyter",
        # NOTE: a bare three-letter command-line-interface part name used to
        # live here, but the livekit.agents leaf with that same name is a
        # runtime requirement — livekit/agents/voice/agent_session.py does
        # ``from .. import <that-name>``, and excluding the leaf made the
        # frozen bundle boot-crash with ``ImportError: cannot import name
        # ... from partially initialized module 'livekit.agents'`` (circular).
        # Removed 2026-05-27 (rc1 ship-blocker fix). If a specific package's
        # subtree ever needs to be excluded, do it by full module name in the
        # explicit blocks below — not by part-name match. Regression-guarded
        # by tests/dist/test_spec_blocklist_keeps_livekit_cli.py.
    }
    if any(part in blocked for part in parts):
        return False
    if name == "vibemix.bench" or name.startswith("vibemix.bench."):
        return False
    if name.startswith(
        (
            "onnxruntime.backend",
            "onnxruntime.capi.convert_npz_to_onnx_adapter",
            "onnxruntime.datasets",
            "onnxruntime.tools",
            "onnxruntime.transformers",
            "onnxruntime.quantization",
        )
    ):
        return False
    return not any(
        part.startswith(("test_", "_test", "_tst"))
        or part.endswith(("_test", "_tests", "_testutils", "_tstutils"))
        for part in parts
    )


def _collect_runtime_submodules(package: str) -> list[str]:
    return collect_submodules(package, filter=_runtime_submodule)


def _runtime_data_file(item: tuple[str, str]) -> bool:
    """Drop packaged test/benchmark/example data that hooks add as files."""
    src, dest = item
    parts = Path(dest.replace("\\", "/")).parts + Path(src.replace("\\", "/")).parts
    blocked = {"tests", "testing", "benchmarks", "benchmark", "examples"}
    return not any(part in blocked for part in parts)


# Third-party deps with dynamic dispatch / plugin discovery.
_DYNAMIC_PKGS = (
    "sounddevice",
    "mido",
    "rtmidi",
    "livekit",
    "livekit.agents",
    "livekit.plugins.openai",
    "google.genai",
    "mss",
    "jsonschema",
)
for _pkg in _DYNAMIC_PKGS:
    try:
        hiddenimports.extend(_collect_runtime_submodules(_pkg))
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)

# VibeMix uses LiveKit's Gemini LLM leaf only. Product speech is local Chatterbox; the
# package initializer eagerly imports Google Cloud STT/TTS; keep the frozen
# hiddenimports to the exact leaves used by vibemix.agent._livekit_google_slim.
hiddenimports.extend(
    [
        "livekit.plugins.google",
        "livekit.plugins.google.llm",
        "livekit.plugins.google.log",
        "livekit.plugins.google.models",
        "livekit.plugins.google.tools",
        "livekit.plugins.google.utils",
        "livekit.plugins.google.version",
    ]
)

# Local AI + watcher runtime deps. These are lazy-imported by CLAP/CUE/Chatterbox
# voice and freshness-watcher paths, so PyInstaller can miss native libs/submodules.
# The build script runs `uv run --extra ai-local ...`; this block makes sure the
# installed runtime actually lands in the frozen sidecar.
_LOCAL_AI_SUBMODULES = (
    "av",
    "hf_xet",
    "huggingface_hub",
    "miniaudio",
    "mlx",
    "mlx_audio",
    "mlx_lm",
    "onnxruntime",
    "onnxruntime.capi",
    "scipy",
    "sentencepiece",
    "tokenizers",
    "tqdm",
    "transformers",
    "watchfiles",
)

# Pillow is needed for screen JPEG capture and the DETR image preprocessor, but
# collecting all PIL submodules pulls unused UI/tool plugins. Keep only the
# runtime image core + JPEG/PNG plugin modules used by capture/save paths.
_PIL_MODULES = (
    "PIL.Image",
    "PIL.ImageFile",
    "PIL.ImageMode",
    "PIL.ImageOps",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
)
hiddenimports.extend(_PIL_MODULES)
for _pkg in _LOCAL_AI_SUBMODULES:
    try:
        hiddenimports.extend(_collect_runtime_submodules(_pkg))
    except Exception as exc:  # pragma: no cover — optional local-AI dep drift
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)
for _pkg in (
    "av",
    "hf_xet",
    "miniaudio",
    "mlx",
    "mlx_audio",
    "mlx_lm",
    "onnxruntime",
    "sentencepiece",
    "watchfiles",
):
    try:
        binaries.extend(collect_dynamic_libs(_pkg))
    except Exception as exc:  # pragma: no cover — native-lib packaging drift
        print(f"[spec] collect_dynamic_libs({_pkg!r}) skipped: {exc}", file=sys.stderr)

# sqlite-vec loads its extension at runtime via sqlite_vec.loadable_path(), so
# the vec0 native library must sit next to sqlite_vec/__init__.py in the frozen
# bundle. If it is missing, packaged apps silently fall back to NumpyStore.
try:
    hiddenimports.extend(_collect_runtime_submodules("sqlite_vec"))
    _sqlite_vec_bins = collect_dynamic_libs("sqlite_vec")
    binaries.extend(_sqlite_vec_bins)
    _sqlite_vec_bin_srcs = {Path(src).resolve() for src, _ in _sqlite_vec_bins}
    datas.extend(
        (src, dest)
        for src, dest in collect_data_files("sqlite_vec", includes=["vec0.*"])
        if Path(src).resolve() not in _sqlite_vec_bin_srcs
    )
except Exception as exc:  # pragma: no cover — native extension packaging drift
    print(f"[spec] sqlite_vec extension collection skipped: {exc}", file=sys.stderr)

# livekit ships a native FFI lib (livekit/rtc/resources/liblivekit_ffi.dylib)
# plus non-.py resources under livekit/{rtc,agents}/resources. collect_submodules
# above only grabs .py modules, so the frozen sidecar ImportErrors at
# AgentSession.start() ("failed to load liblivekit_ffi.dylib ... not found when
# the application was frozen"). collect_dynamic_libs walks the package for
# .dylib/.so and preserves their package-relative dest paths; collect_data_files
# keeps the lightweight non-demo resource siblings. 2026-05-20: this is what
# unblocks the .app's LiveKit cohost from booting at all.
try:
    binaries.extend(collect_dynamic_libs("livekit"))
    datas.extend(
        collect_data_files(
            "livekit",
            includes=["**/resources/**"],
            excludes=[
                "**/*.ogg",  # built-in background-audio demo clips; VibeMix does not call them
                "**/jupyter-html/**",
            ],
        )
    )
except Exception as exc:  # pragma: no cover — defensive
    print(f"[spec] livekit native-lib collection skipped: {exc}", file=sys.stderr)

# vibemix sub-packages — explicit so PyInstaller picks up every Phase 2-10
# leaf module (cohost*.py POC files are intentionally NOT bundled).
for _pkg in (
    "vibemix",
    "vibemix.agent",
    "vibemix.audio",
    "vibemix.midi",
    "vibemix.platform",
    "vibemix.prompts",
    "vibemix.runtime",
    "vibemix.state",
    "vibemix.ui_bus",
):
    try:
        hiddenimports.extend(_collect_runtime_submodules(_pkg))
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)

# pyobjc frameworks — ``collect_all`` returns (binaries, datas, hiddenimports)
# Try each individually; some frameworks may not be present on every macOS
# version. Graceful degradation per RESEARCH Pitfall 2.
_PYOBJC_FRAMEWORKS = (
    "ScreenCaptureKit",
    "Quartz",
    "Cocoa",
    "AVFoundation",
    "CoreAudio",
)
for _fw in _PYOBJC_FRAMEWORKS:
    try:
        b, d, h = collect_all(f"pyobjc.framework.{_fw}")
        binaries.extend(b)
        datas.extend(d)
        hiddenimports.extend(h)
    except Exception as exc:  # pragma: no cover — graceful per Pitfall 2
        print(f"[spec] collect_all(pyobjc.framework.{_fw}) skipped: {exc}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Data files — JSON profiles, prompts, IPC schema. Explicitly excludes
# secrets-bearing patterns (RESEARCH Pitfall 5 — API key leak gate).
# ---------------------------------------------------------------------------

datas += collect_data_files(
    "vibemix",
    includes=["**/*.json", "**/*.txt", "**/*.wav"],
    excludes=["*.env", ".env*", "*credentials*", "*.key", "*.pem"],
)

# The ipc messages schema lives outside the package tree (under tauri/ui/);
# include it explicitly so vibemix.ui_bus can locate it inside the bundle.
_IPC_SCHEMA = Path("tauri/ui/src/ipc/messages.schema.json")
if not _IPC_SCHEMA.exists():
    raise RuntimeError(
        f"vibemix-core.macos.spec: expected IPC schema at {_IPC_SCHEMA} — "
        "Phase 11 Wave 0 should have created it."
    )
datas += [(str(_IPC_SCHEMA), "tauri/ui/src/ipc")]

# Phase 9 controller profiles (10 JSONs) — already picked up by
# ``collect_data_files('vibemix', includes=['**/*.json'])`` above, but list
# them explicitly so a missing-file regression fails the build loudly.
_MIDI_PROFILES = Path("src/vibemix/midi/profiles")
if not _MIDI_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.macos.spec: missing {_MIDI_PROFILES}")

# Phase 6 genre profiles (5 JSONs) — same defensive check.
_GENRE_PROFILES = Path("src/vibemix/state/genre/profiles")
if not _GENRE_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.macos.spec: missing {_GENRE_PROFILES}")

datas = [item for item in datas if _runtime_data_file(item)]
datas.extend(collect_chatterbox_ref_datas())

_ANALYSIS_EXCLUDES = [
    "tkinter",
    "matplotlib",
    "IPython",
    "pytest",
    "ruff",
    "black",
    "pyinstaller",
    "onnxruntime.backend",
    "onnxruntime.capi.convert_npz_to_onnx_adapter",
    "onnxruntime.datasets",
    "onnxruntime.tools",
    "onnxruntime.transformers",
    "onnxruntime.quantization",
    "mido.scripts",
    "numba.scripts",
    "tokenizers.tools",
    "telegram",
    "telegram.ext",
    "vibemix.bench",
    "vibemix.bench.assemble",
    "vibemix.bench.cell",
    "vibemix.bench.eval",
    "vibemix.bench.fixtures",
    "vibemix.bench.matrix",
    "vibemix.bench.review",
    "vibemix.bench.run",
    # NOTE: livekit.agents.cli is NOT excluded — it is a RUNTIME dependency, not
    # a dev CLI. ``livekit/agents/voice/agent_session.py::start()`` unconditionally
    # does ``from .. import cli; AgentsConsole.get_instance()`` to read console-mode
    # state on EVERY session start. Excluding it boot-crashed the frozen sidecar
    # with ``ModuleNotFoundError: No module named 'livekit.agents.cli'`` at start()
    # (verified 2026-05-30 on the real onedir bundle). The import-TIME circular
    # ImportError is handled separately by the lazy-cli patch in
    # scripts/dist/patch_livekit_agents_init.py. Do NOT re-exclude cli.
    "livekit.agents.jupyter",
    "livekit.plugins.google.realtime",
    "livekit.plugins.google.stt",
    "livekit.plugins.google.tts",
    "google.genai._test_api_client",
    "google.cloud",
    "google.cloud.speech",
    "google.cloud.speech_v1",
    "google.cloud.speech_v1p1beta1",
    "google.cloud.speech_v2",
    "google.cloud.texttospeech",
    "google.cloud.texttospeech_v1",
    "google.cloud.texttospeech_v1beta1",
    "grpc",
    "PIL.ImageTk",
    "PIL._imagingtk",
    "PIL._imagingft",
    "PIL._imagingmorph",
    "PIL._avif",
    "PIL.__main__",
    "jsonschema.__main__",
    "jsonschema.cli",
    "opentelemetry.exporter.otlp.proto.grpc",
    "opentelemetry.exporter.otlp.proto.grpc._log_exporter",
    "opentelemetry.exporter.otlp.proto.grpc.exporter",
    "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
]

# ---------------------------------------------------------------------------
# Binaries — bundled native executables.
# ---------------------------------------------------------------------------

# nowplaying-cli is required by ``vibemix.platform._track_macos`` (Phase 3)
# to poll the macOS NowPlaying framework. Apple Silicon brew lives under
# /opt/homebrew/bin/; Intel Macs land at /usr/local/bin/. Either is fine.
_NOWPLAYING_CANDIDATES = (
    Path("/opt/homebrew/bin/nowplaying-cli"),  # Apple Silicon
    Path("/usr/local/bin/nowplaying-cli"),  # Intel Mac fallback
)
_nowplaying = next((p for p in _NOWPLAYING_CANDIDATES if p.exists()), None)
if _nowplaying is None:
    raise RuntimeError(
        "vibemix-core.macos.spec: nowplaying-cli not found at /opt/homebrew/bin/ or "
        "/usr/local/bin/. Install via: `brew install nowplaying-cli` "
        "(documented in CLAUDE.md Platform Requirements)."
    )
binaries += [(str(_nowplaying), ".")]

# ---------------------------------------------------------------------------
# Analysis — entry-point script + paths + excludes.
# ---------------------------------------------------------------------------

a = Analysis(
    ["src/vibemix/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthooks/pyi_rth_livekit_agents.py"],
    # Exclude dev / test tooling so they never accidentally land in the
    # shipping bundle. ``pyinstaller`` itself is in dev deps; explicit
    # exclude blocks recursive bundling.
    excludes=_ANALYSIS_EXCLUDES,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vibemix-core",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # NEVER True — AV false positives (RESEARCH Pitfall 1)
    console=False,  # Tauri spawns headless; no stray terminal
    disable_windowed_traceback=False,
    target_arch=None,  # PyInstaller auto-detects host arch
    codesign_identity=None,  # Phase 18 signs the entire bundle
    entitlements_file=None,  # see tauri/src-tauri/entitlements.plist
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vibemix-core",  # produces dist/vibemix-core/
)
