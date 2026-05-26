---
status: partial
phase: 81-bench-the-validation-instrument
source: [81-VERIFICATION.md]
started: 2026-05-26
updated: 2026-05-26
---

## Current Test

[awaiting Kaan — this is THE HARD HUMAN GATE of the milestone; produce-and-park complete, verdict is Kaan's]

## Tests

### 1. Run the bounded two-study produce run (on the funded key)
expected: `uv run python -m vibemix bench run --study A` (architecture-axis, one fixed model), `--study B` (model-axis, best architecture), `--study no-audio` (the decisive "does the intelligence reside in the structured EAR" cell). Cost-bounded + fail-safe — parks any cell on API error/timeout/blocked (`output=""`, `error=...`), never fabricates, never wedges. Records each cell + cost (now against the real pricing lane). See `docs/bench.md`.
result: [pending — KAAN-ACTION, funded key `...32u744`]

### 2. ★ Kaan's-ear VERDICT — the hard human gate
expected: Read the generated review surface (ranked by the auto first-pass: groundedness vs DSP facts / specificity / lens-fidelity — but the auto-score only RANKS, it does NOT decide). Judge "did it click / is it slop", fill the literally-empty `## VERDICT (Kaan fills this)` section, and pick the winning **architecture × model**. Autonomous NEVER filled this in. This is the Phase-16 rule + the anti-slop release gate — your ear is the judge.
result: [pending — KAAN-ACTION, the milestone's central human decision]

### 3. Author the final TASTE_RUBRIC wording (your IP)
expected: Replace the clearly-marked placeholder `TASTE_RUBRIC` in `src/vibemix/bench/matrix.py` with your own wording for "what 'clicked' means" — the non-outsourceable soul layer (like the HYPE_INTERMEDIATE persona). The `with_rubric` taste axis already assembles a distinct prompt with the placeholder; your wording sharpens it.
result: [pending — KAAN-ACTION, Kaan's authored IP]

### 4. Act on the verdict (follow-up)
expected: Once the winner is chosen — set the `live_coach` alias in `src/vibemix/llm/_router_config.py` to the winning model (GROUND-02's one-line swap) and make the winning architecture the live default. Then the milestone's empirical question is answered: the architecture is PROVEN, not asserted.
result: [pending — KAAN-ACTION follow-up after the verdict]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

None — no engineering gaps. All 4/4 BENCH must-haves verified in code (honest green, 4525 passed / 0 failed). The instrument is built: BENCH-01 harness composes the real Phase 77-80 seams (6 dimensions, the no-audio cell, the 429/timeout/blocked fail-safe, cost bounded against the pricing lane), BENCH-02 eval reuses CitationLinter verbatim + ranks-never-decides, BENCH-03 review surface is ranked with a literally-EMPTY verdict. Code review (0 blockers) fixed 4 live-run-robustness warnings (cost no-op, None-text fake-success, no timeout, JSON round-trip misgroup). The 4 items above are the produce-and-park human gate — the live run, **Kaan's-ear verdict (the milestone's central decision)**, the taste-rubric IP, and acting on the verdict. Intentionally deferred to KAAN-ACTION; NEVER faked, never auto-judged, never block the autonomous run.

**This is the phase the whole milestone was built to reach: the empirical test of "does the structured EAR carry the intelligence." Autonomous produced the instrument; Kaan's ear renders the verdict.**
