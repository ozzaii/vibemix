# SPDX-License-Identifier: Apache-2.0
"""−60 dB silence cues — scar 20 §3.3, the first/last audible sample bounds.

``audio/cues.py`` turns decoded samples into the :class:`TrackCues` the transition
clock consumes, so the auto-mix reel runs on REAL audio rather than synthetic cues.
The −60 dB threshold (``0.001``) is the exact AutoDJ / AnalyzerSilence boundary.
"""
from __future__ import annotations

import numpy as np

from vibemix.audio.cues import (
    SILENCE,
    first_sound_frame,
    last_sound_frame,
    track_cues_from_audio,
)
from vibemix.state.transition_clock import TrackCues, TransitionMode


def test_silence_threshold_is_minus_60db() -> None:
    assert SILENCE == 0.001  # 10**(-60/20)


def test_first_last_sound_frames_mono() -> None:
    x = np.zeros(300, dtype=np.float32)
    x[50:250] = 0.5  # audible region indices [50, 249]
    assert first_sound_frame(x) == 50
    assert last_sound_frame(x) == 249


def test_sub_threshold_is_treated_as_silence() -> None:
    x = np.full(100, 0.0005, dtype=np.float32)  # below -60 dB
    assert first_sound_frame(x) == 0  # nothing audible -> default 0
    assert last_sound_frame(x) == len(x)  # -> end sentinel


def test_stereo_audible_if_any_channel_is() -> None:
    x = np.zeros((200, 2), dtype=np.float32)
    x[80:120, 1] = 0.3  # only the right channel sounds
    assert first_sound_frame(x) == 80
    assert last_sound_frame(x) == 119


def test_track_cues_from_audio_builds_usable_cues() -> None:
    sr = 44100
    x = np.zeros(sr * 10, dtype=np.float32)
    x[sr : 9 * sr] = 0.4  # audible 1 s .. 9 s
    cues = track_cues_from_audio(x, sr)
    assert isinstance(cues, TrackCues)
    assert abs(cues.duration_sec - 10.0) < 1e-6
    assert abs(cues.first_sound_sec - 1.0) < 0.01
    assert 8.9 < cues.last_sound_sec <= 9.01


def test_real_audio_cues_drive_the_reel_skip_silence() -> None:
    # the payoff: real -60 dB bounds drive the demo reel under skip-silence mode,
    # with NO marked intro/outro (the common un-analyzed case).
    from vibemix.runtime.automix_demo import build_automix_reel

    sr = 44100
    x = np.zeros(sr * 30, dtype=np.float32)
    x[sr : 29 * sr] = 0.4  # audible 1 s .. 29 s of a 30 s track
    cues = track_cues_from_audio(x, sr)
    reel = build_automix_reel(
        cues, cues, mode=TransitionMode.FIXED_SKIP_SILENCE, transition_sec=8.0,
    )
    assert [b.cue for b in reel.beats] == ["drop_incoming", "mixing_in", "landed_clean"]
    # the fade must END no later than the last audible sample (~29 s of 30 s)
    assert reel.beats[-1].t_sec <= 29.0 + 0.1
