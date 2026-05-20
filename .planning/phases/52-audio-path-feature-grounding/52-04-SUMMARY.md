# 52-04 SUMMARY — Expose detected genre + confidence on the ws bus (GENRE-02)

**Requirements:** GENRE-02
**Status:** complete

## What shipped

Two additive keys on the 30Hz mascot bus frame in `ws_broadcast`, sourced from
the MusicState fields Plan 52-03 writes:
- `"detected_genre": state.detected_genre`
- `"genre_confidence": state.genre_confidence`

Plus a payload-capture test pinning the fields, the values, the unknown-honesty
case, and the no-empty-frame-guard-trip property.

## The two additive keys + their MusicState source

Added alongside `active_genre` in the `mascot_frame` dict literal (ws_bus.py),
carried exactly the way `phase`/`bpm`/`mood`/`active_genre` are. `detected_genre`
is the FULL-LIBRARY auto-detected genre name (any of `list_profiles()`, or
`"unknown"`); `genre_confidence` is the detector's score in [0, 1]. Both default
to `"unknown"` / `0.0` on a fresh MusicState.

## Anti-slop honesty: enforced at the SOURCE, carried by the bus

The wire shows `unknown` whenever the detector is unsure — never a hallucinated
label. This is enforced at the SOURCE (Plan 52-03's `score_genre` returns
`"unknown"` below the confidence gate / on a tie, and `GenreHysteresis` commits
`"unknown"` immediately). The bus is a dumb wire that carries the value as-is —
it never reshapes or fabricates. A load-bearing comment in ws_bus.py records this
contract. Mirrors the existing `active_genre` "unknown" honesty already on the
wire.

## Empty-frame guard + 30Hz cadence + active_genre unchanged

The fields are STRICTLY ADDITIVE:
- The Phase-51 empty-frame guard (ws_bus.py) checks only `music`/`voice`/`mic` —
  adding keys cannot remove the meter keys, so the guard never trips. PROVEN by
  `test_genre_fields_do_not_trip_empty_frame_guard` (asserts meter keys still
  present in the captured frame).
- `asyncio.sleep(1 / 30)` (the 30Hz cadence, pinned by `test_ws_07`) is
  untouched.
- `active_genre` stays on the wire (parallel field, not replaced) — asserted in
  the new test AND still green in `test_ws_bus_phase22_fields`.
- The `ipc.session.snapshot` block is untouched.

## No-regression sweep result

`pytest -q tests/runtime/test_ws_bus.py test_ws_bus_empty_frames.py
test_ws_bus_snapshot.py test_ws_bus_phase22_fields.py test_ws_bus_genre_fields.py`
→ **27 passed**. Every existing ws_bus pin (cadence, empty-frame, snapshot,
phase22 active_genre/beat_phase) stays green; the additive keys broke nothing.
Task 3 required no fix (the change was genuinely additive).

## Verification (observed)

- `pytest -q tests/runtime/test_ws_bus_genre_fields.py` → **4 passed**.
- ws_bus regression sweep (5 files) → **27 passed**.
- ws_bus parse OK; `grep -c '"detected_genre"|"active_genre"'` → 2 (both present).

## Commits (1 atomic + this summary)

- `958ff89` feat(52-04): carry detected_genre + genre_confidence on the mascot bus frame (GENRE-02).
- `3d7842a` test(52-04): pin detected_genre + genre_confidence on ws bus incl. unknown honesty (GENRE-02).
  (Task 3 was a green regression gate — no fix needed, no commit.)
