---
phase: 61-actionable-not-hype-coach-persona
plan: 01
subsystem: coach-persona-test-fence
tags: [tests, coach, anti-slop, harmonic, dual-path, RED-spec]
requires:
  - "Phase 60 harmonic arms (KEY_CLASH / TRANSITION_OPPORTUNITY in coach.py)"
  - "Phase 59 existence-only CitationLinter (key source)"
  - "Phase 10 prompt matrix + dispatch (_VALID_MODES, _prompt_body, _gen_cfg)"
provides:
  - "Coach-cell actionable-not-hype contract asserts (RED spec for 61-02)"
  - "KEY_CLASH + TRANSITION coach-voice fence (GREEN)"
  - "Dual-path _prompt_body / no-new-mode invariant proof (GREEN)"
  - "Coach-context fabricated-key strip proof (GREEN)"
affects:
  - "tests/prompts/test_matrix.py"
  - "tests/state/test_coach.py"
  - "tests/agent/test_dj_cohost_matrix_dispatch.py"
  - "tests/agent/test_coach_prompt_grounding.py"
tech-stack:
  added: []
  patterns:
    - "RED-spec fencing: write the contract asserts first, let them fail, 61-02 turns them green"
    - "Word-token verb check via re.findall to avoid substring false-positives"
key-files:
  created: []
  modified:
    - "tests/prompts/test_matrix.py — 4 test_prompt_61_coach_* parametrized groups + import re"
    - "tests/state/test_coach.py — test_task_key_clash_* + test_task_transition_opportunity_*"
    - "tests/agent/test_dj_cohost_matrix_dispatch.py — test_dispatch_61_coach_prompt_body_feeds_both_paths"
    - "tests/agent/test_coach_prompt_grounding.py — test_coach_grounding_61_fabricated_key_strips"
    - ".planning/phases/61-actionable-not-hype-coach-persona/61-VALIDATION.md — Per-Task Map status"
decisions:
  - "Verb-vocabulary assert lands RED for all 3 coach skills (not just BEGINNER/INTERMEDIATE) — PRO also lacks the full canonical word-token set (swap/wait/tighten); the plan required RED for ≥ BEGINNER+INTERMEDIATE, PRO RED is acceptable and is also a 61-02 target."
  - "No xfail markers used — RED-spec failures are tracked by name/grouping (-k 61_coach) so they stay visibly distinct from the 7 pre-existing baseline failures."
metrics:
  duration: "~9 min"
  completed: "2026-05-21"
  tasks: 3
  files-modified: 5
---

# Phase 61 Plan 01: Wave-0 Coach-Persona Test Fence Summary

Laid the Wave-0 test fence for the actionable-not-hype coach sharpening: coach-cell
contract asserts that land RED as the spec for Plan 61-02, plus three Wave-0 gap
tests (KEY_CLASH/TRANSITION harmonic voice, dual-path `_prompt_body` proof,
coach-context fabricated-key strip) that fence already-correct behavior GREEN.
Test files only — no production code, no prompt constants touched.

## What Was Built

### Task 1 — Coach-cell contract asserts (RED spec) — `34cc286`
Four `test_prompt_61_coach_*` parametrized groups (over beginner/intermediate/pro,
mode fixed to coach), grouped under `-k 61_coach`:
- **(a) DJ-verb vocabulary** — word-token check (via `re.findall`) for the FEATURES §147
  canonical set `{kill, swap, cut, filter, wait, tighten, ride}`. **RED** (all 3 skills).
- **(b) prescribe "same line"** — normalized `"same line"` marker. **RED** (BEGINNER/INTERMEDIATE;
  PRO already carries it via matrix.py:506).
- **(c) positive-callout balance** — `any(marker in body)` over synonymous markers
  (props / encouraging / balance / …). **RED for INTERMEDIATE** (BEGINNER has "ENCOURAGING TONE",
  PRO has "PROPS").
- **(d) calm-only TTS tag routing** — coach body has `[chill]`/`[whisper]`, NOT `[excited]`/`[fast]`.
  **GREEN** now (routing already exists; fences Pitfall 5 calm-tag drift).

### Task 2 — KEY_CLASH/TRANSITION harmonic voice fence (GREEN) — `3ccaa20`
Two tests in test_coach.py modeled on the MIX_MOVE anti-slop analog, using `_ev(...)`:
- `test_task_key_clash_*`: asserts a DJ-verb move (kill/cut/filter), BOTH keys cited
  exactly (`[key:A:8A]` + `[key:B:2A]`), no-invent guard, system-owns-verdict framing
  ("you do NOT decide this" / "confirmed by the system"), and the pre-computed
  "3 semitones apart" + "do NOT compute intervals".
- `test_task_transition_opportunity_*`: past-tense-only framing ("PAST-TENSE",
  "no present-tense advice", "the moment's already gone"), both keys cited, no-invent,
  and the `clash=False` → "the keys sat fine together" verdict branch.
Both GREEN against the Phase-60 arms (coach.py:267-316). Closes the Wave-0 gap from 61-RESEARCH.

### Task 3 — Dual-path COACH-02 proof + coach-context anti-slop (GREEN) — `9fdc2e5`
- `test_dispatch_61_coach_prompt_body_feeds_both_paths` (dispatch test): asserts
  `agent._gen_cfg.system_instruction == agent._prompt_body` — the genai path (dj_cohost.py:447)
  and the OpenRouter `stream_or` path (:813-816) consume the SAME body, no path-specific
  persona code. Also asserts the rendered COACH_PRO prefix and the no-new-mode invariant
  `_VALID_MODES == {"hype","coach"}`. **GREEN.**
- `test_coach_grounding_61_fabricated_key_strips` (grounding test): with a snapshot that
  observed no `key`, a fabricated `[key:A:12B]` runs through `CitationLinter` and the WHOLE
  turn strips (`valid is False`, `reason == "invalid_atoms"`). **GREEN.** Linter NOT modified.

## RED-spec vs Already-Green (explicit)

| Assert | Status | Owner |
|--------|--------|-------|
| coach verb vocabulary (a) | **RED** (3 skills) | 61-02 turns green |
| coach prescribe same-line (b) | **RED** (beginner, intermediate) | 61-02 |
| coach positive-callout balance (c) | **RED** (intermediate) | 61-02 |
| coach calm-only tag routing (d) | GREEN | — |
| KEY_CLASH harmonic fence | GREEN | — |
| TRANSITION harmonic fence | GREEN | — |
| dual-path `_prompt_body` equality + no-new-mode | GREEN | — |
| coach-context fabricated-key strip | GREEN | — |

The 6 RED `61_coach` failures are the intended spec for 61-02; they are grouped under
`-k 61_coach` and named distinctly so they never blur with the 7 pre-existing baseline failures.

## Deviations from Plan

None — plan executed exactly as written. (Note: the verb-vocabulary assert is RED for PRO
as well as BEGINNER/INTERMEDIATE; the plan only required RED for ≥ BEGINNER+INTERMEDIATE, so
this is within spec and is also a 61-02 target.)

## Verification

- **Hype-fence subset** (`tests/prompts/test_matrix.py tests/state/test_coach.py
  tests/agent/test_persona.py tests/agent/test_hype_prompt_grounding.py`):
  130 passed, 6 failed — the 6 failures are EXACTLY the RED `61_coach` cell-contract asserts.
  Every hype golden + persona byte-identity + hype-grounding test passes (hype goldens byte-stable).
- **Full suite**: 13 failed, 4079 passed, 26 skipped.
  - Baseline before this plan: 7 failed, 4069 passed (captured at start).
  - Delta: +6 failures (all the intended RED `61_coach` asserts) + 10 new passing tests
    (4 calm-tag GREEN + 2 harmonic + 2 dispatch/anti-slop, etc.). The 7 pre-existing failures
    are byte-for-byte the same set — no NEW failures introduced beyond the RED spec.
- No production module modified (`matrix.py`, `coach.py`, `dj_cohost.py`, `citation_linter.py`
  all untouched). No hype anchor or coach `ANCHOR_PHRASES` entry modified.

## Known Stubs

None.

## Self-Check: PASSED

- tests/prompts/test_matrix.py — FOUND (modified, contains `test_prompt_61_coach`)
- tests/state/test_coach.py — FOUND (contains `test_task_key_clash`)
- tests/agent/test_dj_cohost_matrix_dispatch.py — FOUND (contains `test_dispatch_61_coach_prompt_body_feeds_both_paths`)
- tests/agent/test_coach_prompt_grounding.py — FOUND (contains `test_coach_grounding_61_fabricated_key_strips`)
- Commit 34cc286 — FOUND
- Commit 3ccaa20 — FOUND
- Commit 9fdc2e5 — FOUND
