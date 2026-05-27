# Architecture Research Pointer

Status: current pointer, refreshed 2026-05-27.

The previous v6.0 architecture research is archived at
`.planning/archive/2026-05-27-stale-v6-memory-research/ARCHITECTURE.md`. It
predates the local CLAP architecture and is historical.

Current architecture anchors:

- Python package: `src/vibemix/`
- Tauri shell: `tauri/src-tauri/`
- Webview UI: `tauri/ui/`
- Runtime entry point: `vibemix.__main__:main()`
- Current stack map: `.planning/codebase/STACK.md`
- Sweep/open-risk map: `.planning/research/CODEX-full-product-sweep-map.md`

Current product architecture:

- The live co-host runtime owns audio/state/prompt orchestration and preserves
  the `MusicState` single-writer invariant.
- The UI talks to the runtime through the local websocket surface at
  `127.0.0.1:8765`; debrief uses `8766`.
- Library intelligence uses Rekordbox ingest, local CLAP ONNX embeddings,
  sqlite-vec storage, and local cue/feature extraction.
- Viber set-prep/chat/build-set flows currently use the local Codex backend
  seam, not hardcoded model literals.
- Optional model assets are managed through the library models CLI/UI surfaces.

Historical section references to this file belong to the archived v6 file unless
the referencing phase has been refreshed.
