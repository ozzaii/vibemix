---
phase: quick-260526-i3j
plan: 01
subsystem: library
tags: [clap, embedding, on-device, staging]
requires: []
provides:
  - "ClapEngine — import-safe local CLAP 512-dim embedder (audio + text)"
  - "docs/clap-engine.md — engine spec, evidence, ONNX ship path, parity gate, wiring map"
affects:
  - "future embedding-swap phase (the seam to plug into; not wired yet)"
tech-stack:
  added: []  # NO pyproject change — torch/torchaudio/laion_clap/onnxruntime stay out of the bundle
  patterns:
    - "lazy heavy-import inside methods (telegram_bridge.py convention) → CI/bundle import-safe"
    - "backend seam via env (VIBEMIX_CLAP_BACKEND) with NotImplementedError stub for the un-gated path"
key-files:
  created:
    - src/vibemix/library/clap_engine.py
    - docs/clap-engine.md
  modified: []
decisions:
  - "onnx backend is a NotImplementedError stub until the parity gate passes — never a silent wrong vector"
  - "empty-chunk guard raises ValueError, not a faked zero vector (trust-the-audio / no-slop)"
metrics:
  duration: "~10 min"
  completed: 2026-05-26
---

# Phase quick-260526-i3j Plan 01: Stage CLAP engine Summary

Staged the local on-device CLAP audio/text embedder as a new import-safe module
(`ClapEngine`) plus a full spec doc — staging + docs only, NOT the 14-file
embedding swap.

## What shipped

**Task 1 — `src/vibemix/library/clap_engine.py` (284 lines, commit `d640b94`)**
- `ClapEngine` class porting the proven deterministic pipeline from
  `bravoh-gpu-worker/clap_mix_only.py` byte-for-byte: load → mono → resample 48k
  → 10s non-overlapping chunks (≤10s zero-pad single-chunk branch; trailing
  remainder ≥5s kept) → per-chunk L2 → mean-pool → re-L2 → `(512,)` float32.
- Constants ported verbatim: `CLAP_SR=48000`, `CHUNK_SAMPLES=480000`,
  `CHUNK_BATCH=128`, `CLAP_DIM=512`.
- Heavy deps (`torch`, `torchaudio`, `laion_clap`, `onnxruntime`) lazy-imported
  inside `_ensure_model` / `_load_and_chunk` only — module top level pulls only
  numpy + stdlib + `__future__` (telegram_bridge.py convention).
- `_ensure_model` applies the two MANDATORY monkeypatches (torch.load
  `weights_only=False`; `load_state_dict` `strict=False`), loads
  `CLAP_Module(enable_fusion=True, amodel='HTSAT-tiny', device='cpu')` +
  `load_ckpt(model_id=3)`, RESTORES both originals in a `finally`, caches on
  `self._model` (warm reuse, never reloaded per call).
- Public contract mirrors a future `ClapEmbedder` 1:1: `embed_audio_file`,
  `embed_audio_bytes` (tempfile + MIME→suffix map, cleaned up), `embed_query`
  (CLAP text encoder, same 512-dim space).
- Backend seam: `VIBEMIX_CLAP_BACKEND` (default `torch`). `onnx` is a
  `NotImplementedError` stub pointing at the parity gate — never a silent wrong
  vector. Empty-chunk guard raises `ValueError` — never a faked zero vector.

**Task 2 — `docs/clap-engine.md` (145 lines, commit `5cea087`)**
- Five sections + STAGED-not-wired status banner: what-it-is + pipeline (why
  10s-chunk = deterministic); the 99-track reliability evidence (cos=1.000000
  determinism, 100% top-10 genre separation, honest calibration, 2.21 s/track);
  the on-device ONNX ship path + upload-vs-download rationale; THE parity gate
  (laion_clap 630k + torchlibrosa mel vs HF larger_clap_music + numpy Slaney
  mel can silently shift vectors; ≥0.98 mean cosine over 50 tracks, fallback to
  manual export of the 630k checkpoint); the future wiring change-map
  (`EMBEDDING_DIM` 1536→512 at `_cosine.py:56`, `ClapEmbedder`, the
  `grounding.py:120-126` `_client` coupling, cache rebuild, dispatch seam,
  tests to update).

## Verification

- **Load-bearing acceptance — PASSED:** `import vibemix.library.clap_engine`
  succeeds with NO `laion_clap`/`torch`/`torchaudio`/`onnxruntime` installed
  (all four confirmed absent in the dev `.venv`). Constants + the three-method
  contract assert clean.
- `VIBEMIX_CLAP_BACKEND=onnx` → `_ensure_model()` raises `NotImplementedError`
  mentioning the parity gate (no silent vector). PASSED.
- `pyproject.toml` + `uv.lock` unchanged (git diff empty). No heavy dep added.
- Doc-section grep gate (parity / 512 / onnx / 1.000000 / `_cosine.py`) PASSED.
- `pytest -q tests/library -x` → **261 passed, 1 xfailed** (the pre-existing
  budget-cost decision gate, unrelated) — no import/collection regression.

## Deviations from Plan

None — plan executed exactly as written. The two commits are code/doc only;
SUMMARY/STATE/PLAN docs are left for the orchestrator's docs commit.

## Self-Check: PASSED

- FOUND: `src/vibemix/library/clap_engine.py` (284 lines ≥ 120 min)
- FOUND: `docs/clap-engine.md` (145 lines ≥ 60 min)
- FOUND commit: `d640b94` (Task 1)
- FOUND commit: `5cea087` (Task 2)
- `pyproject.toml` / `uv.lock` unchanged (diff empty)
