# SPDX-License-Identifier: Apache-2.0
"""vibemix.audio — domain layer audio primitives.

Pure Python audio primitives: rolling ring buffers (zero-alloc on push),
EMA-smoothed levels, DSP free functions (FFT / RMS / BPM autocorr / peak-normalize
/ WAV-wrap), per-session WAV/JSONL recorder, and the LOAD-BEARING v4-tuned
constants. No OS imports — platform-specific I/O lives in `vibemix.platform._audio_*`.

The constants are LOAD-BEARING IP — tuned against real DJ sessions on 2026-05-11
for the French Touch / Daft Punk / Digitalism profile (125-128 BPM). Phase 6 will
add genre-aware overrides on top. See constants.py for the full set + v4 line anchors.
"""

from __future__ import annotations

from vibemix.audio.buffers import AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue
from vibemix.audio.constants import (
    AI_TALK_THRESHOLD,
    AUDIBLE_DEBOUNCE_SEC,
    BPM_VALID_MAX,
    BPM_VALID_MIN,
    EVENT_GLOBAL_MIN_GAP,
    HEARTBEAT_SEC,
    INPUT_CHUNK_FRAMES,
    INPUT_SR_NATIVE,
    INPUT_SR_TARGET,
    INVOKE_AUDIO_SECONDS,
    LOW_RMS,
    MIC_GAIN,
    MIC_GAIN_AT_AI_TALK,
    MIC_HOLD_AFTER_AI_MS,
    MIC_TALK_THRESHOLD,
    MIN_EVENT_GAP_PER_TYPE,
    MUSIC_GAIN_TO_GEMINI,
    MUSIC_PRESENCE_MIN_SECONDS,
    OUTPUT_BLOCKSIZE,
    OUTPUT_SR,
    PASSTHROUGH_GAIN,
    PEAK_RMS,
    SILENCE_DEBOUNCE_SEC,
    SILENT_RMS,
    TRACK_CHANGE_MIN_CONFIDENCE,
    VOICE_BLOCKSIZE,
    WS_HOST,
    WS_PORT,
)
from vibemix.audio.errors import SampleRateMismatchError
from vibemix.audio.features import (
    compute_downbeat_phase,
    energy_curve,
    estimate_bpm,
    long_arc_curve,
    snapshot_features,
    snapshot_wav,
)
from vibemix.audio.levels import Levels
from vibemix.audio.lookahead import (
    LOOKAHEAD_SAMPLE_RATE,
    LOOKAHEAD_SECONDS,
    LOOKAHEAD_TIMEOUT_S,
    LOOKAHEAD_WINDOW_SECONDS,
    LookaheadProvider,
)
from vibemix.audio.recorder import VoiceRecorder
from vibemix.audio.registry import BufferRegistry

__all__ = [
    "AI_TALK_THRESHOLD",
    "AUDIBLE_DEBOUNCE_SEC",
    "BPM_VALID_MAX",
    "BPM_VALID_MIN",
    "EVENT_GLOBAL_MIN_GAP",
    "HEARTBEAT_SEC",
    "INPUT_CHUNK_FRAMES",
    "INPUT_SR_NATIVE",
    "INPUT_SR_TARGET",
    "INVOKE_AUDIO_SECONDS",
    "LOOKAHEAD_SAMPLE_RATE",
    "LOOKAHEAD_SECONDS",
    "LOOKAHEAD_TIMEOUT_S",
    "LOOKAHEAD_WINDOW_SECONDS",
    "LOW_RMS",
    "MIC_GAIN",
    "MIC_GAIN_AT_AI_TALK",
    "MIC_HOLD_AFTER_AI_MS",
    "MIC_TALK_THRESHOLD",
    "MIN_EVENT_GAP_PER_TYPE",
    "MUSIC_GAIN_TO_GEMINI",
    "MUSIC_PRESENCE_MIN_SECONDS",
    "OUTPUT_BLOCKSIZE",
    "OUTPUT_SR",
    "PASSTHROUGH_GAIN",
    "PEAK_RMS",
    "SILENCE_DEBOUNCE_SEC",
    "SILENT_RMS",
    "TRACK_CHANGE_MIN_CONFIDENCE",
    "VOICE_BLOCKSIZE",
    "WS_HOST",
    "WS_PORT",
    "AudioBuffer",
    "BufferRegistry",
    "Levels",
    "LookaheadProvider",
    "MicBuffer",
    "PassthroughBuffer",
    "PlaybackQueue",
    "SampleRateMismatchError",
    "VoiceRecorder",
    "compute_downbeat_phase",
    "energy_curve",
    "estimate_bpm",
    "long_arc_curve",
    "snapshot_features",
    "snapshot_wav",
]
