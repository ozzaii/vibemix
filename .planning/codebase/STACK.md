# Technology Stack

**Analysis Date:** 2026-05-27

This is the active orientation map for the current packaged app. Pin truth
lives in `pyproject.toml`, `uv.lock`, `tauri/ui/package-lock.json`, and
`tauri/src-tauri/Cargo.lock`.

## Languages

- **Python 3.12** (`>=3.12,<3.13`) - backend app logic under `src/vibemix/`.
- **TypeScript** - Tauri renderer under `tauri/ui/`.
- **Rust** - Tauri parent process under `tauri/src-tauri/`.
- **HTML/CSS/Canvas** - root `mascot.html` overlay.

## Runtime And Packaging

- `uv` is the Python runner and lockfile workflow.
- Hatchling builds the Python package.
- Tauri spawns the Python sidecar. In dev, use the source sidecar path; stale
  frozen sidecars can produce false negatives.
- PyInstaller builds the sidecar through `scripts/build_sidecar.py`; app builds
  should include the `ai-local` extra so local CLAP/CUE runtimes are present.

## Core Backend Dependencies

- `google-genai` - live co-host Gemini brain/TTS. Model names must resolve
  through `vibemix.llm.model_router`.
- `livekit`, `livekit-agents`, `livekit-plugins-google`, `livekit-plugins-openai`
  - live co-host pipeline and TTS fallback seam.
- `numpy` + PyAV/FFmpeg - audio decode, DSP helpers, CLAP/CUE preprocessing, and
  local resampling. The product path does not depend on SciPy, librosa,
  Transformers, or torch.
- `sounddevice` - local audio I/O.
- `mido` + `python-rtmidi` - MIDI controller input.
- `pyrekordbox==0.4.4` - Rekordbox XML import/export only; SQLCipher database
  access is intentionally unused.
- `sqlite-vec` - local vector stores for library/search and memory.
- `mcp` - Codex MCP bridge for Viber chat/curate/build-set.

## Local AI Extras

- `clap` - `onnxruntime` + `tokenizers` for local CLAP ONNX embeddings.
- `cue` - `onnxruntime` for CUE-DETR cue detection.
- `ai-local` - combined installer/dev extra for CLAP plus CUE runtimes.

The product library embedding path is local CLAP ONNX, 512-dim, under
`src/vibemix/library/clap_engine.py` and `embed_clap.py`. Gemini embeddings are
legacy/router compatibility only, not the product default.

## Frontend

- `tauri/ui/` uses TypeScript, Vite, Vitest, AJV, and Tauri JS APIs.
- Any edit to `tauri/ui/src/ipc/messages.schema.json` requires
  `npm run codegen:ipc` or `npm run check:ipc` so the precompiled validator is
  regenerated.
- Current UI contracts live in `mocks/`, especially the Deck Speaks session,
  pill hover/notch, and Viber chat mocks.

## Platform Requirements

- macOS: BlackHole 2ch, `nowplaying-cli`, PyObjC frameworks, optional MIDI
  controller.
- Windows: WASAPI loopback and Windows-specific capture/device dependencies.
- Linux is not a v1 target.

## Configuration

- `.env` may carry `GEMINI_API_KEY` for live Gemini/co-host direct mode.
  Library/Viber uses local Codex and does not need a Gemini key.
- Viber Codex defaults need `codex login`; app/Rust bridge sets
  `VIBEMIX_CODEX_ALLOW_SHELL=1` for explicit Codex tool calls.
- CLAP/CUE model caches live under `~/.cache/vibemix/`, with override env vars
  for explicit model paths where supported.
