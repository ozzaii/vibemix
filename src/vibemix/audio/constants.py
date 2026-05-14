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
