---
phase: 13-3d-mascot-overlay
plan: 05
subsystem: state-bus-prompts
tags: [music-state, ipc-schema, settings-applier, ws-bus, coach-prompt, anti-slop]
requires:
  - "MusicState (Phase 3)"
  - "SettingsApplier (Phase 12-02)"
  - "ws_broadcast 30Hz mascot bus (Phase 4)"
  - "Coach prompt matrix (Phase 10)"
  - "ipc schema oneOf @ 26 entries (Phase 12 W1 baseline)"
provides:
  - "MusicState.mood + bpm_confidence + downbeat_phase fields"
  - "compute_downbeat_phase pure function (features.py)"
  - "ipc.mascot.mood_change envelope (27th oneOf entry)"
  - "SettingsApplier handles mood + click_through fields"
  - "ws_broadcast 30Hz payload extended with mood/bpm_confidence/downbeat_phase/bpm"
  - "Coach prompt template renders {mood_persona} for COACH_* cells"
affects:
  - "Plan 13-04 (mascot renderer reads bpm_confidence + downbeat_phase for beat-locked entry)"
  - "Plan 13-06 (event dispatcher consumes ipc.mascot.mood_change on mood swap)"
  - "Phase 12 Settings UI (mood + click_through now valid ipc.settings.set fields)"
tech-stack:
  added:
    - "Phase 13-05 introduces no new deps. Uses existing numpy (cross-correlation), threading.Lock (state writes), jsonschema (envelope validation), dataclasses (wrapper)."
  patterns:
    - "Single-writer invariant preserved: state_refresh_loop owns bpm_confidence + downbeat_phase; SettingsApplier owns mood. Documented at the write sites."
    - "Anti-hallucination guard (T-13-05-02): compute_downbeat_phase returns (0.0, 0.0) on invalid BPM rather than fabricating a phase. Few-peak cap caps confidence at n_peaks/8.0 so noisy short captures cannot fake certainty."
    - "Schema-validated emit (T-13-05-03): MascotMoodChange.to_json() validates against the source-of-truth schema on every emit — Python-side schema drift surfaces at runtime."
    - "Anti-prompt-injection (T-13-05-06): MOOD_PERSONAS is a fixed constant; user input never enters the persona fragment — only the Literal-enum-validated mood selects which fragment is rendered."
key-files:
  created:
    - "tests/state/test_music_state_mood.py — 5 tests for new MusicState fields"
    - "tests/state/test_downbeat_phase.py — 8 tests for the pure function"
    - "tests/ui_bus/test_mood_change_envelope.py — 10 tests for schema + SettingsApplier emit + ws_bus payload"
    - "tests/agent/test_coach_mood_template.py — 7 tests for prompt {mood_persona} substitution"
    - ".planning/phases/13-3d-mascot-overlay/deferred-items.md — pre-existing failure log"
  modified:
    - "src/vibemix/state/music_state.py — +3 fields with documented defaults"
    - "src/vibemix/audio/features.py — +compute_downbeat_phase pure function (~95 LOC)"
    - "src/vibemix/audio/__init__.py — export compute_downbeat_phase"
    - "src/vibemix/state/refresh.py — call compute_downbeat_phase inside the per-tick lock block"
    - "src/vibemix/runtime/settings.py — _apply_mood + _apply_click_through cases"
    - "src/vibemix/runtime/ws_bus.py — snapshot payload extended"
    - "src/vibemix/ui_bus/messages.py — MascotMoodChange wrapper + payload dataclass"
    - "src/vibemix/ui_bus/__init__.py — export the wrapper"
    - "src/vibemix/prompts/matrix.py — MOOD_PERSONAS + {mood_persona} placeholder in COACH_* cells + build_system_instruction mood kwarg"
    - "src/vibemix/agent/dj_cohost.py — VIBEMIX_MOOD env + state.mood preference at agent build time"
    - "tauri/ui/src/ipc/messages.schema.json — +MascotMoodChange definition; SettingsSet field enum extended (+mood +click_through); value accepts boolean"
    - "tauri/ui/src/ipc/messages.ts — codegen output (committed alongside schema per Phase 11 W0 invariant)"
    - "scripts/check_ipc_schema.py — registers MascotMoodChange in minimal examples"
    - "tests/ui_bus/test_messages_schema.py — count parity bumped 26→27 (definitions 27→28); minimal example added"
    - "tests/prompts/test_matrix.py — dispatcher test updated to compare against substituted COACH form"
    - "tests/agent/test_dj_cohost_matrix_dispatch.py — same substitution helper for the env-var dispatch tests"
decisions:
  - "ConfigStore field for mood + click_through: stored in ConfigStore.extra (not a typed top-level field). Keeps the Phase 12 typed surface untouched (no config_store.py schema bump). Rust shell's tauri-plugin-store round-trip preserves extra keys verbatim."
  - "Invalid mood handling: returns (False, err) via the existing dispatch contract rather than raising ValueError (as the plan threat model wording suggested). Consistent with all other SettingsApplier cases. The security goal (rejecting bad input at the trust boundary, no silent fallback to default) is met either way — see T-13-05-01."
  - "{mood_persona} placeholder added ONLY to COACH_* templates (not HYPE_*). This preserves the HYPE_INTERMEDIATE byte-identical-to-v4 golden invariant (load-bearing IP per CLAUDE.md). The persona for HYPE_INTERMEDIATE is already tone-locked by v4 — Plan 13-05's mood swap only needs to differentiate the COACH register, where the persona shift is most meaningful (teacher = vocabulary-rich, coach = post-mortem)."
  - "Downbeat-phase algorithm: spectral-flux onset envelope + adaptive-threshold peak detection + cross-correlation against synthetic beat comb at 64 lag positions per bar. Considered FFT-phase-tracking (heavier, no improvement for the 0.6 confidence threshold) and dynamic-programming beat tracker (overkill for 4-bar windows). Few-peak cap at n_peaks/8.0 (~2 bars of kicks @ 120BPM) prevents fabricating confidence on short captures."
  - "ws_bus.py adds 'bpm' to the snapshot payload (was implicit before — Plan 13-04 renderer needs it for the beat-locked entry scheduler that uses (bpm + downbeat_phase) to compute ms_until_next_downbeat)."
metrics:
  duration: ~75min
  completed: 2026-05-12
  tasks_complete: "3/3"
  commits: "6 (3 RED + 3 GREEN)"
  new_tests: "30 (13 + 10 + 7)"
  regression_tests_passing: "539"
---

# Phase 13 Plan 05: Sidecar mood + beat-lock signals + Coach prompt Summary

Wired the Python sidecar to be the source of truth for mascot mood + beat-locked entry signals. `MusicState` gains `mood` / `bpm_confidence` / `downbeat_phase`; `SettingsApplier` handles the mood + click_through fields and emits a new `ipc.mascot.mood_change` envelope; `ws_broadcast` extends the 30Hz snapshot with all three; the Coach prompt template renders the active mood persona via a `{mood_persona}` placeholder.

## What landed

### Task 1: MusicState extension + compute_downbeat_phase pure function

- `MusicState` dataclass gains 3 fields, all in the "evidence" cluster:
  - `mood: str = "hype-man"` — Literal["hype-man", "teacher", "coach"]; backward-compat default. **SettingsApplier-owned, never written from state_refresh_loop.**
  - `bpm_confidence: float = 0.0` — 0..1; renderer skips beat-locked entry below 0.6 threshold (CONTEXT.md Open Q 4).
  - `downbeat_phase: float = 0.0` — 0..1 fraction-through-current-bar.
- `compute_downbeat_phase(samples, bpm, sample_rate, *, prior_phase=0.0) -> tuple[float, float]` — pure function in `vibemix.audio.features`. Anti-hallucination guards:
  - Invalid BPM (≤0, NaN, inf, >220) → `(0.0, 0.0)` — no fake confidence.
  - Fewer than 4 peaks in the analysis window → `(prior_phase, 0.0)` — preserve last known phase but signal zero confidence.
  - Few-peak cap: confidence ≤ `n_peaks / 8.0` so a handful of accidental peaks can't fake high confidence.
- `state_refresh_loop` calls `compute_downbeat_phase` per tick AFTER the BPM cache is updated, writes both fields under the existing `state._lock`. Reuses the `pcm_for_crest` snapshot — zero extra audio buffer reads.

### Task 2: ipc.mascot.mood_change envelope + SettingsApplier mood/click_through + ws_bus extension

- New schema entry `MascotMoodChange` (`payload: {mood, previous_mood?, at?}`) brings `oneOf` count to **27** (was 26 — see "Count Parity Transition" below).
- `SettingsSet.field` enum extended with `"mood"` and `"click_through"`; `value` now accepts `boolean` in addition to string/integer/null.
- `MascotMoodChange` + `MascotMoodChangePayload` dataclasses added to `vibemix.ui_bus.messages`. `.to_json()` drops `None` optionals before validation for cleaner wire frames.
- `SettingsApplier.__init__` gains optional `music_state` + `ws_bus` kwargs.
- `_apply_mood`: validates against `{hype-man, teacher, coach}` → writes `MusicState.mood` under the lock → persists via `ConfigStore.extra` → emits `ipc.mascot.mood_change` with `previous_mood` + `at=time.monotonic()`. Skips emit when same-value swap (no UI re-render noise). Returns `(False, err)` on invalid value or missing wiring.
- `_apply_click_through`: validates `bool` → persists via `ConfigStore.extra` only. No MusicState write, no ws_bus emit (Rust/webview-side concern).
- `ws_broadcast` 30Hz snapshot extended with `mood`, `bpm_confidence`, `downbeat_phase`, and `bpm`.
- `scripts/check_ipc_schema.py` + `tests/ui_bus/test_messages_schema.py` register the new wrapper; count-parity invariants bumped 26→27.

### Task 3: Coach prompt template gains {mood_persona} placeholder

- `MOOD_PERSONAS: dict[str, str]` constant in `matrix.py` — ~120-char persona fragment per mood (hype-man = "high-energy ... celebrate every clean move"; teacher = "patient ... name techniques"; coach = "frank, post-mortem-anchored ... debrief-style").
- `{mood_persona}` placeholder inserted into the first line of each COACH_* template (after the role intro, before the anchor phrases).
- `build_system_instruction(skill, mode, mood="hype-man")` validates mood against `MOOD_PERSONAS` keys (raises `ValueError` on miss); substitutes via `str.replace()` only for COACH cells. HYPE cells return as-is — **preserves the HYPE_INTERMEDIATE byte-identical-to-v4 golden invariant** (load-bearing IP per CLAUDE.md).
- `DJCoHostAgent.__init__` reads `state.mood` at agent build time (preferred over `VIBEMIX_MOOD` env var). Plan 13-06 will handle agent re-instantiation on mid-session mood swaps.

## Count Parity Transition (26 → 27)

The Phase 11 W0 invariant requires `len(schema.oneOf) == count(wrapper-dataclasses-with-type-field)`. Plan 13-05 grows both sides by 1:

| Side | Before | After |
|---|---|---|
| `messages.schema.json` `oneOf` | 26 | **27** |
| `messages.schema.json` `definitions` | 27 | **28** (LevelPair stays as a shared helper, not a top-level message) |
| Python wrapper dataclasses | 26 | **27** |
| `check_ipc_schema.py` minimal examples | 26 | **27** |
| `tests/ui_bus/test_messages_schema.py` example fixtures | 26 | **27** |

All five sides validated by `python scripts/check_ipc_schema.py` (exits 0).

## Downbeat-Detection Algorithm Choice

Considered three approaches:

| Approach | Why rejected / chosen |
|---|---|
| FFT phase-tracking | Heavier (~3× more CPU), no improvement for the 0.6 confidence threshold the renderer uses. Phase resolution above 1/64 of a bar is wasted on visual sync. |
| Dynamic-programming beat tracker (Ellis 2007) | Overkill for 4-bar analysis windows. State_refresh_loop calls this at 10Hz — keeping it pure + sub-10ms matters. |
| **Spectral-flux onset envelope + adaptive-threshold peak detection + cross-correlation against synthetic beat comb @ 64 lag positions per bar** | Chosen. ~2-5ms per call on the 4s int16 PCM windows state_refresh_loop hands us. Pure function (testable). Confidence model: peak-prominence z-score clamped to [0, 1] × few-peak cap (`n_peaks / 8.0`). |

The few-peak cap of `n_peaks / 8.0` was tuned to 8 (not the plan's initial 16) because realistic 4-second @ 120-128 BPM gives at most 8-9 kick onsets — 16 would force confidence below 0.6 on legitimate stable beats. Documented inline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test regression] COACH dispatcher tests asserted against raw template constants**

- **Found during:** Task 3 GREEN sweep — `test_prompt_01_dispatcher_returns_right_cell[*-coach-*]` + `test_dispatch_03_each_cell_selectable_via_env[*-coach-*]` + `test_dispatch_04_pro_coach_via_env` + `test_dispatch_05_case_insensitive_via_env` + `test_dispatch_06_gen_cfg_system_instruction_matches_dispatch` + `test_dispatch_10_re_reading_env_per_instantiation` failed.
- **Issue:** Existing Phase 10 tests assert `instructions == COACH_*` (raw template with `{mood_persona}` placeholder), but `build_system_instruction` now substitutes the placeholder at dispatch time. The plan's must-haves explicitly anticipated this for HYPE cells (byte-identical pin must hold for default mood) but didn't call out the COACH-cell update.
- **Fix:** Added a `_coach_rendered(template, mood="hype-man")` helper in the test files that applies the same substitution. Updated all 11 affected parametrize entries / assertion sites to compare against the rendered form.
- **Files modified:** `tests/prompts/test_matrix.py`, `tests/agent/test_dj_cohost_matrix_dispatch.py`
- **Commit:** d8fa2c1

### Plan-Adjacent Decisions

**2. [Decision] Invalid mood returns `(False, err)` rather than raising ValueError**

- **Where the plan says:** `<threat_model>` T-13-05-01 mitigation: "SettingsApplier rejects any value not in the literal 3-element set with ValueError; no silent default fallback".
- **What I did:** Return `(False, "mood must be one of [...]")` via the existing dispatch contract. Consistent with every other case in `SettingsApplier` (voice/mode/genre/output_*/retention/hotkey all return `(False, err)` rather than raise).
- **Why:** The dispatch contract `apply(field, value) -> tuple[bool, str|None]` is what the WizardLoop / IpcBus handler unpack to emit `ipc.error` or `ipc.settings.state` acks. Raising would break the existing pattern AND require try/except wrappers at every call site. The security goal (rejecting bad input at the trust boundary with no silent default fallback) is met either way — the value is rejected, no state is mutated, no bus emit happens.
- **Tests reflect this:** `test_apply_mood_invalid_value_returns_error_no_emit` asserts `(False, err)`. The threat model wording is updated effectively (not in the file itself — that's a CONTEXT-doc edit beyond this plan's scope) by the test pin.

**3. [Decision] mood + click_through stored in ConfigStore.extra**

- **Where the plan says:** `self._config_store.set("mood", value)` / `self._config_store.set("click_through", value)`.
- **What I did:** Wrote to `ConfigStore.extra["mood"]` / `ConfigStore.extra["click_through"]`.
- **Why:** `ConfigStore` doesn't have a `set()` method; it has typed top-level fields (`voice`, `mode`, `genre`, etc.) plus an `extra: dict` catch-all for unknown keys preserved on round-trip. Adding `mood` + `click_through` as typed fields would require:
  - Updating `_PHASE12_FIELDS` tuple,
  - Adding the dataclass field with default,
  - Adding to `to_dict` always-emit list,
  - Bumping the config-store schema effectively.
  - For two fields whose canonical source-of-truth lives in MusicState (mood) or the Rust shell (click_through), `extra` is the right home. The Rust shell's `tauri-plugin-store` round-trip preserves `extra` keys verbatim, so persistence works identically.
- **Tests reflect this:** `test_apply_mood_writes_music_state_and_config_and_emits` asserts `store.extra.get("mood") == "teacher"`.

## Authentication Gates

None.

## Known Stubs

None.

## Deferred Issues (out of scope — pre-existing, surfaced for follow-up)

See `.planning/phases/13-3d-mascot-overlay/deferred-items.md`:

1. **`tauri/ui/src/main.ts:104` imports `./session/mock.js`** — file exists only as untracked in main repo (`?? tauri/ui/src/session/mock.ts`). Blocks `npm run check:ipc`'s `tsc --noEmit` step. Pre-existing; not caused by Plan 13-05's schema/codegen changes.
2. **`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`** — reads `cohost_v4.py` from CWD, file untracked in main repo and absent from worktree. Pre-existing.
3. **`tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke`** + **`tests/test_phase05_verification.py::test_g5_poc_files_untouched`** — same root cause (untracked `cohost_v4.py`).

## Threat Flags

None — Plan 13-05 introduces no new surface beyond what the `<threat_model>` covers.

## Verification Results

```
$ python scripts/check_ipc_schema.py
OK: 27 dataclasses validate against schema
OK: count parity — 27 oneOf entries == 27 wrapper dataclasses

$ python -m pytest tests/state/test_music_state_mood.py tests/state/test_downbeat_phase.py \
    tests/ui_bus/test_mood_change_envelope.py tests/agent/test_coach_mood_template.py -q
30 passed in 0.10s

$ python -m pytest tests/prompts/ tests/state/ tests/ui_bus/ tests/runtime/ -q
539 passed in 1.91s

$ grep -c "mood:" src/vibemix/state/music_state.py        # ≥ 1
1
$ grep -c "ipc.mascot.mood_change" tauri/ui/src/ipc/messages.schema.json  # ≥ 1
1
$ grep -c "MOOD_PERSONAS" src/vibemix/prompts/matrix.py   # ≥ 1
6
```

## Self-Check: PASSED

- [x] `tests/state/test_music_state_mood.py` exists and committed (commit 73fc2b3)
- [x] `tests/state/test_downbeat_phase.py` exists and committed (commit 73fc2b3)
- [x] `tests/ui_bus/test_mood_change_envelope.py` exists and committed (commit c6de7f6)
- [x] `tests/agent/test_coach_mood_template.py` exists and committed (commit f844d68)
- [x] `src/vibemix/state/music_state.py` modified (commit 8f6698d) — 3 new fields visible
- [x] `src/vibemix/audio/features.py` gains `compute_downbeat_phase` (commit 8f6698d)
- [x] `src/vibemix/state/refresh.py` calls `compute_downbeat_phase` under the lock (commit 8f6698d)
- [x] `src/vibemix/runtime/settings.py` extends apply dispatch with mood + click_through (commit 4b33cc1)
- [x] `src/vibemix/runtime/ws_bus.py` snapshot payload extended (commit 4b33cc1)
- [x] `src/vibemix/ui_bus/messages.py` exports MascotMoodChange (commit 4b33cc1)
- [x] `tauri/ui/src/ipc/messages.schema.json` 27th oneOf entry committed (commit 4b33cc1)
- [x] `src/vibemix/prompts/matrix.py` MOOD_PERSONAS + placeholder (commit d8fa2c1)
- [x] `src/vibemix/agent/dj_cohost.py` mood env var + state-mood preference (commit d8fa2c1)
- [x] 6 git commits in the expected RED/GREEN sequence (verified via `git log`)
- [x] `check_ipc_schema.py` exits 0
- [x] 539 prompts+state+ui_bus+runtime tests green; 30 new plan-13-05 tests green
- [x] Pre-existing failures (cohost_v4.py-dependent + session/mock.ts-dependent) documented in deferred-items.md and confirmed not caused by Plan 13-05 changes
