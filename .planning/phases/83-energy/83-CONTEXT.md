# Phase 83: ENERGY — Perceived-Dancefloor-Energy v1 - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Research-driven (discuss skipped — implementation-ready research exists)

<domain>
## Phase Boundary

Give the DJ a trustworthy 0-100 **perceived-dancefloor-energy** score per track (how hard it hits the floor, not how loud), computed offline from the local audio file, genre-robust, cached, exposed to the agent. Pure-compute foundation; NON-BLOCKING for the sequencer (which degrades to a BPM proxy when energy is absent).

IN: `library/energy.py` (`score_energy(audio_path) -> EnergyScore`), content-hash cache, `get_track_energy` tool in `LibraryToolset`, energy tuning constants in `audio/constants.py`, offline unit tests.
OUT: XGBoost regressor (Future), 1001Tracklists scraping (out-of-scope), any new dep, any Gemini call.
</domain>

<decisions>
## Implementation Decisions (LOCKED by research — `.planning/research/vibe-mix-engine-research.md` §A)

- **Reuse existing hand-rolled DSP — ZERO new deps.** essentia is AGPL (poison) AND not installed; librosa not installed. Use: `library/cue_detect.py::decode_to_mono(path, sr=16000)` (ffmpeg decode), `audio/features.py` (`snapshot_features` band-split + onset, `energy_curve`), `state/genre/crest_factor.py::crest_factor`, `state/detectors/_dsp.py::sub_share`. ADD ONE new primitive: spectral flux (~15 LOC, rfft frame-diff half-wave-rectified) — the strongest perceived-arousal predictor (the spec's v1 formula omits it = its biggest gap).
- **v1 weights (sum 1.0, ×100), in `audio/constants.py` as one-line-edit constants:** loudness(crest-corrected P80 dBFS) 0.18 · sub-bass SHARE 0.15 · onset rate 0.15 · **spectral flux 0.22** · brightness(centroid) 0.15 · beat regularity 0.08 · RMS dynamic-range(CoV) 0.07.
- **Normalization = fixed perceptual windows + `np.clip` per track, NOT corpus min-max** (corpus min-max = "one loud track skews everything" + non-reproducible). Aggregate over BUSY frames only (RMS > 5% of peak — the `cue_detect` mask) so intro/outro dead air doesn't contaminate.
- **Genre robustness (the make-or-break):** demote raw RMS, promote flux/brightness, crest-correct the loudness term, use shares/ratios. Quiet hypnotic ≠ low; loud-sparse intro ≠ high.
- **Cache:** content-hash keyed (mirror the embedding cache pattern), re-runs free.
- **`get_track_energy(track_id)` in `LibraryToolset`** (single tool core → inherited by gemini + codex/MCP + Telegram). Honest `null` when no decodable audio. Deterministic fact — model never supplies energy.
- **Energy is OPTIONAL to the sequencer** (Phase 85 takes `energy: dict|None`); do not block anything on it.

### Claude's Discretion
EnergyScore dataclass shape, exact dBFS/Hz/onset windows (tune to sane DJ ranges), cache file location under `~/.cache/vibemix/`, flux frame size (reuse the rfft frame conventions already in `_dsp.py`).
</decisions>

<code_context>
## Existing Code Insights
- `cue_detect.decode_to_mono` is the offline-decode template (16kHz mono, matches live pipeline bit-for-bit). **DO NOT EDIT cue_detect.py** (concurrent session owns it) — import and call it.
- `audio/features.py` band split = sub(20-100)/low(100-300)/mid(300-4k)/high(4-8k); onset = adaptive-threshold RMS-delta peaks. `audio/constants.py` is the constants home.
- Vectors/embeddings unrelated here — energy is pure DSP over the decoded file.
</code_context>

<specifics>
## Specific Ideas
- **Validation = cheap, NO 200 hand-labels:** (1) pairwise-ranking test ~ a handful of known A>B pairs (peak banger > deep intro; drop window > breakdown window of the same track via rolling-window scoring), (2) within-track monotonicity, (3) **hypnotic-regression guard** (quiet-energetic afterhours out-ranks loud-sparse ambient) as a unit test. Synthetic fixtures (sine / white-noise / compressed-square) pin flux/centroid/crest on known signals.
- Offline-green: no API key, no Gemini, no network. New `tests/library/test_energy.py`.
- If touching stack docs, fix the CLAUDE.md "essentia in the stack" claim (it is NOT installed and must not be).
</specifics>

<deferred>
## Deferred Ideas
- XGBoost regressor (keep the 7 features as its future input vector). Genre-conditioned re-centering (phase 1.5). Cue-anchored energy windows (once `CueAnchor` lands).
</deferred>
