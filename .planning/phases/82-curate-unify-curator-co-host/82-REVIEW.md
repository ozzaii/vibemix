---
phase: 82-curate-unify-curator-co-host
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/vibemix/library/agent.py
  - src/vibemix/library/codex_curate.py
  - src/vibemix/library/toolset.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 82: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 3 (+4 cross-referenced: `genre_prototypes.py`, `profile/cache_render.py`, `profile/storage.py`, `profile/schema.py`)
**Status:** issues_found

## Summary

Phase 82 wires two thin seams into the curator: SEAM #1 (`toolset._resolve_genre` via a lazily-built `GenrePrototypeLookup`) and SEAM #2 (`_taste_hint()` appended at three instruction-build sites in `agent.py`/`codex_curate.py`). The overall structure is sound and the prompt's headline concerns hold up under inspection:

- **SEAM #1 build-once: CORRECT.** `_genre_lookup` is memoized on the toolset instance; the expensive prototype table is built once inside `GenrePrototypeLookup._ensure_prototypes` (guarded `if self._protos is not None: return`). No per-call prototype rebuild. Honest-None on abstain is correct (`label != "unknown"` check).
- **SEAM #2 cache interaction: CORRECT.** The taste hint is appended to `base` AFTER the lens-keyed cache read and recomputed per call — so a profile change is never served stale, and a cached instruction is never returned without the hint. Cold-path byte-identity holds when the profile is genuinely `None` (`base + "" == base`).
- **Lazy-import boundary: CORRECT.** Both seams import cross-package (`genre_prototypes`, `profile`) inside the function bodies, never at module top.
- **Invariant #1 (no MusicState read): HOLDS.** The curator builds its own `GenrePrototypeLookup` and calls `classify_playing` directly; it never reads `MusicState`, `refresh`, or the co-host's holder.
- **Invariant #2 (grounding gate): UNTOUCHED.** The diff only changes the `genre:` field value and the instruction-build append; the seen-set gate in `create_playlist` and the codex result-boundary re-validation are unchanged.
- **No hardcoded model literals / no genai.Client / no API key** on any of the three paths. Model is resolved via `model_router.resolve("library_agent")[0]`.

Three WARNINGs and two INFO items below. The most important is the consent-gate bypass (WR-01): the `_taste_hint` docstrings claim "`''` when consent-OFF", but the code never checks consent — it surfaces the profile whenever a `profile.json` file exists on disk.

## Warnings

### WR-01: `_taste_hint()` bypasses the profile consent gate — contradicts its own docstring

**File:** `src/vibemix/library/agent.py:153-155`, `src/vibemix/library/codex_curate.py:127-129`
**Issue:**
Both `_taste_hint()` implementations call `render_profile_for_cache(load_profile())` with **no consent check**. The docstrings explicitly assert the opposite:

> `render_profile_for_cache(load_profile())` returns `""` when the profile is None / **consent-OFF** (default OFF) → the cold path is byte-identical to today.

But `storage.load_profile()` (verified at `profile/storage.py:48-67`) only checks whether the file exists and validates the schema — it does **not** read `load_consent()`. `render_profile_for_cache` (verified at `profile/cache_render.py:40`) only short-circuits on `if not profile`. So if a `profile.json` exists on disk while `profile_consent` is `False`, the taste hint is emitted into the curator system instruction — the consent gate is silently bypassed.

This is the canonical project pattern in `runtime/session_loop.py:543-544`:
```python
consent = load_consent()
profile = load_profile() if consent else None
```
Phase 82 instead mirrored the un-gated `__main__.py:852` cache-build call. Per the profile module's own contract (`profile/__init__.py:15`: "Default-OFF consent (PROFILE-05) gates creation") and the threat model, the consent flag must gate every surface that emits the profile.

Severity note: classified WARNING (not BLOCKER) because the schema is fully enum-locked with `additionalProperties: false` (verified `profile/schema.py:78,87-107`) — only coarse allowlisted tendencies (`preferred_genre`, `tempo_preference_bin`, `mix_style_tags`, cadences) can cross, never track titles/paths/free-form. It is a consent-contract violation, not a content leak. Still must be fixed: the cold-path byte-identity claim is false whenever a stale profile file outlives a consent toggle-off.

**Fix:** Gate on consent in both `_taste_hint()` bodies (mirror `session_loop.py`):
```python
try:
    from vibemix.profile import load_consent, load_profile, render_profile_for_cache

    if not load_consent():
        return ""
    return render_profile_for_cache(load_profile())
except Exception:
    return ""
```
Then the docstring's "consent-OFF → `''`" claim becomes true and the cold path is byte-identical regardless of a leftover profile file.

### WR-02: `_resolve_genre` reloads the entire vector corpus on every `get_track_features` call

**File:** `src/vibemix/library/toolset.py:158` → `genre_prototypes.py:325` → `genre_prototypes.py:299-307`
**Issue:**
The prototype table is built once (good), but `classify_playing` calls `self._cached_embedding(track_id)` which calls `store._backend.load_all()` on **every** invocation (`genre_prototypes.py:302`). `load_all()` materializes the full `(N, 1536)` float32 corpus, then does a linear `ids.index(track_id)`. For a ~1500-track library that is a ~9 MB array re-loaded and re-scanned on every single `get_track_features` call. Within one curation run the model may peek at features for a dozen+ candidate tracks, so this is N full-corpus loads per run.

Pure-performance issues are out of v1 scope, but the phase prompt explicitly asked to confirm no per-call full-corpus work, and this is a real per-call cost the build-once memoization does NOT cover (the memoization only caches the prototype table, not the embedding lookup). Flagging so it is a conscious accept, not an oversight.

**Fix:** Cache `(ids, vectors)` (or an `id -> row index` dict) on the `GenrePrototypeLookup` instance alongside the prototype table, refreshed only on snapshot-hash change — the vectors are already loaded once inside `load_or_build_prototypes`. Alternatively expose a `store` lookup-by-id that does not materialize the whole corpus. If the team accepts the cost for v1 (curation is a low-frequency, off-live operation), document it explicitly rather than relying on the misleading "Reads the track's CACHED library embedding at €0" comment, which implies cheap.

### WR-03: `_resolve_genre` lazy-init check-then-set is not thread-safe under `dispatch`'s executor

**File:** `src/vibemix/library/toolset.py:154-157`
**Issue:**
`dispatch` runs each handler on a fresh `ThreadPoolExecutor(max_workers=1)` (`toolset.py:211`). The agent loop dispatches tool calls sequentially within a run, so in practice this is safe. But the contract documented in the class docstring is "one instance == one run" with no statement that calls are serialized — and `_resolve_genre`'s `if self._genre_lookup is None: ... = GenrePrototypeLookup(...)` (lines 154-157) is an unguarded check-then-set. If a future caller ever dispatches two `get_track_features` concurrently against the same toolset (e.g. a batched tool-call turn), two `GenrePrototypeLookup` instances could be constructed and one discarded. The inner `GenrePrototypeLookup` is itself thread-safe (double-checked locks, verified `genre_prototypes.py:266-297`), so the worst case is wasted work, not corruption — hence WARNING not BLOCKER.

**Fix:** Either document the serialized-dispatch assumption on `_resolve_genre`, or guard the lazy init with a per-instance `threading.Lock` mirroring `GenrePrototypeLookup._ensure_store`'s double-checked pattern. Given the inner class is already safe, a one-line comment asserting "dispatch serializes tool calls within a run" is acceptable.

## Info

### IN-01: `_taste_hint` logic is duplicated verbatim across two modules

**File:** `src/vibemix/library/agent.py:137-157`, `src/vibemix/library/codex_curate.py:116-131`
**Issue:**
The two `_taste_hint()` bodies are byte-identical (same docstring intent, same try/except, same call). The same is already true of `_shared_lens()` in both files. When WR-01 (consent gate) is fixed, the fix must be applied in **both** places or the codex backend silently diverges from the gemini backend — exactly the "orphaned backend" failure the codex docstring warns about. A shared helper (e.g. in a small `library/_curator_seams.py`) would make the consent contract single-sourced.

**Fix:** Extract `_taste_hint` (and optionally `_shared_lens`) into one shared module imported lazily by both backends, so the privacy/consent contract has one implementation.

### IN-02: `classify_playing` mutates per-run lookup state the curator never reads

**File:** `src/vibemix/library/genre_prototypes.py:317-335` (called from `toolset.py:158`)
**Issue:**
`classify_playing` bumps `_inflight_gen` and latches `self._latest` under lock on every call — machinery designed for the co-host's off-loop single-writer holder. The curator uses its own fresh `GenrePrototypeLookup` and only consumes the return value, never `get_latest()`, so the latch/generation-token work is dead weight on this path (harmless, but it reuses a method whose contract is "off-loop worker that latches for the refresh loop to read"). Not a bug — flagged so a future reader doesn't assume the curator participates in the co-host's holder lifecycle. No fix required; consider a comment at `toolset.py:158` noting the curator uses only the return value.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
