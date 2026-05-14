---
phase: 16
status: deferred
deferred_by: gsd-autonomous fully mode
deferred_at: 2026-05-14
deferred_to: kaan-action-required
runs_alongside: P17, P18, P19, P20
---

# Phase 16 — DEFERRED (Kaan's DJ Ear)

Phase 16 is calendar-blocking on Kaan running 3-5 real DJ sessions against the dev build to flag hallucinations, forced reactions, late triggers, and AI-slop.

**Per memory `project_phase_16_kaan_dj_testing`:** Don't auto-build the 30-session replay harness / LLM scorer / F1 validator. Kaan's personal DJ ear-test = the gate.

## What Kaan needs to do

1. Build dev: `npm run tauri dev` (after Phase 15 ear-test signs off)
2. Run a 60-90min ad-hoc DJ session covering one genre slice (e.g., techno)
3. Live-listen + flag in-session: hallucinations, forced reactions, late triggers, AI-slop, missed reactions
4. After session: review `events.jsonl` + replay voice.wav clips via Phase 15 recording browser
5. Write `16-EAR-TEST-{NN}.md` with: date, duration, track list, reactions w/ timestamps, flags, fix-tickets opened against P17/P19/P20
6. Repeat 3-5x across techno / house / hard-tek

## Pass criteria

- 3-5 sessions, each with explicit Kaan PASS verdict
- All flagged hallucinations have fix-tickets routed to P17 (detector), P18 (citation grammar), P19 (latency), or P20 (citation linter)

## Why this can't be auto-built

The bar is "real DJ friend in your ear" — only Kaan's ear can verify that subjectively. Any LLM scorer would itself hallucinate the verdict.

## When Kaan is ready

Just run sessions. Drop `16-EAR-TEST-{NN}.md` files in this dir as you go. Phase closes when Kaan signs the rollup `16-VERIFICATION.md` PASS.

## Status

- ⏸ Deferred to Kaan-action — runs ALONGSIDE P17-P20
