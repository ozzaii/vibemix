# Phase 30: 2 Hard Tek Detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY) - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

Complete the v2.0 6-detector taxonomy with the 2 Hard Tek overlays Phase 17 pre-committed to, so Hard Tek sessions get the same DSP-grounded event firing as techno/house.

**Mapped REQ-IDs (4):** SENSE-17 (DISTORTION_CLIMB), SENSE-18 (ACID_LINE_ENTRY), SENSE-19 (GenreRouter atomic-swap regression test), SENSE-20 (`tune_detectors.py` extended with Hard Tek refs).

**In scope:**
- `DISTORTION_CLIMB` detector — band-limited spectral-flatness rise + harmonic-distortion proxy + sustained kick density. 6s cooldown. Cites `[ev:DISTORTION_CLIMB@<t>]` with `chain_position` + `distortion_db` fields.
- `ACID_LINE_ENTRY` detector — TB-303-style 200–800Hz formant-sweep autocorr + resonance-rise envelope. 8s cooldown. Cites `[ev:ACID_LINE_ENTRY@<t>]` with `formant_hz` + `resonance_q` fields.
- `GenreRouter` registers all 8 detectors at construct time only via `MappingProxyType` (immutable mapping). 1000-cycle stress test (Pitfall P49 atomic-swap break).
- `scripts/tune_detectors.py` extended with Kaan-curated Hard Tek reference tracks → `eval/corpus/hard_tek/README.md` documents the curated set.

**Out of scope:**
- New detectors beyond DISTORTION_CLIMB + ACID_LINE_ENTRY.
- Genre detection logic changes (GenreRouter already routes Hard Tek per v2.0 Phase 17).
- Detector retuning for techno/house (taxonomy stays at 4 there).
- ML-based detection — pure DSP only (memory + project anti-slop thesis).
- Real-time visualization of detector activations.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 30 success criteria (verbatim)
- REQUIREMENTS.md SENSE-17..20
- Pitfall P49 (GenreRouter atomic-swap break)
- v2.0 Phase 17 GenreRouter + `build_hard_tek_chain` slot (shipped)
- POC `cohost_v4.py` canonical baseline for detector contracts (memory)
- `cohost_lk.py` band-shift detection (memory `feedback_poc_is_reference`)

### DISTORTION_CLIMB DSP (SENSE-17)
- **Band-limited spectral flatness:** Wiener entropy on 200Hz–2kHz band → rising over 4 windows (Δ ≥ 0.15) indicates distortion onset.
- **Harmonic-distortion proxy:** ratio of energy in 1st 6 harmonics of kick fundamental (~50–80Hz) vs odd-harmonic energy ≥ 1.5 over baseline.
- **Sustained kick density:** kick-onset rate ≥ 8/sec for ≥ 4s.
- **Fire condition:** ALL THREE conditions met simultaneously within a 2s window → emit. 6s cooldown.
- **Citation payload:** `{chain_position: int (0-7 sequential per session), distortion_db: float}`.

### ACID_LINE_ENTRY DSP (SENSE-18)
- **TB-303 formant sweep:** autocorrelation of dominant frequency in 200–800Hz band → linear or exponential sweep over ≥ 1.5s (slope > 0.2 oct/sec).
- **Resonance-rise envelope:** spectral peakiness (peak energy / mean energy in formant band) rising from < 3 to > 8 over the sweep window.
- **Fire condition:** BOTH within a 3s window → emit. 8s cooldown.
- **Citation payload:** `{formant_hz: float (sweep midpoint), resonance_q: float (peak-to-mean ratio)}`.

### GenreRouter atomic-swap (SENSE-19 / P49)
- Construct-time registration ONLY. `_detectors: MappingProxyType[str, Detector]` — immutable mapping.
- No `register_detector(...)` runtime method (delete if exists; assert no callers).
- 1000-cycle stress test: spin up GenreRouter under threading.Thread × 8 concurrent reads — no race, no mutation, MappingProxyType raises on write attempt.
- Per-genre detector lists are pre-built tuples at construct time.

### Tuning evidence (SENSE-20)
- `scripts/tune_detectors.py --genre=hard_tek` accepts a directory of reference WAVs, runs both detectors, emits per-track scorecard with detector activations + thresholds + cooldown rejections.
- `eval/corpus/hard_tek/README.md` documents: source attribution (archive.org / CCMixter / FMA per Phase 27 corpus policy), track titles, BPM, runtime length, license, why-included rationale.
- Output: `eval/tuning/hard_tek_2026-05-15.json` scorecard.

### Genre activation
- Hard Tek detectors fire ONLY when `GenreRouter.current_genre == "hard_tek"`. House/techno sessions never see them — no false positives in non-target genres.
- Genre detection logic comes from Phase 17 (unchanged).

### Integration with v2.1 eval harness (Phase 27)
- Both detectors must be replayable through `scripts/eval/replay_harness.py` deterministically.
- 2-judge cross-check rubric scores the detectors against the hard_tek corpus segment.
- F1 ≥ 0.80 per detector in the hard_tek genre slice (Phase 27 EVAL-03 per-detector-per-genre matrix).

### Test discipline
- Unit tests for each DSP primitive (spectral flatness, autocorr sweep, etc) — pure-function with NumPy fixtures.
- Integration tests with synthesized signal fixtures (programmatically generated TB-303 sweeps, distortion bursts).
- 1000-cycle GenreRouter race test (threaded).
- Replay test through eval harness against hard_tek corpus.

</decisions>

<code_context>
## Existing Code Insights

- **`GenreRouter`** — v2.0 Phase 17 shipped. File: `src/vibemix/detectors/genre_router.py` (assumed; verify in plan-phase). Has `build_hard_tek_chain` slot.
- **Detector base contract** — v2.0 6-detector taxonomy. Files under `src/vibemix/detectors/` per genre.
- **`cohost_v4.py` canonical POC** — has the original Hard Tek heuristics tuned over real Kaan sessions (memory `project_v4_canonical_baseline`). Lift logic; do not edit POC.
- **EvidenceRegistry** — Phase 18. Detectors emit via `registry.fire("DISTORTION_CLIMB", payload)`.
- **AudioBuffer + Levels** — Phase 17 audio core. Snapshot features available.
- **scripts/tune_detectors.py** — exists from v2.0 Phase 17 (or scaffold from there).
- **Test discipline** — `tests/detectors/test_<detector>.py` pattern.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **DSP-only, no ML** — memory + anti-slop thesis. Detectors are deterministic-signal-grounded, not learned.
- **TB-303 sweep is the iconic acid sound** — research on its harmonic profile is well-documented.
- **Hard Tek session = 150-180 BPM** — kick density gating per BPM scaling.
- **Curated reference tracks** — Kaan has Hard Tek session corpus in his library; pick 3-5 reference tracks at planning time.
- **Cooldown windows are CRITICAL** — 6s + 8s prevent firing-spam during sustained passages. Test that no DISTORTION_CLIMB fires in [0, 6s] after a prior fire.
- **MappingProxyType** is Python 3.12+ standard — perfect immutable map without freezing.

</specifics>

<deferred>
## Deferred Ideas

- **ML-based detector enhancement (e.g., CNN classifier):** explicitly excluded (memory `feedback_no_clap_use_gemini_embedding`).
- **More detector types** — gabber sub-genre / industrial / DnB-specific: v2.2 backlog.
- **Real-time detector visualization in UI:** out of scope.
- **Detector self-tuning from session feedback:** v2.2 stretch (would need Phase 32 profile).
- **Multi-deck detector context** — e.g., distortion only on outgoing deck: v2.2.
- **Stems-aware detection** — separate kick layer for harmonic-distortion proxy: deferred (memory v2 candidates).

</deferred>
