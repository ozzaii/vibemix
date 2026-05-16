# SPDX-License-Identifier: Apache-2.0
"""Constant presence + value parity tests for vibemix.audio.constants.

These constants are LOAD-BEARING IP — tuned against real DJ sessions on
2026-05-11 for the French Touch profile. Any drift fails the build before
merge so a silent typo can't regress the engine.

Source of truth: cohost_v4.py:96-143 (module-level) + cohost_v4.py:1178-1182
(lifted OUT of EventDetector class-attrs per 02-PATTERNS.md).
"""

from __future__ import annotations

from vibemix.audio import (
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
)


def test_engine_constants_match_v4() -> None:
    """Engine tuning constants — v4:127-133 (the FT profile retune from v3).

    HEARTBEAT_SEC re-tuned by Plan 40-04 / AUDIO-03 from 70.0 → 45.0 to match
    the v4 chat-tested 2026-05-11 "harikaydı" baseline (memory:
    project_v4_canonical_baseline). The OLD 70s was a v4-shipped-file literal
    that diverged from the chat-tested ear-test value; locked target is the
    chat-tested baseline.
    """
    assert SILENT_RMS == 0.012
    assert LOW_RMS == 0.040
    assert PEAK_RMS == 0.110
    assert AUDIBLE_DEBOUNCE_SEC == 0.6
    assert SILENCE_DEBOUNCE_SEC == 1.2
    assert EVENT_GLOBAL_MIN_GAP == 10.0  # retuned post-2026-05-11 — "let the music breathe"
    assert HEARTBEAT_SEC == 45.0  # Plan 40-04 — was 70.0; v4 chat-tested 2026-05-11 baseline


def test_io_constants_match_v4() -> None:
    """I/O constants — v4:100-113."""
    assert INVOKE_AUDIO_SECONDS == 18.0
    assert INPUT_SR_NATIVE == 48000
    assert INPUT_SR_TARGET == 16000
    assert OUTPUT_SR == 24000
    assert INPUT_CHUNK_FRAMES == 480
    assert OUTPUT_BLOCKSIZE == 256
    assert VOICE_BLOCKSIZE == 1024
    assert PASSTHROUGH_GAIN == 0.0
    assert MUSIC_GAIN_TO_GEMINI == 1.0  # v4 retuned from 8.0


def test_mic_gating_constants_match_v4() -> None:
    """Mic + AI-gating constants — v4:116-120."""
    assert MIC_GAIN == 1.0
    assert MIC_TALK_THRESHOLD == 0.09
    assert MIC_GAIN_AT_AI_TALK == 0.0
    assert MIC_HOLD_AFTER_AI_MS == 350
    assert AI_TALK_THRESHOLD == 0.02


def test_event_gap_dict_shape_and_values() -> None:
    """MIN_EVENT_GAP_PER_TYPE dict — v4:134-142 + Phase 17 SENSE-12 / Phase 30
    SENSE-17/18 extensions + Plan 40-04 re-tune.

    Phase 17 Plan 02 added three kick-side event types (KICK_SWAP,
    SUB_LAYER_ARRIVAL, KICK_DENSITY_SHIFT) per CONTEXT D-cooldown LOCKED rule
    "matches G-followup-1". Plan 17-03 added the paired breakdown / re-entry
    pair (BREAKDOWN_KICK_KILL, REENTRY_KICK_LAND). Plan 17-04 added
    PHRASE_BOUNDARY (sixth Wave-2 detector). Phase 30 SENSE-17/18 added
    DISTORTION_CLIMB and ACID_LINE_ENTRY (Hard Tek genre-specific detectors).

    Plan 40-04 / AUDIO-03 re-tuned the v4 baseline entries to match the
    chat-tested 2026-05-11 "harikaydı" session ear-test:
        TRACK_CHANGE 6 → 5, PHASE 18 → 10, LAYER_ARRIVAL 16 → 10,
        MIX_MOVE 20 → 14, HEARTBEAT 70 → 45.
    Phase 17 SENSE-12 / Phase 30 SENSE-17/18 detector cooldowns and MIC /
    MANUAL UNCHANGED.
    """
    assert set(MIN_EVENT_GAP_PER_TYPE.keys()) == {
        "TRACK_CHANGE",
        "PHASE",
        "LAYER_ARRIVAL",
        "MIX_MOVE",
        "HEARTBEAT",
        "MIC",
        "MANUAL",
        # Phase 17 SENSE-12 — kick-side cross-genre detectors (Plan 17-02)
        "KICK_SWAP",
        "SUB_LAYER_ARRIVAL",
        "KICK_DENSITY_SHIFT",
        # Phase 17 SENSE-12 — paired breakdown / re-entry detectors (Plan 17-03)
        "BREAKDOWN_KICK_KILL",
        "REENTRY_KICK_LAND",
        # Phase 17 SENSE-14 — phrase-boundary structural detector (Plan 17-04)
        "PHRASE_BOUNDARY",
        # Phase 30 SENSE-17/18 — Hard Tek genre-specific detectors
        "DISTORTION_CLIMB",
        "ACID_LINE_ENTRY",
    }
    # Plan 40-04 re-tuned v4 baseline entries (v4 2026-05-11 ear-test).
    assert MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"] == 5.0  # Plan 40-04 — was 6.0
    assert MIN_EVENT_GAP_PER_TYPE["PHASE"] == 10.0  # Plan 40-04 — was 18.0
    assert MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"] == 10.0  # Plan 40-04 — was 16.0
    assert MIN_EVENT_GAP_PER_TYPE["MIX_MOVE"] == 14.0  # Plan 40-04 — was 20.0
    assert MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"] == 45.0  # Plan 40-04 — was 70.0
    assert MIN_EVENT_GAP_PER_TYPE["MIC"] == 3.0  # unchanged
    assert MIN_EVENT_GAP_PER_TYPE["MANUAL"] == 1.5  # unchanged
    # Plan 17-02 kick-side detector cooldowns — UNCHANGED by Plan 40-04
    assert MIN_EVENT_GAP_PER_TYPE["KICK_SWAP"] == 14.0
    assert MIN_EVENT_GAP_PER_TYPE["SUB_LAYER_ARRIVAL"] == 16.0
    assert MIN_EVENT_GAP_PER_TYPE["KICK_DENSITY_SHIFT"] == 18.0
    # Plan 17-03 paired-detector cooldowns — UNCHANGED by Plan 40-04
    assert MIN_EVENT_GAP_PER_TYPE["BREAKDOWN_KICK_KILL"] == 20.0
    assert MIN_EVENT_GAP_PER_TYPE["REENTRY_KICK_LAND"] == 12.0
    # Plan 17-04 phrase-boundary cooldown — UNCHANGED by Plan 40-04
    assert MIN_EVENT_GAP_PER_TYPE["PHRASE_BOUNDARY"] == 24.0
    # Phase 30 SENSE-17/18 — UNCHANGED by Plan 40-04
    assert MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"] == 6.0
    assert MIN_EVENT_GAP_PER_TYPE["ACID_LINE_ENTRY"] == 8.0
    # HEARTBEAT key should reference the HEARTBEAT_SEC module-level constant
    # (identity, not value — preserves the source-of-truth coupling).
    assert MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"] == HEARTBEAT_SEC


def test_event_detector_constants_lifted_to_module_scope() -> None:
    """The 3 constants that lived on EventDetector class in v4:1178-1182 are
    now module-level per 02-PATTERNS.md — so Phase 3 can import without
    dragging EventDetector along."""
    assert MUSIC_PRESENCE_MIN_SECONDS == 4.0
    assert BPM_VALID_MIN == 100.0
    assert BPM_VALID_MAX == 180.0


def test_track_change_min_confidence_present() -> None:
    """v4-new constant (absent in v3) — v4:143. Phase 3 phantom-nowplaying-cli filter."""
    assert TRACK_CHANGE_MIN_CONFIDENCE == 0.5
