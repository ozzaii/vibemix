---
phase: 03-sensing-state-port
plan: rollup
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - SENSE-01
  - SENSE-02
  - SENSE-05
  - SENSE-09
  - SCREEN-01  # partial — Quartz baseline; ScreenCaptureKit migration is Phase 8
  - SCREEN-03  # partial — find_window_bounds groundwork; full picker UI is Phase 11
  - SCREEN-04
  - SCREEN-05
wave_commits:
  - c923025  # wave 1 — MusicState + classify_phase + audible-deck/track resolvers (v4 verbatim)
  - 8106a16  # wave 2 — Event + EventDetector (constants imported, no class-attrs)
  - 9104052  # wave 3 — AICoach (evidence_line + task_for_event + build_prompt)
  - 8e04dfc  # wave 4 — state_refresh_loop + macOS Screen/MIDI/Track backends
---

# Phase 3 — Sensing & State Port — Summary

**Completed:** 2026-05-11
**Plan:** 03-sensing-state-port / 5 plans across 5 waves (4 feat + 1 docs gate)
**Verdict:** All 11 acceptance gates PASS. Phase 3 is shipped.

## What Phase 3 Delivered

Six load-bearing v4 sensing/state primitives ported from `cohost_v4.py:1009-1751` into `src/vibemix/state/` and `src/vibemix/platform/`: `MusicState` (the 22-field single source of truth), `Event` + `EventDetector` (the 7-event taxonomy with the v4 MUSIC_PRESENCE anti-hallucination gate), `AICoach` (per-event evidence + task string builder — byte-for-byte v4), plus three macOS platform backends (`ScreenMacOS`, `MidiMacOS`, `TrackMacOS`) that satisfy the Phase 1 Protocols structurally. `state_refresh_loop` is the **single 10Hz writer** to MusicState; the read-only consumers (`EventDetector.detect`, `AICoach.build_prompt`) are now stable surfaces Phase 4 can wire into a LiveKit cascade agent.

The load-bearing IP is preserved verbatim: the DDJ-FLX4 `_CC_MAP` + `_NOTE_MAP` are byte-identical to v4:582-598 (asserted by equality test); the 7 AICoach task strings match v4:1391-1427 byte-for-byte (golden-string tests pin them); the MUSIC_PRESENCE gate (sustained-audible ≥ 4.0s AND BPM ∈ [100, 180]) is the v4 anti-mic-ambient / anti-stale-nowplaying-cli core; and `evidence_line` deliberately **omits** the `phase=` field (v4:1350-1351 anti-hallucination removal — the RMS-tagged label was priming the AI to invent kicks/drops on atmospheric audio).

The Pioneer DDJ-FLX4 play-state propagation bug Kaan hit live on 2026-05-11 is **reproduced verbatim** from v4, with a `KNOWN ISSUE (Phase 9)` block documenting it at the top of `_midi_macos.py`. The macOS `Quartz.CGWindowListCopyWindowInfo` deprecation is preserved (Phase 8 migrates to ScreenCaptureKit). Both deferred items are docketed; neither is a regression.

## Requirements Coverage

| Req | Description | How Phase 3 satisfied it |
|-----|-------------|--------------------------|
| SENSE-01 | MusicState dataclass (single source of truth, 10Hz writer) | `src/vibemix/state/music_state.py` — 22 fields verbatim from v4:1009-1062 with `_lock: threading.Lock` for batched writer. `src/vibemix/state/refresh.py` is the ONLY writer; lock-protected; 10Hz via `await asyncio.sleep(0.1)`. |
| SENSE-02 | EventDetector + 7-event taxonomy + per-type cooldowns + MUSIC_PRESENCE gate | `src/vibemix/state/event_detector.py` — verbatim port of v4:1169-1325 with class-level constants (MUSIC_PRESENCE_MIN_SECONDS / BPM_VALID_MIN / BPM_VALID_MAX) lifted to `vibemix.audio.constants`. 29 tests cover all 7 event types + 3 gates + ref-update invariant. |
| SENSE-05 | derive_audible_deck + derive_audible_track (controller + nowplaying-cli cross-reference) | `src/vibemix/state/track_resolver.py` — verbatim port of v4:1093-1159. Free functions, no I/O. 28 tests cover xfader 4-tier boundaries (both sides) + every branch of both ladders. |
| SENSE-09 | AICoach evidence string + task templates (NO `phase=` field — v4 anti-hallucination) | `src/vibemix/state/coach.py` — verbatim port of v4:1327-1433. 30 tests pin every component of `evidence_line`, all 7 task strings byte-for-byte, the LOAD-BEARING `Do NOT name faders/EQs/knobs/decks/controls` and `don't go silent` clauses, and the `phase=` absence invariant. |
| SCREEN-01 (partial) | macOS screen capture via Quartz + mss | `src/vibemix/platform/_screen_macos.py` — Quartz baseline shipped. **Phase 8 migrates to ScreenCaptureKit** (deprecation chase) — docstring notes the carry-forward. |
| SCREEN-03 (partial) | djay Pro window discovery (substring + size filter) | `_find_djay_window_bounds(substr)` finds the largest window matching substring. Phase 11 ships the full source-picker UI. |
| SCREEN-04 | Screen capture pauses when no music plays | `ScreenMacOS.run_capture_loop` checks `state.audible` and `await asyncio.sleep(1.0); continue` when False — v4:993-997 verbatim. |
| SCREEN-05 | JPEG-encoded inline payload (~1Hz refresh) | `ScreenMacOS.capture` returns `CapturedFrame(jpeg, width, height)` with thumbnail (max 1280×800) + JPEG quality 82. Loop runs at ~1Hz via `await asyncio.sleep(1.0)`. |

## Files

**Created (15):**
- `src/vibemix/state/__init__.py` — package re-exports
- `src/vibemix/state/music_state.py` — `@dataclass MusicState` (22 fields + 2 @property)
- `src/vibemix/state/phase.py` — `classify_phase` free function
- `src/vibemix/state/track_resolver.py` — `derive_audible_deck` + `derive_audible_track`
- `src/vibemix/state/event.py` — `@dataclass Event`
- `src/vibemix/state/event_detector.py` — `EventDetector` class
- `src/vibemix/state/coach.py` — `AICoach` (static-method-only)
- `src/vibemix/state/refresh.py` — `state_refresh_loop` (the 10Hz single writer)
- `src/vibemix/platform/_screen_macos.py` — `ScreenMacOS` + `_ScreenBuffer` + `_find_djay_window_bounds`
- `src/vibemix/platform/_midi_macos.py` — `MidiMacOS` + `ControllerState` + `_CC_MAP`/`_NOTE_MAP`/`_knob_label`/`_xfader_label`
- `src/vibemix/platform/_track_macos.py` — `TrackMacOS` + `TrackInfo`
- `tests/state/` — 6 test files: `test_music_state.py`, `test_phase.py`, `test_track_resolver.py`, `test_event.py`, `test_event_detector.py`, `test_coach.py`, `test_refresh.py` (~135 tests)
- `tests/test_screen_macos.py` (12 tests)
- `tests/test_midi_macos.py` (27 tests)
- `tests/test_track_macos.py` (14 tests)

**Modified (3):**
- `src/vibemix/platform/__init__.py` — re-exports `ScreenMacOS`, `MidiMacOS`, `TrackMacOS`
- `src/vibemix/state/__init__.py` — incrementally built up across all 4 waves
- `src/vibemix/audio/constants.py` — ruff format whitespace only (Phase-2-inherited; no semantic change)

**POC files touched: 0.** `cohost_v4.py`, `cohost_v3.py`, `cohost.streaming.py.bak`, `run_v4.sh`, `run_v3.sh`, `mascot.html`, `fillers/`, `_test_*.py`, `test_voice.py`, `generate_bat.py` all untouched. v4 remains runnable via `./run_v4.sh` throughout this entire phase.

## Architectural Decisions Locked

- **MusicState is a mutable `@dataclass` with `_lock: threading.Lock`.** Single-writer guarantee is by convention — only `state_refresh_loop` writes, and its writes are batched inside `with state._lock:`. Readers (`EventDetector.detect`, `AICoach.build_prompt`) don't bother acquiring the lock — read tearing is acceptable at 10Hz cadence.
- **EventDetector imports MUSIC_PRESENCE / BPM thresholds from `vibemix.audio.constants`.** v4 had them as class-attrs (cohost_v4.py:1182-1186); 02/03-PATTERNS.md lifted them to module scope so tuning lives in one place. The class-attrs were REMOVED; verified by `not hasattr(EventDetector, ...)` test.
- **AICoach is static-method-only — no constructor, no instance state.** Three `@staticmethod` methods: `evidence_line`, `task_for_event`, `build_prompt`. Asserted by introspection (`AICoach.__init__ is object.__init__`).
- **AICoach.evidence_line OMITS `phase=`** (the v4:1350-1351 anti-hallucination invariant). Pinned by an exclusion test that feeds every phase label and asserts the substring is absent. Two confidence thresholds: `>= 0.3` (this module, for evidence-line quoting) vs `TRACK_CHANGE_MIN_CONFIDENCE = 0.5` (EventDetector, for event firing) — two separate purposes, do NOT conflate.
- **`classify_phase`, `derive_audible_deck`, `derive_audible_track` are FREE FUNCTIONS.** Not methods. Phase 6's genre-aware percentile detector swaps `classify_phase` without touching the class hierarchy.
- **`state_refresh_loop` calls feature functions as FREE FUNCTIONS** — the ONE structural deviation from v4 (Phase 2 refactored AudioBuffer methods → free functions). Verified by AST walk (`method_calls=0`, `free_function_calls=4`).
- **MIDI listener runs on a daemon `threading.Thread`** (mido.poll is blocking-only — asyncio is not viable here). `ControllerState`'s cross-thread surface is lock-protected. `state_refresh_loop` reads via `controller_state.deck_snapshot()` (returns deep-copy dict) and `controller_state.moves_since(t)` (returns seconds-relative tuples).
- **`screen_capture_loop` pauses when `not state.audible`** — v4 CPU save (verbatim from v4:993-997).
- **Pioneer DDJ-FLX4 play-state limitation reproduced verbatim from v4** — `_NOTE_MAP` maps `(0, 0x0B) → ('A', 'play')`, `handle_msg` toggles `deck[deck]['play']` on `note_on`. But when djay Pro is active, the FLX4 firmware sometimes consumes presses locally. Phase 9 fix docketed in `_midi_macos.py` docstring.
- **All three macOS backends satisfy Phase 1 Protocols structurally** (`isinstance(impl(), Protocol) is True`) — no inheritance. The AST OS-leak guard in `tests/test_platform.py` already exempts underscore-prefixed concrete impls (`_screen_macos.py`, `_midi_macos.py`, `_track_macos.py`).
- **SCREEN-01 partial completion:** Phase 3 ships Quartz `CGWindowListCopyWindowInfo` path; Phase 8 migrates to ScreenCaptureKit (deprecation chase).

## Deviations from Plan

- **Wave 4 Task 4.1 — `_tick_once` helper extraction (PRE-PLANNED).** The plan called for this extraction so tests can drive single ticks deterministically without spinning up asyncio. Not a deviation.
- **Wave 4 Task 4.2 — pytest-asyncio not added.** The plan's behavior bullet #10 used `@pytest.mark.asyncio`, but pytest-asyncio is not a project dep (Phase 2 didn't add it). The two loop-level invariants (sleep cadence + error wrap) use synchronous `asyncio.run(...)` inside sync test functions instead — equivalent coverage, no dep change. **Documented in `tests/state/test_refresh.py`.**
- **Wave 1 Task 1.2 — Two test fixtures in `03-01-PLAN.md` were arithmetically wrong** (the example curves wouldn't have actually hit "drop" or "breakdown" given the v4 thresholds). Replaced with traced-through fixtures: `[0.05, 0.05, 0.05, 0.02, 0.05, 0.12]` for drop (lands recent[:3]=[0.05, 0.05, 0.02] with 0.02 < LOW_RMS); `[0.10]*5 + [0.07, 0.06, 0.05, 0.045, 0.041]` for breakdown (last=0.041 ≥ LOW_RMS to dodge the early-out, earlier_max=0.10, last < 0.5 × 0.10 = 0.05). Behavior under test is identical; only the fixture data changed.
- **Wave 2 Task 2.2 — `_prime_music_playing` helper bypasses `detect()` to avoid `_reset_change_refs` polluting refs.** The plan suggested walking through `detect()` to set `_audible_since`, but that path calls `_reset_change_refs` which syncs `last_phase/last_audible_track/last_mix_moves_seen` to the current state — preventing change-driven events from firing on the very next tick. Solved by setting `_audible_since` directly on the detector and seeding `last_phase` to `state.phase` (or to a different value when the test wants to exercise a PHASE transition).
- **Wave 5 Task 5.4 — Optional Kaan smoke test:** marked optional in plan; orchestrator confirmed `gate="optional"`. Phase 3 in isolation produces no audible output (no Gemini call yet), so the smoke test is a nice-to-have, not a blocker. Marked "skipped" as a valid resume signal — Phase 4 is the first true end-to-end smoke test.

## Dependent Phases Unlocked

| Phase | Depends on Phase 3 for | Imports |
|-------|------------------------|---------|
| 4 — LiveKit Cascade Agent Pivot | DJCoHostAgent + AgentSession + llm_node override | `from vibemix.state import MusicState, Event, EventDetector, AICoach, state_refresh_loop`<br>`from vibemix.platform import ScreenMacOS, MidiMacOS, TrackMacOS` |
| 6 — Genre-Aware Phase Detection | Percentile-per-genre detector swap-in | `from vibemix.state.phase import classify_phase` — Phase 6 either monkey-patches the module's SILENT_RMS/LOW_RMS/PEAK_RMS reads or substitutes a replacement function. |
| 7 — Windows Port | Screen / MIDI / Track Windows impls | Mirrors `_screen_macos.py` / `_midi_macos.py` / `_track_macos.py` shape — `_screen_windows.py` (mss + pywin32 EnumWindows), `_midi_windows.py` (same mido), `_track_windows.py` (SMTC via pywin32 winrt). |
| 8 — macOS ScreenCaptureKit Migration | Replaces `_screen_macos.py` Quartz path | Same `ScreenBackend` Protocol surface; deprecation chase. |
| 9 — MIDI Controller Library | Extends `_midi_macos.py` with curated 10-controller library | Per-controller `_CC_MAP` / `_NOTE_MAP` sets + hot-plug rescan every 2s + Pioneer DDJ-FLX4 play-state fix (the KNOWN ISSUE docketed in this phase). |
| 10 — Prompt Template Matrix | Wraps `AICoach.build_prompt` output | Layers full anti-slop stack (persona, system instruction, `<silence/>` short-circuit, per-event template matrix) on top of Phase 3's evidence + task strings. |

## Open Items Carried Forward

- **Pioneer DDJ-FLX4 play-state propagation bug** → Phase 9 (`_midi_macos.py` docstring + module-private TODO; cross-reference with nowplaying-cli's playback-state OR audio-side "deck has signal energy" fallback)
- **macOS ScreenCaptureKit replacement for deprecated Quartz API** → Phase 8 (`_screen_macos.py` docstring)
- **Hot-plug MIDI re-enumeration every 2s** → Phase 9 (Phase 3 enumerates once at listener-thread start)
- **Curated 10-controller MIDI library** → Phase 9 (Phase 3 ships DDJ-FLX4 maps only)
- **Genre-aware phase detection (percentile per-genre)** → Phase 6 (Phase 3 ships v4's absolute-threshold detector)
- **Prompt template matrix + anti-slop stack** → Phase 10 (Phase 3's AICoach builds evidence + task; full Gemini prompt template is Phase 10)
- **Optional Kaan-verify checkpoint (Wave 5 Task 5.4)** → SKIPPED. Phase 4 is the first true end-to-end LiveKit smoke test; the lack of audible output in Phase 3 means the live smoke would only exercise the MIDI decode path that 27 mocked tests already cover.

## Verification Snapshot

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | Full suite green | `uv run pytest tests/ -x -q --ignore=tests/test_audio_macos_live.py` | 270 passed ✓ |
| 2 | Ruff check | `uv run ruff check src/ tests/` | clean ✓ |
| 2b | Ruff format | `uv run ruff format --check src/ tests/` | clean ✓ |
| 3 | POC files untouched | `git diff --name-only HEAD~4..HEAD -- 'cohost*.py' run*.sh mascot.html generate_bat.py '_test_*.py' test_voice.py fillers/` | empty ✓ |
| 4 | state import surface | `python -c "from vibemix.state import MusicState, Event, EventDetector, AICoach, state_refresh_loop, classify_phase, derive_audible_deck, derive_audible_track"` | OK ✓ |
| 5 | platform import surface | `python -c "from vibemix.platform import ScreenMacOS, MidiMacOS, TrackMacOS"` | OK ✓ |
| 6 | Protocols satisfied | `isinstance(ScreenMacOS(), ScreenBackend); isinstance(MidiMacOS(), MidiBackend); isinstance(TrackMacOS(), TrackInfoBackend)` | OK ✓ |
| 7 | All 6 primitives ported | `grep ^class …` | MusicState + Event + EventDetector + AICoach + ControllerState + TrackInfo + _ScreenBuffer present ✓ |
| 8 | EventDetector constants imported, NOT class-attrs | `grep -cE '^\s*(MUSIC_PRESENCE_MIN_SECONDS\|BPM_VALID_MIN\|BPM_VALID_MAX)\s*=' src/vibemix/state/event_detector.py` | 0 ✓ |
| 9 | state_refresh_loop uses FREE FUNCTIONS | AST-walk: method_calls=0, free_function_calls=4 | ✓ |
| 10 | AICoach evidence_line has NO `phase=` | `grep -nE "append.*phase=" src/vibemix/state/coach.py` | empty ✓ |
| 11 | ≥ 4 atomic `feat(03)` commits | `git log --oneline \| grep -cE "^[a-f0-9]+ feat\(03\):"` | 4 ✓ |

## Commit History (Phase 3)

```
c923025 feat(03): wave 1 — MusicState + classify_phase + audible-deck/track resolvers (v4 verbatim)
8106a16 feat(03): wave 2 — Event + EventDetector (constants imported, no class-attrs)
9104052 feat(03): wave 3 — AICoach (evidence_line + task_for_event + build_prompt)
8e04dfc feat(03): wave 4 — state_refresh_loop + macOS Screen/MIDI/Track backends
```
Plus the earlier `plan(03)` + research commits and the upcoming `docs(03)` rollup commit (this file).

## Self-Check

All files referenced in `must_haves.artifacts` across plans 01-04 verified to exist via `[ -f path ] && echo FOUND`:
- `src/vibemix/state/__init__.py` — FOUND
- `src/vibemix/state/music_state.py` — FOUND
- `src/vibemix/state/phase.py` — FOUND
- `src/vibemix/state/track_resolver.py` — FOUND
- `src/vibemix/state/event.py` — FOUND
- `src/vibemix/state/event_detector.py` — FOUND
- `src/vibemix/state/coach.py` — FOUND
- `src/vibemix/state/refresh.py` — FOUND
- `src/vibemix/platform/_screen_macos.py` — FOUND
- `src/vibemix/platform/_midi_macos.py` — FOUND
- `src/vibemix/platform/_track_macos.py` — FOUND
- `tests/state/test_music_state.py` — FOUND
- `tests/state/test_phase.py` — FOUND
- `tests/state/test_track_resolver.py` — FOUND
- `tests/state/test_event.py` — FOUND
- `tests/state/test_event_detector.py` — FOUND
- `tests/state/test_coach.py` — FOUND
- `tests/state/test_refresh.py` — FOUND
- `tests/test_screen_macos.py` — FOUND
- `tests/test_midi_macos.py` — FOUND
- `tests/test_track_macos.py` — FOUND

All four wave commit hashes verified via `git log`: c923025 ✓, 8106a16 ✓, 9104052 ✓, 8e04dfc ✓.

**Self-Check: PASSED**
