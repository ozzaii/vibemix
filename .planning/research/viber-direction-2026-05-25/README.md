# Viber Direction Research

This directory is now a pointer, not an active research source.

The original 2026-05-25 design reports were archived at
`.planning/archive/2026-05-27-stale-viber-direction-research/`.

## Why Archived

Those reports were useful pre-implementation research, but several files
predate the shipped CLAP/Codex product path. The current product path is:

- library embeddings/search/similarity: local CLAP ONNX, 512 dimensions;
- Viber/library chat and set-prep: local Codex over the grounded tool surface;
- live co-host/TTS brain: Gemini-routed via the existing model router paths;
- library UI: search, chat, curate, model setup, and Build a Set are wired
  through current CLI/Rust/TypeScript seams.

## Current References

- `docs/codex-agent.md`
- `docs/clap-engine.md`
- `docs/library.md`
- `.planning/v8.2-MILESTONE-AUDIT.md`
- `.planning/phases/v8.2-STATUS.md`
- `.planning/research/CODEX-full-product-sweep-map.md`
