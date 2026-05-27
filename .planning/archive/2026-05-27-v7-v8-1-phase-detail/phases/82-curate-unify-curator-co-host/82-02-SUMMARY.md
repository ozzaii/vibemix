---
phase: 82-curate-unify-curator-co-host
plan: 02
subsystem: library (curator) — toolset + both backends
tags: [wave-2, curate, seam, unify, anti-slop, one-mind]
requires:
  - "Phase 78 genre_prototypes (GenrePrototypeLookup.classify_playing — the shared perception mechanism the co-host reads)"
  - "Phase 79 read_shared_lens / build_curator_instruction (the shared lens, already DONE — regression-pinned)"
  - "profile/ render_profile_for_cache (the privacy-safe taste vehicle)"
  - "82-01 (the xfail scaffolds this flips green)"
provides:
  - "get_track_features genre resolved via the ONE genre_prototypes mechanism (SEAM #1) — reaches gemini + codex/MCP + Telegram via the shared LibraryToolset"
  - "_taste_hint() lazy+guarded profile read appended at all 3 instruction-build sites (SEAM #2) — curate 'for this DJ' across both backends"
  - "v8.1 'One Mind' diamond closed — curator + co-host derive genre from one source and read one taste layer"
affects:
  - "closes Phase 82 (CURATE) — last phase of the v8.1 milestone"
tech-stack:
  added: []
  patterns:
    - "Lazy+guarded cross-package read mirroring the Phase-79 _shared_lens seam (import-boundary discipline)"
    - "Per-surface default-when-unset (honest-null genre / '' taste → byte-identical cold path)"
    - "Recompute-per-call seam OUTSIDE the lens-keyed cache (profile change reflected without a cache miss)"
key-files:
  created: []
  modified:
    - "src/vibemix/library/toolset.py"
    - "src/vibemix/library/agent.py"
    - "src/vibemix/library/codex_curate.py"
    - "tests/library/test_toolset.py"
    - "tests/library/test_curate_unify.py"
    - ".planning/phases/82-curate-unify-curator-co-host/82-VALIDATION.md"
decisions:
  - "SEAM #1 is ONE edit (shared toolset.get_track_features) reaching all LLM backends + Telegram + MCP; genre delegated entirely to genre_prototypes (no re-rolled centering, Pitfall 2)"
  - "SEAM #2 recomputes _taste_hint() per call OUTSIDE the lens-keyed cache (plan option b) so a profile change is reflected; the lens-keyed cache covers only build_curator_instruction(lens)+RULES"
  - "GenrePrototypeLookup cached lazily on the toolset instance (self._genre_lookup) so repeated feature lookups reuse the built prototype table; no work in __init__ (import-boundary stays clean)"
metrics:
  duration: ~30 min
  completed: 2026-05-26
---

# Phase 82 Plan 02: CURATE — The Two Unification Seams + Regression Gate Summary

The v8.1 "One Mind" diamond closes here: the library/Viber **curator** and the live **co-host** stop being islands and become two facets of one mind. Two thin, additive seams — the curator now resolves genre through the SAME `genre_prototypes` mechanism the co-host reads (ONE source, both surfaces) and lazy-reads the shared DJ `profile/` so it curates "for this DJ" — flip the four Plan-01 CURATE xfail scaffolds to real-green while keeping the five must-stay-true pins and the import-boundary gate clean. No new abstraction (the existing functions ARE the contract), honest green (no API key, no model literal), the four cardinal invariants hold by additive design.

## What Was Built

### Task 1 — SEAM #1: `get_track_features` genre via the ONE perception mechanism (CURATE-01)

- `src/vibemix/library/toolset.py`: replaced the hardcoded `"genre": None` with `self._resolve_genre(track_id)`, a new helper that routes through the SAME `GenrePrototypeLookup.classify_playing` the co-host reads (`refresh.py` → `genre_prototypes`). The lookup is lazy-built once per toolset instance (`self._genre_lookup`, no work in `__init__`) so repeated feature lookups in one run reuse the prototype table.
- The genre_prototypes import is LAZY (inside `_resolve_genre`, not module-top) — import-boundary discipline (Pattern 1).
- Honest-null on abstain: `("unknown", _)` → `None` (byte-identical class to the prior `genre: None` and the Camelot honest-null), never a fabricated label (invariant #3). ALL prototype-distance math delegated to genre_prototypes — no `np.mean`/cosine added to toolset.py (Pitfall 2, grep-clean).
- Guarded (`except Exception: return None`) so a feature lookup never raises. The seen-set grounding gate (`toolset.py:134-147`) + `create_playlist` re-validation are UNTOUCHED (invariant #2) — genre is a deterministic library-side fact, the model never supplies it.
- One edit reaches gemini (`agent.py`), codex/MCP (`mcp_server.py`), and Telegram (routes through `ViberAgent`) — the CURATE acid test satisfied by construction.
- Flipped `test_genre_via_prototypes_when_classified` + `test_genre_honest_none_on_abstain` from xfail-strict to real-green (7 passed in `test_toolset.py`).

### Task 2 — SEAM #2: `_taste_hint()` reads the shared profile at all 3 build sites (CURATE-02 taste half)

- Added a lazy+guarded `_taste_hint()` helper to BOTH `agent.py` and `codex_curate.py` (per-backend twin convention, mirroring `_shared_lens`): lazy-imports `load_profile` + `render_profile_for_cache` from `vibemix.profile` INSIDE the function, guarded with `except Exception: return ""`. `render_profile_for_cache(load_profile())` returns `""` when the profile is None/consent-OFF (default OFF) → cold-path byte-identical.
- Attached at all THREE instruction-build sites: gemini `_system_instruction` (one-shot), gemini `_interactive_system_instruction` (interactive not orphaned), and codex `_system_prompt`. The hint is appended OUTSIDE the lens-keyed cache (recompute per call, plan option b) so a profile change is reflected without a cache miss; the lens-keyed cache still covers only the `build_curator_instruction(lens) + RULES/FLOW` base.
- Only the 5 allowlisted fields cross via `render_profile_for_cache` — NO track titles / free-form (T-82-01; the renderer enforces it with `.get` defaults, never raw JSON / `profile[...]`).
- No module-top profile import in either backend (lazy only — grep-confirmed). Flipped `test_curator_taste_hint_present_when_profile_set` + `test_taste_hint_reaches_codex_backend` from xfail-strict to real-green; the cold-path-identity, no-leak, and lens-shared pins stay green (16 passed across `test_curate_unify.py` + `test_curator_persona_seam.py`).

### Task 3 — Regression gate + full suite + import-boundary + VALIDATION sign-off

- `tests/library/ tests/profile/ tests/memory/test_no_live_path_import.py`: 323 passed, 1 xfailed (the pre-existing budget gate only), import-boundary CLEAN — the two new lazy reads did not leak the live path into the curator namespace.
- Full suite: **4538 passed / 26 skipped / 1 xfailed (pre-existing budget gate) / 4 xpassed (pre-existing live-hardware)** (292s, exit 0). Baseline was 4534 passed → +4 (the four CURATE flips), zero new failures, zero remaining CURATE xfails/xpasses.
- Diff scope verified: touches only `src/vibemix/library/{toolset,agent,codex_curate}.py` + the two test files + `82-VALIDATION.md` — NO `messages.schema.json`, NO ws_bus/port change (invariant #4), NO `state/music_state.py` touch (invariant #1).
- `82-VALIDATION.md`: filled the per-task map (P01/P02 all ✅ green), `nyquist_compliant: true` (kept), `wave_0_complete: true`, status complete, sign-off recorded.

## Deviations from Plan

None — plan executed exactly as written. The two minor in-prose comment wordings adjusted (rephrasing a "cosine math" comment in `toolset.py` to "prototype-distance math" so the Pitfall-2 grep gate `np.mean\|cosine` returns nothing, and refreshing the two test-file header comments from "xfail scaffold" to "real-green as of Plan 02") are documentation alignment, not behavioral deviations.

## Known Stubs

None. The two seams are the concrete wiring the Plan-01 scaffolds spec'd; both are now real-green and reach both backends. The remaining "does curating-for-this-DJ actually FEEL personal" judgment is a parked KAAN-ACTION live item (documented in `82-VALIDATION.md` Manual-Only Verifications), never a code stub.

## Threat Flags

None. The diff introduces no new network endpoint, auth path, file-access pattern, or schema change. The two reads cross trust boundaries already in the Phase-82 threat register (T-82-01 profile→instruction mitigated via `render_profile_for_cache`; T-82-02 genre-as-deterministic-fact via `genre_prototypes`), both mitigated as planned.

## Self-Check: PASSED

- FOUND: src/vibemix/library/toolset.py (modified — _resolve_genre)
- FOUND: src/vibemix/library/agent.py (modified — _taste_hint x2 sites)
- FOUND: src/vibemix/library/codex_curate.py (modified — _taste_hint)
- FOUND commit: 4ce9fef (Task 1 — SEAM #1)
- FOUND commit: fc4b842 (Task 2 — SEAM #2)
- FOUND commit: bd1ac84 (Task 3 — VALIDATION sign-off)
