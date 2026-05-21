# Phase 61 — Deferred Items + KAAN-ACTION (live-ear gate)

Per `gsd-autonomous fully`, this surfaces (does NOT pause). Phase 61 is
**4/4 COACH must-haves engineering-verified** (`61-VERIFICATION.md` status
`human_needed`); the only open items are perceptual live-ear judgments that
code/tests cannot settle. Engineering proceeds.

## KAAN-ACTION 1 — Live coach-mode ear-pass (COACH-01 "real session trace")

Run a real DJ session in **coach** mode (any/all skill levels), listen to
~10–20 coach turns through headphones. Confirm:
- Roughly **half the turns are fresh positive callouts** (props/credit), not
  nothing-but-faults.
- Notes are **prescriptive** (observed → impact → prescribe with a real DJ verb:
  kill/swap/cut/filter/wait/tighten/ride), NOT narration or cheerleading.
- Tone stays **warm "friend in your ear"**, not robotic/cold.
- Cooldown/pacing means it **does not nag** (no constant stream of corrections).

Why human: COACH-01's success criterion says "verifiable on a real session
trace"; warmth / positive-balance / non-nagging are perceptual.

## KAAN-ACTION 2 — WR-01: confirm the lifted EQ/control-naming ban is grounded

The MIX_MOVE clause + `COACH_CLOSING_BLOCK` deliberately lifted the old hard ban
on naming faders/EQ/knobs (Kaan-directed product decision). The `CitationLinter`
only validates bracketed atoms (`[key:…]`/`[ev:…]`), so a **bare prose control
claim is not structurally caught**. During the live session, confirm coach mode
does not invent a specific EQ-band / physical control move (e.g. "you killed the
deck-B lows") that the `recent_moves[8s]` evidence did not actually supply.

Why human: this is the hallucination-gate concern from code-review WR-01; only a
live ear can confirm the model's actual delivery respects the evidence.

> If the ear-pass surfaces a false-positive control claim, the remediation is to
> re-tighten the `COACH_CLOSING_BLOCK` / MIX_MOVE clause in
> `src/vibemix/prompts/matrix.py` (NOT to revert the whole actionable persona).

## Pre-existing full-suite failures on `live-tuning-or-brain` (count: 7 — unchanged)

Phase 61 added zero new failures. The 7 are the documented in-flight WIP failures
(`test_main_anti_slop_wiring`, `test_cut_release_*`, `test_readme_feature_matrix_*`,
`test_main_smoke`) — none touch coach/matrix/prompt/harmonic paths.
