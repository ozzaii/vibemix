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

MIN_EVENT_GAP_PER_TYPE: dict[str, float] = {  # v4:134-142
    "TRACK_CHANGE": 6.0,
    "PHASE": 18.0,
    "LAYER_ARRIVAL": 16.0,
    "MIX_MOVE": 20.0,
    "HEARTBEAT": HEARTBEAT_SEC,
    "MIC": 3.0,
    "MANUAL": 1.5,
}

TRACK_CHANGE_MIN_CONFIDENCE = 0.5  # v4:143 — ignore stale nowplaying-cli phantom tracks

# ---- Lifted OUT of EventDetector class-attrs per 02-PATTERNS.md ----
# Phase 3 EventDetector imports these directly; no class needed.
MUSIC_PRESENCE_MIN_SECONDS = 4.0  # v4:1178 — sustained-audible gate before auto-events
BPM_VALID_MIN = 100.0  # v4:1181 — autocorr-noise reject lower bound
BPM_VALID_MAX = 180.0  # v4:1182 — autocorr-noise reject upper bound
