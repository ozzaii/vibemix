# Phase 17: Hard Tek Detectors v1 + GenreRouter + MusicState Extension - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

Six cross-genre event detectors fire on the bar that defines the moment — closes Kaan's "feels surface-level" critique. Extends `MusicState` with 4 new fields (`buildup_score`, `predicted_drop_in_sec`, `beat_phase`, `active_genre`); ships `GenreRouter` for atomic per-genre detector swap; ships `scripts/tune_detectors.py` reference-WAV harness feeding Phase 16 ear-audit.

</domain>

<decisions>
## Implementation Decisions

### Detector Set (LOCKED — per ROADMAP + STATE)
- **Six baseline detectors:** `KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`.
- **Deferred to v2.1:** `DISTORTION_CLIMB`, `ACID_LINE_ENTRY` (Hard Tek overlay) — explicitly cut per memory + STATE locked decision.
- **Predictive drop firing OFF-by-default in v2.0** (per memory `feedback_no_scope_creep_clean_utility`). Telemetry guard pre-wired for v2.1 turn-on after Phase 16 ear-test baseline.

### Architecture (LOCKED — per cross-doc reconciliation in STATE)
- **MusicState extension:** new fields are `buildup_score: float`, `predicted_drop_in_sec: float | None`, `beat_phase: float`, `active_genre: str`. Backward-compat defaults so Phase 3 golden-equivalence tests stay green.
- **GenreRouter:** atomic swap of `detector_dict` on `MusicState.active_genre` change; no session restart.
- **Per-genre cooldown** (LOCKED): tuning matches `G-followup-1` (`MIN_EVENT_GAP_PER_TYPE`).
- **Autocorrelation band:** PHRASE_BOUNDARY uses 40-120 Hz band-limited autocorr; self-corrects on `BREAKDOWN_KICK_KILL`.

### Tuning Harness (LOCKED)
- `scripts/tune_detectors.py` — reads reference-WAV files (Hard Tek 7-10 anchor tracks Kaan-owned), emits per-fire CSV consumable by Kaan in Phase 16 ear-audit.
- CSV schema: `(track, t_seconds, bar_index, detector_name, score, threshold, fired)`.
- Hard Tek anchor tracks: STATE outstanding — Kaan-action. If unavailable, harness runs against existing recorded sessions from Phase 15 instead (degraded mode).

### Genre Detection (Claude's Discretion)
- `active_genre` derived from BPM-band + spectral-centroid heuristics (no ML in v2.0). Coarse buckets: `house` (118-128 BPM), `techno` (128-138), `hard_tek` (140-160+), `unknown` (everything else).
- Genre flips trigger atomic `GenreRouter.swap()`; per-genre detector dict registered at boot.

### POC Port-From (LOCKED — per CLAUDE.md + memory)
- Canonical baseline: `cohost_v4.py` (per memory `project_v4_canonical_baseline`).
- Port detector logic + thresholds, do NOT touch POC files (they remain reference-only).
- Honor "trust the audio" anti-hallucination rule from v4.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/state/music_state.py` — Phase 6 `MusicState` dataclass (extend in-place with new fields, not new class).
- `src/vibemix/state/event_detector.py` — Phase 6 EventDetector v4 baseline (existing detectors port pattern).
- `src/vibemix/audio/buffer.py` — Phase 4 audio buffer (FFT/RMS/onset extraction primitives).
- `cohost_v4.py` — POC reference (port-from only, don't modify).
- Phase 3 golden-equivalence tests — must stay green after MusicState extension.

### Established Patterns
- Single-writer `state_refresh_loop` @100ms (cohost_v2 pattern, lifted into v4 sidecar).
- Typed Event objects with per-type cooldown (`MIN_EVENT_GAP_PER_TYPE`).
- Dependency injection — pass `MusicState` + `Levels` + `AudioBuffer` explicitly, no globals.
- pytest tests live in `tests/state/`, `tests/detectors/`.

### Integration Points
- `session_loop.py` reads MusicState; existing event consumers continue to work via backward-compat defaults.
- `EventDetector` becomes `GenreRouter`-wrapped — same call surface (`.detect(state) -> list[Event]`).
- Reference-WAV harness `scripts/tune_detectors.py` is standalone — no IPC, just file in / CSV out.

</code_context>

<specifics>
## Specific Ideas

- Wave-1: MusicState extension + golden-equivalence regression test (Phase 3 tests stay green).
- Wave-2 (parallel): 3 of the 6 detectors per plan.
- Wave-3: GenreRouter + atomic swap.
- Wave-4: tune_detectors.py harness.

</specifics>

<deferred>
## Deferred Ideas

- Hard Tek overlay detectors (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY`) — v2.1.
- ML-based genre classifier — v2.x (use heuristic BPM+centroid in v2.0).
- Predictive drop firing turn-on — v2.1 (telemetry pre-wired, OFF by default).
</deferred>
