# Stale Planning Notes Archive — 2026-05-26

These files were moved out of active planning surfaces during the Codex product
sweep because their guidance now conflicts with the current source truth:

- Gemini Embedding / 1536-dim folder ingest is historical. Product library
  embeddings are local CLAP ONNX/512.
- The "CLAP staged, not wired" quick plan is superseded. CLAP is now wired as
  the product embedding path.
- The old no-CLAP/Gemini-only memory-turn notes remain useful context, but they
  are unsafe as live guidance after the CLAP pivot.
- The old live-session cost-meter quick plan still claims the legacy €50 budget
  ceiling stayed green. That is superseded by the corrected Gemini audio
  embedding pricing model and the current CLAP default.

## Moved Here

- `mem0-rejected-2026-05-18.md`
- `v-next-memory-turn.md`
- `vibe-mix-concept-brief.md`
- `260525-gz2-embed-real-music-library-dim-1536-folder/`
- `260525-fuv-token-and-cost-counter-for-live-sessions/`
- `260526-i3j-stage-clap-engine/`

## Current Replacements

- Current product map: `.planning/research/CODEX-full-product-sweep-map.md`
- Current CLAP docs: `docs/clap-engine.md`
- Current library ingest spec:
  `docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md`
- Current auto-cue spec:
  `docs/superpowers/specs/2026-05-26-auto-cue-engine-design.md`
