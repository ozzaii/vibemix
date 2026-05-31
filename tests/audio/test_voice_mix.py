# SPDX-License-Identifier: Apache-2.0
"""Duck-and-mix the co-host voice over the live mix (the viral drop moment).

When the AI calls the drop, the music dips under the voice for the length of the
line, then comes back — the "real DJ friend leaning into your ear" feel. The
demo's audio callback runs on the OS audio thread, so the mix math is a pure,
allocation-light numpy function tested here in isolation.
"""
from __future__ import annotations

import numpy as np

from vibemix.audio.voice_mix import mix_voice_over


def _music(n: int, value: float = 0.5) -> np.ndarray:
    return np.full((n, 2), value, dtype=np.float32)


def _voice(n: int, value: float = 0.3) -> np.ndarray:
    return np.full((n, 2), value, dtype=np.float32)


def test_voice_active_ducks_music_and_adds_voice() -> None:
    music = _music(64, 0.5)
    voice = _voice(256, 0.3)
    out, cursor = mix_voice_over(music, voice, 0, voice_gain=1.0, duck_gain=0.4)
    assert out.shape == (64, 2)
    expected = 0.5 * 0.4 + 0.3 * 1.0
    assert np.allclose(out, expected, atol=1e-6)
    assert cursor == 64


def test_voice_tail_only_ducks_the_overlapping_frames() -> None:
    # voice has 40 samples left, block is 64 → first 40 ducked+mixed, last 24 pure.
    music = _music(64, 0.5)
    voice = _voice(40, 0.3)
    out, cursor = mix_voice_over(music, voice, 0, voice_gain=1.0, duck_gain=0.4)
    assert cursor == 40
    head_expected = 0.5 * 0.4 + 0.3
    assert np.allclose(out[:40], head_expected, atol=1e-6)
    assert np.allclose(out[40:], 0.5, atol=1e-6)  # music unducked once voice ends


def test_cursor_past_end_returns_music_untouched() -> None:
    music = _music(32, 0.5)
    voice = _voice(40, 0.3)
    out, cursor = mix_voice_over(music, voice, 40, duck_gain=0.4)
    assert cursor == 40
    assert np.allclose(out, 0.5, atol=1e-6)


def test_resumes_from_cursor_midway() -> None:
    music = _music(10, 0.5)
    voice = _voice(25, 0.3)
    out, cursor = mix_voice_over(music, voice, 20, voice_gain=1.0, duck_gain=0.5)
    # 5 voice samples remain (20..25) → 5 ducked+mixed, 5 pure music.
    assert cursor == 25
    head_expected = 0.5 * 0.5 + 0.3
    assert np.allclose(out[:5], head_expected, atol=1e-6)
    assert np.allclose(out[5:], 0.5, atol=1e-6)


def test_does_not_mutate_the_music_input() -> None:
    music = _music(16, 0.5)
    voice = _voice(16, 0.3)
    before = music.copy()
    mix_voice_over(music, voice, 0, duck_gain=0.4)
    assert np.array_equal(music, before)
