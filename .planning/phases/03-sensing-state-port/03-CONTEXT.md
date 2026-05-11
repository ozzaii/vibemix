# Phase 3: Sensing & State Port - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Canonical POC baseline:** `cohost_v4.py` (line anchors verified 2026-05-11)

<domain>
## Phase Boundary

Port the sensing & state layer from `cohost_v4.py` into the `src/vibemix/` package. After Phase 3, `MusicState` is the single source of truth at 10Hz, written by `state_refresh_loop`, read by `EventDetector` and `AICoach`. macOS implementations of `ScreenBackend`, `MidiBackend`, and `TrackInfoBackend` Protocols (Phase 1) are wired and tested. `derive_audible_track()` cross-references nowplaying-cli + MIDI deck weights to produce a confident track label (or `unknown` when confidence < `TRACK_CHANGE_MIN_CONFIDENCE`).

**In scope:**
- `src/vibemix/state/` package — `MusicState` (frozen dataclass + mutable view object pair), `state_refresh_loop` (async, 10Hz writer — SINGLE writer), `EventDetector` (typed `Event` dataclass, per-type cooldowns, MUSIC_PRESENCE gate, fire(...) API), `AICoach` (builds per-event evidence text — does NOT call Gemini).
- `src/vibemix/platform/_screen_macos.py` — `ScreenMacOS` implementing `ScreenBackend` via `mss` (full screen) + `Quartz.CGWindowListCopyWindowInfo` (window crop bounds for djay Pro).
- `src/vibemix/platform/_midi_macos.py` — `MidiMacOS` implementing `MidiBackend` via `mido` + `python-rtmidi`. Includes `ControllerState` decoding CC + Note maps with the DDJ-FLX4 mappings from v4 (the curated 10-controller library is Phase 9 — Phase 3 just ports v4's DDJ-FLX4 map and the generic-fallback skeleton).
- `src/vibemix/platform/_track_macos.py` — `TrackMacOS` implementing `TrackInfoBackend` via `nowplaying-cli` subprocess polling at ~1Hz.
- `src/vibemix/state/track_resolver.py` — `derive_audible_track()` cross-reference (nowplaying-cli vs. MIDI deck weights + audio-band fingerprint).
- Unit tests for each module + an `EventDetector` golden-file regression suite seeded from POC `recordings/*/events.jsonl` if available.

**Out of scope:**
- LiveKit `AgentSession` wiring (`DJCoHostAgent`, `llm_node` override, OpenRouter TTS chain + monkey-patch, `generate_reply` invocation) — Phase 4.
- Curated 10-controller MIDI library (DDJ-FLX4/400/FLX6/FLX10/1000/SX3 + XDJ-RX3 + Numark Party Mix Live + Hercules Inpulse 300/500) + generic positional fallback — Phase 9. Phase 3 ships ONLY the DDJ-FLX4 map from v4.
- `Pioneer FLX4 play-state` bug fix (deck=none always — Kaan's 2026-05-11 live bug). Captured as known issue; Phase 9 fixes it. Phase 3 reproduces v4 behavior verbatim.
- macOS ScreenCaptureKit replacement for deprecated `Quartz.CGWindowListCreateImageFromArray` — Phase 8.
- Windows screen/MIDI/track impls — Phase 7.
- Genre-aware percentile phase detector — Phase 6. Phase 3 ships v4's absolute-threshold detector (the load-bearing v4 behavior).
- Prompt template matrix + anti-slop stack — Phase 10. Phase 3's `AICoach` builds the evidence STRING per event, not the full instruction prompt.
- Hot-plug re-enumeration every 2s — Phase 9. Phase 3 enumerates once at startup.

</domain>

<decisions>
## Implementation Decisions

### MusicState (locked)
- **Shape:** Single `@dataclass` with frozen=False (mutable) — match v4's `MusicState` at `cohost_v4.py:1005-...`. Fields: `audible`, `rms`, `bpm_est`, `band_energies`, `phase` (silent/low/groove/drop), `audible_since`, `track_title`, `track_confidence`, `deck_weights`, `audible_deck`, `recent_controller_moves`, `screen_jpeg`, `last_updated_ts`. (Verify exact field list against v4 line 1005-1130 during execution.)
- **Single writer guarantee:** Only `state_refresh_loop` writes. EventDetector + AICoach read. Enforced by convention + a docstring contract. No formal lock.
- **Update rate:** 10Hz (100ms sleep). Lifted from v4.
- **Threading:** asyncio task. Reads from `AudioBuffer.snapshot_features` (already from Phase 2), `ScreenBuffer.snapshot()`, `TrackInfo.snapshot()`, `ControllerState.snapshot()` — all of those are thread-safe (audio_buf/passthrough lock-protected from Phase 2; the others are async-thread-only).

### EventDetector (locked)
- **Event types** (port verbatim from v4 line 1158-1320): `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, `KAAN_SPOKE`, `MANUAL`.
- **Cooldown source:** `MIN_EVENT_GAP_PER_TYPE` from Phase 2's `vibemix.audio.constants` — already lifted from v4:134-141. EventDetector consults this dict; do NOT redefine cooldowns in `state/`.
- **Music-presence gate:** `MUSIC_PRESENCE_MIN_SECONDS = 4.0` (from Phase 2 constants) — automatic events (HEARTBEAT/PHASE/LAYER_ARRIVAL/MIX_MOVE/TRACK_CHANGE) only fire when `(now - audible_since) >= MUSIC_PRESENCE_MIN_SECONDS` AND BPM is in `[BPM_VALID_MIN, BPM_VALID_MAX]` (100-180).
- **KAAN_SPOKE and MANUAL bypass** music-presence gate (Kaan asked a question — always reply, per v4 anti-hallucination rule).
- **Last-event-at tracking:** Per-type `last_event_at: dict[str, float]` + global `last_event_at: float`. Cooldown is `max(per_type_gap, EVENT_GLOBAL_MIN_GAP)`.

### AICoach (locked, scoped narrow)
- **Output:** Per-event evidence string built from `MusicState` snapshot. Format matches v4 line 1323-... output verbatim — comma-separated key=value pairs (e.g., `rms=0.094, bpm=126, phase=groove, deck=A, track="Around the World"`, `recent_moves[8s]: low-cut, hi-pass`, `hearing[loud, bandy]`).
- **NOT included this phase:** the full Gemini prompt template (Phase 10) and the call to Gemini (Phase 4). Phase 3's AICoach exposes `build_evidence(state: MusicState, event: Event) -> str`. Phase 4's DJCoHostAgent feeds this into the AgentSession.

### Screen, MIDI, Track Backends (locked)
- **`ScreenBackend` macOS impl** (`_screen_macos.py`):
  - `mss` for screen pixel capture
  - `Quartz.CGWindowListCopyWindowInfo` for djay window enumeration + crop bounds
  - JPEG encoding via Pillow before returning (`bytes` over the wire to Phase 4)
  - ~1Hz refresh rate (background asyncio task or executor-offloaded blocking call — v4 uses executor)
  - Phase 8 will replace `Quartz.CGWindowListCreateImageFromArray` with ScreenCaptureKit — Phase 3 ships the v4 Quartz path with a deprecation comment pointing to Phase 8.
- **`MidiBackend` macOS impl** (`_midi_macos.py`):
  - `mido.open_input(port_name)` opening DDJ-FLX4 by default; graceful no-op if device absent
  - Decoder maps `_CC_MAP` and `_NOTE_MAP` lifted verbatim from v4 (CC numbers + note numbers for DDJ-FLX4)
  - `ControllerState` class with: live position dict (knob/fader/jog states) + `recent_moves` ring (12s; magnitude-aware emission via configurable per-control threshold)
  - Generic positional fallback skeleton (returns coarse "knob_moved", "fader_moved" events without semantic labels) — full Phase 9 work fills in the 9 other controllers.
  - **Known issue carried in (Phase 9 fix):** play-state notes from DDJ-FLX4 don't propagate to `MusicState.deck_weights` — `audible_deck` reads `none` for now. Document this in `_midi_macos.py` docstring and link to PITFALLS for Phase 9.
  - Hot-plug rescan is Phase 9 — Phase 3 enumerates once.
- **`TrackInfoBackend` macOS impl** (`_track_macos.py`):
  - `subprocess.run(["/opt/homebrew/bin/nowplaying-cli", "get-raw"], capture_output=True)` at 1Hz, parsed via JSON or k=v lines
  - Fields: `title`, `artist`, `duration_s`, `position_s`. Returns `NowPlayingSnapshot` (frozen dataclass from `vibemix.platform.track`).
  - Graceful fallback when binary missing (returns `None` snapshot; logged once at startup).

### derive_audible_track() (locked)
- **Inputs:** `track_title` (from nowplaying-cli), `deck_weights: dict[str, float]` (from MIDI), `audio_fingerprint: dict[str, float]` (band energies from AudioBuffer.snapshot_features). Per v4:1134-1156.
- **Output:** `(track: str | None, confidence: float in [0, 1])`. `confidence >= TRACK_CHANGE_MIN_CONFIDENCE` (0.5 from Phase 2 constants) gates whether AICoach quotes the track name.
- **Decision logic:** Port v4's algorithm verbatim (deck-weighted track title when one deck dominates; raw nowplaying-cli when single deck; "unknown" when ambiguous).

### File Layout
```
src/vibemix/
├── state/
│   ├── __init__.py            # Re-exports MusicState, Event, EventDetector, AICoach, state_refresh_loop, derive_audible_track
│   ├── music_state.py         # @dataclass MusicState
│   ├── refresh.py             # state_refresh_loop async fn — SINGLE writer
│   ├── event.py               # @dataclass Event + EventType literal
│   ├── event_detector.py      # EventDetector class
│   ├── coach.py               # AICoach.build_evidence(state, event) -> str
│   └── track_resolver.py      # derive_audible_track()
└── platform/
    ├── _screen_macos.py        # ScreenMacOS (mss + Quartz)
    ├── _midi_macos.py          # MidiMacOS + ControllerState + _CC_MAP/_NOTE_MAP for DDJ-FLX4
    └── _track_macos.py         # TrackMacOS (nowplaying-cli subprocess)
```

### Claude's Discretion
- Whether `MusicState` is `@dataclass(frozen=True)` with copy-on-write writes or `frozen=False` with in-place writes. Recommend `frozen=False` matching v4 (the 10Hz writer rate makes copy-on-write expensive).
- Internal organization of `_screen_macos.py` (one class vs. functional). Recommend `ScreenMacOS` class with internal `ScreenBuffer` analog state.
- Test mocking strategy for `subprocess.run(nowplaying-cli)` — recommend `unittest.mock.patch` returning a canned `CompletedProcess`. Real nowplaying-cli optional smoke test under `macos_track` pytest marker.
- Mock fixture for MIDI port — `mido.IOPort` is mockable; provide a fixture that simulates DDJ-FLX4 CC + Note traffic.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 2)
- `src/vibemix/audio/AudioBuffer` — `snapshot_features(seconds=7.0)` is consumed by `state_refresh_loop` for RMS/BPM/band energies
- `src/vibemix/audio/Levels` — read by `state_refresh_loop` for `audible_since` debouncing
- `src/vibemix/audio/constants` — `SILENT_RMS`, `LOW_RMS`, `PEAK_RMS`, `AUDIBLE_DEBOUNCE_SEC`, `SILENCE_DEBOUNCE_SEC`, `EVENT_GLOBAL_MIN_GAP`, `HEARTBEAT_SEC`, `MIN_EVENT_GAP_PER_TYPE`, `MUSIC_PRESENCE_MIN_SECONDS`, `BPM_VALID_MIN`, `BPM_VALID_MAX`, `TRACK_CHANGE_MIN_CONFIDENCE` — all already lifted; Phase 3 imports, never redefines
- `src/vibemix/platform/` Protocols — `ScreenBackend`, `MidiBackend`, `TrackInfoBackend` (Phase 1) — concrete macOS impls land in this phase

### v4 Line Anchors (verified 2026-05-11)
- `class TrackInfo` @ cohost_v4.py:528
- `class ControllerState` @ cohost_v4.py:614
- `class ScreenBuffer` @ cohost_v4.py:755
- `@dataclass class MusicState` @ cohost_v4.py:1005
- `def derive_audible_track` @ cohost_v4.py:1134
- `class EventDetector` @ cohost_v4.py:1165
- `class AICoach` @ cohost_v4.py:1323
- `async def state_refresh_loop` @ cohost_v4.py:1633

### Established Patterns
- Async loops named `*_loop` suffix
- `from __future__ import annotations` at module top
- `threading.Lock` for buffers, asyncio everywhere else
- Closures used inside factories; classes for state-holding objects
- `_HAS_*` feature flags pattern from v4 — NOT carried forward (Phase 1 firewall makes them unnecessary; failed imports = phase fails fast)

### Integration Points
- **Phase 4 (LiveKit Cascade Agent)** imports `from vibemix.state import MusicState, EventDetector, AICoach` and wires `AICoach.build_evidence(state, event)` output into the `DJCoHostAgent.llm_node` override that drives Gemini.
- **Phase 6 (Genre-Aware Phase Detection)** subclasses or composes `EventDetector` to swap the absolute-threshold `phase` detector for percentile-based per-genre detection.
- **Phase 7 (Windows Port)** adds `_screen_windows.py` (`mss` + `pywin32` EnumWindows), `_midi_windows.py` (same `mido` impl works cross-platform; verify python-rtmidi Windows wheel), `_track_windows.py` (Windows SMTC via `pywin32 winrt`).
- **Phase 8 (macOS ScreenCaptureKit Migration)** replaces `_screen_macos.py`'s Quartz path with ScreenCaptureKit (deprecation chase).
- **Phase 9 (MIDI Controller Library)** extends `_midi_macos.py`'s controller library + hot-plug rescan + per-controller mapping JSON.
- **Phase 10 (Prompt Template Matrix)** layers the full prompt instruction stack ON TOP of `AICoach.build_evidence` output.

</code_context>

<specifics>
## Specific Ideas

- **Deck-weight semantics from v4**: `deck_weights = {"A": 0.0..1.0, "B": 0.0..1.0}` derived from per-deck volume faders + crossfader. `audible_deck` = `argmax(deck_weights)` when `max(weights) >= 0.6`, else `"none"`. Phase 9 fix wires play-state into this.
- **`recent_moves` ring**: 12-second sliding window of MIDI events with magnitude >= per-control threshold. Stored as `list[ControllerMove]` (frozen dataclass: `timestamp`, `control_label`, `delta`, `direction`).
- **nowplaying-cli polling cadence**: 1Hz is enough (track changes are slow events). Don't over-poll.
- **Screen capture rate**: ~1fps. Use `asyncio.run_in_executor(None, blocking_capture)` since mss + Quartz are blocking.
- **EventDetector golden tests**: If POC `recordings/*/events.jsonl` exists, replay them through the new EventDetector and assert event ordering + types match within tolerance. Otherwise, synthesize fixtures from v4's event docstrings.

</specifics>

<deferred>
## Deferred Ideas

- Pioneer FLX4 play-state → `deck_weights` fix → Phase 9
- Hot-plug MIDI re-enumeration every 2s → Phase 9
- Curated 10-controller MIDI library → Phase 9
- macOS ScreenCaptureKit replacement for deprecated Quartz API → Phase 8
- Windows ScreenBackend / MidiBackend / TrackInfoBackend impls → Phase 7
- Genre-aware phase detection (percentile per-genre profile) → Phase 6
- Prompt template matrix + anti-slop stack → Phase 10
- LiveKit AgentSession + OpenRouter TTS chain + DJCoHostAgent → Phase 4
- Track-change recognition robustness (multi-signal fusion beyond nowplaying-cli + deck weights) → carry-forward to Phase 6 verification harness

</deferred>
