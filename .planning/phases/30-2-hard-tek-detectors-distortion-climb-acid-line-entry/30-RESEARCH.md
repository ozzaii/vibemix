# Phase 30 — Research

**Date:** 2026-05-15
**Mode:** gsd-autonomous fully
**Author:** Phase-execution agent

## Sources reviewed

| File | Why |
|------|-----|
| `src/vibemix/state/genre_router.py` | Existing GenreRouter; needs `MappingProxyType` swap (SENSE-19) |
| `src/vibemix/events/genres/__init__.py` | `GENRE_REGISTRY` dict — convert to immutable mapping |
| `src/vibemix/events/genres/hard_tek.py` | `build_hard_tek_chain` — extend with two new detectors |
| `src/vibemix/state/detectors/__init__.py` | Export surface for new detectors |
| `src/vibemix/state/detectors/_dsp.py` | Shared kick-band DSP — extend with new primitives |
| `src/vibemix/state/detectors/kick_swap.py` | Reference detector skeleton |
| `src/vibemix/state/detectors/breakdown_kick_kill.py` | State + cooldown idiom |
| `src/vibemix/state/event.py` | Event dataclass + `EVENT_PRIORITY` — must add new types |
| `src/vibemix/audio/constants.py` | `MIN_EVENT_GAP_PER_TYPE` + new thresholds |
| `src/vibemix/state/event_detector.py` | How `router.active_chain()` is iterated |
| `src/vibemix/audio/buffers.py` | `AudioBuffer.snapshot(n)` returns int16 |
| `scripts/tune_detectors.py` | Tuning harness — extend with `--genre=hard_tek` corpus support |
| `tests/state/detectors/test_kick_swap.py` | Test fixture patterns + `_FakeAudioBuf` |
| `tests/state/detectors/conftest.py` | `_state()` + `_audio_sine()` helpers |
| `tests/state/test_genre_router.py` | Existing router test surface |
| `eval/corpus/sessions/hard_tek_01/` | Existing slice — `genre.txt`, `events.jsonl`, `source.txt` |

## Key findings

### Detector contract
- `def detect(self, state: MusicState, audio_buf: AudioBuffer | None, now: float) -> Event | None`
- Silence gate FIRST (`state.rms < LOW_RMS` → None) — anti-hallucination.
- `audio_buf is None` → graceful None.
- Snapshot via `audio_buf.snapshot(int(audio_buf._sr * window_sec))` returns int16.
- Cooldown via `MIN_EVENT_GAP_PER_TYPE[<TYPE>]`.
- Event fired with `Event("<TYPE>", state, extra={...})`.

### Router consumption
- `EventDetector.detect()` runs `for det in self.router.active_chain(): ev = det.detect(state, self.audio_buf, now)` and short-circuits on first non-None.
- Chain order matters — paired detectors (kill/reentry) must keep ordering.
- `MIN_EVENT_GAP_PER_TYPE` lookup in `_cooldown_ok` uses string event type.

### Hard Tek genre gate (already wired)
- `state_refresh_loop` writes `state.active_genre` from BPM bands.
- `event_detector.detect()` swaps router chain when active_genre flips.
- Hard Tek detectors fire ONLY when chain is the hard_tek chain — no extra gate inside detector needed; chain selection IS the gate.

### MappingProxyType refactor (SENSE-19 / P49)
- `GENRE_REGISTRY: dict[str, Callable] = {...}` → wrap with `types.MappingProxyType(...)`.
- `GenreRouter._initialized` sentinel kept for first-swap path.
- 1000-cycle threaded race test: spawn 8 reader threads doing `router.active_chain()` in tight loop while main thread does `swap("hard_tek")` ↔ `swap("techno")` × 1000.
- Iteration must never raise (snapshot tuple semantics).

### DSP primitives required
**For DISTORTION_CLIMB:**
- Band-limited spectral flatness (Wiener entropy on 200Hz–2kHz). `geometric_mean / arithmetic_mean` of magnitude spectrum within the band.
- Harmonic distortion proxy: energy in 1st 6 harmonics of kick fundamental (~60Hz peak in 40-80Hz band) vs odd-harmonic energy.
- Kick onset density: per-second onset rate (already in `state.onset_density`? — check; fall back to local kick-band peak picking).

**For ACID_LINE_ENTRY:**
- Dominant frequency tracking in 200–800Hz band (argmax of FFT magnitudes within band).
- Sweep detection: linear regression slope of dominant_freq over time (≥ 1.5s of samples).
- Resonance: peak_magnitude / mean_magnitude in formant band (peakiness).

All numpy + scipy only. No new deps.

### Reference corpus
- `eval/corpus/sessions/hard_tek_01/` exists but source URL placeholder.
- Phase 30 corpus README captures KAAN-ACTION items for real-track acquisition; for now the harness runs against synthetic fixtures + the existing placeholder slice.

### Detector cooldowns
- DISTORTION_CLIMB → 6.0s
- ACID_LINE_ENTRY → 8.0s
- Both added to `MIN_EVENT_GAP_PER_TYPE`.

### Event priority
- Both are "structural moment" — same priority tier as `LAYER_ARRIVAL`/`MIX_MOVE` (4-5). Use 5 for both (more salient than LAYER_ARRIVAL since they're climactic moments).

## Open questions deferred to KAAN

- Curated Hard Tek reference tracks — Kaan to commit anchors to `eval/corpus/hard_tek_refs/` (Phase 27 corpus policy: archive.org / CCMixter / FMA). README ships with placeholder + acquisition checklist.

## Plan decomposition

Phase 30 splits into 4 atomic plans, one per REQ-ID:

1. **30-01: DISTORTION_CLIMB detector** (SENSE-17) — DSP primitives + detector class + unit tests + integration into hard_tek chain.
2. **30-02: ACID_LINE_ENTRY detector** (SENSE-18) — DSP primitives + detector class + unit tests + chain integration.
3. **30-03: GenreRouter MappingProxyType + 1000-cycle race test** (SENSE-19 / P49).
4. **30-04: tune_detectors.py Hard Tek extension + corpus README** (SENSE-20).

Each plan ships its own atomic commit. No cross-plan dependencies inside the phase except: Plan 30-03 must run AFTER 30-01 + 30-02 so the new detector types are registered in the constants tables before the immutable-mapping refactor pins them.
