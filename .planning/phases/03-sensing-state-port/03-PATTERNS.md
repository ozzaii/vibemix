# Phase 3: Sensing & State Port — POC Pattern Map (v4 canonical)

**Date:** 2026-05-11
**Mapper:** gsd-pattern-mapper
**Source of truth:** `cohost_v4.py` (lines verified against on-disk file 2026-05-11)
**Diff comparator:** `cohost_v3.py`

This map gives the planner exact line spans, verbatim code blocks, public method
signatures, and v4-vs-v3 deltas for every primitive the Sensing & State Port
must lift. Read top-to-bottom; each section is a self-contained porting
checklist.

---

## File-Map Recommendation (target package layout)

```
src/vibemix/state/
├── __init__.py              # re-exports MusicState, Event, EventDetector,
│                            # AICoach, derive_audible_deck, derive_audible_track,
│                            # state_refresh_loop, classify_phase
├── music_state.py           # @dataclass MusicState (mutable, threading.Lock field)
├── event.py                 # @dataclass Event
├── event_detector.py        # EventDetector (per-type cooldowns, music-presence gate)
├── coach.py                 # AICoach (evidence_line / task_for_event / build_prompt)
├── phase.py                 # classify_phase()  (kept separate so Phase 6 can swap impl)
├── track_resolver.py        # derive_audible_deck + derive_audible_track
└── refresh.py               # state_refresh_loop (THE 10Hz writer)

src/vibemix/platform/
├── _screen_macos.py         # ScreenMacOS implementing ScreenBackend
│                            #   (mss + Quartz CGWindowListCopyWindowInfo)
├── _midi_macos.py           # MidiMacOS implementing MidiBackend
│                            #   (mido listener thread + ControllerState + DDJ-FLX4 maps)
└── _track_macos.py          # TrackMacOS implementing TrackInfoBackend
                             #   (nowplaying-cli subprocess poll)
```

The `classify_phase` split is a Phase 6 hook — keeping it as a stand-alone
function (matching v4's free-function shape at `cohost_v4.py:1065`) lets Phase 6
inject a percentile-per-genre version without re-architecting EventDetector.

---

## Per-Primitive Map

### 1. MusicState  (cohost_v4.py:1009–1062)

**Decorator:** `@dataclass` — **mutable** (`frozen=False`, the default). Carries
an internal `_lock: threading.Lock` so the single-writer (`state_refresh_loop`)
can hold it while batching field updates and readers (EventDetector / AICoach /
DJCoHostAgent) acquire it for consistent snapshots.

**Fields (verbatim, in v4 declaration order):**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `audible` | `bool` | `False` | Debounced — true only when sustained sound (sustained ≥ `AUDIBLE_DEBOUNCE_SEC`, false after ≥ `SILENCE_DEBOUNCE_SEC` low) |
| `rms` | `float` | `0.0` | From `AudioBuffer.snapshot_features` |
| `bands` | `dict` | `{"sub":0, "low":0, "mid":0, "high":0}` | Band-share dict (default via `field(default_factory=...)`) |
| `onset_density` | `float` | `0.0` | onsets/sec from `snapshot_features` |
| `bpm` | `float` | `0.0` | Cached every 3s when `currently_loud` |
| `energy_curve` | `list` | `[]` | last ~12s, 1s hop, from `AudioBuffer.energy_curve` |
| `phase` | `str` | `"silent"` | one of: `silent / low / groove / build / drop / peak / breakdown` |
| `phase_started_at` | `float` | `0.0` | unix-ts when current phase began |
| `deck_a` | `dict` | `{}` | from `ControllerState.deck_snapshot()['A']` |
| `deck_b` | `dict` | `{}` | from `ControllerState.deck_snapshot()['B']` |
| `xfader` | `int` | `64` | 0..127 raw MIDI value |
| `controller_connected` | `bool` | `False` | Mirrors MIDI listener `_connected` |
| `audible_deck` | `str` | `"none"` | `'A' / 'B' / 'mix' / 'none'` |
| `deck_confidence` | `float` | `0.0` | 0..1 from `derive_audible_deck` |
| `audible_track` | `str \| None` | `None` | resolved title (only set when `derive_audible_track` returns one) |
| `audible_track_confidence` | `float` | `0.0` | 0..1; gated against `TRACK_CHANGE_MIN_CONFIDENCE` (0.5) for TRACK_CHANGE firing |
| `last_audible_track` | `str \| None` | `None` | snapshot from previous refresh (used by EventDetector for diff) |
| `recent_moves` | `list` | `[]` | `[(seconds_ago, label), ...]` from `ControllerState.moves_since` |
| `long_arc` | `list` | `[]` | ~120s RMS, 10s hop (`AudioBuffer.long_arc_curve(120, 10)`) |
| `phase_history` | `list` | `[]` | `[(t, from_phase, to_phase), ...]` last 6 |
| `track_history` | `list` | `[]` | `[(t, title), ...]` last 6 audibly-confirmed titles |
| `set_start_at` | `float` | `0.0` | unix-ts session start |
| `last_kaan_spoke_at` | `float` | `0.0` | unix-ts of last mic-detected speech |
| `_lock` | `threading.Lock` | `threading.Lock()` | guards writes batched per refresh tick |

**Computed properties (verbatim):**
```python
@property
def set_seconds(self) -> float:
    return time.time() - self.set_start_at if self.set_start_at else 0.0

@property
def time_in_phase(self) -> float:
    return time.time() - self.phase_started_at if self.phase_started_at else 0.0
```

**Mutation rule:** SINGLE WRITER. Only `state_refresh_loop` writes inside
`with state._lock:`. EventDetector and AICoach read fields directly; for
multi-field consistent snapshots they could also `with state._lock:` but in v4
they don't bother (read tearing is acceptable — single-tick latency).

**v4-vs-v3 diff for MusicState:** identical structure (v3:984–1036 vs v4:1009–
1062). No new fields, no removed fields. The diff is entirely in the consumers.

---

### 2. EventDetector  (cohost_v4.py:1169–1325)

**Class docstring (v4, verbatim) — captures the cardinal rules:**
```
Reads MusicState diffs, emits at most ONE event per cycle.
Returns None most of the time. Cardinal rules:
  1. KAAN_SPOKE + MANUAL always bypass.
  2. Auto-events only fire when MUSIC IS TRULY PLAYING — meaning
     continuous audible RMS for MUSIC_PRESENCE_MIN_SECONDS AND a BPM in
     the valid dance-music range. This kills phantom triggers from mic
     ambient + stale nowplaying-cli entries.
  3. Quality > quantity: skip an ambiguous event rather than fire a bad one.
```

**Class-level gate constants (v4:1182–1186 — DO NOT redefine; planner should
import these from `vibemix.audio.constants` if already there, else lift):**
```python
MUSIC_PRESENCE_MIN_SECONDS = 4.0    # sustained-audible threshold
BPM_VALID_MIN = 100.0               # below = autocorr locked on noise
BPM_VALID_MAX = 180.0               # above = autocorr locked on noise
```

*Note: CONTEXT.md states these live in `vibemix.audio.constants` from Phase 2.
Confirm at planning time; if so, EventDetector reads them, doesn't re-declare.*

**Constructor:**
```python
def __init__(self):
    self.last_event_at = 0.0
    self.last_per_type_at: dict[str, float] = {}
    self.last_phase: str = "silent"
    self.last_audible_track: str | None = None
    self.last_band_signature: tuple[float, float] | None = None
    self.last_mix_moves_seen: list[str] = []
    self._audible_since: float | None = None    # NEW IN v4 (music-presence tracker)
```

**Public API (single method):**
```python
def detect(self, state: MusicState, *, kaan_just_spoke: bool, manual: bool) -> Event | None
```

**Event-type taxonomy (the seven canonical strings — these are
`Event.type` literals, not enum members):**

| Type | Source | Cooldown key | Bypasses music-presence gate? |
|------|--------|--------------|-------------------------------|
| `"KAAN_SPOKE"` | mic detect → `kaan_just_spoke=True` | `"MIC"` (3.0s) | YES |
| `"MANUAL"` | manual trigger event | `"MANUAL"` (1.5s) | YES |
| `"TRACK_CHANGE"` | `state.audible_track` flipped AND `conf ≥ TRACK_CHANGE_MIN_CONFIDENCE` | `"TRACK_CHANGE"` (6.0s) | NO |
| `"PHASE"` | `state.phase` changed (and not `"silent"`) | `"PHASE"` (18.0s) | NO |
| `"LAYER_ARRIVAL"` | `mid_jump > 0.15` OR `high_jump > 0.10` AND `rms > LOW_RMS` | `"LAYER_ARRIVAL"` (16.0s) | NO |
| `"MIX_MOVE"` | new significant move in `state.recent_moves` (keys: `killed`, `_low:`, `_mid:`, `_hi:`, `_filter:`, `xfader`, `big`, `_play→`) | `"MIX_MOVE"` (20.0s) | NO |
| `"HEARTBEAT"` | nothing else fired, cooldown elapsed | `"HEARTBEAT"` (70.0s = `HEARTBEAT_SEC`) | NO |

**Cooldown helper (v4:1198–1201):**
```python
def _cooldown_ok(self, ev_type: str, now: float) -> bool:
    gap = MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
    last = self.last_per_type_at.get(ev_type, 0.0)
    return (now - last) > gap and (now - self.last_event_at) > EVENT_GLOBAL_MIN_GAP
```
Both per-type cooldown AND global min-gap must clear. `EVENT_GLOBAL_MIN_GAP =
10.0` in v4 (was `3.0` in v3 — v4 explicitly "let the music breathe").

**MUSIC_PRESENCE gate (v4:1203–1217 — verbatim, this is the v4 anti-hallucination
core):**
```python
def _music_truly_playing(self, state: MusicState, now: float) -> bool:
    """Sustained-audible + valid-BPM gate. Eliminates phantom auto-fires
    from mic ambient and stale nowplaying-cli entries."""
    if state.audible:
        if self._audible_since is None:
            self._audible_since = now
    else:
        self._audible_since = None
        return False
    if (now - self._audible_since) < self.MUSIC_PRESENCE_MIN_SECONDS:
        return False
    bpm = state.bpm or 0
    if bpm < self.BPM_VALID_MIN or bpm > self.BPM_VALID_MAX:
        return False
    return True
```

**Reset-refs helper (v4:1219–1226):**
```python
def _reset_change_refs(self, state: MusicState) -> None:
    """When music isn't truly playing we still keep the change-detection
    refs in sync with the current state — so that the moment music DOES
    start, we don't fire spurious 'change' events on stale baselines."""
    self.last_phase = state.phase
    self.last_audible_track = state.audible_track
    self.last_band_signature = None
    self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]
```

**Fire helper (v4:1322–1324):**
```python
def _fire(self, ev_type: str, now: float):
    self.last_event_at = now
    self.last_per_type_at[ev_type] = now
```

**`detect()` body — full v4:1228–1320 control flow (port verbatim):**
1. KAAN_SPOKE bypass → check `_cooldown_ok("MIC", now)` → `_fire("MIC")` →
   return `Event("KAAN_SPOKE", state)`.
2. MANUAL bypass → check `_cooldown_ok("MANUAL", now)` → `_fire("MANUAL")` →
   return `Event("MANUAL", state)`.
3. `if not self._music_truly_playing(state, now): self._reset_change_refs(state); return None`
   — the cardinal v4 gate.
4. TRACK_CHANGE: `state.audible_track` non-null AND `!= self.last_audible_track`
   AND `state.audible_track_confidence >= TRACK_CHANGE_MIN_CONFIDENCE` (0.5)
   AND `_cooldown_ok("TRACK_CHANGE", now)`. Emits with
   `extra={"prev_track", "new_track"}`.
5. PHASE: `state.phase != self.last_phase AND state.phase != "silent"` AND
   cooldown. Emits with `extra={"prev_phase", "new_phase"}`.
6. LAYER_ARRIVAL: band-signature diff. Round bands to 2 decimals before
   comparing: `sig = (round(state.bands["mid"], 2), round(state.bands["high"], 2))`.
7. MIX_MOVE: filter `state.recent_moves` against `last_mix_moves_seen`,
   keep labels containing any of `('killed', '_low:', '_mid:', '_hi:',
   '_filter:', 'xfader', 'big', '_play→')`. Emits with `extra={"moves":
   new_significant[-3:]}`.
8. HEARTBEAT: fallthrough if cooldown clears.
9. Always update `last_phase`, `last_audible_track`, `last_band_signature`,
   `last_mix_moves_seen` even if cooldown blocks fire — keeps next-cycle diff
   honest.

**v4-vs-v3 EventDetector diff (high signal):**
- **NEW in v4:** `_music_truly_playing` gate + class-level
  `MUSIC_PRESENCE_MIN_SECONDS`, `BPM_VALID_MIN/MAX` constants. v3 had only
  `if not state.audible: return None` (single-frame gate, didn't kill
  ambient/mic noise).
- **NEW in v4:** `_reset_change_refs` (was inlined in v3:1174–1180, now its
  own method).
- **NEW in v4:** `_audible_since: float | None` instance state.
- **NEW in v4:** TRACK_CHANGE now gated by
  `state.audible_track_confidence >= TRACK_CHANGE_MIN_CONFIDENCE` (constant
  itself is new in v4: `TRACK_CHANGE_MIN_CONFIDENCE = 0.5`).
- **CHANGED in v4:** MIX_MOVE significance keys are more specific. v3 used
  `('killed', 'xfader', 'play', 'filter:', 'cue_hit', 'loop_in_hit', 'big')`.
  v4 dropped `'cue_hit'` + `'loop_in_hit'` and added EQ band tier keys
  `('_low:', '_mid:', '_hi:')` plus `'_play→'` (so partial `'play'` matches
  must be tightened). Lift v4 verbatim.
- **CHANGED in v4:** All per-type cooldowns + global gap roughly tripled —
  see "Tuning constants delta" table below.

---

### 3. AICoach  (cohost_v4.py:1327–1433)

**Class docstring (verbatim):**
```
Builds the per-event prompt. Single persona is set at session-open via
SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task.
```

**Public API (three static methods, no instance state):**
```python
@staticmethod
def evidence_line(state: MusicState) -> str: ...

@staticmethod
def task_for_event(ev: Event) -> str: ...

@staticmethod
def build_prompt(ev: Event) -> str:
    evidence = AICoach.evidence_line(ev.state)
    task = AICoach.task_for_event(ev)
    return f"[{evidence} | event={ev.type}] {task}"
```

**Phase 3 boundary:** Phase 3 ships `evidence_line` (the grounded state string)
and `task_for_event` (per-event instruction tail) verbatim. The full
`build_prompt` wrapper is also Phase 3 — but Phase 4 wires its output into
`DJCoHostAgent.llm_node` and Phase 10 may layer additional anti-slop framing
on top.

**`evidence_line` output format (v4:1331–1389) — verbatim pipe-separated key=value
pairs. This is the format the planner must port byte-for-byte:**

Components (in order):
1. **Audio block (always present):**
   - If `state.audible`:
     `hearing[rms={state.rms:.3f} sub={b['sub']:.2f} low={b['low']:.2f} mid={b['mid']:.2f} high={b['high']:.2f} bpm={state.bpm:.0f}]`
   - Else: `hearing[silent]`
2. **Track:**
   - If `state.audible_track AND state.audible_track_confidence >= 0.3`:
     `track={state.audible_track!r}`  ← note `!r` (repr → quoted string)
   - Else: `track=unknown`
3. **Deck:** `deck={state.audible_deck}`  (one of `A / B / mix / none`)
4. **Set time:** `set_time={int(state.set_seconds // 60)}:{int(state.set_seconds % 60):02d}`
5. **NO `phase=` field.** v4 explicitly removed it (comment at v4:1350–1351:
   *"phase= removed — RMS-based label was priming the AI to invent kicks/drops
   when the audio was actually atmospheric. AI should hear the phase from
   audio."*). v3 still included it. **Do not re-add when porting.**
6. **Per-event ages (only when histories exist):**
   - `phase_age={now - state.phase_history[-1][0]:.1f}s`
   - `track_age={now - state.track_history[-1][0]:.1f}s`
7. **Recent moves (≤ 8s old, newest first):**
   - If non-empty: `recent_moves[8s]: {age:.1f}s ago {label}, ...`
   - Else: `recent_moves[8s]: NONE`
8. **Set arc (only when ≥ 2 entries):** `set_arc[{len*10}s]={state.long_arc}`
9. **Phase history (last 3 transitions chained):** `phase_history: a→b→c`
   (built from `state.phase_history[-4:]` using fr/to tuples).
10. **Track history (≥ 2 entries):** `recent_tracks: 'X'→'Y'→'Z'` (using
    `repr(title)` for each).

**Join:** `" | ".join(e)` — pipe-separated, NOT comma-separated.

**`task_for_event(ev)` — verbatim mapping (v4:1391–1427):**

| `ev.type` | Returned task string (port verbatim, word-for-word) |
|-----------|------------------------------------------------------|
| `KAAN_SPOKE` | `"Kaan just SPOKE — answer him directly, friend tone, 6-15 words. Not a music reaction."` |
| `MANUAL` | `"Kaan hit his trigger — react with substance to ONE concrete thing (audible event or recent move). 12-18 words."` |
| `TRACK_CHANGE` | `f"Track flipped{prev_clause}. React to the NEW track's vibe vs the previous — heavier, weirder, darker, more euphoric? 12-18 words. Past tense."` where `prev_clause = f" (was: {prev!r})" if prev else ""` |
| `PHASE` | `f"Phase shifted: {prev}→{new}. React to what the new section FEELS like, not the label. 10-14 words."` |
| `LAYER_ARRIVAL` | `"A new sonic layer arrived — synth lead, hi-hat layer, vocal, riff, pad. Name what arrived and how it feels. 10-14 words."` |
| `MIX_MOVE` | `f"Trigger seed (do NOT quote): MIDI moves [{mv}]. Listen to the AUDIO and describe the SONIC EFFECT — how the music CHANGED in sound (bass dropped out, highs scooped, space opened up, vocal pierced through). Do NOT name faders/EQs/knobs/decks/controls. Past tense, 8-12 words. If the audio didn't actually change, output a single space to stay silent."` |
| `HEARTBEAT` | `"Steady stretch. ONE sharp observation about the SOUND right now — groove, texture, what the track is doing musically. 8-12 words. Always reply with something fresh; don't go silent."` |
| (fallback) | `"React naturally. 10-14 words."` |

**v4-vs-v3 AICoach diff:**
- API surface identical (same three static methods).
- v4 removed `phase=` from `evidence_line` (anti-hallucination, see comment).
- v4 task strings were tuned heavily (MIX_MOVE got the "do NOT name controls"
  clause; HEARTBEAT got "don't go silent"). Lift v4 verbatim.

---

### 4. derive_audible_deck  (cohost_v4.py:1093–1135)

This is the deck-weight + xfader → audible-deck inference. CONTEXT asked for
`derive_audible_track` only, but the deck function is its upstream — port
both into `track_resolver.py`.

```python
def derive_audible_deck(deck_a: dict, deck_b: dict, xfader: int,
                        connected: bool) -> tuple[str, float]:
    """Returns (audible_deck, confidence). 'A' / 'B' / 'mix' / 'none'.
    Confidence considers play state, channel volume, and crossfader position."""
    if not connected:
        return "none", 0.0

    # Per-side weight = play * vol * xfader_factor
    def xfader_factor(side: str) -> float:
        if side == 'A':
            if xfader >= 112: return 0.0
            if xfader >= 80:  return 0.3
            if xfader >= 48:  return 0.7
            return 1.0
        else:  # B
            if xfader < 16:   return 0.0
            if xfader < 48:   return 0.3
            if xfader <= 80:  return 0.7
            return 1.0

    def deck_weight(d: dict, side: str) -> float:
        if not d.get('play'):
            return 0.0
        vol = d.get('vol', 0) / 127.0
        if vol < 0.1:
            return 0.0
        return vol * xfader_factor(side)

    wa = deck_weight(deck_a, 'A')
    wb = deck_weight(deck_b, 'B')

    if wa < 0.05 and wb < 0.05:
        return "none", 0.0
    if wa > 0.3 and wb < 0.1:
        return "A", min(1.0, wa)
    if wb > 0.3 and wa < 0.1:
        return "B", min(1.0, wb)
    if wa > 0.2 and wb > 0.2:
        return "mix", min(0.5, max(wa, wb))
    if wa > wb:
        return "A", max(0.4, wa - wb)
    return "B", max(0.4, wb - wa)
```

**Crucial dependency — `d.get('play')`:** this reads `deck['A']['play']` /
`deck['B']['play']` from `ControllerState.deck_snapshot()`. That `play` flag
is written **only** by `ControllerState.handle_msg` on `note_on` events
matching `_NOTE_MAP[(channel, note)] == (deck, 'play')`. So Phase 9's "FLX4
play-state bug" is actually:

- The DDJ-FLX4 firmware DOES emit `note_on` with note `0x0B` for the play
  button (`_NOTE_MAP[(0, 0x0B)] = ('A', 'play')`, `(1, 0x0B) = ('B', 'play')`).
- But the unit toggles its own LED locally on press without necessarily
  emitting `note_on` to the host in every mode. When djay Pro is the active
  controlling app, the FLX4 sometimes swallows the play-state outbound. The
  result: `deck.play` stays `False` → `deck_weight()` returns `0.0` → audible
  deck = `"none"` → `audible_track_confidence` ≤ 0.3 always → TRACK_CHANGE
  never gated past the 0.5 threshold.
- Phase 3 reproduces v4 verbatim; Phase 9 fixes it (likely by also reading
  djay Pro's MediaRemote play-state via nowplaying-cli's `get playbackState`).

**v4-vs-v3 diff:** identical (v3:1067–1109 vs v4:1093–1135 — same algorithm,
same thresholds).

---

### 5. derive_audible_track  (cohost_v4.py:1138–1159)

```python
def derive_audible_track(track_title: str | None,
                         audible_deck: str,
                         deck_confidence: float,
                         audio_audible: bool) -> tuple[str | None, float]:
    """Combines nowplaying-cli's title with controller-derived audible deck
    to produce a confidence-tagged track. Conservative — would rather say
    `unknown` than name a track that isn't actually playing.

    nowplaying-cli only gives ONE current title (whichever deck cued/loaded
    most recently). When the controller says audio is coming primarily from
    a single deck, we trust the title. Otherwise we lower confidence."""
    if not audio_audible or not track_title:
        return None, 0.0
    if audible_deck == "none":
        # Audio is heard but controller says no deck is active — controller may
        # be disconnected or in a weird state. Don't anchor on the title.
        return track_title, 0.3
    if audible_deck == "mix":
        # Two decks playing — title may be either. Mark unsure.
        return track_title, 0.4
    # Single dominant deck. Trust the title roughly proportional to confidence.
    return track_title, min(0.85, max(0.5, deck_confidence))
```

**Return ladder (read this once, it's the load-bearing IP):**
| Condition | Return |
|-----------|--------|
| `not audio_audible OR not track_title` | `(None, 0.0)` |
| `audible_deck == "none"` (controller silent but audio playing) | `(title, 0.3)` |
| `audible_deck == "mix"` | `(title, 0.4)` |
| Single deck dominant | `(title, clamp(deck_conf, 0.5, 0.85))` |

`TRACK_CHANGE_MIN_CONFIDENCE = 0.5` means only the "single dominant deck" case
triggers EventDetector. The `0.3` evidence-line threshold is separate: that
just controls whether AICoach quotes the title vs. printing `track=unknown`.

**v4-vs-v3 diff:** identical (v3:1112–1133 vs v4:1138–1159 — same logic, same
constants).

---

### 6. state_refresh_loop  (cohost_v4.py:1647–1751)

**Signature:**
```python
async def state_refresh_loop(state: MusicState, audio_buf: AudioBuffer,
                             controller_state: ControllerState, track_info: TrackInfo,
                             stop_event: asyncio.Event)
```

**Sleep cadence:** `await asyncio.sleep(0.1)` at top of loop → **10Hz**.

**Local cache state (declared above the while loop):**
```python
last_audible_high = 0.0    # ts of latest "loud" sample (debounce up-edge)
last_audible_low = 0.0     # ts of latest "silent" sample (debounce down-edge)
bpm_cache = 0.0
last_bpm_at = 0.0
```

**Per-tick body (port verbatim — this is THE writer):**

1. `feats = audio_buf.snapshot_features(seconds=4.0)` — RMS + band shares +
   onset density. Phase 2 already lifted this.
2. `curve = audio_buf.energy_curve(seconds=12.0, hop=1.0)` — used by
   `classify_phase`.
3. `rms = feats.get("rms", 0.0)`
4. `currently_loud = rms > SILENT_RMS` (0.012 in v4).
5. **BPM refresh gate:** only call `audio_buf.estimate_bpm(seconds=6.0)` if
   `now - last_bpm_at > 3.0 AND currently_loud`. Cache the result;
   `state.bpm = bpm_cache` always assigned.
6. **Debounce edges:**
   - If `currently_loud`: `last_audible_high = now` (only if not already set),
     reset `last_audible_low = 0.0`.
   - Else: `last_audible_low = now` (only if not already set), reset
     `last_audible_high = 0.0`.
7. **Acquire `state._lock` for the rest:**
   - `if state.audible AND last_audible_low > 0 AND (now - last_audible_low) >= SILENCE_DEBOUNCE_SEC: state.audible = False`
   - `elif not state.audible AND last_audible_high > 0 AND (now - last_audible_high) >= AUDIBLE_DEBOUNCE_SEC: state.audible = True`
   - Write `rms`, `bands` (4-key dict), `onset_density`, `bpm`, `energy_curve`.
   - `new_phase = classify_phase(curve, state.audible)`. If
     `new_phase != state.phase`: append `(now, state.phase, new_phase)` to
     `phase_history`, trim to last 6, write `state.phase = new_phase`,
     `state.phase_started_at = now`.
   - `cs = controller_state.deck_snapshot()` → write `deck_a`, `deck_b`,
     `xfader`, `controller_connected`.
   - Call `derive_audible_deck(cs['A'], cs['B'], cs['xfader'], cs['connected'])`
     → write `audible_deck`, `deck_confidence`.
   - `tsnap = track_info.snapshot()`; call `derive_audible_track(tsnap.get("title") or None, aud_deck, deck_conf, state.audible)`
     → conditionally append `(now, tt)` to `track_history` if
     `tt AND tc >= 0.5 AND tt != last_history_title`; trim to last 6. Write
     `audible_track`, `audible_track_confidence`.
   - Write `state.recent_moves = controller_state.moves_since(now - 12.0)`.
   - Write `state.long_arc = audio_buf.long_arc_curve(seconds=120.0, hop=10.0)`.
8. **Error wrap:** entire tick body is `try: ... except Exception as e: print(f"[state refresh err] {e}", file=sys.stderr)`. The loop NEVER exits on
   exception — it just logs and continues at next 100ms tick.

**Threading:** runs as `asyncio.create_task(state_refresh_loop(...))`. All
inputs (`AudioBuffer`, `ControllerState`, `TrackInfo`) are internally
lock-protected, so this function is safe to call without any extra
synchronization beyond `state._lock` for the writes.

**v4-vs-v3 diff:** identical body (v3:1559+ matches v4:1647+ line-for-line —
the writer didn't change between v3 and v4; v4's improvements are downstream
in EventDetector + AICoach + tuning constants).

---

### 7. ScreenBuffer + screen_capture_loop + find_djay_window_bounds  (cohost_v4.py:759–772, 956–1002, 220–242)

**`ScreenBuffer` class (v4:759–772) — thread-safe latest-frame holder:**
```python
class ScreenBuffer:
    def __init__(self):
        self._jpeg: bytes | None = None
        self._dims: tuple[int, int] = (0, 0)
        self._lock = threading.Lock()

    def push(self, jpeg: bytes, w: int, h: int):
        with self._lock:
            self._jpeg = jpeg
            self._dims = (w, h)

    def latest(self) -> tuple[bytes | None, tuple[int, int]]:
        with self._lock:
            return self._jpeg, self._dims
```

**`find_djay_window_bounds()` (v4:220–242) — Quartz window enumeration:**
```python
def find_djay_window_bounds():
    """Return (x, y, w, h) of djay Pro's main window in screen coords, or None."""
    if not _HAS_QUARTZ:
        return None
    try:
        infos = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    except Exception:
        return None
    best = None
    for w in infos:
        owner = (w.get("kCGWindowOwnerName") or "").lower()
        title = (w.get("kCGWindowName") or "").lower()
        if "djay" not in owner and "djay" not in title:
            continue
        b = w.get("kCGWindowBounds")
        if not b:
            continue
        x, y, ww, hh = int(b.get("X", 0)), int(b.get("Y", 0)), int(b.get("Width", 0)), int(b.get("Height", 0))
        if ww < 200 or hh < 200:
            continue
        if best is None or ww * hh > best[2] * best[3]:
            best = (x, y, ww, hh)
    return best
```

**Quartz import header (v4:77–85) — keep the try/except in the macOS backend
file ONLY (Phase 1's firewall keeps `_HAS_QUARTZ` style flags out of the
package shape; the import goes inside `_screen_macos.py` and a failed import
just raises ImportError at backend-load time, which the platform factory
catches):**
```python
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
)
```

**`screen_capture_loop` (v4:956–1002) — the ~1Hz async capture loop:**
- Uses `mss.mss()` once, picks `monitor = sct.monitors[1]` (full screen).
- Inner `grab()` function: `sct.grab(monitor)` → `Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")` → if `find_djay_window_bounds()` returns
  bounds, crop with scale factors → `img.thumbnail((1280, 800))` →
  `img.save(buf, format="JPEG", quality=82)` → return `(jpeg_bytes, w, h)`.
- Outer loop: skip if `not state.audible` (don't capture when no music is
  playing — saves CPU). Otherwise
  `await loop.run_in_executor(None, grab)` (mss + Pillow are blocking), then
  `screen_buf.push(jpeg, w, h)`. Then `await asyncio.sleep(1.0)`.
- Error wrap: `try/except` per tick → `print(f"[screen err] {e}", file=sys.stderr)`.

**Port to `_screen_macos.py`:** wrap `find_djay_window_bounds` as a private
module function. Expose a `ScreenMacOS(ScreenBackend)` class with two methods:
- `def latest(self) -> tuple[bytes | None, tuple[int, int]]` (mirrors v4's
  `ScreenBuffer.latest`).
- `async def run(self, *, while_audible: Callable[[], bool], stop_event: asyncio.Event) -> None`
  — long-running capture loop (the v4 `screen_capture_loop` body, with
  `state.audible` gated via the injected `while_audible` callable so the
  state layer's not a hard dep of the platform layer).

**v4-vs-v3 diff:** identical capture path. No changes.

---

### 8. ControllerState + DDJ-FLX4 maps + midi_listener_thread  (cohost_v4.py:580–757)

**`_CC_MAP` (cohost_v4.py:582–590) — VERBATIM:**
```python
_CC_MAP = {
    (0, 0x13): ('A', 'vol'),    (1, 0x13): ('B', 'vol'),
    (0, 0x07): ('A', 'eq_hi'),  (1, 0x07): ('B', 'eq_hi'),
    (0, 0x0B): ('A', 'eq_mid'), (1, 0x0B): ('B', 'eq_mid'),
    (0, 0x0F): ('A', 'eq_low'), (1, 0x0F): ('B', 'eq_low'),
    (0, 0x00): ('A', 'tempo'),  (1, 0x00): ('B', 'tempo'),
    (6, 0x17): ('A', 'filter'), (6, 0x18): ('B', 'filter'),
    (6, 0x1F): ('M', 'xfader'),
}
```
Key = `(midi_channel, cc_number)`. Channels 0/1 = deck A/B, channel 6 =
"master" section (filter knobs + xfader). All values 0..127.

**`_NOTE_MAP` (cohost_v4.py:591–598) — VERBATIM:**
```python
_NOTE_MAP = {
    (0, 0x0B): ('A', 'play'),       (1, 0x0B): ('B', 'play'),
    (0, 0x0C): ('A', 'cue'),        (1, 0x0C): ('B', 'cue'),
    (0, 0x60): ('A', 'sync'),       (1, 0x60): ('B', 'sync'),
    (0, 0x36): ('A', 'jog_touch'),  (1, 0x36): ('B', 'jog_touch'),
    (0, 0x10): ('A', 'loop_in'),    (1, 0x10): ('B', 'loop_in'),
    (0, 0x11): ('A', 'loop_out'),   (1, 0x11): ('B', 'loop_out'),
}
```

**`_knob_label` (cohost_v4.py:601–607) — 6-tier EQ/filter knob mapping:**
```python
def _knob_label(v: int) -> str:
    if v < 8:    return "killed"
    if v < 30:   return "deep-cut"
    if v < 55:   return "cut"
    if v <= 73:  return "flat"
    if v <= 100: return "boost"
    return "max"
```

**`_xfader_label` (cohost_v4.py:610–615) — 5-tier xfader mapping:**
```python
def _xfader_label(v: int) -> str:
    if v < 16:   return "full-A"
    if v < 48:   return "A-side"
    if v <= 80:  return "center"
    if v <= 112: return "B-side"
    return "full-B"
```

**`ControllerState` constructor + `_record_move` ring (cohost_v4.py:618–652):**
- `self.deck = {'A': {...}, 'B': {...}}` with 9 fields each: `vol, eq_low,
  eq_mid, eq_hi, filter, tempo` (init 64 for centered knobs, 0 for vol),
  `play, cue` (bool), `jog_touched` (bool).
- `self.xfader = 64` (center).
- `self._moves: list[tuple[float, str]] = []` — 12-second ring of `(timestamp,
  label)` tuples.
- `_record_move`: dedupe rule — if last move has same label AND was < 0.4s ago,
  skip. Trim entries older than `now - 12.0`.

**`handle_msg(msg)` decode rules (cohost_v4.py:654–712) — port verbatim:**

For `control_change`:
- Lookup `(msg.channel, msg.control)` in `_CC_MAP`. Skip if not found.
- xfader (deck 'M'): if `_xfader_label(prev) != _xfader_label(v)`, record
  `f"xfader→{_xfader_label(v)}"`.
- `vol` / `tempo`: only emit if `abs(v - prev) > 15`. Magnitude bucket:
  `"small"` (<15) / `"medium"` (<40) / `"big"` (≥40). Label:
  `f"{deck}_{field} {direction} ({mag})"`.
- `eq_low` / `eq_mid` / `eq_hi` / `filter`: emit only if
  `_knob_label(prev) != _knob_label(v)`. Label:
  `f"{deck}_{field.replace('eq_','')}: {prev_label}→{new_label} ({mag} twist)"`.

For `note_on`:
- Lookup `(msg.channel, msg.note)` in `_NOTE_MAP`. Skip if not found.
- `play`: TOGGLE `self.deck[deck]['play']`. Record
  `f"{deck}_play→{'ON' if ... else 'OFF'}"`.
  **Bug note:** the FLX4 firmware sometimes doesn't emit note_on for play
  while djay Pro is in focus → `play` flag stays at boot default `False` →
  `derive_audible_deck` returns `"none"`. Phase 9 fix.
- `cue`: record `f"{deck}_cue_hit"`. No state change.
- `sync`: record `f"{deck}_sync_hit"`. No state change.
- `jog_touch`: set `self.deck[deck]['jog_touched'] = (msg.velocity > 0)`. No
  record.
- `loop_in`: SET `self.deck[deck]['play'] = True` (workaround — loop_in
  implicitly starts play). Record `f"{deck}_loop_in_hit (play=ON)"`.
- `loop_out`: record `f"{deck}_loop_out_hit"`.

For `note_off`:
- Only `jog_touch` is handled: clear `jog_touched = False`.

**Public snapshot methods:**
```python
def deck_snapshot(self) -> dict:
    """Static snapshot — used by MusicState to compute audible deck weights."""
    with self._lock:
        return {
            'A': dict(self.deck['A']),
            'B': dict(self.deck['B']),
            'xfader': self.xfader,
            'connected': self._connected,
        }

def moves_since(self, t: float) -> list[tuple[float, str]]:
    with self._lock:
        now = time.time()
        return [(round(now - mt, 1), label) for mt, label in self._moves if mt > t]
```

Note `moves_since` returns `(seconds_ago, label)` — relative time, not absolute.
That's the shape `MusicState.recent_moves` carries and EventDetector iterates.

**Lifecycle helpers:**
```python
def mark_connected(self, port_name: str): ...  # called by listener thread on open
def is_connected(self) -> bool: ...
```

**`midi_listener_thread` (cohost_v4.py:730–756) — blocking-thread MIDI port
opener (port_hint `"DDJ-FLX4"`, retry every 2s on disconnect, `port.poll()` +
`time.sleep(0.005)` busy-loop):**
```python
def midi_listener_thread(controller_state: ControllerState, stop_event: threading.Event):
    try:
        import mido
    except ImportError:
        print("-> mido not installed, MIDI controller disabled", file=sys.stderr)
        return

    PORT_HINT = "DDJ-FLX4"
    while not stop_event.is_set():
        try:
            ports = mido.get_input_names()
            match = next((p for p in ports if PORT_HINT.lower() in p.lower()), None)
            if not match:
                time.sleep(2.0)
                continue
            with mido.open_input(match) as port:
                controller_state.mark_connected(match)
                print(f"-> MIDI controller in: {match!r}")
                while not stop_event.is_set():
                    msg = port.poll()
                    if msg is None:
                        time.sleep(0.005)
                        continue
                    controller_state.handle_msg(msg)
        except Exception as e:
            print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
            time.sleep(2.0)
```

**Port to `_midi_macos.py`:** `MidiMacOS(MidiBackend)` class wraps
`ControllerState` + spawns the listener as a daemon `threading.Thread`.
Expose `snapshot()` (returns deck snapshot) and `moves_since(t)` on the
backend; internally delegate to the ControllerState. The maps + `_knob_label`
+ `_xfader_label` are module-level (private with leading underscore — they're
"hard-coded controller knowledge", not configurable yet).

**v4-vs-v3 diff for ControllerState:** identical maps, identical logic
(v3:556–731 matches v4:582–757 essentially line-for-line). No new fields, no
changed channels.

---

### 9. TrackInfo + track_poll_loop  (cohost_v4.py:532–577)

**Class body (verbatim):**
```python
class TrackInfo:
    """Polls macOS Now Playing every 1s for djay's current title.
    Doesn't know which deck owns it — MusicState infers that from controller.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.title_changed_at: float = 0.0
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"

    def poll_once(self) -> None:
        try:
            out = subprocess.check_output(
                [self._cli, "get", "title", "artist"],
                timeout=1.5, stderr=subprocess.DEVNULL,
            ).decode().strip().splitlines()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return
        title = out[0].strip() if len(out) > 0 else ""
        artist = out[1].strip() if len(out) > 1 else ""
        full = f"{artist} - {title}" if (artist and title) else title
        with self._lock:
            if full and full != self.title:
                self.prev_title = self.title
                self.title = full
                self.title_changed_at = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "title_changed_at": self.title_changed_at,
            }
```

**Polling loop (cohost_v4.py:570–577):**
```python
async def track_poll_loop(track_info: TrackInfo, stop_event: asyncio.Event):
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        try:
            await loop.run_in_executor(None, track_info.poll_once)
        except Exception as e:
            print(f"[track poll err] {e}", file=sys.stderr)
        await asyncio.sleep(1.0)
```

**Subprocess invocation details:**
- Binary: `shutil.which("nowplaying-cli")` with `/opt/homebrew/bin/nowplaying-cli`
  fallback. NOT JSON — v4 uses `get title artist` which returns two
  newline-separated lines (title, then artist).
- Timeout: 1.5s. stderr suppressed.
- Catches: `TimeoutExpired`, `CalledProcessError`, `FileNotFoundError`, `OSError`
  — all silently return (no log spam). Graceful degradation when
  `nowplaying-cli` not installed.
- Change detection: `if full and full != self.title:` → update prev/current/ts.

**Port to `_track_macos.py`:** `TrackMacOS(TrackInfoBackend)` class. The Phase 1
Protocol probably defines a `NowPlayingSnapshot` frozen dataclass — convert
v4's dict-returning `snapshot()` to return that dataclass. Run the polling
loop as an async task spawned from `__aenter__` or a `start()` method;
`stop()` flips an internal asyncio.Event.

**v4-vs-v3 diff:** identical (v3:508–553 vs v4:532–577 — same subprocess
invocation, same parse logic).

---

## Cross-Cutting Semantics

### Deck-weight semantics (LOAD-BEARING IP)

Crossfader + per-channel volume fader combine into per-side weights via:
```
weight(side) = play_state * (vol_127 / 127) * xfader_factor(side)
```

`xfader_factor` table (xfader value 0..127, center = 64):

| xfader range | A factor | B factor |
|--------------|----------|----------|
| 0–15 (full-A) | 1.0 | 0.0 |
| 16–47 (A-side) | 1.0 | 0.3 |
| 48–80 (center) | 0.7 | 0.7 |
| 81–111 (B-side) | 0.3 | 1.0 |
| 112–127 (full-B) | 0.0 | 1.0 |

**Audible-deck thresholds:**
- `max(wa, wb) < 0.05` → `"none"`, conf 0.0
- `wa > 0.3 AND wb < 0.1` → `"A"`, conf `min(1.0, wa)`
- `wb > 0.3 AND wa < 0.1` → `"B"`, conf `min(1.0, wb)`
- `wa > 0.2 AND wb > 0.2` → `"mix"`, conf `min(0.5, max(wa, wb))`
- otherwise → dominant side with conf `max(0.4, |wa-wb|)`

The lowest "deck is real" threshold is `0.3` on a single side — anything
below = "none". Trust depends on having `play=True` registered (the FLX4 bug
keeps `play` at False → audible_deck always "none" without the Phase 9 fix).

### Recent-moves ring semantics

- **Window:** 12 seconds. Older entries dropped in `_record_move` and again
  in `moves_since`.
- **Dedupe:** if same label fired within 0.4s, skip (prevents jog-wheel
  spam).
- **Per-control emission thresholds:**
  | Control | Threshold |
  |---------|-----------|
  | xfader (CC ch 6 / 0x1F) | label-tier change (5-tier) |
  | vol / tempo CC | abs delta > 15 |
  | EQ knobs / filter CC | knob-tier change (6-tier) |
  | play / loop_in note_on | always (these are events, not gradual moves) |
  | cue / sync / loop_out note_on | always |
  | jog_touch note_on/off | NEVER (state-only, no move record) |
- **Stored per move:** `(unix_ts, label_string)` internally. `moves_since`
  returns `(seconds_ago_rounded_to_0.1, label)` — relative time for AI
  reasoning ("2s ago you killed the lows").

### MusicState single-writer convention

Only `state_refresh_loop` writes. Convention enforced by docstring + tests
(unit test: spawn EventDetector/AICoach against a fixture state, assert no
attribute mutation). Lock `state._lock` held only during the per-tick batched
write — readers don't need to acquire it for individual field reads (tearing
is acceptable at 10Hz cadence).

### Tuning-constants delta (v4 - v3) — verify all are already in `vibemix.audio.constants` from Phase 2

| Constant | v3 | v4 | Notes |
|----------|-----|-----|-------|
| `SILENT_RMS` | 0.008 | **0.012** | Higher floor → fewer phantom-audible flips |
| `LOW_RMS` | 0.025 | **0.040** | Raised filtered-breakdown band |
| `PEAK_RMS` | 0.055 | **0.110** | 2x — was too sensitive in v3 |
| `AUDIBLE_DEBOUNCE_SEC` | 0.6 | 0.6 | unchanged |
| `SILENCE_DEBOUNCE_SEC` | 1.2 | 1.2 | unchanged |
| `EVENT_GLOBAL_MIN_GAP` | 3.0 | **10.0** | 3.3x — "let the music breathe" |
| `HEARTBEAT_SEC` | 25.0 | **70.0** | 2.8x — less chatty |
| `MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"]` | 3.0 | **6.0** | 2x |
| `MIN_EVENT_GAP_PER_TYPE["PHASE"]` | 4.0 | **18.0** | 4.5x |
| `MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"]` | 5.0 | **16.0** | 3.2x |
| `MIN_EVENT_GAP_PER_TYPE["MIX_MOVE"]` | 3.5 | **20.0** | 5.7x |
| `MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"]` | 25.0 | **70.0** | mirrors HEARTBEAT_SEC |
| `MIN_EVENT_GAP_PER_TYPE["MIC"]` | 2.0 | **3.0** | small bump |
| `MIN_EVENT_GAP_PER_TYPE["MANUAL"]` | 1.5 | 1.5 | unchanged |
| `TRACK_CHANGE_MIN_CONFIDENCE` | — | **0.5** | NEW in v4 |

These are the empirically-tuned anti-slop knobs from Kaan's 2026-05-11 live
DJ session. Port v4's values; do NOT split the difference with v3.

---

## v4-vs-v3 Diff Summary (high-signal)

1. **EventDetector gained the MUSIC_PRESENCE gate** (`_music_truly_playing`)
   — sustained-audible AND BPM-in-range. v3 only checked single-frame
   `state.audible`. This is the core anti-hallucination upgrade.
2. **EventDetector gained `_reset_change_refs`** — explicit helper for
   resyncing diff refs when the gate fails.
3. **TRACK_CHANGE gained a confidence gate** — `audible_track_confidence >=
   TRACK_CHANGE_MIN_CONFIDENCE (0.5)`. v3 fired on any title diff.
4. **MIX_MOVE significance keys tightened** — v4 drops `cue_hit` /
   `loop_in_hit`, adds EQ band-tier keys (`_low:` `_mid:` `_hi:`) and play-arrow
   `_play→`.
5. **AICoach.evidence_line removed `phase=`** — RMS-tagged phase string was
   priming the LLM to invent kicks/drops on atmospheric audio.
6. **AICoach task strings were tuned heavily** — MIX_MOVE got "do NOT name
   controls"; HEARTBEAT got "don't go silent"; MANUAL got "ONE concrete thing".
7. **Tuning constants roughly 2-5x looser** — see table above. v3 was chatty;
   v4 has Kaan calling it "real DJ friend in your ear".
8. **No structural change to MusicState, ControllerState, TrackInfo,
   ScreenBuffer, derive_audible_deck, derive_audible_track, or
   state_refresh_loop body** — those are byte-for-byte identical between v3
   and v4. The v4 wins are concentrated in EventDetector + AICoach + tuning.

---

## Anti-Patterns to NOT Carry Forward

- **Module-level `_HAS_VISION` / `_HAS_QUARTZ` / `_HAS_WS` feature flags.**
  Phase 1 firewall makes them unnecessary — failed import in `_screen_macos.py`
  bubbles up as `ImportError` at backend-load time, and the platform factory
  catches it.
- **`print(...)` for live diagnostics scattered everywhere.** Phase 11 wires
  the mascot UI for this; for now use `logging.getLogger(__name__)` or stay
  silent. The two exceptions: startup banners (one-liners like "-> MIDI
  controller in: ...") and exception logs (these can stay as `print(..., file=sys.stderr)` until the logging infra lands).
- **Inline `subprocess.run`/`subprocess.check_output` calls scattered across
  files.** All `nowplaying-cli` invocation lives in `_track_macos.py`. No
  other module imports `subprocess`.
- **Module-level globals other than constants.** Constants are in
  `vibemix.audio.constants` (Phase 2 already lifted). The maps (`_CC_MAP`,
  `_NOTE_MAP`) and label helpers (`_knob_label`, `_xfader_label`) stay
  module-private to `_midi_macos.py` — they're not "configuration", they're
  "hard-coded DDJ-FLX4 protocol knowledge".
- **The `np.concatenate`-per-callback ring-buffer anti-pattern** — Phase 2
  fixed it. Nothing in Phase 3 should reintroduce it; the audio primitives
  Phase 3 reads (`snapshot_features`, `energy_curve`, `long_arc_curve`,
  `estimate_bpm`) are already on the new pre-allocated ring.

---

## Known Issues Documented (Carried Into Later Phases)

- **Pioneer DDJ-FLX4 play-state not propagating** — `_NOTE_MAP` does map
  notes `0x0B` → `play`, and `handle_msg` does toggle `deck[deck]['play']`
  on `note_on`. BUT when djay Pro is the active controlling app, the FLX4
  firmware sometimes consumes play presses locally without forwarding the
  `note_on` to other listeners. Result: `deck['play']` stays `False` →
  `derive_audible_deck` returns `"none"` → `derive_audible_track` confidence
  capped at 0.3 → TRACK_CHANGE never gated past 0.5. Phase 3 reproduces v4
  verbatim. **Phase 9 fix:** cross-reference with nowplaying-cli's
  playback-state, or use djay's IAC port if available, or implement an
  audio-side "deck has signal energy" fallback. Document at the top of
  `_midi_macos.py` with a `# KNOWN ISSUE (Phase 9)` block.

- **macOS `CGWindowListCopyWindowInfo` deprecation** — `find_djay_window_bounds`
  uses `CGWindowListCopyWindowInfo` + `kCGWindowListOptionOnScreenOnly`. The
  Quartz-based window enumeration API is deprecated in macOS 14+ in favor of
  ScreenCaptureKit. Phase 3 ships the Quartz path with a docstring pointer to
  Phase 8 (ScreenCaptureKit migration).

- **`nowplaying-cli` not bundled** — Phase 3 hard-codes
  `/opt/homebrew/bin/nowplaying-cli` as the fallback path. Installer story is
  Phase 19/20 (packaging). For now: silent graceful failure if binary missing
  (TrackMacOS returns empty snapshot, `audible_track` stays `None`).

- **Hot-plug MIDI rescan** — Phase 3 enumerates once at startup and reconnects
  on listener thread error (every 2s when port disappears). True hot-plug
  rescan (re-detecting newly attached controllers without a port-disconnect
  event) is Phase 9.

- **Curated 10-controller library** — Phase 3 ships ONLY the DDJ-FLX4 maps
  from v4. Phase 9 extends with DDJ-400, FLX6, FLX10, 1000, SX3, XDJ-RX3,
  Numark Party Mix Live, Hercules Inpulse 300/500. The generic positional
  fallback skeleton (emit coarse `knob_moved` / `fader_moved` events without
  semantic labels) is Phase 9 work too — Phase 3 just leaves a TODO comment.
