---
phase: 96-course-3-play-mode
plan: 01
subsystem: state + learn (AST gates + MusicState fields + evidence_line lens marker)
tags: [course-3-play-mode, ast-gates, confidence-gate, trust-the-audio, invariant-3-pin, runtime-gate-first]
requirements:
  - CURR-3.07
provides:
  - tests/learn/test_no_speculative_phrase.py (AST gate — Invariant #3 BIND)
  - tests/learn/test_course3_uses_existing_coach.py (AST gate — reuse-existing-coach BIND)
  - src/vibemix/state/music_state.py:session_active (additive field; default False)
  - src/vibemix/state/music_state.py:phrase_position_confidence (additive field; default 0.0)
  - src/vibemix/state/music_state.py:next_phrase_at (additive field; default None)
  - src/vibemix/state/coach.py:_COUNT_IN_BPM_FLOOR (=0.8)
  - src/vibemix/state/coach.py:_COUNT_IN_PHRASE_FLOOR (=0.7)
  - src/vibemix/state/coach.py:_count_in_eligible() (the runtime conditional)
  - src/vibemix/state/coach.py:AICoach.evidence_line (gated lens=<...> marker)
  - tests/state/test_coach_course3_confidence_gate.py (9 runtime gate tests)
requires:
  - src/vibemix/state/music_state.py (existing dataclass extended additively)
  - src/vibemix/state/coach.py (existing AICoach.evidence_line extended with gated branch)
affects:
  - downstream Plan 96-02 (consumes the gate marker via build_tutor_system_instruction prompt path)
  - downstream Plan 96-03 (fixtures + ExemplarPlayer guard consume session_active)
key-files:
  created:
    - tests/learn/test_no_speculative_phrase.py
    - tests/learn/test_course3_uses_existing_coach.py
    - tests/state/test_coach_course3_confidence_gate.py
  modified:
    - src/vibemix/state/music_state.py
    - src/vibemix/state/coach.py
    - src/vibemix/learn/prompts.py (opt-out annotation)
tech-stack:
  added: []
  patterns:
    - ast.walk over src/vibemix/learn/**/*.py (static gate; pure-stdlib; <50 ms wall)
    - opt-out comment scanner walks the contiguous header block above a def
    - additive default-safe dataclass field extension (preserves v8.0 byte-identical golden)
    - gated evidence_line marker emit (session_active=False → ZERO bytes)
decisions:
  - "_has_opt_out_comment scans the CONTIGUOUS header block above the def, not just the line immediately above; the planner's stricter shape would have missed the natural placement of opt-out comments (the build_tutor_system_instruction case)."
  - "prompts.py::build_tutor_system_instruction annotated with the opt-out token; it composes the SESSION-LEVEL system instruction (persona + frames + lock), not a per-turn prompt body. Per-turn composition routes through AICoach at the call site (P96-03)."
  - "Float comparison semantic: bpm_confidence >= 0.8 (not strictly greater) — at-floor passes. Pinned by test_count_in_at_exact_floor_passes."
metrics:
  duration: ~30 minutes
  completed: 2026-05-28
---

# Phase 96 Plan 01: AST Gates + MusicState Extension + Confidence Gate Summary

Land the three Invariant #3 enforcement primitives BEFORE any Gemini wiring touches the Course 3 proactive tutor lens — two static AST gates (no-phrase-guessing + reuse-existing-coach) and one runtime gate (the evidence_line lens marker downgrade).

## What Shipped

### AST Gate 1 — `tests/learn/test_no_speculative_phrase.py` (Invariant #3 BIND)

4 tests. Walks `src/vibemix/learn/**/*.py` via `ast.parse` + `ast.walk`, asserts ZERO imports of `numpy.fft` / `scipy.signal` / `scipy.fft` / `librosa.beat` / `librosa.onset`. Detects all three syntactic forms (`import numpy.fft` / `from numpy import fft` / `from numpy.fft import rfft`). Negative-control test plants a synthetic offender under `tmp_path` and confirms the gate fires red with an actionable diagnostic. `__pycache__` + non-Python files are ignored. The real learn/ tree has zero forbidden imports.

This pin guarantees the learn package never computes its own phrase structure — it consumes already-grounded phrase data from `state/refresh.py` + `CueAnchor`. Without this gate, a future planner could write the Course 3 tutor narration with a quick `from scipy.signal import find_peaks` for onset detection, and the tutor would invent "breakdown in 16 beats" structure the audio never showed (the exact Invariant #3 "trust the audio" failure mode).

### AST Gate 2 — `tests/learn/test_course3_uses_existing_coach.py` (reuse-existing-coach BIND)

5 tests. Walks `src/vibemix/learn/{prompts,tutor_narration,proactive_lens,tutor}.py` and for every function name matching the prompt-builder smell test (`*tutor_prompt*`, `*build_tutor*`, `*tutor_narration*`, `*compose_prompt*`, `*proactive_lens*`), asserts the body calls `AICoach.build_prompt(...)` or carries the `# allow-tutor-prompt-without-coach: <reason>` opt-out comment. Negative-control synthetic offender reds the gate; positive-control complier passes; out-of-scope `runtime.py` modules ride forward (scope narrows by filename — only the 4 named composition modules).

`src/vibemix/learn/prompts.py::build_tutor_system_instruction` (P92-01 ship) was correctly flagged by the gate. Annotated with the opt-out comment in a contiguous header block above the function — it composes the **session-level** system instruction (persona + course frame + controller frame + lesson addendum + 4-forbidden-moves lock), **not** a per-turn prompt body. Per-turn composition routes through `AICoach.build_prompt` at the call site (Plan 96-03's proactive lens wrapper).

The opt-out comment scanner walks the contiguous block of comment/blank lines above the def, breaking at the first non-comment non-blank line. This is the natural place a planner annotates "this looks like a prompt builder but is not" — the spec's stricter "line immediately above" shape would have missed this real-world placement. Decision documented in §decisions above.

### MusicState Extension — 3 Additive Default-Safe Fields

Added immediately before `_lock` (per the planner's spec — the v8.0 field-order golden tests pin the existing layout):

```python
# Phase 96 (Plan 96-01) — Course 3 proactive tutor lens scaffolding.
session_active: bool = False
phrase_position_confidence: float = 0.0  # 0..1 — 0 means "no phrase lock yet"
next_phrase_at: float | None = None  # set_seconds; None = cold
```

All three are **written ONLY by `state/refresh.py`** (Invariant #1 single-writer; learn/ never writes — pinned by `tests/learn/test_runtime_invariants.py` AST gate). All three default to OFF / cold so the v8.0 byte-identical evidence_line golden in `tests/state/test_coach.py` stays green (the new fields read in a gated branch only).

### evidence_line Lens Marker — Runtime Gate

Added module-level threshold constants + helper above the `AICoach` class:

```python
_COUNT_IN_BPM_FLOOR: float = 0.8
_COUNT_IN_PHRASE_FLOOR: float = 0.7

def _count_in_eligible(state: "MusicState") -> bool:
    return (
        state.bpm_confidence >= _COUNT_IN_BPM_FLOOR
        and state.phrase_position_confidence >= _COUNT_IN_PHRASE_FLOOR
        and state.next_phrase_at is not None
    )
```

Added a gated marker emit at the very end of `evidence_line` (after the `recall_moments` block, before the final `return " | ".join(e)`):

- `state.session_active == False` (default cold path) → emits **ZERO bytes** → v8.0 byte-identical golden preserved.
- `state.session_active == True AND _count_in_eligible(state)` → emits `"lens=count_in_eligible[next@<t>]"` with `state.next_phrase_at` formatted to 1-decimal precision.
- `state.session_active == True AND any floor fails` → emits `"lens=retrospective_only"`.

The marker is per-turn instruction to Gemini: count-in language is permitted only when grounded. Combined with the AST gate (`test_no_speculative_phrase.py`) preventing learn/ from computing its own phrase data, fabricated count-ins are **uncitable-by-construction** at both structural and runtime layers.

### Runtime Gate Tests — `tests/state/test_coach_course3_confidence_gate.py`

9 tests covering:
1. Constants locked at orchestrator brief thresholds (0.8 / 0.7)
2. MusicState default extension safe (cold defaults)
3. Cold-state emits no lens marker (v8.0 byte-identity preservation)
4. High confidence with session_active=False still emits no marker
5. Downgrade when bpm_confidence below floor
6. Downgrade when phrase_position_confidence below floor
7. Downgrade when next_phrase_at is None
8. count_in_eligible when all floors pass (emits `next@42.5`)
9. At-exact-floor passes + just-below-floor downgrades (numeric edge)

## Verification

```
tests/learn/test_no_speculative_phrase.py             4 passed
tests/learn/test_course3_uses_existing_coach.py       5 passed
tests/state/test_coach_course3_confidence_gate.py     9 passed
tests/state/test_coach.py + sibling goldens         111 passed
tests/learn/ (full suite)                           209 passed / 3 expected skips
```

All P92+P93+P94+P95 invariant pins stay GREEN. v8.0 byte-identical evidence_line golden stays GREEN.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `_has_opt_out_comment` lookback too narrow**
- **Found during:** Task 2 verification
- **Issue:** The planner's spec restricted the opt-out comment to the function-def line or the line directly above it. `src/vibemix/learn/prompts.py::build_tutor_system_instruction` carries a documentation header block that is the natural place to annotate "this is a system-instruction composer, not a per-turn prompt builder" — but the opt-out comment sits ~8 lines above the def, separated from it only by other comment/blank lines.
- **Fix:** Widened the helper to walk the contiguous block of comment/blank lines above the def, breaking at the first non-comment non-blank line. This matches the natural Python convention for documenting a function with a multi-line header.
- **Files modified:** `tests/learn/test_course3_uses_existing_coach.py`
- **Commit:** `deedbc21` (Task 2 commit)

### Annotations Added

**`src/vibemix/learn/prompts.py::build_tutor_system_instruction`** — added the `# allow-tutor-prompt-without-coach: <reason>` annotation explaining that this is the SESSION-LEVEL system instruction composer (P92-01 LESSON-05 ship), not a per-turn prompt builder. Per-turn composition routes through `AICoach.build_prompt` at the call site (Plan 96-03's proactive lens wrapper).

## KAAN-ACTION Parks

None added in 96-01. The `§LEARN-EAR-COURSE-3` discharge target stays parked for P98.

## Commits

| # | Hash | Message |
| --- | --- | --- |
| 1 | `d2fa518d` | `test(96-01): land AST gate test_no_speculative_phrase.py (Invariant #3 BIND)` |
| 2 | `deedbc21` | `test(96-01): land AST gate test_course3_uses_existing_coach.py + opt-out annotate` |
| 3 | `53061c2f` | `feat(96-01): MusicState +3 fields + AICoach.evidence_line lens marker` |

## Self-Check: PASSED

- All 3 created test files exist and pass.
- All 3 commit hashes resolve in git log.
- v8.0 byte-identical evidence_line golden (`tests/state/test_coach.py`) stays GREEN.
- All P92+P93+P94+P95 invariant pins (test_runtime_invariants / test_no_new_ws_port / test_tutor_system_instruction_lock / test_scripts_are_fixtures) stay GREEN.
- Full tests/learn/ suite: 209 passed / 3 expected skips (pre-existing P93 packaged-bank deferrals).
