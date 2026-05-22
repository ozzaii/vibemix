---
phase: 64-session-ingest
plan: 02
subsystem: memory
tags: [ingest, coach_line, signature, embed-cache, idempotency, path-traversal, no-extraction, no-live-path, sqlite, off-hot-path]

# Dependency graph
requires:
  - phase: 63-memory-store
    provides: MemoryStore.add_record / query_topk / delete_session + Record shape + the no-live-path / no-extraction / model-literal gates that auto-cover memory/*.py
  - phase: 64-session-ingest (plan 01)
    provides: the RED contract (tests/memory/test_ingest.py 6 tests + the ingest-dormancy subprocess assertion) this plan flips GREEN
provides:
  - src/vibemix/memory/ingest.py — build_coach_line_signature + ingest_session + run_ingest_sweep + IngestResult + memory_ingested marker + signature-keyed embed cache
  - the GREEN INGEST capability — deterministic coach_line text records into MemoryStore, idempotent + path-defended + gate-clean
affects: [64-03, 65-memory-retrieval, copilot]

# Tech tracking
tech-stack:
  added: []  # ZERO net-new deps — stdlib (sqlite3, hashlib, json, re, os, time) + shipped in-repo modules only
  patterns:
    - "Pure deterministic signature assembly (regex + string ops, no model in path) keyed by SHA256(sig||model||template-version) for a content-hash embed cache"
    - "Two-layer idempotency: memory_ingested marker (skip session) + signature-keyed embed_cache (skip API on miss/template-bump); re-ingest = 0 embeds + 0 writes"
    - "A4 marker↔retention coupling solved WITHOUT editing Phase-63 code: short-circuit gated on marker AND COUNT(*) FROM moments — an evicted session re-ingests"
    - "MIRROR not import: 12-line JSONL reader cloned from session_loader (no 5-min floor); SESSION_DIR_RE + is_relative_to copied from recordings_index"
    - "Function-local runtime imports only (none needed here — cache/marker DBs derive from store._db_path) so the ingest dormancy gate prints CLEAN"

# Key files
key-files:
  created:
    - src/vibemix/memory/ingest.py
  modified:
    - .planning/codebase/orphans.csv

# Decisions
decisions:
  - "Embed-cache + marker live in an ingest-OWNED sibling DB (memory_ingest.db next to memory.db) — does NOT reuse the store's backend connection nor library/embeddings.db, keeping the Phase-64 idempotency layer fully isolated from Phase-63 internals"
  - "model_id for the cache key = getattr(embedder, '_model', '') — the real LibraryEmbedder always exposes the probe-derived _model (NEVER a literal); a stand-in exposing only embed_query namespaces to an empty model component (still caches by text+version)"
  - "IngestResult registered in the orphan baseline (orphans.csv) — it is referenced by 64-03 runtime wiring (Wave 3); orphan-diff CI gate refresh per its own instruction"

# Metrics
metrics:
  tasks: 2
  files_created: 1
  files_modified: 1
  duration_minutes: ~22
  completed: 2026-05-22
---

# Phase 64 Plan 02: Session-Ingest GREEN Implementation Summary

**One-liner:** `src/vibemix/memory/ingest.py` — the off-hot-path post-session ingest module that turns each session's `events.jsonl` into ONE deterministic `coach_line` TEXT record per EMITTED `ai_text` reaction (skipping silenced `citation_strip` lines), embeds each via the shipped `LibraryEmbedder.embed_query` behind a NEW signature-keyed content-hash cache, writes tagged records through `MemoryStore.add_record`, is marker-gated idempotent (re-ingest = 0 embeds, 0 writes), exposes a best-effort boot sweep with `SESSION_DIR_RE` + `is_relative_to` path-traversal defense, and imports no live reaction path. Flips the 64-01 RED contract GREEN.

## What Was Built

- **`src/vibemix/memory/ingest.py`** (new, ~430 lines):
  - **`build_coach_line_signature(reaction_text, ctx)`** — PURE function (regex + string assembly only; no genai client, no generation/chat call, no I/O). Emits the locked template `coach_line | track={track} | phase={phase} | deck={deck} | event={event_type} | cite={citation_tokens} | said: {reaction_text}` with the missing-value defaults `unknown/unknown/none/MANUAL`, citation tokens parsed via the copied `EVIDENCE_CITATION_RE`, sorted + `,`-joined, the leading `[emotion]` TTS tag stripped via `_EMOTION_TAG_RE`, and NO `t` in the embedded string (byte-reproducible → powers the cache).
  - **`EVIDENCE_CITATION_RE`** — COPIED VERBATIM from `state/evidence_registry.py:133` (lock-step source-of-truth comment) rather than imported, keeping the import surface minimal and unambiguously gate-clean.
  - **`_read_events_jsonl(path)`** — MIRROR of `session_loader._read_events` (per-line `json.loads` + skip-on-error), WITHOUT the 5-min `SessionTooShort` floor. Not imported.
  - **`SESSION_DIR_RE` + `_session_dir_is_safe`** — COPIED from `recordings_index.py:78,388-401` (regex shape THEN `is_relative_to(root.resolve())` containment THEN refuse-root) — the two-layer path-traversal gate.
  - **Signature-keyed embed cache** — `embed_cache(key, vector, ts)` table CLONED from `embed.py:146-157`, with `_cache_get`/`_cache_put` round-trips cloned from `embed.py:605-623`; key = `SHA256(signature ‖ model_id ‖ SIG_TEMPLATE_VERSION)`. `library/embed.py` is UNMODIFIED — this is a clone living in the memory layer.
  - **`memory_ingested(session_id, ingested_at, sig_template_version)` marker** — DDL mirroring `store.py`'s `CREATE TABLE IF NOT EXISTS` idiom. Both the marker + cache live in an ingest-owned sibling `memory_ingest.db` (next to the store's `memory.db`).
  - **`ingest_session(session_dir, store, embedder) -> IngestResult`** — guard (is-dir + events.jsonl-exists) → idempotency short-circuit (marker present AND `COUNT(*) FROM moments WHERE session_id=?` > 0, the A4 fix) → for each EMITTED `ai_text` line only (SKIP `citation_strip`), find the nearest preceding `event` line for context, build the signature, cache-guarded embed, `store.add_record(f"{sid}:{seq}", sid, ts, "coach_line", sig, vec)` → write the marker last.
  - **`run_ingest_sweep(recordings_root, store, embedder) -> list[str]`** — best-effort `os.scandir` boot sweep mirroring `run_retention_sweep`'s shape; the path-traversal gate runs BEFORE any read; one session's failure logs + continues (never raises).
  - **`IngestResult`** dataclass (`.records_written`, `.embeds_made`, `.skipped`).

## Verification

Run under `.venv` / Python 3.12 (the authoritative runner):

```
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory tests/repo/test_model_literal_gate.py -p no:cacheprovider
```

- **All 6 `test_ingest.py` tests GREEN** (signature determinism, coach_line emission + citation_strip skip, idempotent re-ingest, record tagging, embed-cache hit, sweep + traversal-dir rejection).
- **`test_importing_ingest_loads_no_coach_loop` GREEN** — the ingest-dormancy subprocess gate now prints `CLEAN` (was the intentional 64-01 RED edge).
- **`test_no_extraction.py` GREEN** (static gate auto-covers `ingest.py`); **`test_model_literal_gate.py` GREEN** (no model literal — `grep -vE '^\s*#|"""' … | grep gemini-embedding` → NO-LITERAL).
- `tests/memory` (38) + `tests/scripts/test_orphan_inventory.py` + model-literal gate = **44 passed**.
- `grep -nE "^\s*(import|from)" src/vibemix/memory/ingest.py | grep -E "agent|prompts|state.coach|state.refresh|ws_bus|MusicState|EventDetector|session_loop"` → empty (no live-path import).
- `git diff` shows `store.py` / `embed.py` / `delete_session` UNMODIFIED.
- **Full suite: 9 failed, 4116 passed, 26 skipped.** 8 of the 9 are the documented `live-tuning-or-brain` WIP baseline (confirmed identical with `ingest.py` removed: README-matrix ×2, gate-42 STATE annotation, cut-release tag-regex, cut-release-preflight ×2, coach anti-slop-wiring, main-smoke-08). The 9th (orphan-inventory) was caused by + resolved within this plan (see Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `model_id` source for the cache key on a stand-in embedder**
- **Found during:** Task 2 (sweep + emission tests).
- **Issue:** The plan said the cache-key model component comes from `embedder._model`. The contract's `_FakeEmbedder` exposes ONLY `embed_query` (no `_model`), so `embedder._model` raised `AttributeError`, failing 4 ingest tests.
- **Fix:** `model_id = getattr(embedder, "_model", "") or ""`. The real `LibraryEmbedder` always has the probe-derived `_model` (never a literal); a stand-in namespaces to an empty model component (still caches by text + version). No literal introduced — model-literal gate stays GREEN.
- **Files modified:** `src/vibemix/memory/ingest.py`
- **Commit:** `c68fe31`

**2. [Rule 3 - Blocking] Orphan-inventory CI gate flagged `IngestResult`**
- **Found during:** Full-suite verification.
- **Issue:** `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` failed with `NEW ORPHANS: + IngestResult` — the new dataclass is not yet referenced (64-03 Wave 3 wires `ingest_session`/`run_ingest_sweep` and consumes `IngestResult`).
- **Fix:** Refreshed the baseline per the test's own instruction (`scripts/integration_audit.py --orphan-inventory > .planning/codebase/orphans.csv`) — a clean single-line addition. This is intentional new surface, not dead code.
- **Files modified:** `.planning/codebase/orphans.csv`
- **Commit:** `d6b29cf`

## Authentication Gates

None.

## Known Stubs

None — `ingest.py` is the full INGEST capability. Runtime wiring (the `run_in_executor` enqueue at session-close/boot) is Wave 3 (64-03) by plan scope, not a stub: `ingest_session` + `run_ingest_sweep` are the complete, tested seam 64-03 calls.

## Threat Flags

None — every surface (`events.jsonl` reader, boot-sweep dir names, the single `embed_query` outbound) is in the plan's `<threat_model>` and mitigated as specified (T-64-01 no generation call, T-64-02 skip `citation_strip`, T-64-03 SESSION_DIR_RE + is_relative_to, T-64-04 per-line + per-session best-effort, T-64-06 no live-path import).

## Notes for 64-03

- Wire `ingest_session(session_dir, store, embedder)` at session-close (`on_session_close`) and `run_ingest_sweep(recordings_root, store, embedder)` at boot (`run_boot_sweeps`), both via `run_in_executor`. One-way runtime→ingest; ingest never imports the live path.
- Both functions are idempotent + best-effort by construction — safe to call on every boot. `run_ingest_sweep` returns the list of session_ids that wrote ≥1 record.
- The embedder must be the real proxy-wired `LibraryEmbedder` (exposes `_model` + `embed_query`); the marker/cache DB auto-creates as `memory_ingest.db` beside the store's `memory.db`.

## Self-Check: PASSED

- `src/vibemix/memory/ingest.py` — FOUND
- `.planning/codebase/orphans.csv` — FOUND (IngestResult registered)
- commit `c68fe31` (feat ingest.py) — FOUND
- commit `d6b29cf` (chore orphan baseline) — FOUND
