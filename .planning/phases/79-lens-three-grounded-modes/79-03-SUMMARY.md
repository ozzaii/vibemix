---
phase: 79-lens-three-grounded-modes
plan: 03
subsystem: runtime
tags: [lens, shared-selection, config-extra, settings-bus, cold-path-byte-identity, no-schema-bump]

requires:
  - phase: 79-lens-three-grounded-modes (Plan 02)
    provides: "prompts/matrix.py::LENS_TO_MODE_MOOD + build_lens_instruction — the co-host read target for the shared lens"
provides:
  - "src/vibemix/runtime/settings.py::_apply_lens — settings-bus handler validating the lens enum + persisting ConfigStore.extra['lens'] (no env, no schema bump)"
  - "src/vibemix/runtime/settings.py::read_shared_lens — the ONE shared-lens read consumed by BOTH surfaces, per-surface default-when-unset"
  - "src/vibemix/agent/dj_cohost.py::_resolve_prompt_cell — reads the shared lens → LENS_TO_MODE_MOOD cell; explicit mood arg still wins; cold path byte-identical"
  - "src/vibemix/library/agent.py + codex_curate.py — curator seams read the shared lens (was hardcoded 'tutor'); cache invalidates on lens change"
  - "the final 4 LENS-02 xfail scaffolds flipped → real-green; LENS-02 closed; Phase 79 complete"
affects:
  - "Phase 81 BENCH: the shared lens selection is what the lens dimension drives across both surfaces"
  - "Phase 82 CURATE: curator+co-host now share the lens SELECTION (full engine unification is 82)"
  - "deferred follow-up: a UI selector for the lens rides the existing settings bus + (then) a messages.schema.json + codegen:ipc step"

tech-stack:
  added: []
  patterns: [shared-config-extra-read, per-surface-default-when-unset, lens-keyed-cache-invalidation, lazy-import-boundary-guard]

key-files:
  created: []
  modified:
    - src/vibemix/runtime/settings.py
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/library/agent.py
    - src/vibemix/library/codex_curate.py
    - tests/runtime/test_settings_apply.py
    - tests/agent/test_dj_cohost.py
    - tests/prompts/test_lens.py
    - tests/library/test_curator_persona_seam.py

key-decisions:
  - "Lens persists in ConfigStore.extra['lens'] ONLY — no SettingsState wire snapshot, no messages.schema.json edit, no npm run codegen:ipc (the smallest additive diff; avoids a stale pre-compiled ajv validator). Invariant #4 (one socket, zero new envelope) holds."
  - "read_shared_lens(store, default) is the ONE shared read; the default is PER-SURFACE — co-host passes None (cold path → env/DEFAULT → hype), curator passes 'tutor' (cold path → the voice it shipped with). Both cold paths stay byte-identical."
  - "Co-host precedence preserved: explicit mood arg (live MusicState.mood rebuild) > shared lens > env/DEFAULT_*. Lens read is lazy + guarded — any config-read failure falls through to the env path so the cold path never regresses."
  - "Curator caches are keyed by the lens they were built under (_SYSTEM_INSTRUCTION_LENS etc.) — a lens change in-process rebuilds, never serves the stale voice (Flag #3)."
  - "_VALID_LENSES lives in settings.py as a plain literal mirroring matrix.LENS_TO_MODE_MOOD keys (settings stays import-light; matrix drags the prompt stack)."

patterns-established:
  - "Shared-config-extra read: one import-light helper (read_shared_lens) reads ConfigStore.extra and is consumed by two unrelated surfaces, lazy-imported to keep each surface's import-time boundary clean."
  - "Per-surface default-when-unset: one shared selection, but each consumer supplies its own cold-path default so an unset value reproduces today's behavior exactly."
  - "Lens-keyed cache invalidation: a module-global cache stores the input it was built under alongside the value; the value is rebuilt when the input differs."

requirements-completed: [LENS-02]

duration: ~18min
completed: 2026-05-26
---

# Phase 79 Plan 03: LENS-02 One Shared Lens Selection Summary

**ONE shared `ConfigStore.extra["lens"]` (set via the new `_apply_lens` settings-bus handler) is read by BOTH the live co-host AND the curator — choose the lens once, it flows to both. Extra-only: no IPC envelope, no schema bump, no codegen. Both cold paths byte-identical.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-26
- **Completed:** 2026-05-26
- **Tasks:** 2 (TDD — Plan-01 scaffolds are the RED, this is the GREEN)
- **Files modified:** 8 (4 source + 4 test)

## Accomplishments
- **Settings bus (`_apply_lens` + `_VALID_LENSES` + dispatch case).** `_apply_lens` mirrors `_apply_skill`: validate `isinstance(value,str) and value in _VALID_LENSES` (fail-loud `(False, ...)` on a bad value — no silent fallback), persist `ConfigStore.extra["lens"]`, `save_config`. Unlike skill it sets NO env var — the co-host reads `extra["lens"]` directly (Pitfall 3: one consistent read, not the orphaned `VIBEMIX_MODE` env). `_VALID_LENSES = {"hype","critique","tutor"}` mirrors `matrix.LENS_TO_MODE_MOOD` keys. Added the `if field == "lens"` dispatch case before the unknown-field fallthrough.
- **`read_shared_lens(store, default)`** — the ONE shared-lens read in `settings.py` (import-light: stdlib + config_store only) consumed by both surfaces. Returns `store.extra["lens"]` when a non-empty string, else the caller's per-surface default.
- **Co-host (`_resolve_prompt_cell`)** reads the shared lens (lazy `load_config()` + `read_shared_lens`, guarded) → `LENS_TO_MODE_MOOD[lens]` → `(mode, mood)` → `build_system_instruction`. An explicit `mood` arg (the live `MusicState.mood` rebuild path) still WINS over the shared lens, which wins over the env/`DEFAULT_*` cold path. When no lens is set, the function is byte-identical to today.
- **Curator (`library/agent.py` ×2 + `codex_curate.py` ×1)** swapped the hardcoded `build_curator_instruction("tutor")` for `build_curator_instruction(_shared_lens())` where `_shared_lens()` reads the shared selection and DEFAULTS to `"tutor"` when unset (curator cold path byte-identical). Each module-global cache is now keyed by the lens it was built under and rebuilds on a lens change (Flag #3 — no stale voice).
- **Flipped the final 4 LENS-02 xfail scaffolds → real-green:** `test_settings_apply::test_apply_lens_happy_path`, `test_lens::test_shared_selection_flows_to_both_builders`, `test_curator_persona_seam::test_curator_seam_reads_shared_lens`, `test_dj_cohost::test_resolve_prompt_cell_uses_shared_lens`. **LENS-02 closed → Phase 79 complete.**

## Task Commits

1. **Task 1: settings bus — `_apply_lens` + `_VALID_LENSES` + `read_shared_lens` + dispatch case** — `6c42bca` (feat)
2. **Task 2: shared-read wiring — co-host `_resolve_prompt_cell` + both curator seams read `ConfigStore.extra["lens"]`; caches invalidate on change** — `0d41036` (feat)

_TDD note: Plan 01 installed the RED scaffolds (xfail-strict); this plan is the GREEN — implementation + scaffold-flip committed together per task (the failing tests already existed)._

## Files Created/Modified
- `src/vibemix/runtime/settings.py` — `_VALID_LENSES` frozenset, `read_shared_lens` module helper, `_apply_lens` handler (after `_apply_skill`), `"lens"` dispatch case.
- `src/vibemix/agent/dj_cohost.py` — `_resolve_prompt_cell` reads the shared lens (lazy + guarded) → `LENS_TO_MODE_MOOD` cell when set; cold path + mood-arg precedence unchanged.
- `src/vibemix/library/agent.py` — `_shared_lens()` helper + lens-keyed cache invalidation on both lazy seams; hardcoded `"tutor"` removed.
- `src/vibemix/library/codex_curate.py` — `_shared_lens()` helper + lens-keyed cache invalidation on the codex seam; hardcoded `"tutor"` removed.
- `tests/runtime/test_settings_apply.py` — un-xfailed `test_apply_lens_happy_path`.
- `tests/agent/test_dj_cohost.py` — un-xfailed `test_resolve_prompt_cell_uses_shared_lens`.
- `tests/prompts/test_lens.py` — un-xfailed `test_shared_selection_flows_to_both_builders`; removed the now-unused `_LENS_REASON_02`.
- `tests/library/test_curator_persona_seam.py` — un-xfailed `test_curator_seam_reads_shared_lens`.

## Decisions Made
- **Extra-only, no schema bump** (Planner Decision Flag #1). Persisting `lens` in `ConfigStore.extra` and reading it directly satisfies LENS-02 with the smallest additive diff, keeps invariant #4 (one socket, zero new envelope), and avoids the stale-pre-compiled-ajv-validator risk that a `messages.schema.json` edit + `codegen:ipc` would carry. A UI selector is the explicitly-deferred follow-up.
- **Per-surface default-when-unset** (Flag #2). One shared selection, but co-host defaults to `hype` (env/DEFAULT path) and curator defaults to `tutor` when no lens is set — so each cold path is byte-identical to today.
- **Lens-keyed cache invalidation** (Flag #3). Curator caches store the lens they were built under; a change rebuilds rather than serving the stale voice within a process.
- **Defense-in-depth on the persisted value** (T-79-03-02). The builders re-validate the lens against their own fixed enum (`LENS_TO_MODE_MOOD` / `_CURATOR_LENS_TO_MOOD` / `MOOD_PERSONAS`); a corrupt persisted lens raises at build (surfaces the corruption) rather than silently degrading the voice.

## Deviations from Plan
None - plan executed exactly as written. (`_LENS_REASON_02` became unused after flipping the last LENS-02 scaffold in `test_lens.py`; removed it to keep the lint clean — the plan's intended scaffold-flip, not a deviation.)

## Issues Encountered
None.

## Authentication Gates
None. Honest green — no `genai.Client`, no `GEMINI_API_KEY`, no network.

## Known Stubs
None. Both surfaces are fully wired to the one shared `extra["lens"]`; no placeholders.

## WR-1 Regression Handling (verifier-flagged)
The two existing curator-seam tests (`test_curator_persona_seam.py::test_{gemini,codex}_curator_voice_sourced_from_matrix_seam`) and the new `test_curator_seam_defaults_to_tutor_when_lens_unset` stay GREEN: `read_shared_lens(load_config(), default="tutor")` deterministically returns `"tutor"` when `extra["lens"]` is unset, and the tests monkeypatch `config_store.config_path` to a tmp dir so the test process never picks up a real persisted lens from `~/.cache/vibemix`. Confirmed green in both the targeted run and the full suite.

## Verification
- `PYTHONPATH=src python3 -m pytest -q tests/runtime/test_settings_apply.py -k "lens or skill or mood"` → **6 passed** (Task 1).
- `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py tests/library/test_curator_persona_seam.py tests/agent/test_dj_cohost.py tests/memory/test_no_live_path_import.py` → **55 passed** (Task 2 — all LENS-02 scaffolds green, no-live-path boundary green, WR-1 seam tests green).
- `grep -rn "lens" tauri/ui/src/ipc/messages.schema.json` → ABSENT; `lens` is NOT in `src/vibemix/ui_bus/messages.py` (the IPC payload module) — no schema/envelope edit, no `codegen:ipc` needed.
- `PYTHONPATH=src python3 -m pytest -q tests/repo/test_model_literal_gate.py` → **10 passed** (no model literal introduced).
- Full suite: `PYTHONPATH=src python3 -m pytest -q` → **4501 passed, 26 skipped, 1 xfailed, 4 xpassed** in 241s. Net +4 vs Plan-02 baseline (4497) — exactly the 4 LENS-02 scaffolds flipping green. The 1 remaining xfailed = the pre-existing budget cost gate; the 4 xpassed = pre-existing live-only markers (wizard port-bind + macOS BlackHole kext). **Zero remaining LENS xfails, zero new failures.**

## TDD Gate Compliance
Plan 01's `test(79-01)` commits installed the failing xfail-strict scaffolds (RED); this plan's `feat(79-03)` commits make them pass (GREEN). GREEN gate commits `6c42bca` + `0d41036` present; the RED gate lives in Plan 01's history.

## Next Phase Readiness
- LENS-02 satisfied: ONE shared `ConfigStore.extra["lens"]` read by both the co-host and the curator — choose once, flows to both. Phase 79 (LENS) complete (3/3); LENS-01 + LENS-02 closed.
- Phase 81 BENCH can now drive the shared lens across both surfaces for the lens dimension; Phase 82 CURATE inherits the shared lens SELECTION (full engine/taste unification is 82's scope).

## Self-Check: PASSED

- `src/vibemix/runtime/settings.py` carries `_apply_lens` + `read_shared_lens` — FOUND.
- `src/vibemix/agent/dj_cohost.py` `_resolve_prompt_cell` reads `LENS_TO_MODE_MOOD` — FOUND.
- `src/vibemix/library/agent.py` + `codex_curate.py` `_shared_lens()` (hardcoded "tutor" removed) — FOUND.
- `.planning/phases/79-lens-three-grounded-modes/79-03-SUMMARY.md` — FOUND.
- Task commits `6c42bca` + `0d41036` present in git history — FOUND.

---
*Phase: 79-lens-three-grounded-modes*
*Completed: 2026-05-26*
