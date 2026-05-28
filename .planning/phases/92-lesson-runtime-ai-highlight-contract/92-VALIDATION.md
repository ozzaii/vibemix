---
phase: 92
slug: lesson-runtime-ai-highlight-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 92 — Validation Strategy

Derived from `92-RESEARCH.md` §Validation Architecture (line 2152+).

## Test Infrastructure

| Property | Value |
|----------|-------|
| Frameworks | pytest (Python) · vitest (TS unit) · playwright (TS spec/DOM) · cargo test (Rust unaffected) |
| Quick run | `cd tauri/ui && npm test -- tests/learn/` + `PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/ipc/test_learn_envelope_parity.py` |
| Full suite | `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && npx playwright test tests/learn/` |
| Estimated runtime | ~25–40 s |

## Sampling Rate

- Per task: vitest learn-suite (~3–5 s)
- Per wave: vitest + pytest learn-suite (~10 s)
- Phase gate: full pytest + vitest + playwright (~40 s)

## Per-Task Verification Map (key gates)

| REQ-ID | Behavior | Test |
|--------|----------|------|
| LESSON-01 | LessonRuntime sole writer of LearnState; zero MusicState/ControllerState writes from `src/vibemix/learn/` | `tests/learn/test_runtime_invariants.py` (AST grep) |
| LESSON-01 | python-statemachine 3.1.2 installed; LessonRuntime declares one state per lesson | `tests/learn/test_lesson_runtime_states.py` |
| LESSON-02 | 11 new envelopes shipped; `additionalProperties: false` on each; ajv validator regenerated | `python3 scripts/check_ipc_schema.py` + `tests/ipc/test_learn_envelope_parity.py` (round-trip for all 13 envelopes) |
| LESSON-02 / RENDER-04 | Highlight paint ≤16 ms via CSS-variable swap | `tauri/ui/tests/learn/highlight-paint.test.ts` |
| LESSON-03 | Expected-action match: CC drop ≥30% OR button press matches `expected_action.control`+`direction` | `tests/learn/test_advance_predicates.py` |
| LESSON-03 | 3-strike progressive hint + `min_dwell` ≥45s | `tests/learn/test_hint_strikes_and_min_dwell.py` |
| LESSON-03 | "I got it" skip always available | `tests/learn/test_skip_always_available.py` |
| LESSON-04 | Atomic write to `~/.cache/vibemix/learn-progress.json` (os.replace pattern) | `tests/learn/test_learn_progress_atomic.py` |
| LESSON-04 | Corruption → silent unlink + fresh empty + `was_recovered: true` flag | `tests/learn/test_learn_progress_corruption_recovery.py` |
| LESSON-04 | Reset CLI `vibemix learn reset` + settings drawer button | `tests/cli/test_learn_reset_cli.py` + `tauri/ui/tests/settings/test_learn_group_reset.spec.ts` |
| LESSON-05 / TONE-02 | Tutor scripts hand-authored JSON, NO live generation of tutor_speak.text | `tests/learn/test_scripts_are_fixtures.py` (AST grep) |
| LESSON-06 / TONE-04 | Tutor system instruction includes the 4-forbidden-moves lock + uses MOOD_PERSONAS["teacher"] | `tests/learn/test_tutor_system_instruction_lock.py` |
| TONE-04 | All AI dialog via `model_router.resolve("learn_tutor")` — zero hardcoded model literals | `tests/llm/test_model_router_no_inline_literals.py` (existing) |

## Wave 0 Requirements

- [ ] `pyproject.toml` += `python-statemachine ^3.1.2` (then `uv sync`)
- [ ] `src/vibemix/llm/_router_config.py` += `"learn_tutor"` route (per Open Q1 in RESEARCH.md)
- [ ] `tauri/ui/src/ipc/messages.schema.json` += 11 oneOf entries + 11 definitions
- [ ] `cd tauri/ui && npm run codegen:ipc` (regenerate `validator.generated.mjs`)
- [ ] AST gate stubs: `test_runtime_invariants.py`, `test_tutor_system_instruction_lock.py`, `test_scripts_are_fixtures.py`
- [ ] Round-trip parity: `tests/ipc/test_learn_envelope_parity.py` extended to 13 envelopes
- [ ] Highlight paint harness: `tauri/ui/tests/learn/highlight-paint.test.ts` (NEW)
- [ ] Test scaffolds for hint/strike/min-dwell + advance predicates + progress atomic + corruption recovery
- [ ] Reset CLI test + settings drawer reset test

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify
- [ ] Sampling continuity holds
- [ ] Wave 0 covers all Wave 0 items above
- [ ] No watch-mode flags
- [ ] Feedback latency < 10 s per-task
- [ ] `nyquist_compliant: true` set after first Wave-0 green

**Approval:** pending
