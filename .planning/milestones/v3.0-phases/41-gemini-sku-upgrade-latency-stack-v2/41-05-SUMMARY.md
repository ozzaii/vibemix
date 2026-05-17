---
phase: 41
plan: 41-05
title: Embedding 2 GA probe + auto-bump + 768-dim parity + migration script
status: complete
shipped: 2026-05-16
req_ids: [LAT-06]
---

# Plan 41-05 — Embedding 2 GA probe + parity test + migration script

**Status:** GREEN. Tests: 18/18 pass (13 GA-probe + 5 parity).

## What shipped

**LAT-06 closure surface:**

1. **GA-rename auto-bump probe** — `_probe_ga_model_id()` in `src/vibemix/library/embed.py` (lines ~155-260). On `LibraryEmbedder` startup, the probe tries the candidates in `vibemix.llm._router_config.EMBEDDING_GA_CANDIDATES` (order: GA-renamed first, legacy second) and locks the first one that returns a valid embedding for a canary text. If the GA-renamed id wins, `EXCERPT_STRATEGY_VERSION` bumps to `EXCERPT_STRATEGY_VERSION_GA_RENAME` so cache keys invalidate cleanly. If the legacy id stays in service, existing cache rows continue hitting.

2. **768-dim MRL parity test** — `tests/library/test_embeddings_parity.py` (5 tests) pins:
   - Top-K retrieval order stable across 3 sequential embed calls on identical text.
   - 768-dim truncation preserves cosine ordering vs hypothetical 2048-dim full vectors (mocked, no real spend).
   - Cache-key consistency: same text + same model_id + same EXCERPT_STRATEGY_VERSION → same SHA256 cache key.
   - **EMBEDDING_DIM = 768 locked** (escalation to 1024 NOT triggered — parity holds at 768).

3. **Migration script** — `scripts/library/migrate_embeddings_2.py`:
   - `--audit` mode: walks `~/.cache/vibemix/embeddings.db`, reports current model_id + EXCERPT_STRATEGY_VERSION + row count + average vector dim. No writes.
   - `--dry-run` mode: identifies rows that would be re-embedded under the current locked shape (mismatched model_id or version). Reports count + sample. No writes.
   - `--re-embed-all` mode: re-embeds every row under the current locked shape. Idempotent (no-op if everything already matches).

4. **Grep-gate relocation (this commit / merge-resolution fixup):** Moved the GA candidates literal `("gemini-embedding-002", "gemini-embedding-2")` from `src/vibemix/library/embed.py` to `src/vibemix/llm/_router_config.EMBEDDING_GA_CANDIDATES` (the only allowlisted file). `library/embed.py` now imports + re-exports as `GEMINI_EMBEDDING_MODEL_GA_CANDIDATES`. Probe comparison uses `candidate == GEMINI_EMBEDDING_MODEL_GA_CANDIDATES[0]` (positional) rather than the literal string. Docstrings rewritten to reference the candidate tuple by name. `scripts/release/check_no_hardcoded_model.sh` now passes clean.

## Commits

- `ef43ddd` — test(41-05): add failing tests for Embedding 2 GA probe + auto-bump
- `f07252f` — feat(41-05): GA-rename probe + auto-bump in LibraryEmbedder (LAT-06)
- `f48eace` — test(41-05): bit-identical top-K parity test for 768-dim MRL
- `533206e` — feat(41-05): Embedding 2 migration script — audit / dry-run / re-embed-all
- *(merge cleanup)* — fix(41-05): relocate GA candidate literals to `_router_config.EMBEDDING_GA_CANDIDATES` (grep gate compliance)

## Tests

- **Plan-named verification suite:** 18/18 pass
  - `tests/library/test_embedding_ga_probe.py` — 13 tests (probe happy path / fallback path / all-fail RuntimeError / version-bump logic / cache-key stability / recorder event emission)
  - `tests/library/test_embeddings_parity.py` — 5 tests (top-K stability / EMBEDDING_DIM lock / cache-key SHA256 / migration audit / migration dry-run)

## Deviations

1. **Merge-time refactor — GA candidates moved to `_router_config.py`.** The plan originally proposed defining `GEMINI_EMBEDDING_MODEL_GA_CANDIDATES` in `library/embed.py`, but that placement trips Plan 41-01's grep gate (literals only allowed in `_router_config.py`). Moved the tuple to `_router_config.EMBEDDING_GA_CANDIDATES`, re-exported through `embed.py` under the original name for backward compatibility, and rewrote the comparison `candidate == "gemini-embedding-002"` to `candidate == GEMINI_EMBEDDING_MODEL_GA_CANDIDATES[0]`. Functionally equivalent; grep-gate compliant. Tests pass without modification.

## Deferred

None. LAT-06 is fully closed.

## Background process note

The original async executor agent stalled at the SUMMARY-write step (watchdog kill at 600s no-progress). All 4 plan commits had already landed in the worktree branch; this SUMMARY was written by the orchestrator from the agent's terminal state plus a merge-time refactor for grep-gate compliance.
