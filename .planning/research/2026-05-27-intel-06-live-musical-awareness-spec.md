# INTEL-06 spec - live musical awareness and playhead confidence

**Date:** 2026-05-27
**Scope:** live identity, playhead estimation, section position, and confidence
**Depends on:** `.planning/research/2026-05-27-intel-05-taste-learning-flywheel-spec.md`
**Code posture:** no product code changed in this research pass

## Goal

Make the live pill aware of where the DJ is in the current track without
Rekordbox process-memory reads, screen vision, or PRO DJ LINK hardware.

The app already knows a lot:

- `DeckPoller` can resolve the audible deck's track ID/key/BPM from now-playing
  title plus Rekordbox XML library match.
- `MusicState` already carries `audible_deck`, `deck_confidence`, `deck_state`,
  `bpm`, `bpm_confidence`, `downbeat_phase`, `beat_phase`, `phase`, and
  `recent_moves`.
- `compute_downbeat_phase` already has an anti-hallucination confidence model.
- `LookaheadProvider` already extracts now-playing title, elapsed time, playback
  rate, and local file path on macOS for file-based lookahead.
- INTEL-01 gives per-track ANLZ beatgrid and phrase sections.

What is missing is a derived playhead/section holder:

```text
active track + position + section + confidence
```

This should be derived state, not another writer into `MusicState`.

## Non-goals

- No Rekordbox process-memory reads.
- No screen vision.
- No direct `master.db` reads.
- No PRO DJ LINK dependency.
- No exact timing claims when confidence is weak.
- No LLM inference of playhead, section, or bar count.

## Existing local seams

### `MusicState`

Relevant fields:

```text
audible_deck
deck_confidence
deck_state.decks[side].track_id
deck_state.decks[side].bpm
deck_state.decks[side].camelot
bpm
bpm_confidence
downbeat_phase / beat_phase
phase
recent_moves
```

Rule: keep `MusicState` single-writer. Live awareness reads snapshots and stores
its own holder.

### `DeckPoller`

Current ladder:

```text
controller + nowplaying title -> audible deck -> Rekordbox XML title match
```

It intentionally suppresses non-audible deck guesses. Preserve that. A wrong
track ID poisons every section/timing claim downstream.

### `LookaheadProvider`

Current provider already polls:

```text
nowplaying-cli get-raw -> title, elapsedTime, playbackRate
```

It also has a stale elapsed extrapolation guard. That is a valuable position
source and should be factored or wrapped rather than reimplemented.

### `compute_downbeat_phase`

This is not a full playhead. It provides:

```text
fraction-through-current-bar
bpm_confidence
```

Use it to decide whether bar/timing claims are allowed, and to snap coarse
elapsed estimates to the nearest bar/phrase.

## Architecture

Add a derived service:

```text
LiveAwarenessService
```

It reads:

```text
MusicState snapshot
ANLZ index / SectionIntelligence store
optional NowPlayingPositionSource
optional AudioAlignmentSource
```

It writes only to its own thread-safe holder:

```text
LiveAwarenessSnapshot | None
```

`SuggestionService` and context-packet code read that holder when building
`next_transition`.

## Data contracts

### `PlayheadEstimate`

```python
@dataclass(frozen=True, slots=True)
class PlayheadEstimate:
    track_id: str
    deck: str
    position_s: float | None
    beat_index: int | None
    bar_index: int | None
    beat_phase: float | None
    playback_rate: float | None

    confidence: float
    source: str  # nowplaying_elapsed | load_clock | audio_alignment | none
    stale: bool
    flags: tuple[str, ...]
    updated_at: float
```

### `SectionPosition`

```python
@dataclass(frozen=True, slots=True)
class SectionPosition:
    track_id: str
    section_id: str | None
    role: str | None
    section_start_s: float | None
    section_end_s: float | None
    seconds_into_section: float | None
    seconds_to_next_section: float | None
    bars_to_next_section: int | None
    confidence: float
    flags: tuple[str, ...]
```

### `LiveAwarenessSnapshot`

```python
@dataclass(frozen=True, slots=True)
class LiveAwarenessSnapshot:
    active_track_id: str | None
    active_deck: str | None
    identity_confidence: float
    playhead: PlayheadEstimate | None
    section: SectionPosition | None
    blend_state: str  # single | blend | none | unknown
    suppress_timing_claims: bool
    suppress_recommendations: bool
    reasons: tuple[str, ...]
    generated_at: float
```

This is the live half of the `MusicalContextPacket` in INTEL-02.

## Source ladder

### Tier 1: now-playing elapsed

Use when all are true:

- active track ID resolved from `MusicState.deck_state`;
- now-playing title matches the same resolved library entry;
- elapsed time is present and sane;
- playback rate is present or defaults to 1.0;
- elapsed does not jump backward/forward implausibly except on track change.

Confidence:

```text
base 0.78
+0.08 if title and track_id matched through Rekordbox XML
+0.05 if playbackRate > 0 and stable
-0.15 if elapsed was extrapolated rather than freshly updated
-0.20 if audible_deck == "mix"
-0.15 if bpm_confidence < 0.6
clamp 0..0.90
```

This tier is enough for first live pill timing on macOS file/local playback.

### Tier 2: load clock estimate

Use when:

- deck track ID is known;
- `DeckTrack.loaded_at` exists;
- no trustworthy elapsed source exists.

Estimate:

```text
position_s = wall_now - loaded_at
```

Only useful for rough section awareness, because loaded time may mean "resolved
by poller" rather than actual transport start.

Confidence:

```text
base 0.35
-0.10 if controller confidence < 0.6
-0.20 if blend
cap 0.45
```

This tier must never emit exact bar timing.

### Tier 3: audio alignment

Future upgrade. Use live captured audio to align against the active track's
known audio/ANLZ grid.

Suggested path:

```text
live audio ring buffer
  -> beat/onset/chroma features
  -> candidate local track segment features
  -> subsequence DTW / beat-synchronous alignment
  -> position_s + beat_index + confidence
```

Use only when:

- active track identity is already known;
- local audio path is available;
- blend window is not dominant, or alignment confidence remains high;
- score margin beats the next-best offset.

This is the route to Rekordbox-independent playhead confidence. It is not
needed for the first ANLZ-powered prep/live suggestion.

### Tier 4: none

If no source clears the floor:

```text
playhead = None
section may still be known as "track has structure" but current position is unknown
suppress_timing_claims = True
```

## Section mapping

Given `PlayheadEstimate.position_s` and `AnlzTrackMeta.phrases`:

```text
find phrase where start_s <= position_s < end_s
next phrase = following phrase
bars_to_next = floor((next.start_beat - current_beat) / 4)
```

Confidence:

```text
section_confidence = min(playhead.confidence, phrase.confidence)
```

Role rules:

- high-mood ANLZ roles can be stated when confidence floor passes;
- mid/low-mood roles may be used internally but should be hedged in language;
- unknown ANLZ kind maps to no role but can still provide a boundary.

## Confidence floors

Use these floors:

```text
section_awareness_floor = 0.50
prep_suggestion_floor   = 0.50
live_suggestion_floor   = 0.62
rounded_timing_floor    = 0.70
exact_bars_floor        = 0.80
```

Behavior:

```text
<0.50      no current-section claim
0.50-0.62  prep-style suggestion only
0.62-0.70  suggest track/cue, no timing
0.70-0.80  "soon" / rounded phrase timing
>=0.80     exact "in N bars" timing allowed
```

## Blend suppression

Blend is likely when:

- `MusicState.audible_deck == "mix"`;
- both channel faders are up with crossfader centered;
- recent moves include crossfader/channel fader motion;
- now-playing title changed recently while audio from previous deck likely still
  audible.

Blend behavior:

```text
if blend_state == "blend":
    suppress exact timing claims
    keep prep suggestion if candidate confidence is high
    do not re-anchor audio alignment unless confidence is strong
```

Default blend suppression window:

```text
10-15 seconds after deck/title transition or heavy fader movement
```

Wrong confidence during blends is the main trust killer.

## Agent policy

Agent may say:

- "cue B is a good next entry" when track/cue/section is grounded.
- "soon" when playhead confidence is medium.
- "in 16 bars" only when `exact_bars_floor` passes.
- "timing is not locked" when the candidate is useful but live position is weak.

Agent must not say:

- exact bar counts below floor;
- current section role below floor;
- "drop/breakdown" as fact for low-confidence/mid-mood mappings;
- anything inferred from raw LLM listening.

## EvidenceRegistry posture

Do not add new citation sources in the first slice.

Use existing citations:

```text
track:<track_id>
mix:audible_deck=<side>
key:<side>:<camelot>
aud:bpm
```

Later, if the linter/schema work is scheduled, add:

```text
playhead:<estimate_id>
section:<section_id>
packet:<packet_id>
```

That must be a locked multi-file schema update because `EvidenceRegistry`
sources are mirrored.

## Proposed files

Add:

```text
src/vibemix/intel/live_awareness.py
tests/intel/test_live_awareness.py
```

If `intel/` package is deferred:

```text
src/vibemix/runtime/live_awareness.py
tests/runtime/test_live_awareness.py
```

Support source extraction:

```text
src/vibemix/audio/nowplaying_position.py
tests/audio/test_nowplaying_position.py
```

This can wrap/factor `LookaheadProvider._current_position()` so lookahead and
live awareness share the stale-elapsed guard.

## Build order

### INTEL-06A: data types and pure mapper

- Add `PlayheadEstimate`, `SectionPosition`, `LiveAwarenessSnapshot`.
- Add pure `map_position_to_section(meta, estimate)`.
- Tests use synthetic ANLZ-like phrase objects.

### INTEL-06B: now-playing position source

- Factor now-playing title/elapsed/rate polling out of `LookaheadProvider`.
- Preserve stale elapsed extrapolation guard.
- Tests mock subprocess JSON and title changes.

### INTEL-06C: LiveAwarenessService holder

- Reads `MusicState` snapshots.
- Resolves identity from `deck_state`.
- Builds Tier-1/Tier-2 playhead estimates.
- Maps to ANLZ sections.
- Writes only its own holder.

### INTEL-06D: SuggestionService integration

- Context packet reads `LiveAwarenessSnapshot`.
- `next_transition` uses current/next section when available.
- Old `next_suggestion` remains for compatibility.

### INTEL-06E: audio alignment spike

- Offline first: align captured snippets against known track files.
- Measure margin/confidence on local sessions.
- Only then consider BeatNet or heavier deps.

## Tests

Minimum tests:

- title/track mismatch suppresses elapsed source;
- stale elapsed extrapolates but lowers confidence;
- blend state suppresses exact timing;
- low `bpm_confidence` suppresses exact bar claims;
- `map_position_to_section` returns current/next section and bars-to-next;
- no position source -> no timing claim;
- service does not write `MusicState`;
- old `next_suggestion` payload remains unchanged.

## Eval gates

Add to INTEL-03 scorecard:

```text
playhead_known_rate
exact_timing_claim_rate
timing_claim_below_floor_rate
wrong_section_claim_rate
blend_suppression_precision
blend_suppression_recall
position_error_seconds_median
position_error_bars_p90
```

Initial gates:

```text
timing_claim_below_floor_rate = 0
wrong_section_claim_rate <= 0.05 on labeled local review
blend_exact_timing_claim_rate = 0
position_error_bars_p90 <= 2 for exact-timing tier
```

## Failure modes and responses

| Failure | Response |
|---------|----------|
| active track unknown | no live transition, prep suggestions only |
| title mismatch | suppress elapsed source |
| elapsed stale | extrapolate with lower confidence |
| deck is mix | suppress exact timing |
| no ANLZ for track | track-level pill only |
| low mood/low confidence section | use internally, hedge or suppress language |
| audio alignment ambiguous | keep previous estimate briefly, then suppress |
| source jumps backward | reset on track change, otherwise mark stale |

## First coding slice

Smallest useful slice:

```text
src/vibemix/audio/nowplaying_position.py
src/vibemix/intel/live_awareness.py
tests/audio/test_nowplaying_position.py
tests/intel/test_live_awareness.py
```

No model dependency. No audio alignment. No UI work.

Success means the backend can answer:

```text
Track X is active on deck A.
Position is probably 143.2s from now-playing elapsed.
That maps to ANLZ section "drop" with 0.76 confidence.
Next section begins in about 12 bars.
Exact timing is allowed/not allowed.
```

That is the live bridge from grounded structure to a trustworthy pill.
