---
phase: 20-citation-linter-enforcement-live-mode
plan: 02
subsystem: prompts + coach
tags: [grounding, anti-slop, prompt-fragments, fail-soft, GROUND-08]
requires:
  - 20-01  # CitationLinter + StrippedRateTracker shipped (wave 1)
provides:
  - vibemix.coach.IM_LISTENING_FRAGMENT
  - vibemix.coach.FAIL_SOFT_EXAMPLES
  - build_system_instruction(include_listening_fallback=True) default-on append
  - persona.SYSTEM_INSTRUCTION double-opt-out v4-byte-identity invariant
affects:
  - vibemix.prompts.matrix.build_system_instruction signature (+1 keyword-only kwarg)
  - vibemix.agent.persona.SYSTEM_INSTRUCTION call shape (now double-opt-out)
  - DJCoHostAgent live system instruction (now carries fail-soft rule by default)
tech-stack:
  added: []
  patterns:
    - "Mirror Plan 18-03's CITATION_GRAMMAR_BLOCK opt-out flow exactly — same kwarg style, same byte-identity preservation pattern."
    - "Anti-prompt-injection via fixed module constant (no f-string, no .format)."
key-files:
  created:
    - src/vibemix/coach/prompt_fragments.py
    - tests/coach/test_prompt_fragments.py
  modified:
    - src/vibemix/coach/__init__.py
    - src/vibemix/prompts/matrix.py
    - src/vibemix/agent/persona.py
    - tests/prompts/test_matrix.py
    - tests/agent/test_coach_mood_template.py
decisions:
  - "Fragment lives in vibemix.coach.prompt_fragments (not vibemix.prompts) — single source of truth for Phase 20 prompt-side mitigation copy, package-aligned with the rest of the linter chain (CitationLinter, StrippedRateTracker)."
  - "Append order is body → grammar → fragment (load-bearing): the grammar block primes 'if you cannot cite' before the fragment opens with that exact clause."
  - "IM_LISTENING_FRAGMENT owns its leading '\\n\\n' separator (no extra glue in the dispatcher) so the constant in the fragment file is the single source of formatting truth."
  - "persona.SYSTEM_INSTRUCTION uses the double opt-out (grammar=False + listening=False) — preserves the v4-byte-identity invariant + the import-time `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` gate."
metrics:
  duration: 18m
  completed: 2026-05-14
  tests_added: 13      # 6 prompt_fragments + 7 matrix
  tests_pass_post: 1779
  tests_fail_pre: 9
  tests_fail_post: 9   # unchanged — pre-existing only
---

# Phase 20 Plan 02: I'm-listening Fail-Soft Prompt Mitigation Summary

`IM_LISTENING_FRAGMENT` shipped as a default-on prompt-side mitigation in `build_system_instruction(...)`; failure mode shifts from silent strip to graceful "I'm listening" fail-soft (GROUND-08).

## What Shipped

### `src/vibemix/coach/prompt_fragments.py` (new)

Single source of truth for Phase 20 prompt-side mitigation copy. Two locked constants:

- **`IM_LISTENING_FRAGMENT: str`** — verbatim from CONTEXT D-Prompt-Side-Mitigation. Teaches Gemini that when it would otherwise emit `<silence/>` AND the event class is NOT `KAAN_SPOKE` / `MANUAL`, prefer a humble fail-soft line over the void. Four canonical phrases enumerated inside the fragment body:
  - "I'm listening."
  - "I'm here, just listening."
  - "Tracking it."
  - "Listening through this stretch."
- **`FAIL_SOFT_EXAMPLES: tuple[str, ...]`** — the four phrases as a tuple, for Plan 20-03's replay harness to recognize fail-soft replies in the post-session debrief stream.

Anti-prompt-injection (T-20-02-01): both constants are fixed strings — no f-string, no `.format()`, no `%` substitution, no `$` shell glue. Mirrors `MOOD_PERSONAS` (T-13-05-06) + `CITATION_GRAMMAR_BLOCK` (T-18-03-01) precedent.

### `src/vibemix/prompts/matrix.py` (modified)

`build_system_instruction(...)` extended:

```python
def build_system_instruction(
    skill: str = "intermediate",
    mode: str = "hype",
    mood: str = "hype-man",
    *,
    include_citation_grammar: bool = True,
    include_listening_fallback: bool = True,  # ← Plan 20-02
) -> str:
```

Append order is now `body → CITATION_GRAMMAR_BLOCK → IM_LISTENING_FRAGMENT`. The grammar block primes "if you cannot cite"; the fragment opens with that exact clause — order is load-bearing.

`IM_LISTENING_FRAGMENT` owns its leading `"\n\n"` separator (the dispatcher appends without glue), so the formatting source-of-truth is the constant file.

### `src/vibemix/agent/persona.py` (modified)

`SYSTEM_INSTRUCTION` call updated to the double opt-out:

```python
SYSTEM_INSTRUCTION: str = build_system_instruction(
    "intermediate", "hype",
    include_citation_grammar=False,
    include_listening_fallback=False,
)
assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE  # nosec B101
```

The `assert` is the byte-identity gate; if either kwarg ever drifts from the prior contract, import fails loud. Mirrors the Plan 18-03 opt-out shape exactly.

### `vibemix.coach` package re-exports

`IM_LISTENING_FRAGMENT` + `FAIL_SOFT_EXAMPLES` added to `vibemix.coach.__init__.__all__`; tests import via the package boundary so the re-export contract is part of the lock.

## Tests Delta

**+13 net new tests** (6 in `tests/coach/test_prompt_fragments.py`, 7 appended to `tests/prompts/test_matrix.py`):

| Test | Pins |
|------|------|
| `test_im_listening_fragment_contains_locked_phrase` | "I'm listening" anchor (paraphrase-detect) |
| `test_im_listening_fragment_starts_with_section_header` | "FAIL-SOFT RULE (live mode)" — Phase 18 grep convention |
| `test_im_listening_fragment_is_str` | type + len > 100 (catches accidental blanking) |
| `test_im_listening_fragment_no_user_input_interpolation` | T-20-02-01 — no `{`, `%`, `$` |
| `test_fail_soft_examples_tuple` | tuple, len 4, all str, "I'm listening." present |
| `test_fail_soft_examples_subset_of_fragment` | machine-readable surface in lock-step with prompt body |
| `test_default_path_includes_im_listening_fragment` | GROUND-08 hard requirement — default appends |
| `test_default_path_includes_grammar_block_too` | both Phase 18 + Plan 20-02 active by default |
| `test_grammar_after_cell_body_then_fragment` | append order body < grammar < fragment |
| `test_opt_out_listening_fallback_alone` | suppresses fragment, keeps grammar (Phase 18 backward compat) |
| `test_double_opt_out_byte_identical_to_cell` | persona.SYSTEM_INSTRUCTION path |
| `test_invalid_skill_still_raises` | new kwarg doesn't change ValueError surface |
| `test_persona_system_instruction_still_byte_equal_to_hype_intermediate` | v4-byte-identity invariant intact |

**Suite count delta:** 1766 passing pre-Plan-20-02 → **1779 passing** post (+13). Pre-existing 9 failures unchanged (`test_persona_02_byte_identical_to_v4` + 3 phase15 retention + 3 main_smoke + 1 audio_macos_live + 1 phase05 — all on HEAD before Plan 20-02 started; verified via `git stash` baseline run). 7 platform-skipped (Windows live tests + 1 macOS live opt-in).

## Commits

| SHA | Type | What |
|-----|------|------|
| `c335ab1` | test(20-02) | RED — `tests/coach/test_prompt_fragments.py` (6 failing) |
| `39a4411` | feat(20-02) | GREEN — `vibemix.coach.prompt_fragments` + `__init__` re-exports |
| `9b5bf6b` | test(20-02) | RED — 7 new dispatcher integration tests in `test_matrix.py` |
| `01ce31b` | feat(20-02) | GREEN — dispatcher kwarg + persona double opt-out + 4 pre-existing test forwards |

## Deviations from Plan

**[Rule 1 — Forwarding pre-existing tests through the new kwarg layer]** Four pre-existing byte-identity-vs-cell-constant tests (3 in `tests/prompts/test_matrix.py`, 1 in `tests/agent/test_coach_mood_template.py`) called `build_system_instruction(include_citation_grammar=False)` and asserted equality with `SYSTEM_INSTRUCTION` or `HYPE_INTERMEDIATE`. Once the dispatcher started default-appending `IM_LISTENING_FRAGMENT`, those calls returned `cell + fragment` instead of `cell` — breaking the original semantic intent of the tests (which was "the cell-constant opt-out path returns the constant byte-for-byte"). Fix: forward each test to the new double-opt-out shape (`include_citation_grammar=False, include_listening_fallback=False`) so the asserted equality continues to express "the cell constant is preserved at the dispatcher boundary when both layers are opted out". Mirrors how Plan 18-03 amended the original Phase 4/10 byte-identity tests when `include_citation_grammar` was introduced. Files modified:
- `tests/prompts/test_matrix.py::test_prompt_01_hype_intermediate_byte_identical_to_persona`
- `tests/prompts/test_matrix.py::test_prompt_01_each_cell_dispatches_to_its_constant`
- `tests/prompts/test_matrix.py::test_q_v4_byte_identity_preserved_at_constant_level`
- `tests/agent/test_coach_mood_template.py::test_hype_intermediate_byte_identical_to_v4_invariant_holds_for_default_mood`

These are not bug fixes — they're contract-forward updates required by the deliberate Plan 20-02 dispatcher signature change. No production logic shifted; the test assertions kept their original intent.

## Verification

- `pytest tests/prompts/test_matrix.py tests/agent/test_persona.py tests/coach/test_prompt_fragments.py -q` — all green except the pre-existing `test_persona_02_byte_identical_to_v4` (cohost_v4.py drift, unrelated to Plan 20-02; tracked outside this plan).
- `pytest -q` full suite: **9 failed, 1779 passed, 7 skipped** — matches HEAD baseline (no regression introduced).
- `grep -c include_listening_fallback src/vibemix/prompts/matrix.py` → 3 (signature + docstring + if-block).
- `grep -c "include_listening_fallback=False" src/vibemix/agent/persona.py` → 1 (single opt-out call).
- `.venv/bin/python -c "from vibemix.prompts import build_system_instruction; from vibemix.coach import IM_LISTENING_FRAGMENT; assert IM_LISTENING_FRAGMENT in build_system_instruction()"` → exit 0.
- `.venv/bin/python -c "from vibemix.agent.persona import SYSTEM_INSTRUCTION; from vibemix.prompts.matrix import HYPE_INTERMEDIATE; assert SYSTEM_INSTRUCTION == HYPE_INTERMEDIATE"` → exit 0 (v4-byte-identity invariant intact).
- POC files (`cohost*.py`, `mascot.html`) untouched — `git status --short cohost.py cohost_v2.py cohost_lk.py mascot.html` shows nothing.

## Wave 2 Status

Plan 20-02 is the prompt-side companion to 20-01's runtime linter. With both shipped, the failure mode for ungrounded music-reaction turns now flows: **Gemini emits a fail-soft line → CitationLinter strips it (no citation) → user hears silence rather than slop**, while Gemini's NEXT response (with grounded citation) flows through unmodified. The "graceful degrade under uncertainty" loop is now closed in v1 — Plan 20-03 can begin.

## Self-Check: PASSED

- Files created: `src/vibemix/coach/prompt_fragments.py` ✓, `tests/coach/test_prompt_fragments.py` ✓
- Files modified: `src/vibemix/coach/__init__.py` ✓, `src/vibemix/prompts/matrix.py` ✓, `src/vibemix/agent/persona.py` ✓, `tests/prompts/test_matrix.py` ✓, `tests/agent/test_coach_mood_template.py` ✓
- Commits in `git log --oneline -4`: `c335ab1` ✓, `39a4411` ✓, `9b5bf6b` ✓, `01ce31b` ✓
- Pre-existing 9 failures unchanged ✓
- POC files untouched ✓
