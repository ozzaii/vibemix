---
phase: 64-session-ingest
plan: 01
subsystem: testing
tags: [pytest, tdd, red-first, ingest, coach_line, signature, no-live-path, dormancy, no-extraction, idempotency, path-traversal]

# Dependency graph
requires:
  - phase: 63-memory-store
    provides: MemoryStore.add_record / query_topk / delete_session + Record shape (the write target the contract rounds-trips against) + the no-live-path / no-extraction gates that auto-cover memory/*.py
  - phase: 28-library-index
    provides: cosine_topk / l2_normalize / EMBEDDING_DIM chokepoint + the _vec(seed) deterministic-vector test helper cloned here
provides:
  - tests/memory/test_ingest.py — the full Wave-0 RED-first contract for vibemix.memory.ingest (6 tests + in-test synthetic events.jsonl fixture)
  - build_coach_line_signature / ingest_session / run_ingest_sweep / SIG_TEMPLATE_VERSION interface pinned (the identifiers 64-02 implements verbatim)
  - IngestResult shape pinned (.records_written + .embeds_made) for the 0-cost re-ingest assertion
  - subprocess runtime-dormancy gate extended to import vibemix.memory.ingest (closes the PATTERNS gap; T-64-02 mitigation)
affects: [64-02, 64-03, session-ingest, retrieve, copilot]

# Tech tracking
tech-stack:
  added: []  # ZERO net-new deps — pytest only; no install step (RESEARCH §Package Legitimacy Audit)
  patterns:
    - "RED-first TDD contract: tests target the unbuilt vibemix.memory.ingest module; collection ModuleNotFoundError IS the pinned contract, not a defect"
    - "In-test synthetic events.jsonl fixture mirroring real on-disk shapes (event/ai_text/citation_strip) — no repo fixture file"
    - "FakeEmbedder exposes ONLY embed_query with a call counter — no generation surface, honors the no-extraction invariant by construction"
    - "Subprocess sys.modules dormancy parity: clone the store-side leak-scan block, swap store->ingest"

# Key files
key-files:
  created:
    - tests/memory/test_ingest.py
  modified:
    - tests/memory/test_no_live_path_import.py

# Decisions
decisions:
  - "citation_strip-skip assertion lives inside test_ingest_emits_coach_lines (per VALIDATION) — asserts the silenced line's fabricated content never reaches memory (anti-confabulation)"
  - "test_embed_cache_hit pins the byte-identical-signature cache-key precondition at the FakeEmbedder boundary; the end-to-end 0-call invariant is verified in test_reingest_is_noop (the marker short-circuit)"
  - "Synthetic fixture uses a real-corpus track string + [chill] emotion tags + one [aud:rms@96.0] inline citation + one citation-free [chill] line (legit empty cite=) + one citation_strip line"

# Metrics
metrics:
  tasks: 2
  files_created: 1
  files_modified: 1
  duration_minutes: ~14
  completed: 2026-05-22
---

# Phase 64 Plan 01: Session-Ingest RED Contract Summary

**One-liner:** The Wave-0 RED-first test contract for `vibemix.memory.ingest` — 6 tests pinning the deterministic `coach_line` signature, emitted-only ingest (skip `citation_strip`), idempotent zero-cost re-ingest, record tagging, the signature-keyed embed-cache hit, and the executor sweep with path-traversal defense, plus an in-test synthetic `events.jsonl` fixture — and a parallel subprocess dormancy assertion for `import vibemix.memory.ingest` that closes the PATTERNS gap. Both edges are intentionally RED until 64-02 lands the module.

## What Was Built

- **`tests/memory/test_ingest.py`** (new) — clones the `test_store.py` shape: the `_vec(seed)` deterministic-vector helper, `tmp_path` fixture, `prefer_sqlite_vec=False` numpy store path. Imports the RED edge `from vibemix.memory.ingest import build_coach_line_signature, ingest_session, run_ingest_sweep, SIG_TEMPLATE_VERSION` (raises `ModuleNotFoundError` until 64-02). A `_FakeEmbedder` stub exposes only `embed_query` with a call counter. A `_write_session()` helper generates a synthetic `events.jsonl` in-test mirroring the real on-disk shapes (two `event` lines with `type/track/phase/deck`, two emitted `ai_text` lines with a leading `[chill]` tag — one with an inline `[aud:rms@96.0]` citation, one citation-free — and one `citation_strip` line that must be skipped). The 6 named tests cover signature determinism, coach_line emission (+ citation_strip skip), idempotent re-ingest, record tagging, embed-cache hit, and the executor sweep + traversal-dir rejection.
- **`tests/memory/test_no_live_path_import.py`** (modified) — added `test_importing_ingest_loads_no_coach_loop`, a verbatim clone of the store-side subprocess dormancy block with the import line swapped to `import vibemix.memory.ingest` and the same leak predicate (`vibemix.state.coach` / `state.refresh` / `agent` / `prompts` / `ws_bus`) + the same `assert result.stdout.strip() == "CLEAN"` contract. Closes the gap where the subprocess gate previously only imported `vibemix.memory.store` (the static AST gate already auto-covered `ingest.py` via the `memory/*.py` glob — not duplicated here).

## Verification

Run under `.venv` / Python 3.12 (the authoritative runner; system Python 3.14 masks an unrelated import gap):

```
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory -p no:cacheprovider
```

- `test_ingest.py` → collection `ModuleNotFoundError: No module named 'vibemix.memory.ingest'` (the pinned RED edge — correct for Wave 0).
- `test_no_live_path_import.py` → `test_importing_ingest_loads_no_coach_loop` RED (subprocess import fails, stdout `''` != `'CLEAN'`); the existing `test_importing_memory_loads_no_coach_loop` + the static AST gate stay GREEN.
- Rest of `tests/memory` (excluding the RED ingest module): **21 passed, 1 failed** — the 1 failure is exactly the intentional ingest-dormancy RED. No NEW collateral failures.

Acceptance-criteria greps: 6 test functions present; the `from vibemix.memory.ingest import` RED edge present; `citation_strip` skip assertion present; 2 dormancy functions; `import vibemix.memory.ingest` present; 2× `CLEAN` assertions.

## Deviations from Plan

None — plan executed exactly as written. Reworded one `_FakeEmbedder` docstring line to avoid embedding the literal forbidden generation tokens in prose (cosmetic; the no-extraction gate scans `src/vibemix/memory/*.py`, not `tests/`, so it was never at risk — defensive only).

## Authentication Gates

None.

## Known Stubs

None — this plan ships test code only. The intentional RED state (missing `vibemix.memory.ingest`) is the deliverable, not a stub; 64-02 flips it GREEN.

## Notes for 64-02

- The pinned `IngestResult` must expose `.records_written` (int) and `.embeds_made` (int).
- `build_coach_line_signature(reaction_text, ctx)` fallbacks: `track→unknown`, `phase→unknown`, `deck→none`, `event→MANUAL`; citation tokens sorted+joined `,`; leading `[emotion]` tag stripped; NO `t` in the embedded string. `SIG_TEMPLATE_VERSION == "v1-coach_line"`.
- `run_ingest_sweep(recordings_root, store, embedder)` must skip dir names failing `SESSION_DIR_RE` (e.g. `not-a-session`) and never read them.
- Idempotency: a second `ingest_session` on a marked session = 0 embed calls + 0 new records (the test asserts at the FakeEmbedder counter and via store record count).
- **Invariant (from P63 STATE):** any `config_store` / `vibemix.runtime` import in `ingest.py` MUST be function-local — a module-level pull trips the dormancy gate this plan just extended.

## Self-Check: PASSED

- `tests/memory/test_ingest.py` — FOUND
- `tests/memory/test_no_live_path_import.py` — FOUND
- `.planning/phases/64-session-ingest/64-01-SUMMARY.md` — FOUND
- commit `dcdc307` (test_ingest.py) — FOUND
- commit `1cb9008` (dormancy gate extension) — FOUND
