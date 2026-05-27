# Stale v6 Memory Research Archive

Date: 2026-05-27

Archived files:

- `.planning/archive/2026-05-27-stale-v6-memory-research/SUMMARY.md`
- `.planning/archive/2026-05-27-stale-v6-memory-research/ARCHITECTURE.md`
- `.planning/archive/2026-05-27-stale-v6-memory-research/FEATURES.md`
- `.planning/archive/2026-05-27-stale-v6-memory-research/PITFALLS.md`

Reason:

- These active `.planning/research/` files were v6.0 "Memory Turn" research
  from 2026-05-22.
- They described Gemini Embedding 2 / `LibraryEmbedder` as the embedding reuse
  path and predated the current CLAP ONNX/512 product decision.
- `.planning/research/SUMMARY.md` is specifically consumed by the GSD
  roadmapper flow, so leaving stale guidance at that path creates bad plans.

Replacement:

- The original paths now contain short current pointers to the active stack,
  feature, architecture, and pitfall sources.
