# SPDX-License-Identifier: Apache-2.0
"""LOAD-BEARING tuning constants — French Touch / Daft Punk / Digitalism profile,
125-128 BPM, tuned against real DJ sessions on 2026-05-11. Do not casually re-tune
without a fresh live validation; Phase 6 will add genre-aware overrides on top.

Values lifted VERBATIM from cohost_v4.py — line anchors inline. v4 retuned 8 of
these from v3 for loudness-war-compressed French Touch masters (MUSIC_GAIN_TO_GEMINI
dropped from 8.0, SILENT_RMS / LOW_RMS / PEAK_RMS raised, EVENT_GLOBAL_MIN_GAP
lengthened, HEARTBEAT_SEC lengthened, INVOKE_AUDIO_SECONDS lengthened,
TRACK_CHANGE_MIN_CONFIDENCE added).

Three constants (MUSIC_PRESENCE_MIN_SECONDS, BPM_VALID_MIN, BPM_VALID_MAX) lived
as class-attrs of `EventDetector` in v4 (lines 1178-1182); 02-PATTERNS.md lifts
them OUT to module scope so Phase 3 can import without dragging EventDetector along.
"""

from __future__ import annotations

# ---- Audio I/O ----
INVOKE_AUDIO_SECONDS = 18.0  # v4:100 — rolling audio snapshot length to LLM (Phase 4 consumer)
INPUT_SR_NATIVE = 48000  # v4:106 — BlackHole capture rate
INPUT_SR_TARGET = 16000  # v4:107 — AudioBuffer / LLM consumption rate (post-resample)
OUTPUT_SR = 24000  # v4:108 — AI voice output rate
INPUT_CHUNK_FRAMES = 480  # v4:109 — input stream blocksize (= 10ms @ 48kHz)
OUTPUT_BLOCKSIZE = 256  # v4:110 — passthrough output blocksize
VOICE_BLOCKSIZE = 1024  # v4:111 — voice output blocksize
PASSTHROUGH_GAIN = 0.0  # v4:112 — djay→speakers passthrough gain (0 = silent, stream stays alive)
MUSIC_GAIN_TO_GEMINI = (
    1.0  # v4:113 — natural level (v4 dropped from 8.0; FT masters already compressed)
)

# ---- Mic + AI gating ----
MIC_GAIN = 1.0  # v4:116 — MicBuffer.base_gain
MIC_TALK_THRESHOLD = 0.09  # v4:117 — KAAN_SPOKE detection (Phase 3 consumer)
MIC_GAIN_AT_AI_TALK = 0.0  # v4:118 — mic mute level while AI talks
MIC_HOLD_AFTER_AI_MS = 350  # v4:119 — hold window after AI silence
AI_TALK_THRESHOLD = 0.02  # v4:120 — levels.voice threshold to flip AI-active

# ---- Plan 40-01 — mic-as-2nd-Part wiring (AUDIO-01) ----
# v4 reference: cohost_v4.py:1797 snapshot duration, cohost_v4.py:2278-2296
# zero-fill-on-AI-talk path. The 12s ring window is wider than the 8s
# snapshot (Plan 40-01 — extra 4s is jitter headroom for the resample
# callback boundary). Three constants only; no existing values touched.
MIC_AUDIO_PART_SECONDS: float = 8.0  # Gemini Part 2 snapshot width
MIC_AUDIO_PART_RECENCY_S: float = 4.0  # KAAN_SPOKE-recent gate window (Pattern 2)
MIC_AUDIO_PART_PRESENCE_RMS: float = 0.005  # int16-domain RMS floor; skip Part 2 below this

# ---- WS bus (mascot + Phase 12 Live UI) ----
WS_HOST: str = "127.0.0.1"  # v4:123
WS_PORT: int = 8765  # v4:124

# ---- Engine tuning — French Touch / Daft Punk / Digitalism profile (125-128 BPM) ----
SILENT_RMS = 0.012  # v4:127 — real silence between tracks (v4 raised from 0.008)
LOW_RMS = 0.040  # v4:128 — filtered breakdown / pre-drop / verse (v4 raised from 0.025)
PEAK_RMS = 0.110  # v4:129 — drop / chorus / full mix (v4 raised from 0.055)
AUDIBLE_DEBOUNCE_SEC = 0.6  # v4:130 — debounce silent→audible
SILENCE_DEBOUNCE_SEC = 1.2  # v4:131 — debounce audible→silent
EVENT_GLOBAL_MIN_GAP = (
    10.0  # v4:132 — global cooldown ("let the music breathe", retuned post-chat-log)
)
HEARTBEAT_SEC = 70.0  # v4:133 — heartbeat event cadence (retuned post-chat-log)

MIN_EVENT_GAP_PER_TYPE: dict[str, float] = {  # v4:134-142 + Phase 17 SENSE-12 extension
    "TRACK_CHANGE": 6.0,
    "PHASE": 18.0,
    "LAYER_ARRIVAL": 16.0,
    "MIX_MOVE": 20.0,
    "HEARTBEAT": HEARTBEAT_SEC,
    "MIC": 3.0,
    "MANUAL": 1.5,
    # Phase 17 SENSE-12 — kick-side cross-genre detectors (per CONTEXT D-cooldown
    # locked rule "matches G-followup-1"). Tuned on the v4 coexistence matrix:
    # KICK_SWAP slightly faster than LAYER_ARRIVAL since kick character changes
    # are the main "moment" worth catching; SUB_LAYER_ARRIVAL mirrors
    # LAYER_ARRIVAL (its bass-side analog); KICK_DENSITY_SHIFT mirrors PHASE
    # (it's a structural shift, not a layer arrival).
    "KICK_SWAP": 14.0,
    "SUB_LAYER_ARRIVAL": 16.0,
    "KICK_DENSITY_SHIFT": 18.0,
    # Plan 17-03 — paired breakdown / re-entry detectors. KILL gets the same
    # 20s cooldown as MIX_MOVE (it's a structural moment, not a fast tap).
    # REENTRY uses 12s — shorter because the kill→reentry pair is bounded
    # (KICK_REENTRY_MAX_AGE_S = 30s); a longer cooldown would push the
    # re-entry past the natural pair window and silently swallow the moment.
    "BREAKDOWN_KICK_KILL": 20.0,
    "REENTRY_KICK_LAND": 12.0,
    # Plan 17-04 — phrase-boundary structural detector (SENSE-14). 24s gap
    # prevents same-phrase double-fire while still allowing every-other-phrase
    # reactivity at typical BPM × 16 bars (≈12-15s per phrase). Bar-count is
    # the meaningful unit (PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES below); the
    # 24s wall-clock floor is a redundant guard.
    "PHRASE_BOUNDARY": 24.0,
    # Phase 30 SENSE-17/18 — Hard Tek genre-specific detector cooldowns.
    # Tight relative to PHASE/MIX_MOVE because Hard Tek climbs evolve fast
    # (every 6-8s a fresh distortion stack arrives in a 4-minute peak-time
    # track); longer would silently swallow a real moment.
    "DISTORTION_CLIMB": 6.0,
    "ACID_LINE_ENTRY": 8.0,
}

TRACK_CHANGE_MIN_CONFIDENCE = 0.5  # v4:143 — ignore stale nowplaying-cli phantom tracks

# ---- Lifted OUT of EventDetector class-attrs per 02-PATTERNS.md ----
# Phase 3 EventDetector imports these directly; no class needed.
MUSIC_PRESENCE_MIN_SECONDS = 4.0  # v4:1178 — sustained-audible gate before auto-events
BPM_VALID_MIN = 100.0  # v4:1181 — autocorr-noise reject lower bound
BPM_VALID_MAX = 180.0  # v4:1182 — autocorr-noise reject upper bound

# ---- Phase 17 — Hard Tek detectors v1 (SENSE-13/SENSE-15) ----
# Coarse BPM-band + spectral-centroid heuristic for `MusicState.active_genre`
# (no ML in v2.0 per CONTEXT D-04). Bands are intentionally non-overlapping;
# the gaps (128-128, 138-140) → "unknown" (per "trust the audio" — don't
# force-classify ambiguous tempos). The hard_tek upper bound is anchored to
# `BPM_VALID_MAX` so a spurious 250 BPM autocorr lock can never silently flip
# the active genre — the genre router shares the autocorr-noise-reject ceiling
# (SENSE-15 contract; T-17-01-01 mitigation in 17-01-PLAN threat register).
GENRE_BPM_BANDS: dict[str, tuple[float, float]] = {
    "house": (118.0, 128.0),
    "techno": (128.0, 138.0),
    "hard_tek": (140.0, BPM_VALID_MAX),
    "unknown": (0.0, 0.0),
}

# `buildup_score` is the slope of the trailing 8s of `MusicState.energy_curve`
# (curve resolution = 1s hop in refresh.py → window covers 8 samples).
BUILDUP_SLOPE_WINDOW_S: float = 8.0

# When BPM lands in the hard_tek band, also require (mid_share + high_share)
# to exceed this floor — distorted-kick spectral signature gate, anti-
# misclassify-on-house-with-fast-tempo. Bands are normalized shares (sum to
# ~1.0), so the floor lives in [0.0, 1.0].
GENRE_CENTROID_HARD_TEK_MIN: float = 0.55

# ---- Phase 17 — Kick-side detector thresholds (SENSE-12) ----
# Calibrated against v4 "kick character change" intuition; Plan 06 tuning
# harness (reference-WAV CSV against Hard Tek anchors) will confirm/adjust.
#
# KICK_SWAP_CENTROID_DELTA_HZ: a 12Hz centroid shift in the 40-120Hz band is
# the smallest robustly-perceptible "different kick" delta — below it the
# centroid drift is dominated by low-band noise across consecutive 4s windows.
KICK_SWAP_CENTROID_DELTA_HZ: float = 12.0
# SUB_JUMP_THRESHOLD: 0.10 fraction jump in `state.bands["sub"]` — same
# magnitude as the existing v4 LAYER_ARRIVAL high-band-jump threshold (0.10),
# kept symmetrical so the bass-side detector behaves like its mid/high analog.
SUB_JUMP_THRESHOLD: float = 0.10
# KICK_DENSITY_SHIFT_DELTA: 1.5 onsets/sec absolute change. Half-time techno
# ≈ 1.0/sec, 4-on-floor techno ≈ 2.5/sec, hard tek 4-on-floor ≈ 5.0/sec —
# 1.5/sec is the smallest robustly-detectable shift between any two regimes.
KICK_DENSITY_SHIFT_DELTA: float = 1.5

# ---- Phase 17 Plan 03 — Breakdown / Re-entry detector thresholds (SENSE-12) ----
# Paired detectors: BREAKDOWN_KICK_KILL fires when the kick disappears mid-track
# (filter sweep / breakdown / drop preparation); REENTRY_KICK_LAND fires when
# the kick comes back near a downbeat within KICK_REENTRY_MAX_AGE_S of the kill.
#
# KICK_KILL_SUB_FLOOR: sub_share floor below which the kick is "killed". Half
# of LAYER_ARRIVAL high_jump magnitude (0.10) — kick removal is a smaller
# fraction-shift than a layer arrival because the sub band only needs to drop,
# not jump (its floor doubles as the no-kick anchor for the re-entry watch).
KICK_KILL_SUB_FLOOR: float = 0.10
# KICK_KILL_SUB_DROP_MIN: minimum (prev_sub - new_sub) magnitude — anti-noise
# gate. Without this floor a quiet section that's been at sub=0.08 baseline
# could spuriously fire the kill detector the first time we read it.
KICK_KILL_SUB_DROP_MIN: float = 0.15
# KICK_REENTRY_SUB_FLOOR: hysteresis floor — re-entry requires sub_share to
# recover above 0.18 (higher than KICK_KILL_SUB_FLOOR=0.10 to avoid rapid
# re-fire on jitter near the kill floor).
KICK_REENTRY_SUB_FLOOR: float = 0.18
# KICK_REENTRY_BAR_TOLERANCE: beat_phase distance-to-downbeat tolerance.
# 0.20 = ±20% of one bar (beat_phase ∈ [0, 1)). Looser than ±1 beat (0.25)
# per CONTEXT — Hard Tek's distorted onsets blur precise downbeat detection,
# so we accept ±20% of bar; SENSE-14 PHRASE_BOUNDARY (Plan 04) sharpens the
# absolute downbeat, but re-entry just needs "near a downbeat" not exact lock.
KICK_REENTRY_BAR_TOLERANCE: float = 0.20
# KICK_REENTRY_MAX_AGE_S: maximum age of a kill event for the re-entry to
# still pair with it. After 30s the breakdown effectively "ended on its own"
# — there's no specific re-entry moment worth calling out anymore.
KICK_REENTRY_MAX_AGE_S: float = 30.0

# ---- Phase 17 Plan 04 — PhraseBoundaryDetector thresholds (SENSE-14) ----
# PHRASE_BOUNDARY fires on a downbeat that closes an 8/16/32-bar phrase. The
# bar count is locked via 40-120Hz band-limited autocorrelation in
# `_phrase_dsp.py`. Anti-hallucination: the detector self-corrects when
# `BREAKDOWN_KICK_KILL` fires (re-uses the kill detector's `last_kill_at` —
# same idiom as ReentryKickLand) and refuses to fire on `bpm_confidence < 0.5`
# (the lock cannot be trusted below that threshold).
#
# PHRASE_BOUNDARY_BAR_TOLERANCE: beat_phase distance-to-downbeat tolerance.
# 0.20 = ±20% of one bar — matches KICK_REENTRY_BAR_TOLERANCE for consistency
# (both detectors gate on "near a downbeat" semantics).
PHRASE_BOUNDARY_BAR_TOLERANCE: float = 0.20
# PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES: even outside the wall-clock cooldown,
# never fire two phrase boundaries inside 8 bars (≈12-15s at 130-170 BPM).
# Bar count is the meaningful unit — wall-clock cooldown is a redundant floor.
PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES: int = 8
# PHRASE_AUTOCORR_LOW_HZ / PHRASE_AUTOCORR_HIGH_HZ: band-limit edges for the
# kick-band autocorrelation per SENSE-14. Same band as `kick_band_centroid`
# in `_dsp.py`; deliberately wider than just the sub-band (60Hz) so that
# pitched-up kicks (Hard Tek tops out around 100-120Hz fundamental) still
# register inside the autocorr window.
PHRASE_AUTOCORR_LOW_HZ: float = 40.0
PHRASE_AUTOCORR_HIGH_HZ: float = 120.0

# ---- Phase 17 — bpm_confidence anti-hallucination floor for downbeat-gated
# detectors. Promoted from the private `_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`
# constant in `reentry_kick_land.py` (Plan 17-03) since `PhraseBoundaryDetector`
# (Plan 17-04) consumes the same threshold. Slightly looser than Phase 13's
# mascot-render gate (0.6) — re-entry / phrase detection is more time-critical
# than mascot animation; we'd rather miss a marginal-confidence event than
# fire a fabricated one, but the bar should not be so high that legitimate
# Hard Tek BPM locks at confidence ≈ 0.55 silently lose their structural calls.
BPM_CONFIDENCE_MIN_FOR_DOWNBEAT: float = 0.5
# Alias of the SENSE-14 phrase-lock-confidence floor for callers that want
# the semantic name (the underlying number is the same: lock seeding and
# the per-tick gate share one threshold).
PHRASE_BOUNDARY_MIN_LOCK_CONFIDENCE: float = BPM_CONFIDENCE_MIN_FOR_DOWNBEAT

# ---- Phase 30 — DISTORTION_CLIMB thresholds (SENSE-17) ----
# DISTORTION_CLIMB fires when a band-limited spectral-flatness rise (signal
# becomes more noise-like as harmonic distortion stacks up) AND an odd-vs-
# even harmonic-energy proxy (clipping emphasises odd harmonics) AND
# sustained kick density (we're inside a busy Hard Tek section, not a
# breakdown) all coincide within a 2s window.
DISTORTION_FLATNESS_DELTA_MIN: float = 0.15  # 4-window rise threshold
DISTORTION_HARMONIC_RATIO_MIN: float = 1.5   # odd/even harmonic energy ratio
DISTORTION_KICK_DENSITY_MIN: float = 8.0     # onsets/sec sustained floor
DISTORTION_KICK_DENSITY_SUSTAIN_S: float = 4.0  # density must hold this long
DISTORTION_FLATNESS_WINDOW: int = 4          # samples in flatness history
DISTORTION_FUNDAMENTAL_HZ: float = 60.0      # kick fundamental for harmonic gate

# ---- Phase 30 — ACID_LINE_ENTRY thresholds (SENSE-18) ----
# ACID_LINE_ENTRY fires when a TB-303-style formant sweeps through the
# 200-800Hz band over >=1.5s WITH a resonance-Q rise (proxy: peak-to-mean
# magnitude in band climbs from <3 to >8). Both must coexist inside a 3s
# evaluation window.
ACID_FORMANT_LOW_HZ: float = 200.0
ACID_FORMANT_HIGH_HZ: float = 800.0
ACID_SWEEP_SLOPE_MIN_OCT_PER_S: float = 0.2
ACID_SWEEP_MIN_SPAN_S: float = 1.5
ACID_SWEEP_WINDOW_S: float = 3.0
ACID_RESONANCE_LOW_MAX: float = 3.0  # early-window Q must drop below this
ACID_RESONANCE_HIGH_MIN: float = 8.0  # late-window Q must climb above this
ACID_SNAPSHOT_WINDOW_S: float = 1.5  # samples snapshot per tick
