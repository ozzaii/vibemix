# Stale Handoffs Archive — 2026-05-26

This archive holds handoff notes that are useful history but no longer active
product truth.

## Contents

- `2026-05-26-auto-cue-engine-HANDOFF.md` — auto-cue research/pivot handoff
  that still described the work as "mid-pivot" and "Nothing committed."
  Current source and the sweep map now describe CUE-DETR ONNX as the primary
  cue producer with deterministic local refinement and heuristic fallback.
- `2026-05-26-auto-cue-engine-design.original.md` — original auto-cue design
  spec that still described the client engine as a not-yet-built pure-DSP
  upgrade. The active spec at the original path has been replaced with current
  source truth.
- `2026-05-26-dj-library-ingest-design.original.md` — original ingest design
  spec that still described Rekordbox ingest as future GSD work with staged CLAP
  and untouched cue seams. The active spec at the original path now documents
  the shipped Rekordbox MVP ingest path.

## Active Sources Kept

- `docs/superpowers/specs/2026-05-26-auto-cue-engine-design.md` stays active as
  the current product spec for `cue_engine.detect_cues_auto()`.
- `docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md` stays active
  as the current product spec for `library ingest`.
- `.planning/research/CODEX-full-product-sweep-map.md` remains the current
  implementation/status map.
