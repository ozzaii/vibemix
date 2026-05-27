# Archive Index

This directory holds cleanup artifacts from the 2026-05-26 Codex product sweep.
Each subdirectory has its own manifest; local `.zip` bundles are intentionally
ignored by `.gitignore`.

## Batches

- `2026-05-26-research-sweep/` — archived untracked scratch research notes that
  are no longer the active implementation map.
- `2026-05-26-surface-clutter/` — archived root/top-level clutter such as the old
  CDJ Whisper handoff and live debrief screenshot.
- `2026-05-26-generated-output/` — recorded generated-output cleanup; root
  PyInstaller `build/` was deleted as reproducible ignored output.
- `2026-05-26-eval-run-json/` — archived stale ignored flat load-test JSON files
  out of `.planning/eval-runs/` while preserving `.gitkeep`.
- `2026-05-26-stale-handoffs/` — archived handoff/spec docs whose wording
  conflicted with current source truth; active replacement specs remain at the
  original referenced paths.
- `2026-05-26-stale-planning-notes/` — archived active notes/quick plans whose
  old Gemini-only, 1536-dim, or "CLAP staged" guidance conflicts with the
  current CLAP/Codex product split.
- `2026-05-27-v2.1-phase-detail/` — archived the expanded v2.1 phase-detail
  tree because it is historical and contains retired Gemini Embedding 2,
  Gemini-only/no-CLAP, budget, and installer guidance. A tiny pointer README
  remains at `.planning/milestones/v2.1-phases/`.
- `2026-05-27-stale-stack-research/` — archived the old
  `.planning/research/STACK.md` v6 memory-stack research because it treated
  Gemini Embedding 2 and Gemini-only/no-CLAP library embeddings as current
  guidance. A small current pointer remains at `.planning/research/STACK.md`.
- `2026-05-27-stale-v6-memory-research/` — archived the old active
  `.planning/research/{SUMMARY,ARCHITECTURE,FEATURES,PITFALLS}.md` v6 memory
  suite because those files are GSD/roadmapper inputs and still pointed agents
  at Gemini Embedding 2 / `LibraryEmbedder` instead of CLAP ONNX/512.
- `2026-05-27-stale-clap-deep-dive/` — archived the old
  `.planning/research/clap-engine-deep-dive.md` body because it described a
  server-side `laion_clap` worker and staged Gemini 1536-dim CLAP migration.
  A current pointer remains at the original path.
- `2026-05-27-stale-viber-direction-research/` — archived the old
  `.planning/research/viber-direction-2026-05-25/` design reports because they
  still mixed Gemini Embedding 2, Gemini-only/no-CLAP, staged CLAP, and early
  Codex/Viber assumptions into active-looking research. A pointer README remains
  in the original directory.
- `2026-05-27-root-archived-research/` — moved root-level
  `.planning/research/*-archived.md` files into the archive tree so active
  research searches no longer pick up stale v3.1/v5.0 guidance.
- `2026-05-27-stale-v2-v3-research/` — archived milestone-era `v2-1/`,
  `v2-buckets/`, `v3-buckets/`, and `v3-shipped/` research directories. Pointer
  READMEs remain at the original paths, while live references now resolve to
  the archived copies explicitly.
- `2026-05-27-stale-dated-research/` — archived remaining 2026-05-25 dated
  CLAP spike, frontend critique, and OSS-launch research folders. Pointer
  READMEs remain at the original paths.

## Active Map

The current source-of-truth sweep map is
`.planning/research/CODEX-full-product-sweep-map.md`.
