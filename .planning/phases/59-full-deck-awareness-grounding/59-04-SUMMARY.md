---
phase: 59-full-deck-awareness-grounding
plan: 04
subsystem: state
tags: [deck-poller, single-writer, refresh, evidence-registry, coach, cross-deck-suppression, camelot, stub-events]

# Dependency graph
requires:
  - phase: 59-full-deck-awareness-grounding (Plan 59-01)
    provides: harmonics.to_camelot, DeckTrack/DeckState model, additive MusicState.deck_state field
  - phase: 59-full-deck-awareness-grounding (Plan 59-02)
    provides: dedicated existence-only `key:` evidence source + linter rule (DECK-03)
  - phase: 59-full-deck-awareness-grounding (Plan 59-03)
    provides: KEY_CLASH/TRANSITION_OPPORTUNITY event priorities + cooldowns; DECK-05 read-only repo gate
provides:
  - "DeckPoller — the THIRD external read-only snapshot producer (after ControllerState/TrackInfo): XML source ladder + cross-deck suppression + honest unknown"
  - "_tick_once single-writer copy of deck_source.snapshot() into MusicState.deck_state under state._lock (DECK-04) — the ONLY assignment site of state.deck_state.decks"
  - "camelot normalized via harmonics.to_camelot inside the lock batch (writer-side pure transform)"
  - "change-only, confidence-gated key:/track: registry writes (bounded growth, cross-deck-uncitable below floor)"
  - "coach evidence_line deck block (decks[A='..' 8A 128bpm | ..] / decks=unknown) — out of the diet/ack path"
  - "KEY_CLASH + TRANSITION_OPPORTUNITY task_for_event STUB arms (no firing — Phase 60)"
  - "DeckPoller spawned in __main__ + threaded into the single writer"
affects: [60-harmonic-feedback-confidence-gate, 59-05 vision deck-read]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-writer copy site: a read-only producer owns its holder; _tick_once is the ONLY thing that copies snapshot() into MusicState under state._lock — third such source after ControllerState/TrackInfo"
    - "Writer-side normalization: the poller leaves camelot=None; the µs-cost to_camelot transform runs INSIDE the lock so the producer cadence stays pure-read"
    - "Change-only registry writes: capture prev (side,camelot) BEFORE reassignment, write only on diff + confidence>=floor, try/except so a write failure can't kill the tick (mirrors the mix:audible_deck pattern)"
    - "Golden-equivalence gate: the evidence_line deck block is gated on a non-empty deck_state so an empty deck_state stays byte-identical to the 59-01 baseline (Pitfall 5)"
    - "Plumbing stub arms: KEY_CLASH/TRANSITION_OPPORTUNITY route through the normal (non-diet) path with a graceful placeholder so an accidental fire degrades instead of hitting the bland default"

key-files:
  created:
    - .planning/phases/59-full-deck-awareness-grounding/59-04-SUMMARY.md
  modified:
    - src/vibemix/state/refresh.py
    - src/vibemix/state/coach.py
    - src/vibemix/__main__.py
    - tests/state/test_refresh_deck.py
    - tests/state/test_coach_prompt_grounding.py
    - .planning/codebase/orphans.csv
    - .planning/phases/59-full-deck-awareness-grounding/deferred-items.md

key-decisions:
  - "deck_source is an optional arg defaulting None on BOTH _tick_once and state_refresh_loop — every existing direct _tick_once test passes unchanged (None → deck path skipped)"
  - "Change-only detection reuses the prior state.deck_state.decks camelot values (captured before reassignment) rather than threading new loop-local state — the deck_state IS the prev-tick record, mirroring the mix:audible_deck prev_deck pattern"
  - "evidence_line deck block GATED on non-empty deck_state (decks!={}) — empty emits NOTHING (not decks=unknown) to preserve the 59-01 byte-identical golden; decks=unknown only fires when decks are present but none clear the 0.3 render gate"
  - "DeckPoller reuses the SAME cache-warm RekordboxLibrary (deck_library) + the SAME controller_state/track_info instances the refresh loop owns — no second XML import, no duplicate state (DECK-05 read-only)"
  - "replace_decktrack (Task-1 module-level helper) registered in the orphan-inventory baseline via a surgical single-line add — the two unrelated stale baseline entries (BlackHoleProbeResult, set_device_nominal_sample_rate, in-flight v4.0 WIP) left untouched"

patterns-established:
  - "Third external snapshot producer composed into the single writer without a new lock or a new state object"
  - "Producer leaves the expensive-to-normalize field None; the single writer normalizes it inside the lock"

requirements-completed: [DECK-01, DECK-02, DECK-04, DECK-05]

# Metrics
duration: ~35min (resume of an interrupted session — Task 1 pre-completed)
completed: 2026-05-21
---

# Phase 59 Plan 04: Deck-Poller Single-Writer Integration + Coach Surfacing Summary

Wired the read-only `DeckPoller` (Task 1, pre-completed in the prior session) into the 10Hz single writer and surfaced its grounded deck-state to the coach — the integration spine that composes the already-shipped rails (`RekordboxLibrary` XML cache, `derive_audible_deck`, `harmonics.to_camelot`, the `key:` source) into a citable deck-state without ever breaking the single-writer invariant.

## What shipped (this session — resumed from the interrupt)

**Task 2 — `_tick_once` single-writer wiring (TDD RED→GREEN):**
- Committed the pre-written RED test `tests/state/test_refresh_deck.py` (`ecb3b0d`, 9 failing / 1 passing as expected), then implemented GREEN (`edb9430`).
- Added `deck_source` (optional, default `None`) to both `_tick_once` and `state_refresh_loop`; threaded through the loop's `_tick_once` invocation.
- Inside `with state._lock:`: capture prev `(side, camelot)` → `deck_snap = deck_source.snapshot()` → normalize each `dt.camelot = to_camelot(dt.key)` (pure µs cost, writer-side) → `state.deck_state.decks = deck_snap` + `updated_at = now`. This is the ONLY assignment of `state.deck_state.decks` anywhere in `src/vibemix/`.
- Change-only, confidence-gated `key:`/`track:` registry writes: write only when `(side, camelot)` changed AND `confidence >= DECK_CITE_MIN_CONF` AND `camelot` present; wrapped in try/except so a registry-write failure cannot kill the tick. A sub-floor deck produces no `key:` write → Phase 60's cross-deck clash is uncitable-by-construction.

**Task 3 — coach surfacing + `__main__` spawn (`7b0f283`):**
- `evidence_line` deck block (additive, gated on non-empty `deck_state`): resolved decks render `decks[A='Strobe' 8A 128bpm | ...]` (camelot present + confidence ≥ 0.3); present-but-unresolved renders honest `decks=unknown`; empty `deck_state` emits nothing → byte-identical to the 59-01 golden baseline.
- Deck block is NOT in `_evidence_line_compact`; `KEY_CLASH`/`TRANSITION_OPPORTUNITY` are NOT in `ACK_ELIGIBLE_EVENTS` — deck-state is substantive full-payload (out of the diet/ack path).
- `task_for_event` STUB arms for `KEY_CLASH` + `TRANSITION_OPPORTUNITY` — minimal "react to what you hear" placeholders routed through the normal path, NO firing/clash narration (Phase 60 fills them).
- `__main__`: `DeckPoller` instantiated reusing the cache-warm `RekordboxLibrary` (read-only) + the SAME `controller_state`/`track_info` instances; `run_poll_loop` task spawned and added to the finally-block cleanup list; `deck_source=deck_poller` threaded into `state_refresh_loop`.
- Tightened `tests/state/test_coach_prompt_grounding.py`: the obsolete "populated deck_state does not change evidence_line yet" test replaced with resolved-renders + present-but-unresolved=unknown assertions (the empty-state golden tests stay green).

## Verification

- `tests/state/test_refresh_deck.py` + `tests/state/test_refresh.py` — 53 green.
- Coach/diet/grounding/deck-poller/repo-scrub targeted set — 107 green (incl. `test_deck_readonly`).
- Single-writer invariant: `grep -rn "deck_state.decks =" src/vibemix/ | grep -v refresh.py` returns nothing.
- `__main__.py` imports cleanly via the venv (livekit present).
- Full suite: **7 failed, 3976 passed, 26 skipped** — the SAME 7 pre-existing `live-tuning-or-brain` WIP failures documented in `deferred-items.md`, count unchanged. None reference deck/poller/coach/refresh.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Orphan-inventory baseline drift from Task-1 helper**
- **Found during:** full-suite run after Task 3.
- **Issue:** `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` failed — `replace_decktrack` (a module-level helper added by Task 1's `deck_poller.py`, used inside `DeckPoller.snapshot()`) was flagged as a NEW orphan not in the committed baseline. An 8th failure on top of the documented 7.
- **Fix:** Surgical single-line add to `.planning/codebase/orphans.csv` registering `replace_decktrack`. Deliberately did NOT use the audit's `--orphan-inventory` regen because that ALSO dropped two unrelated stale entries (`BlackHoleProbeResult`, `set_device_nominal_sample_rate` — in-flight v4.0 WIP, out of this plan's scope). Surgical add resolves my contribution without sweeping unrelated baseline churn.
- **Files modified:** `.planning/codebase/orphans.csv`
- **Commit:** `8a1527c`

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `KEY_CLASH` / `TRANSITION_OPPORTUNITY` task_for_event arms | `src/vibemix/state/coach.py` | Plumbing-only placeholders by design — the detector never fires these types yet; firing logic + real clash/transition narration is Phase 60 (60-harmonic-feedback-confidence-gate). The event priorities/cooldowns were registered in Plan 59-03; the stub arms keep an accidental fire graceful. |
| vision (`source="screen_vision"`) + numpy (`source="numpy_key"`) ladder slots | `src/vibemix/state/deck_poller.py` | Scaffolded ladder slots, not implemented this phase — vision deck-read is Plan 59-05's separate structured eval-gated call (the `dj_cohost.py` `screen_jpeg=None` killswitch stays untouched); the numpy KS estimator is deferred (Open Q2). XML-primary covers the live ladder this phase. |

## Self-Check: PASSED
- `.planning/phases/59-full-deck-awareness-grounding/59-04-SUMMARY.md` — written.
- Commits verified in `git log`: `ecb3b0d` (RED), `edb9430` (GREEN Task 2), `7b0f283` (Task 3), `8a1527c` (orphan baseline). Task 1's `473fe0e`/`187ff48` were committed in the prior session.
