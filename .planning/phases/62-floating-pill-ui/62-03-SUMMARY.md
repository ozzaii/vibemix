---
phase: 62-floating-pill-ui
plan: 03
subsystem: api
tags: [websocket, ws-bus, deck-state, serialization, anti-slop, mascot-frame, pill]

# Dependency graph
requires:
  - phase: 59 (deck-awareness)
    provides: MusicState.deck_state (per-deck DeckTrack with title/camelot/key/bpm/confidence, honest-default contract)
provides:
  - "Additive read-only `deck_state` field on the flat 30Hz ws:8765 mascot frame ({side: {title, camelot, key, bpm, confidence}})"
  - "Honest-null on the wire: unresolved deck -> camelot:null + key:null (never fabricated)"
  - "Golden-equivalence: empty deck_state -> {} with all existing flat keys byte-stable"
  - "PILL-03 producer half — the wire source plan 62-04's deck-chips.ts consumes"
affects: [62-04 (deck-chips consumer), 62-05, floating-pill-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive-field-on-flat-mascot-frame (clone of detected_genre/genre_confidence Phase-52 pattern)"
    - "Read-only serialize boundary: ws_bus reads MusicState, single-writer _tick_once untouched"
    - "Honest-null pass-through: None -> JSON null, never a fabricated/recomputed value"

key-files:
  created:
    - tests/runtime/test_ws_bus_deck_state.py
    - .planning/phases/62-floating-pill-ui/deferred-items.md
  modified:
    - src/vibemix/runtime/ws_bus.py

key-decisions:
  - "Emit `deck_state` as `{}` (empty object) when no decks resolved — golden-equivalence, additive-only, existing subscribers byte-undisturbed"
  - "Wire shape = {side: {title, camelot, key, bpm, confidence}} — confidence included so the consumer can dim a low-confidence chip"
  - "`_serialize_deck_state` reads via getattr defensively (older state objects degrade to {} rather than raise)"
  - "camelot/key pass through as-is — never recomputed in ws_bus (_tick_once already normalized camelot via harmonics.to_camelot)"

patterns-established:
  - "Pattern: additive read-only field on the existing ws:8765 flat frame — no new port/socket/transport (one-socket invariant honored)"
  - "Pattern: honest-null on the wire — anti-slop guarantee carried from the Phase-59 source model to the UI surface"

requirements-completed: [PILL-03]

# Metrics
duration: ~10min
completed: 2026-05-21
---

# Phase 62 Plan 03: deck_state on the ws:8765 wire Summary

**Additive read-only `deck_state` field ({side: {title, camelot, key, bpm, confidence}}) serialized onto the EXISTING flat 30Hz mascot frame on ws://127.0.0.1:8765 — honest-null keys, golden-equivalence on empty, single-writer untouched, no new port.**

## Performance

- **Duration:** ~10 min (full-suite regression gate alone ran 3m41s)
- **Started:** 2026-05-21T21:31:08Z
- **Completed:** 2026-05-21T21:36:51Z
- **Tasks:** 3
- **Files modified:** 1 production (`ws_bus.py`); 2 created (test + deferred-items)

## Accomplishments
- Closed the load-bearing wire-source gap PATTERNS flagged: Phase-59 `MusicState.deck_state` existed in-process but was on NEITHER WS frame. It now rides the flat 30Hz frame the pill/mascot consume.
- Honest-null preserved end-to-end: an unresolved deck serializes `camelot: null` + `key: null` (anti-slop — never a fabricated key).
- Golden-equivalence proven: empty `deck_state.decks` serializes `{}` and every pre-existing flat key (`music`/`voice`/`mic`/`deck`/`phase`/`bpm`/`audible`) is byte-identical to the pre-deck_state baseline.
- One-socket / single-writer invariants honored: no new port/socket, no write into `MusicState`, no recomputed camelot. ws_bus is a pure read/serialize boundary.
- Full pytest suite holds at the documented baseline with ZERO new failures from this change.

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Wave-0 RED — deck_state serialization fence** - `a01ef3f` (test)
2. **Task 2: GREEN — additive read-only deck_state on the flat frame** - `c202184` (feat)
3. **Task 3: Full-suite regression gate** - no production change; classification recorded in `deferred-items.md`, committed with plan metadata below

**Plan metadata:** (docs commit — SUMMARY + STATE + ROADMAP + deferred-items)

_RED proof: at Task 1 all 4 tests failed with `KeyError: 'deck_state'`, confirming the field was genuinely absent (the wire-gap). Task 2 made them GREEN._

## Files Created/Modified
- `src/vibemix/runtime/ws_bus.py` - Added module-level `_serialize_deck_state(state)` pure helper + one additive `"deck_state"` key on the flat `mascot_frame` dict (+50 lines, additive only).
- `tests/runtime/test_ws_bus_deck_state.py` - 4 tests: populated deck → wire shape; unresolved deck → null camelot/key; empty deck_state → {} golden-equivalence; emit-boundary intact. Clones the `test_ws_bus_genre_fields.py` mock-serve harness; imports the real Phase-59 `DeckTrack`/`DeckState`.
- `.planning/phases/62-floating-pill-ui/deferred-items.md` - Full-suite failure classification (Task 3): proves all failures are pre-existing branch WIP, none touch ws_bus/deck_state.

## Wire Contract (for plan 62-04's deck-chips consumer)

```jsonc
// flat 30Hz frame on ws://127.0.0.1:8765, additive field:
"deck_state": {
  "A": { "title": "Strobe", "camelot": "8A", "key": "Am", "bpm": 128.0, "confidence": 0.8 },
  "B": { "title": "Untagged", "camelot": null, "key": null, "bpm": 124.0, "confidence": 0.4 }
}
// no decks resolved -> "deck_state": {}
```
`camelot`/`key` are JSON `null` when unresolved — the consumer renders `unknown`, never a fabricated key (matches RESEARCH §Deck-context chip `deckChipText`).

## Decisions Made
- **Empty deck_state → `{}`** (not omitted): keeps the field always-present (stable contract for the consumer) while staying golden-equivalent for existing subscribers. The plan's behavior block accepted "an empty object `{}` (or the agreed empty shape)"; `{}` is the simplest stable contract.
- **`confidence` included on the wire** (beyond the bare `{title, camelot, bpm}` the RESEARCH chip renderer reads): cheap, and lets 62-04 dim a low-confidence chip without a second wire change.
- **Defensive `getattr`** for `deck_state`/`decks`: robust to older/partial state objects (degrade to `{}`, never raise) — the bus must never crash the 30Hz loop.

## Deviations from Plan

None - plan executed exactly as written. The two extra full-suite failures beyond the documented 7-WIP baseline are pre-existing sibling-plan (62-02) WIP (`SNAPSHOT.json` not regenerated after `default.json` gained `"pill"`), not introduced by this plan — see `deferred-items.md`.

## Issues Encountered
- **Full-suite baseline drifted 7 → 9.** Investigated each of the 9 failures: 7 are the documented `live-tuning-or-brain` WIP set (anti-slop-wiring, cut_release ×2, readme-matrix ×2, main-smoke); 2 are `test_capability_snapshot.py` from in-flight plan 62-02 (`default.json` has `"pill"` added but committed `SNAPSHOT.json` was not regenerated). NONE reference `deck_state`/`ws_bus`/`ws_broadcast` (grep-proven). The 4 new deck_state tests are GREEN within the 4087 passed. Resolution: classified + logged in `deferred-items.md`; the 2 snapshot failures are 62-02's responsibility (scope boundary), not fixed here.

## Threat Surface Scan
No new security-relevant surface. T-62-07 (single-writer) mitigated — grep proves zero `state.deck_state =` assignment in ws_bus (read-only). T-62-08 (fabricated key) mitigated — honest-null RED test pins `camelot is None`. T-62-09 (emit-boundary) mitigated — additive field keeps the `("music","voice","mic")` guard intact. T-62-10 (new port) mitigated — grep proves no new listening port (rides existing 8765). No new dependency (T-62-SC N/A).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **PILL-03 producer half is DONE.** The deck-chip wire source is live on the flat 30Hz frame with honest-null + golden-equivalence. Plan 62-04 (`deck-chips.ts`, the CONSUMER half, wave-ordered AFTER this) can now read `frame.deck_state[<side>].{title, camelot, key, bpm, confidence}`.
- No blockers introduced. The 2 sibling capability-snapshot failures are tracked for plan 62-02 (regenerate `SNAPSHOT.json`).

## Self-Check: PASSED
- `tests/runtime/test_ws_bus_deck_state.py` — FOUND
- `src/vibemix/runtime/ws_bus.py` (`deck_state` field) — FOUND
- Commit `a01ef3f` — FOUND
- Commit `c202184` — FOUND

---
*Phase: 62-floating-pill-ui*
*Completed: 2026-05-21*
