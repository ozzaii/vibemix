---
phase: 54-hype-mode-live
plan: 02
title: "Cooldown respect + in-bar tolerance tuning surface (LIVE-03)"
status: complete
req_ids: [LIVE-03]
commits: 3
---

# 54-02 SUMMARY — Cooldown respect + in-bar tolerance tuning surface (LIVE-03)

## What was built

The in-bar reaction-timing + cooldown surface made explicit, test-pinned, and
one-line tunable — so a tuning change after Kaan's live drive is a single
constant edit + restart, never a re-plan.

1. **`IN_BAR_TOLERANCE_S = 2.0`** added to `src/vibemix/audio/constants.py` in
   the engine-tuning section (right after `HEARTBEAT_SEC`). Documented with the
   1-bar derivation (4 beats × 60/bpm: ~1.65s @145 BPM .. ~1.85s @130 BPM;
   conservative upper bound 2.0). The diff is **purely additive** — no existing
   cooldown value touched.

2. **`tests/state/test_hype_cooldown_grounding.py`** pins, with the REAL
   `EventDetector` + a patched clock:
   - **Cooldowns gate without deafening:** a PHASE fire at t0; a second PHASE
     transition inside the per-type window returns None; a PHASE transition
     after `max(per-type, global) + margin` fires again.
   - **`IN_BAR_TOLERANCE_S` pinned** to 2.0 (matches Plan 01's trace-replay
     value) and asserted in a sane band (0 < x <= 2.5).
   - **v4 cooldown baseline pinned** (PHASE 10 / MIX_MOVE 14 / LAYER_ARRIVAL 10
     / TRACK_CHANGE 5 / global 10 / heartbeat 45) so a future re-tune is a
     visible diff.

3. **`tests/eval/test_replay_harness_cooldowns.py`** extended (additive) with a
   test that derives genre-1-trace per-type gaps and feeds them to
   `_emit_cooldown_report`, asserting PHASE + MIX_MOVE rows appear with
   `median_gap` + `expected_min`. The **tuning instrument provably runs over
   REAL data**.

## No v4 cooldown VALUE changed

`git diff src/vibemix/audio/constants.py` shows ONLY the additive
`IN_BAR_TOLERANCE_S` constant + comment. All `MIN_EVENT_GAP_PER_TYPE` entries,
`EVENT_GLOBAL_MIN_GAP`, and `HEARTBEAT_SEC` are byte-identical to the v4 baseline.

## The --print-cooldowns recipe for the Kaan-action tuning pass

The real-trace report (observed): every measured median gap is WIDER than the
locked floor (PHASE 39.75s vs 10.0, MIX_MOVE 33.60s vs 14.0, HEARTBEAT 102.77s
vs 45.0, LAYER_ARRIVAL 185.69s vs 10.0) — the session legitimately breathes
wider than the floor, so the WARNINGs are observational, not failures. After
Kaan's live drive, re-run the instrument over a fresh captured trace; a
measured-vs-locked delta that consistently lands BELOW the floor (events
crowding) would justify a one-line cooldown edit + restart.

## Verification (real)

- `pytest -q tests/state/test_hype_cooldown_grounding.py` → **4 passed**.
- `pytest -q tests/eval/test_replay_harness_cooldowns.py` → **9 passed**
  (8 existing + 1 new — additive).
- `pytest -q tests/state/test_event_detector.py` → 53 passed (cooldown values
  unchanged; detector suite green).

## Commits

1. `69a9d1a` feat(54-02): add IN_BAR_TOLERANCE_S in-bar timing constant (LIVE-03)
2. `4739f41` test(54-02): pin cooldown respect + in-bar tolerance baseline (LIVE-03)
3. `b16b011` test(54-02): exercise --print-cooldowns over the real captured trace (LIVE-03)
