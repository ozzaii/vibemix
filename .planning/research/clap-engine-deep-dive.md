# CLAP Engine Deep Dive

This file is now a pointer, not the active implementation spec.

The original 2026-05-26 research deep dive has been archived at
`.planning/archive/2026-05-27-stale-clap-deep-dive/clap-engine-deep-dive.md`.
It predates the shipped local ONNX path and is historical context only.

## Current Product Truth

- Library embeddings/search/similarity use local CLAP ONNX, 512 dimensions.
- The installable CLAP snapshot is `Xenova/larger_clap_music_and_speech`, pinned
  and checksum-verified by `src/vibemix/library/model_assets.py`.
- Full-precision ONNX is the default. fp16/q8 are future installer variants only
  after real-library parity proves no retrieval regression.
- Cloud embedding code is not a library fallback. Historical embedding code
  remains only for legacy migration/parity tests.
- Viber/library chat and set-prep use local Codex plus the grounded library tool
  surface for the current demo/test path.

## Active References

- `docs/clap-engine.md`
- `src/vibemix/library/clap_engine.py`
- `src/vibemix/library/embed_clap.py`
- `src/vibemix/library/model_assets.py`
- `.planning/research/CODEX-full-product-sweep-map.md`
