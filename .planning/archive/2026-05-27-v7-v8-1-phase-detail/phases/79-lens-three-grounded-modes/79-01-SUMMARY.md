---
phase: 79-lens-three-grounded-modes
plan: 01
subsystem: prompts / runtime-settings / curator-seam / agent
tags: [tdd-scaffold, xfail-strict, byte-identity, lens, nyquist-safety-net]
requires: []
provides:
  - "tests/prompts/test_lens.py — LENS-01/02 xfail-strict scaffolds + v4-golden real-green anchor"
  - "lens xfail scaffolds wired into 3 existing test files (settings/curator/dj_cohost)"
  - "test-isolation env-leak fix (VIBEMIX_SKILL_LEVEL no longer leaks across files)"
affects:
  - "Plan 02 (LENS-01) flips: lens-map / per-lens-shape / unknown-lens / default-byte-identity / three-lenses-gate"
  - "Plan 03 (LENS-02) flips: apply_lens happy-path / curator-reads-lens / resolve-cell-reads-lens / shared-selection"
tech-stack:
  added: []
  patterns: [pytest-xfail-strict, real-green-pin, snapshot-restore-env-fixture]
key-files:
  created:
    - tests/prompts/test_lens.py
  modified:
    - tests/runtime/test_settings_apply.py
    - tests/library/test_curator_persona_seam.py
    - tests/agent/test_dj_cohost.py
decisions:
  - "Reject-by-fallthrough + cold-path-preservation tests are REAL-GREEN guards, not xfail — they hold today AND must keep holding through Plan 02/03 (a strict-xfail would xpass→fail today)."
  - "Hype lens anchors on the v4 HYPE_INTERMEDIATE opening ('Kaan's friend in his studio'), NOT a MOOD_PERSONAS fragment — the hype default predates the {mood_persona} slot."
metrics:
  duration: ~25m
  tasks: 2
  files: 4
  completed: 2026-05-26
---

# Phase 79 Plan 01: LENS Wave-0 RED Scaffolds + v4-Golden Byte-Identity Pin Summary

Installed the Nyquist safety net for the three-lens layer before any `src/` change: 9 `xfail(strict=True)` scaffolds that flip to real passes when Plan 02 (LENS-01) and Plan 03 (LENS-02) land, plus the real-green guards that pin today's co-host/curator cold paths so a half-wired lens cannot ship green.

## What Was Built

**Task 1 — `tests/prompts/test_lens.py` (NEW, 213 lines):**
- `test_v4_golden_anchor_present` — **REAL-GREEN**. Pins that today's untouched `build_system_instruction("intermediate","hype")` exists and carries its own v4 opening; a regression in the builder fails here before the lens layer is even wired.
- 5 `xfail(strict=True)` scaffolds (LENS-01/02): the shared `LENS_TO_MODE_MOOD` map covers `{hype, critique, tutor}`; per-lens prompt shape is distinct (hype→v4 default, critique→coach persona, tutor→teacher persona); unknown lens raises `ValueError`; default-lens byte-identity (`build_lens_instruction("hype","intermediate") == build_system_instruction("intermediate","hype")`); three-lenses-through-the-gate (the `CitationLinter` strip decision is identical across all three lenses for both a cited and an un-cited reply — strips to `<silence/>`, ack-bank retired); shared-selection-flows-to-both-builders (Plan-03 seam).

**Task 2 — additive scaffolds in 3 existing files:**
- `tests/runtime/test_settings_apply.py`: `apply("lens", ...)` happy-path **xfail-strict** (persistence lands in Plan 03); invalid-value + non-string rejection are **REAL-GREEN** guards (a bad lens must never silently persist — true today via unknown-field fallthrough, true after Plan 03 via enum validation).
- `tests/library/test_curator_persona_seam.py`: curator-reads-shared-lens **xfail-strict**; defaults-to-tutor-when-unset **REAL-GREEN** cold-path guard. Module-global seam caches reset between cases.
- `tests/agent/test_dj_cohost.py`: `_resolve_prompt_cell` reads-shared-lens **xfail-strict**; cold-path byte-identity **REAL-GREEN** guard.

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py` → 1 real-green + 6 xfailed (the file's own xfails), exit 0, no xpassed.
- The four plan files run adjacently: **77 passed, 9 xfailed**, zero failures, zero new xpassed.
- Full suite: **4492 passed, 26 skipped, 10 xfailed, 4 xpassed** (the 4 xpassed are all pre-existing non-strict live-only markers — wizard port-bind + macOS BlackHole kext — unrelated to this plan). Baseline was 4488 passed / 7 xfailed; net +4 real-green + the new strict xfails, zero new failures.
- No `genai.Client`, no `GEMINI_API_KEY`, no network, no new package. No `src/` change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing test-isolation env leak**
- **Found during:** Task 2 (running the new adjacent settings→dj_cohost scaffolds).
- **Issue:** `test_skill_happy_path` calls the applier, which sets `os.environ["VIBEMIX_SKILL_LEVEL"]="pro"` directly (NOT via monkeypatch). That mutation leaked out of the test and corrupted `_resolve_prompt_cell` in any test file running afterwards in the same process — flipping the co-host cell to the leaked "pro" persona, failing `test_agent_02_super_init_kwargs` / `test_agent_03_initial_state`. Confirmed pre-existing (reproduced with my Task-2 changes stashed); the default-order full suite happened not to place the files adjacently, so it was latent. The new Wave-0 lens scaffolds put settings + dj_cohost in adjacent collection, surfacing it.
- **Fix:** Added an autouse snapshot/restore fixture (`_isolate_applier_env`) in `test_settings_apply.py` that captures and restores `VIBEMIX_SKILL_LEVEL`/`VIBEMIX_MODE`/`VIBEMIX_MOOD` around each test. `monkeypatch.delenv` alone cannot undo a key it never recorded a prior value for, so the fixture restores raw values explicitly.
- **Files modified:** tests/runtime/test_settings_apply.py
- **Commit:** 6d6ee02

### Plan-spec adjustment (documented, not a behavior change)

The plan's Task-2 acceptance criterion said "ALL new lens scaffolds report `xfailed`." Four of them (the two settings rejection guards, the curator default-to-tutor guard, and the co-host cold-path byte-identity guard) describe behavior that is ALREADY TRUE today and must KEEP being true through Plan 02/03 — under `strict=True` they would `xpass` → HARD-fail immediately. Per the plan's own truth ("the default/cold-path byte-identity is a REAL-GREEN pin, not xfail") these four were made real-green guards. The genuinely-not-yet-implemented behaviors (persist `extra["lens"]`, read shared lens) stay xfail-strict. Net: 9 strict xfails (5 LENS-01 + 4 LENS-02) + the real-green anchor + 4 real-green preservation guards.

## Known Stubs

None. This plan adds tests only; no stubs, no placeholders.

## Self-Check: PASSED

All 4 test artifacts + SUMMARY.md exist on disk; both task commits (bb74088, 6d6ee02) present in git history.
