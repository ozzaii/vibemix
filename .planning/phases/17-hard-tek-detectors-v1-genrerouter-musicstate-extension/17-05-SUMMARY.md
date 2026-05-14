---
phase: 17-hard-tek-detectors-v1-genrerouter-musicstate-extension
plan: 05
subsystem: state
tags: [genre-router, sense-11, sense-15, dispatch, backward-compat, tdd]
requires: [17-04]
provides:
  - GenreRouter (vibemix.state.genre_router) — atomic per-genre detector
    chain dispatch (SENSE-11)
  - GENRE_REGISTRY (vibemix.events.genres) — single dispatch table
    (composition tier per SENSE-15)
  - vibemix.events.genres.{baseline, house, techno, hard_tek} — per-genre
    chain builder modules
  - EventDetector backward-compat wrapper — same public .detect() API,
    new optional audio_buf kwarg, internal GenreRouter composition
affects:
  - src/vibemix/state/event_detector.py — additive wrap (baseline rules
    byte-identical, genre-chain step inserted before HEARTBEAT)
  - src/vibemix/state/__init__.py — re-export GenreRouter
  - src/vibemix/__main__.py — single-line audio_buf=audio_buf kwarg
  - src/vibemix/state/detectors/kick_swap.py — Rule 1 None-tolerance gate
  - src/vibemix/state/detectors/phrase_boundary.py — Rule 1 None-tolerance gate
tech-stack:
  added: []
  patterns:
    - composition-tier vs implementation-tier separation per SENSE-15
    - atomic-swap dispatch (single attribute reassign)
    - dependency-injected pair contracts (kill before reentry/phrase)
    - graceful-degradation None-tolerance for missing audio_buf
key-files:
  created:
    - src/vibemix/events/__init__.py
    - src/vibemix/events/genres/__init__.py
    - src/vibemix/events/genres/baseline.py
    - src/vibemix/events/genres/house.py
    - src/vibemix/events/genres/techno.py
    - src/vibemix/events/genres/hard_tek.py
    - src/vibemix/state/genre_router.py
    - tests/state/test_genre_router.py
    - tests/state/test_genre_router_integration.py
  modified:
    - src/vibemix/state/event_detector.py
    - src/vibemix/state/__init__.py
    - src/vibemix/__main__.py
    - src/vibemix/state/detectors/kick_swap.py
    - src/vibemix/state/detectors/phrase_boundary.py
    - tests/state/test_event_detector.py
decisions:
  - GenreRouter lives in vibemix.state (NOT vibemix.events) — co-located
    with EventDetector since both are the runtime wiring; vibemix.events
    is the per-genre composition data, not the dispatch mechanism
  - baseline chain returns [] (NOT a v4-rule-port) — keeping baseline
    rules INSIDE EventDetector preserves the SENSE-15 byte-identical
    contract without a structural rewrite
  - audio_buf threading via constructor (default None) — backward-compat
    with coach.py + every existing test fixture; __main__.py is the only
    call site that gets the kwarg
  - chain order is load-bearing — kill MUST precede reentry + phrase in
    techno + hard_tek chains so the freshly-set last_kill_at is observed
    on the same tick
  - None-tolerance for audio_buf-needing detectors (KickSwap,
    PhraseBoundary) — Rule 1 deviation; matches T-17-05 threat note
metrics:
  tasks_complete: 3
  duration_min: 17
  completed_date: 2026-05-14
  tests_added: 20
  tests_passing_total: 1541
  tests_passing_state_audio_runtime: 528
  pre_existing_failures: 9
  net_test_delta: +20
---

# Phase 17 Plan 05: GenreRouter + Per-Genre Dispatch Summary

GenreRouter ships as the SENSE-11 atomic chain swap surface and the SENSE-15
composition tier (`vibemix/events/genres/`) is now wired into the existing
EventDetector. The 6 cross-genre detectors built in Plans 17-02 → 17-04 are
no longer orphaned classes — a Hard Tek track following a house track now
swaps the active detector chain mid-set on the next 100ms tick, no session
restart, no in-flight detection interruption.

`coach.py` is byte-identical (zero edits — every constructor + call signature
is backward-compat). `__main__.py` got a single `audio_buf=audio_buf` kwarg
addition. Every other touched file is additive (new modules + new tests).

## Composition vs Implementation Tier (SENSE-15)

Two distinct tiers, one source-of-truth dispatch table:

- **`vibemix/state/detectors/`** — IMPLEMENTATION tier. Stateful detector
  classes + shared band-limited DSP primitives. Each detector is a single-tick
  unit with `.detect(state, audio_buf, now) -> Event | None` signature.
  Wave-2 (Plans 17-02..17-04) shipped 6 detectors here. Reusable across
  genres — a Hard Tek track slipped into a techno set still benefits from
  KickSwap.

- **`vibemix/events/genres/`** — COMPOSITION tier (NEW in this plan). One
  builder function per genre that instantiates the right detectors with the
  right pair-wiring (`ReentryKickLandDetector(kill_detector=...)`,
  `PhraseBoundaryDetector(kill_detector=...)`) and returns a flat list. Per-
  genre tuning overrides will land here in Plan 06 without touching the
  detector classes themselves.

`GENRE_REGISTRY` in `vibemix.events.genres.__init__` is the single dispatch
table the GenreRouter consults at swap time:

```python
GENRE_REGISTRY = {
    "unknown":  build_baseline_chain,    # → []  (baseline rules inside EventDetector carry detection)
    "house":    build_house_chain,       # → [SubLayerArrival, PhraseBoundary]
    "techno":   build_techno_chain,      # → [KickSwap, KickDensityShift, BreakdownKickKill, ReentryKickLand, PhraseBoundary]
    "hard_tek": build_hard_tek_chain,    # → same as techno (v2.0); +DISTORTION_CLIMB +ACID_LINE_ENTRY in v2.1
}
```

Keys MUST be a SUPERSET of `vibemix.audio.constants.GENRE_BPM_BANDS.keys()`
— pinned by `test_genre_registry_keys_match_genre_bpm_bands`.

## GenreRouter Atomic-Swap Contract

**Single-attribute reassign atomicity (T-17-05-02 mitigation):**

```python
def swap(self, new_genre: str) -> bool:
    if new_genre == self.current_genre and self._initialized:
        return False  # idempotent no-op — chain detectors keep seeded baselines
    builder = GENRE_REGISTRY.get(new_genre)
    if builder is None:
        logger.warning("GenreRouter: unknown genre %r — falling back to 'unknown' baseline", new_genre)
        new_genre = "unknown"
        builder = GENRE_REGISTRY["unknown"]
    self._chain = builder()       # ← single attribute write (GIL-protected)
    self.current_genre = new_genre
    self._initialized = True
    return True
```

Atomicity is structural (asyncio is single-threaded — there's no concurrent
swap anyway). The contract that matters is positional: EventDetector calls
`router.swap()` at the TOP of `detect()` BEFORE any chain iteration, so a
swap mid-call cannot leave a half-iterated chain.

**Idempotency rule (T-17-05-04 mitigation):** same-genre swap is a no-op,
preserving detector baselines (`KickSwapDetector.prev_centroid_hz`,
`BreakdownKickKillDetector.last_kill_at`, etc.) across spurious-equal
flips. Construct ONCE per session — Plan 06's tuning harness uses one
router for the entire WAV scan.

**Unknown-genre fallback (T-17-05-01 mitigation):** any string not in
`GENRE_REGISTRY` is replaced with `"unknown"` + WARN log. The router refuses
to register a chain it doesn't have — caller would otherwise see
`current_genre == "dubstep"` while running the techno chain.

## EventDetector Constructor Signature Change

Backward-compat preserved via default-None:

```python
def __init__(self, audio_buf: AudioBuffer | None = None) -> None:
    ...
    self.audio_buf = audio_buf
    self.router = GenreRouter(initial_genre="unknown")
```

`coach.py` and every existing test fixture still construct
`EventDetector()` with no arguments → router seeds to "unknown" baseline
(empty chain), behavior is byte-identical to v4. Only `__main__.py`
constructs with `EventDetector(audio_buf=audio_buf)` so chain detectors
that need raw samples (KickSwap, PhraseBoundary) can call snapshot APIs.

## Call-Site Impact (the Backward-Compat Gate)

| File | Edit | Reason |
|------|------|--------|
| `src/vibemix/runtime/coach.py` | **NONE** | `event_detector.detect(state, kaan_just_spoke=..., manual=...)` API is unchanged; constructor takes no required args |
| `src/vibemix/__main__.py` | **1 line** — `EventDetector(audio_buf=audio_buf)` | The only call site that has an audio_buf in scope |
| every other call site | **NONE** | EventDetector's public surface is identical |

## Detect() Priority Order (with chain inserted)

```
KAAN_SPOKE > MANUAL > [music-presence gate] > TRACK_CHANGE > PHASE >
LAYER_ARRIVAL > MIX_MOVE > [genre-chain detectors in chain order] > HEARTBEAT
```

Genre-chain runs BEFORE HEARTBEAT so a real genre event always beats the
long-silence catch-all. Genre-chain runs AFTER baseline rules so v4
TRACK_CHANGE wins priority over a genre KICK_SWAP on a tick where both
could fire (pinned by
`test_event_detector_baseline_priority_wins_when_both_fire`).

## Chain Ordering Invariant (kill BEFORE reentry/phrase)

In `build_techno_chain()` and `build_hard_tek_chain()`:

```python
return [kick_swap, kick_density, kill, reentry, phrase]
                                 ^      ^        ^
                                 kill MUST come BEFORE reentry + phrase
```

EventDetector iterates the chain in list order on every tick. On a single
tick where the kill fires, `kill.last_kill_at` is freshly set BEFORE
reentry and phrase observe it (via DI — both detectors hold a reference to
the SAME kill instance). A wrong order silently breaks pair detection
without raising — pinned by `test_techno_chain_contains_all_kick_detectors`.

## Test Count Delta

| Suite | Before | After | Delta |
|-------|-------:|------:|------:|
| `tests/state/test_event_detector.py` | 33 | 41 | +8 |
| `tests/state/test_genre_router.py` (NEW) | 0 | 10 | +10 |
| `tests/state/test_genre_router_integration.py` (NEW) | 0 | 2 (+1 skip) | +2 |
| `tests/state/ + tests/audio/ + tests/runtime/` | 508 | 528 (+1 skip) | +20 |
| **FULL `pytest` suite** | **1521 passed / 9 failed** | **1541 passed / 9 failed** | **+20** |

Pre-existing 9 failures (persona byte-identical, retention sweep,
audio_macos_live, main_smoke wiring, poc_files_untouched) are unchanged —
none introduced by this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] KickSwapDetector + PhraseBoundaryDetector crashed on `audio_buf=None`**

- **Found during:** Task 2 (`test_event_detector_chain_detect_continues_on_none_returns`)
- **Issue:** Both detectors dereferenced `audio_buf._sr` without a None
  guard. EventDetector's default `audio_buf=None` (preserving backward
  compat with `coach.py` callers) caused `AttributeError: 'NoneType'
  object has no attribute '_sr'` the moment a techno chain ran without
  an audio_buf.
- **Fix:** Added a graceful None-tolerance gate immediately after the
  silence gate in both detectors — `if audio_buf is None: return None`.
  Matches the T-17-05 threat-model note: "If `audio_buf` isn't passed
  (None), genre detectors that need raw samples (KickSwap,
  PhraseBoundary) silently can't fire — no exception, no log."
- **Files modified:**
  - `src/vibemix/state/detectors/kick_swap.py` (added gate + updated
    type hint to `AudioBuffer | None`)
  - `src/vibemix/state/detectors/phrase_boundary.py` (same)
- **Commit:** `88ab792`

The four other Wave-2 detectors (SubLayerArrival, KickDensityShift,
BreakdownKickKill, ReentryKickLand) read only `state.bands` /
`state.bpm` — they already ignored audio_buf and didn't need the fix.

## Verification Commands (all pass)

```bash
# 1. State + audio + runtime suite
.venv/bin/python -m pytest tests/state/ tests/audio/ tests/runtime/ -x -q
# → 528 passed, 1 skipped

# 2. Registry keys
.venv/bin/python -c "from vibemix.events.genres import GENRE_REGISTRY; print(sorted(GENRE_REGISTRY.keys()))"
# → ['hard_tek', 'house', 'techno', 'unknown']

# 3. Default router genre
.venv/bin/python -c "from vibemix.state import EventDetector; print(EventDetector().router.current_genre)"
# → unknown

# 4. No new state writers (Phase 3 invariant intact)
grep -c "with state._lock:" src/vibemix/state/event_detector.py src/vibemix/state/genre_router.py
# → 0 0

# 5. Single audio_buf kwarg in __main__.py
grep -n "EventDetector(" src/vibemix/__main__.py
# → 363:    event_detector = EventDetector(audio_buf=audio_buf)
```

## Self-Check: PASSED

All claimed files exist:
- `src/vibemix/events/__init__.py` — FOUND
- `src/vibemix/events/genres/__init__.py` — FOUND
- `src/vibemix/events/genres/baseline.py` — FOUND
- `src/vibemix/events/genres/house.py` — FOUND
- `src/vibemix/events/genres/techno.py` — FOUND
- `src/vibemix/events/genres/hard_tek.py` — FOUND
- `src/vibemix/state/genre_router.py` — FOUND
- `tests/state/test_genre_router.py` — FOUND
- `tests/state/test_genre_router_integration.py` — FOUND

All claimed commits exist:
- `c5d7f74` test(17-05): RED Task 1 — FOUND
- `a13993a` feat(17-05): GenreRouter + chain registry — FOUND
- `76ab940` test(17-05): RED Task 2 — FOUND
- `88ab792` feat(17-05): EventDetector wrap — FOUND
- `c0bf431` test(17-05): integration tests — FOUND
