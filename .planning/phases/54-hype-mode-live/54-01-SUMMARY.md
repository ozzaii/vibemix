---
phase: 54-hype-mode-live
plan: 01
title: "Trace-replay grounding — hype events fire at real drops/builds, >=2 genres (LIVE-01)"
status: complete
req_ids: [LIVE-01]
commits: 2
---

# 54-01 SUMMARY — Trace-replay grounding regression (LIVE-01)

## What was built

A real-data grounding regression that PINS the proven hype-firing path so a
future change can't silently re-introduce the historical "a clear event passes
with no Event" dead window.

1. **Ground-truth fixture** — `tests/fixtures/hype_trace_genre1.jsonl`, copied
   verbatim from the real captured session `recordings/20260515-112139/events.jsonl`.
   52 event lines (PHASE 21, MIX_MOVE 20, HEARTBEAT 8, LAYER_ARRIVAL 2,
   TRACK_CHANGE 1) with 52 ai_text lines — the **1:1 event→reaction cadence
   documents reliable firing (0 suppressions)** at HEAD. The 29.6s max
   inter-event gap is natural cooldown spacing, NOT a dropped reaction.
   `*.jsonl` is globally gitignored; a documented `!` exception was added in
   `.gitignore` matching the established peer-fixture convention
   (`ddj_flx4_sync_capture.jsonl`).

2. **Trace-replay test** — `tests/state/test_hype_trace_replay.py` drives the
   REAL `EventDetector` (no mocks of the detector itself, clock patched via
   `vibemix.state.event_detector.time.time`):
   - **Genre 1 (real):** every ground-truth PHASE + LAYER_ARRIVAL event provably
     fires the matching Event type within `IN_BAR_TOLERANCE`.
   - **Genre 2 (synthetic-but-grounded):** a BPM-128 house/techno build→drop
     PHASE + a >0.10 high-band LAYER_ARRIVAL both fire — second genre, automated.
   - **Silence/noise between events** (audible=False / bpm out of [100,180])
     returns None — grounded firing, not spray.

## In-bar tolerance

`TOLERANCE = 2.0` (module-local). Derivation: ~1 bar = 4 beats × 60/bpm ≈ 1.65s
@145 BPM .. 1.85s @130 BPM; conservative upper bound 2.0 so a reaction within
~1 bar of a transition counts in-bar. **Plan 02 promotes this to
`vibemix.audio.constants.IN_BAR_TOLERANCE_S` and pins that the constant value
matches this number** — the two Wave-1 plans stayed independent (this plan
inlined the local value; Plan 02's test asserts the constant equals 2.0).

## >=2 genres: automated vs Kaan-action

The automated suite covers ≥2 genres at the EventDetector boundary (genre-1 real
+ genre-2 synthetic). The **real ≥2-genre live drive across Kaan's library on his
Mac is Kaan-action (deferred)** — documented in the module docstring; this test
catches a firing regression before that live pass.

## Reaction machinery NOT modified

This plan added a fixture + a test only. `EventDetector` / cooldowns / `coach_loop`
are untouched — `git diff` confirms no `src/` change.

## A small implementation note (honest)

The genre-1 LAYER_ARRIVAL replay seeds `last_band_signature` directly (a clean
test seam, no fire) rather than via a seeding `detect()` call. Reason: a seeding
`detect()` fires a HEARTBEAT whose 10s global cooldown would then block a LAYER
fire 2s later — which is exactly the cooldown-respect behavior Plan 02 pins. To
isolate the LAYER **fire timing** contract here, the baseline is seeded directly;
the cooldown interaction is owned by Plan 02's regression.

## Verification (real)

- `pytest -q tests/state/test_hype_trace_replay.py` → **6 passed**.
- `pytest -q tests/state/test_event_detector.py` → 53 passed (detector untouched).

## Commits

1. `a891af8` test(54-01): check in real ground-truth hype firing trace fixture (LIVE-01)
2. `ba4549d` test(54-01): trace-replay pins drop/build fire >=2 genres (LIVE-01)
   (Tasks 2 genre-1 + 3 genre-2 — one new test module; splitting it across two
   commits would be artificial. Both task contracts covered + green.)
