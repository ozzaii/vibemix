# Phase 6: Genre-Aware Phase Detection - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the absolute-threshold `classify_phase` from Phase 3 (`vibemix.state.phase`) with a **percentile-based, per-genre phase detector** that adapts to each track's own loudness distribution rather than relying on globally-tuned RMS constants. Also land three companion DSP guards that v4's absolute-threshold path doesn't have:

1. **Crest-factor compression detection** — measure `peak / rms` ratio on the rolling buffer. Low ratio (< 4) = heavily compressed master (loudness-war / modern dance). High ratio (> 12) = dynamic master (jazz / acoustic / vintage). Influences which percentile thresholds apply.
2. **BPM half/double validator** — autocorrelation often locks onto the half- or double-speed kick pattern (62 BPM detected on a 124 BPM track; 250 BPM on a 125 BPM track). Snap to expected range from the active genre profile before publishing to MusicState.
3. **Vocal-section gating** — high mid-band energy (300-3000 Hz share > 0.45) + sustained pitched onsets + reduced sub-bass share = likely vocal section. Mark `MusicState.vocal_active` and use it to gate certain event types (e.g., don't fire LAYER_ARRIVAL on every word).

5 genre profiles ship as JSON: **techno**, **house**, **drum-and-bass**, **disco**, **pop**. Each profile encodes the percentile thresholds, BPM range, expected crest factor, characteristic band distribution, and any genre-specific overrides.

**In scope:**
- `src/vibemix/state/genre/` — new subpackage
  - `profiles/{techno,house,drum_and_bass,disco,pop}.json` — 5 genre profiles
  - `genre/__init__.py` — re-exports `GenreProfile`, `load_profile(name)`, `list_profiles()`, `detect_genre_from_audio(features)`, plus the active-profile singleton
  - `genre/profile.py` — `@dataclass(frozen=True) GenreProfile` (pydantic-validated load from JSON)
  - `genre/detector.py` — `classify_phase_percentile(curve, features, profile) -> str` (replacement for `vibemix.state.phase.classify_phase`)
  - `genre/crest_factor.py` — `crest_factor(pcm_int16) -> float` (peak / RMS)
  - `genre/bpm_validator.py` — `validate_bpm(raw_bpm, profile) -> tuple[bpm_normalized, was_corrected]`
  - `genre/vocal_detector.py` — `is_vocal_section(features, recent_features) -> bool`
- `src/vibemix/state/phase.py` — extended: `classify_phase` becomes the public entry point; internally dispatches to absolute-threshold (genre=None or "unknown") or percentile-based (active profile). v4 behavior is preserved as the fallback path.
- `src/vibemix/state/refresh.py` — extended to compute crest factor + validated BPM + vocal_active on each 10Hz tick and write into MusicState.
- `MusicState` — extend with: `crest_factor: float`, `vocal_active: bool`, `bpm_corrected: bool`, `genre_profile_name: str`. Constructor defaults preserved (`Optional[str]` → "unknown").
- `EventDetector` — no shape change, but `LAYER_ARRIVAL` is now gated on `not state.vocal_active` (avoid firing when a vocal naturally arrives).
- Settings hook for Phase 12: `set_active_genre_profile(name)` writes to a module-level singleton (Phase 12 UI plumbs it).
- Per-genre validation harness — replay 30-min recorded sets per genre (Kaan's responsibility to collect; tests use synthetic data + 2-3 sample WAVs from POC `recordings/` if available).
- Tests: percentile thresholds correct vs golden curves; BPM half/double validator on synthetic data; crest factor math; vocal detector on synthetic; full classify_phase_percentile golden tests.

**Out of scope:**
- Auto-detection of genre from audio fingerprint (Shazam-style) — too heavy for v1. Kaan picks profile in Settings (Phase 12). Profile defaults to "techno" since that's Kaan's set.
- Per-deck genre profiles (deck A is techno, deck B is house) — single-deck profile for v1. Phase 9+ may revisit.
- Genre profile training UI — JSON files hand-tuned for v1. Future revisit if abuse appears.
- Real-time crest-factor compression smoothing across tracks — emit per-snapshot value only.
- F1≥85% per-genre phase-detection metric (the Phase 16 acceptance gate) — Phase 6 ships the detector; Phase 16 measures it.

</domain>

<decisions>
## Implementation Decisions

### Percentile-Based Phase Detector (locked)
- **Input:** rolling energy curve (1Hz hop over last 120s = 120 samples). Phase 3 already ships `audio_buf.long_arc_curve(seconds=120.0, hop=1.0)`.
- **Algorithm:** compute the **30th**, **70th**, and **95th** percentiles of the recent curve. Map current RMS to a phase tier:
  - `current < p30` → `"low"` (filtered breakdown, verse, intro)
  - `current ≥ p30 AND < p70` → `"groove"` (mid-energy main)
  - `current ≥ p70 AND < p95` → `"peak"` (anthem section, sustained high energy)
  - `current ≥ p95` → `"drop"` (top end, recent climb)
  - `current < absolute_silent` (from active profile) → `"silent"` (track gap)
  - **Build detection** runs FIRST: if the last 5 samples are monotonically climbing AND span > 0.020 RMS → `"build"`
  - **Breakdown detection** runs SECOND: if `last < 0.5 * recent_peak` AND `recent_peak > p70` → `"breakdown"`
- **Hysteresis:** require 3 consecutive ticks above/below a threshold before transitioning. Prevents 10Hz flapping.
- **Cold start:** if curve has < 30 samples (first 30s of session), fall back to absolute thresholds from the active profile.

### Genre Profile Shape (locked)
```json
{
  "name": "techno",
  "label": "Techno / Hard Tek / Acidcore",
  "bpm_range": [125, 175],
  "absolute_thresholds": {
    "silent_rms": 0.012,
    "low_rms": 0.040,
    "peak_rms": 0.110
  },
  "expected_crest_factor": [3.5, 6.5],
  "band_signature": {
    "sub": [0.25, 0.45],
    "low": [0.20, 0.35],
    "mid": [0.10, 0.25],
    "high": [0.05, 0.15]
  },
  "vocal_likelihood": "rare",
  "build_climb_threshold": 0.025,
  "breakdown_ratio": 0.4,
  "drop_jump_threshold": 0.060
}
```

### 5 Initial Profiles (locked)
- **techno** — 125-175 BPM, low crest (3-5), sub-heavy, rare vocals
- **house** — 118-130 BPM, mid crest (4-7), balanced bands, occasional vocals
- **drum_and_bass** — 165-180 BPM, low crest (3-5), sub + high heavy, vocals on intro/breakdown
- **disco** — 110-125 BPM, mid-high crest (5-9), mid + high band heavy, frequent vocals
- **pop** — 95-130 BPM, low crest (3-5), heavy compression, very frequent vocals

JSON files ship in `src/vibemix/state/genre/profiles/`. Loaded via `importlib.resources` (package data).

### Crest Factor Detection (locked)
- **Formula:** `crest = peak_int16 / rms_int16` where peak = `max(abs(pcm))`, rms = `sqrt(mean(pcm**2))`.
- **Windowed:** computed on the snapshot returned by `AudioBuffer.snapshot_features` (already in Phase 2).
- **Smoothing:** EMA with alpha=0.3 across snapshots → published as `MusicState.crest_factor`.
- **No genre auto-detect this phase** — crest just informs the active profile's "is this track typical for this genre?" sanity check. Logged for debugging.

### BPM Half/Double Validator (locked)
- **Inputs:** `raw_bpm` from `AudioBuffer.estimate_bpm` (from Phase 2), active profile's `bpm_range`.
- **Algorithm:**
  - If `raw_bpm` is within range → return as-is.
  - If `raw_bpm * 2` is within range → return `raw_bpm * 2`, `was_corrected=True`.
  - If `raw_bpm / 2` is within range → return `raw_bpm / 2`, `was_corrected=True`.
  - Otherwise → return `raw_bpm` unchanged, `was_corrected=False` (let EventDetector's BPM_VALID gate filter it out).
- **Confidence handling:** When `was_corrected=True`, log it. The genre BPM range is the source of truth.

### Vocal-Section Detector (locked)
- **Inputs:** current `snapshot_features` dict (`sub_share`, `low_share`, `mid_share`, `high_share`, `onsets_per_sec`), recent 5-snapshot history.
- **Heuristics (any 2 of 3 → True):**
  1. `mid_share > 0.45` AND `sustained_for >= 2s` (mids dominate)
  2. `onsets_per_sec` rising trend in last 3 snapshots (vocal phrasing)
  3. `high_share > 0.20` AND `sub_share < 0.30` (vocal sits above sub-bass)
- **Hysteresis:** require 1.5s of sustained "above threshold" to flip vocal_active → True. 2.5s to flip back to False.
- **Effect:** EventDetector skips LAYER_ARRIVAL while vocal_active = True (vocal arrival isn't a "new sonic layer" in the sense the event was designed to surface).

### Phase 3 `classify_phase` Behavior Preservation (locked)
- Phase 3's `classify_phase(curve, audible) -> str` stays available — it's the fallback when no profile is active or for "unknown" profile.
- New entry point: `classify_phase_with_profile(curve, features, profile_or_none, hysteresis_state) -> tuple[phase, hysteresis_state]`.
- `state_refresh_loop` calls the new function; if `profile_or_none is None` it dispatches internally to the old function.
- v4 byte-equivalence test: with profile=None on synthetic curves, the new function produces the same outputs as v4's `classify_phase`. Pin via golden test.

### Settings Integration (locked, minimal)
- `vibemix.state.genre.set_active_profile(name: str | None) -> None` — sets a module-level singleton. None means "use absolute thresholds" (Phase 3 behavior).
- Default at startup: "techno" (Kaan's genre). Phase 12 Settings UI flips it.
- `__main__.py` reads `VIBEMIX_GENRE_PROFILE` env var on startup; if set, calls `set_active_profile` before spawning loops. Defaults to "techno" if not set.

### File Layout
```
src/vibemix/state/
├── phase.py               # extended: classify_phase dispatches
└── genre/
    ├── __init__.py
    ├── profile.py         # GenreProfile dataclass + JSON loader
    ├── detector.py        # classify_phase_percentile()
    ├── crest_factor.py    # crest_factor() helper
    ├── bpm_validator.py   # validate_bpm()
    ├── vocal_detector.py  # is_vocal_section()
    └── profiles/
        ├── techno.json
        ├── house.json
        ├── drum_and_bass.json
        ├── disco.json
        └── pop.json
```

### Claude's Discretion
- Whether crest factor + BPM validator + vocal detector live in `state.genre/` or as standalone modules in `state/`. Recommend grouping under `genre/` since all four are genre-aware.
- Test fixture strategy for the percentile detector — use synthetic energy curves (sine + step + decay patterns) rather than real audio. Real-audio replay is Phase 16 work.
- Hysteresis state container — recommend a small `@dataclass` `HysteresisState` passed by reference through `state_refresh_loop`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phases 1-5)
- `vibemix.audio.AudioBuffer.long_arc_curve(seconds=120.0, hop=1.0)` — the curve the percentile detector reads (Phase 2).
- `vibemix.audio.AudioBuffer.snapshot_features` — band shares + onsets_per_sec + rms (Phase 2).
- `vibemix.audio.AudioBuffer.estimate_bpm` — raw BPM the validator corrects (Phase 2).
- `vibemix.state.MusicState` — extended this phase with `crest_factor`, `vocal_active`, `bpm_corrected`, `genre_profile_name`.
- `vibemix.state.phase.classify_phase` — Phase 3's absolute-threshold detector; kept as fallback.
- `vibemix.state.refresh.state_refresh_loop` — Phase 3's 10Hz writer; extended to call new helpers and write new fields.
- `vibemix.audio.constants` — `SILENT_RMS`, `LOW_RMS`, `PEAK_RMS`, `BPM_VALID_MIN/MAX` already lifted. These become the **fallback / unknown-profile** thresholds; per-profile JSON overrides them.

### Integration Points
- **Phase 10 (Prompt Template Matrix)** — `AICoach.evidence_line` may surface `vocal=on/off` and `crest=N.N` for prompt evidence. Phase 6 ships the data; Phase 10 decides what to expose.
- **Phase 12 (Settings UI)** — genre profile picker in Settings panel. Reads `vibemix.state.genre.list_profiles()` for options; writes via `set_active_profile`.
- **Phase 16 (Hallucination Verification)** — per-genre F1 ≥85% gate runs against the 30-session replay suite. Phase 6 ships the detector; Phase 16 measures.
- **EventDetector** — Phase 6 extends LAYER_ARRIVAL gating with `not state.vocal_active`. All other event types unchanged.

</code_context>

<specifics>
## Specific Ideas

- **Percentile window of 120s** matches Phase 2's `long_arc_curve` already on hand — no new buffer math needed.
- **Hysteresis of 3 ticks** at 10Hz = 300ms minimum dwell time. Tighter than human perception threshold for phase transitions.
- **JSON profiles, not Python dicts** — clean import via `importlib.resources`, easy to add a 6th genre later (drum-and-bass, dubstep, breaks) without code changes.
- **Single active profile per session** for v1 — multi-deck profile inference is post-v1.
- **`MusicState.vocal_active` as `bool`** — not 0..1 confidence. Hysteresis handles flapping.
- **`MusicState.bpm_corrected` as `bool`** — surfaced in evidence_line for debug ("bpm=128 (corrected from 64)").
- **No genre auto-detect from audio in Phase 6** — would need a model + audio fingerprint lookup. v1: Kaan picks. Future: maybe.

</specifics>

<deferred>
## Deferred Ideas

- Auto-detect genre from audio fingerprint → post-v1
- Per-deck genre profiles → post-v1
- Genre profile training UI → post-v1
- 30-session F1≥85% measurement → Phase 16
- 6th+ genre profiles (breaks, dubstep, hardstyle, downtempo, ambient) → future iterations after launch feedback
- Vocal-section confidence (0..1 score) → if Phase 10 prompt work shows it's needed
- Crest-factor smoothing across tracks (i.e., differentiate "this is a heavily-compressed track" vs "this is a compressed section of a dynamic track") → too DSP-heavy for v1
- BPM lock from MIDI (DDJ-FLX4 tempo CC) — overrides autocorr when controller is connected → Phase 9 fix territory

</deferred>
