---
phase: 79-lens-three-grounded-modes
plan: 02
subsystem: prompts
tags: [lens, prompt-matrix, byte-identity, anti-injection, selector-over-builder]

requires:
  - phase: 79-lens-three-grounded-modes (Plan 01)
    provides: "tests/prompts/test_lens.py — LENS-01 xfail-strict scaffolds + v4-golden real-green anchor"
provides:
  - "src/vibemix/prompts/matrix.py::LENS_TO_MODE_MOOD — shared lens→(mode,mood) cell map"
  - "src/vibemix/prompts/matrix.py::build_lens_instruction — validate-and-delegate selector over the untouched build_system_instruction"
  - "5 LENS-01 scaffolds flipped xfail-strict → real-green (map / per-lens shape / unknown-lens ValueError / default byte-identity / three-lenses-gate)"
affects:
  - "Plan 03 (LENS-02): build_lens_instruction + LENS_TO_MODE_MOOD are the co-host read target for the shared lens selection"
  - "Phase 81 BENCH: the three lenses this builds are what the lens dimension measures"

tech-stack:
  added: []
  patterns: [validate-and-delegate-wrapper, import-time-drift-guard, cold-path-byte-identity]

key-files:
  created: []
  modified:
    - src/vibemix/prompts/matrix.py
    - tests/prompts/test_lens.py

key-decisions:
  - "build_lens_instruction is a thin selector over the UNTOUCHED build_system_instruction — never a builder fork (truth: one being, three voices, one structured state)"
  - "critique → (coach, coach) is the charter alias onto the matrix coach mode/mood; NO rename of matrix internals (keeps the v4 golden green)"
  - "tutor → (coach, teacher) reuses the coach cell + teacher persona; NO bespoke TUTOR_* cell this phase (Pitfall 4 — tutor fidelity is Phase-81 BENCH + Kaan's ear, parked)"
  - "Import-time assertion pins set(LENS_TO_MODE_MOOD) == set(_CURATOR_LENS_TO_MOOD) so the two surfaces can never fork the lens vocabulary"

patterns-established:
  - "Validate-and-delegate wrapper: normalize lens.lower().strip() → fail-loud ValueError on unknown → unpack (mode, mood) → delegate to the untouched builder (mirrors build_curator_instruction)"
  - "Import-time drift guard: an assert ties two parallel maps to one shared enum so they cannot silently diverge"

requirements-completed: [LENS-01]

duration: ~12min
completed: 2026-05-26
---

# Phase 79 Plan 02: LENS-01 Selector Over the Untouched Builder Summary

**`LENS_TO_MODE_MOOD` map + `build_lens_instruction` validate-and-delegate wrapper — three grounded lenses (hype/critique/tutor) over the SAME untouched `build_system_instruction`, default hype byte-identical to today's co-host default.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-26
- **Completed:** 2026-05-26
- **Tasks:** 1 (TDD — scaffolds from Plan 01 are the RED, this is the GREEN)
- **Files modified:** 2

## Accomplishments
- Added `LENS_TO_MODE_MOOD: dict[str, tuple[str, str]]` mapping `hype→(hype,hype-man)`, `critique→(coach,coach)`, `tutor→(coach,teacher)` — co-located directly after `build_curator_instruction` so the lens vocabulary stays with the curator's.
- Added `build_lens_instruction(lens="hype", skill="intermediate", **kw)` — validates the lens (unknown → `ValueError` listing valid lenses, mirroring the mood/skill guards), unpacks the `(mode, mood)` cell, and delegates to the UNTOUCHED `build_system_instruction`. The default hype lens resolves to `build_system_instruction("intermediate","hype","hype-man")` — byte-identical to today's default by construction.
- Added an import-time drift guard: `assert set(LENS_TO_MODE_MOOD) == set(_CURATOR_LENS_TO_MOOD)` so the co-host and curator lens vocabularies can never fork.
- Flipped the 5 LENS-01 xfail-strict scaffolds in `tests/prompts/test_lens.py` to real-green (lens map, per-lens prompt shape, unknown-lens ValueError, default byte-identity, three-lenses-through-the-gate). The LENS-02 scaffold stays xfail (Plan 03).

## Task Commits

1. **Task 1: Add LENS_TO_MODE_MOOD + build_lens_instruction (selector over the untouched builder)** — `a0bde15` (feat)

_TDD note: Plan 01 installed the RED scaffolds; this plan is the GREEN — implementation + scaffold-flip committed together as one atomic feat (no separate test commit, the failing tests already existed)._

## Files Created/Modified
- `src/vibemix/prompts/matrix.py` — added `LENS_TO_MODE_MOOD` map, import-time drift guard, and `build_lens_instruction` wrapper after `build_curator_instruction`. `build_system_instruction`, `_CELLS`, `MOOD_PERSONAS`, `_CURATOR_LENS_TO_MOOD` all untouched.
- `tests/prompts/test_lens.py` — removed the `@pytest.mark.xfail(strict=True)` decorators from the 5 LENS-01 scaffolds; dropped the now-unused `_LENS_REASON_01` constant.

## Decisions Made
- **Selector, not a fork.** `build_lens_instruction` is strictly additive ABOVE `build_system_instruction`; it never edits the builder/cells/personas. This is what keeps the v4 byte-identity golden green and satisfies the charter truth "one being, three voices, one structured state".
- **`critique` is an alias, not a rename.** Charter `critique` maps onto the existing matrix `coach` mode/mood — no matrix-internal rename (which would break the v4 golden).
- **`tutor` = `(coach, teacher)`, no bespoke cell** (Pitfall 4). Whether the tutor lens actually teaches well is parked for Phase-81 BENCH + Kaan's ear.
- **`**kw` forwarded verbatim** to the builder so callers can still pass `include_citation_grammar` etc.

## Deviations from Plan

None - plan executed exactly as written. (The plan called out that `_LENS_REASON_01` would become unused after flipping the scaffolds; removed it to keep the lint clean — this is the plan's intended scaffold-flip, not a deviation.)

## Issues Encountered
None.

## Authentication Gates
None.

## Known Stubs
None. The lens layer is fully wired and tested; no placeholders.

## Verification
- `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py tests/prompts/test_matrix.py tests/repo/test_model_literal_gate.py` → **107 passed, 1 xfailed** (the LENS-02 scaffold), zero xpassed, zero failures.
- Full suite: `PYTHONPATH=src python3 -m pytest -q` → **4497 passed, 26 skipped, 5 xfailed, 4 xpassed** in 240s. Net +5 passed vs Plan-01 baseline (4492) — exactly the 5 LENS-01 scaffolds flipping green. The 4 xpassed are pre-existing live-only markers (wizard port-bind + macOS BlackHole kext) carried over from Plan 01, unrelated to this plan. The 5 xfailed = 4 LENS-02 scaffolds (Plan 03) + the pre-existing budget cost gate.
- v4 byte-identity golden (`tests/prompts/test_matrix.py`) fully green — builder/_CELLS/MOOD_PERSONAS untouched.
- Model-literal gate green — no hardcoded model name introduced. No `genai.Client`, no `GEMINI_API_KEY`, no network.

## TDD Gate Compliance
This plan is the GREEN half of a Plan-01/Plan-02 RED/GREEN split: Plan 01's `test(79-01)` commits installed the failing xfail-strict scaffolds; this plan's `feat(79-02): a0bde15` makes them pass. The GREEN gate commit is present; the RED gate lives in Plan 01's history (commits bb74088, 6d6ee02).

## Next Phase Readiness
- LENS-01 satisfied: hype/critique/tutor are three grounded prompt lenses over one builder; switching lens changes voice, not facts.
- Plan 03 (LENS-02) can now wire `build_lens_instruction` + `LENS_TO_MODE_MOOD` as the co-host read target for the shared `ConfigStore.extra["lens"]` selection, flipping the 4 remaining LENS-02 scaffolds.

## Self-Check: PASSED

- `src/vibemix/prompts/matrix.py` carries `build_lens_instruction` — FOUND.
- `.planning/phases/79-lens-three-grounded-modes/79-02-SUMMARY.md` — FOUND.
- Task commit `a0bde15` present in git history — FOUND.

---
*Phase: 79-lens-three-grounded-modes*
*Completed: 2026-05-26*
