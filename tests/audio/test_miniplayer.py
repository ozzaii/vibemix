# SPDX-License-Identifier: Apache-2.0
"""Tests for the owned-deck mini-player tempo engine.

The mini-player resamples a track by a playback ``rate`` so the learning module
can OWN the decks (perfect ground truth for the Beatmatch Judge). The core is a
numpy port of Mixxx ``EngineBufferScaleLinear::do_scale`` — a fractional
read-cursor that carries across audio blocks (the persistent ``m_dNextFrame``),
so playhead phase never drifts at a block boundary. See
``~/projects/mixxx-study/MIXXX-SCARS.md`` §6 for the source-verified derivation.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.audio.miniplayer import (
    DeckState,
    MiniDeck,
    _do_scale_block,
    _equal_power_gains,
)


def test_half_rate_linear_interpolates_ramp_and_advances_cursor() -> None:
    # A straight-line ramp is the exact oracle for linear interpolation:
    # interpolating between collinear points lands back on the same line, so
    # the expected output is known to the bit.
    m = 16
    ramp = np.arange(m, dtype=np.float32)
    src = np.stack([ramp, ramp], axis=1)  # (16, 2) stereo, both channels = ramp

    out, next_frame = _do_scale_block(src, 0.0, 0.5, 4)

    # Output frames map to source positions next_frame + rate*[0..n): 0,0.5,1,1.5
    expected = np.array([0.0, 0.5, 1.0, 1.5], dtype=np.float32)
    assert out.dtype == np.float32
    assert out.shape == (4, 2)
    np.testing.assert_allclose(out[:, 0], expected, rtol=0.0, atol=1e-6)
    np.testing.assert_allclose(out[:, 1], expected, rtol=0.0, atol=1e-6)
    # Cursor carries forward by rate * n = 0.5 * 4 = 2.0 (the persistent accumulator).
    assert next_frame == 2.0


def test_reading_past_end_degrades_to_silence_not_indexerror() -> None:
    # A sd.OutputStream callback runs on the OS audio thread and must NEVER
    # raise. When the cursor runs off the end of a finished/short track the
    # block degrades to silence instead of an IndexError (Mixxx do_scale tail
    # SampleUtil::clear / "bail to silence" 05/10, adapted; honors C5).
    src = np.ones((8, 2), dtype=np.float32)  # frames 0..7 only

    out, _ = _do_scale_block(src, 6.0, 1.0, 6)  # would touch source frames 6..11

    assert out.shape == (6, 2)
    assert out.dtype == np.float32
    assert np.isfinite(out).all()
    assert out[0, 0] == 1.0   # frame 6 is real
    assert out[1, 0] == 1.0   # frame 7 (last real sample) is real
    assert out[2, 0] == 0.0   # frame 8 past end -> silence
    assert out[-1, 0] == 0.0  # frame 11 past end -> silence


def test_cursor_carries_across_blocks_without_drift() -> None:
    # THE scar: the fractional cursor persists across audio blocks, so two
    # back-to-back blocks are bit-identical to one double-length block. If the
    # phase reset or rounded each block, beatmatch grading would drift — this is
    # exactly the property that lets the Judge trust the playhead.
    rng = np.arange(200, dtype=np.float32)
    src = np.stack([rng, rng * 2.0], axis=1)  # (200, 2), non-trivial per channel
    rate = 0.7  # irrational-ish stride so block boundaries land mid-sample

    whole, _ = _do_scale_block(src, 3.25, rate, 64)
    blk1, cur = _do_scale_block(src, 3.25, rate, 30)
    blk2, _ = _do_scale_block(src, cur, rate, 34)

    np.testing.assert_array_equal(np.concatenate([blk1, blk2]), whole)


def test_rate_one_from_integer_cursor_is_exact_passthrough() -> None:
    # rate == 1.0 from an integer cursor must return source frames bit-exact
    # (frac == 0 everywhere → no interpolation error), and advance the cursor
    # by exactly n. This is the keylock-off "normal speed" baseline.
    rng = np.arange(64, dtype=np.float32)
    src = np.stack([rng, -rng], axis=1)

    out, cur = _do_scale_block(src, 10.0, 1.0, 8)

    np.testing.assert_array_equal(out, src[10:18])
    assert cur == 18.0


def test_equal_power_crossfade_holds_constant_power() -> None:
    # Equal-power law (Mixxx enginexfader 04 C5): g_a^2 + g_b^2 == 1 across the
    # whole sweep, 0.707 at center — perceived loudness stays flat through a
    # transition instead of the dip a naive linear fade gives. xfader 0=full A,
    # 1=full B.
    ga0, gb0 = _equal_power_gains(0.0)
    assert ga0 == pytest.approx(1.0) and gb0 == pytest.approx(0.0)
    ga1, gb1 = _equal_power_gains(1.0)
    assert ga1 == pytest.approx(0.0) and gb1 == pytest.approx(1.0)
    gac, gbc = _equal_power_gains(0.5)
    assert gac == pytest.approx(0.7071067811865476, abs=1e-9)
    assert gbc == pytest.approx(0.7071067811865476, abs=1e-9)

    for x in np.linspace(0.0, 1.0, 21):
        ga, gb = _equal_power_gains(float(x))
        assert ga * ga + gb * gb == pytest.approx(1.0, abs=1e-9)


def test_minideck_center_xfader_mixes_both_decks_equal_power() -> None:
    a = np.full((100, 2), 0.5, dtype=np.float32)
    b = np.full((100, 2), 0.5, dtype=np.float32)
    deck = MiniDeck(a, b, rate_a=1.0, rate_b=1.0, xfader=0.5)

    out = deck.render_block(8)

    assert out.shape == (8, 2)
    assert out.dtype == np.float32
    # center: 0.7071*0.5 + 0.7071*0.5 == 0.7071 (constant power, no 1.0 bump)
    np.testing.assert_allclose(out, 0.7071067811865476, atol=1e-5)


def test_minideck_full_a_outputs_deck_a_only_and_advances_both_cursors() -> None:
    a = np.full((50, 2), 0.4, dtype=np.float32)
    b = np.full((50, 2), -0.9, dtype=np.float32)
    deck = MiniDeck(a, b, rate_a=1.0, rate_b=2.0, xfader=0.0)  # full A

    out = deck.render_block(4)

    np.testing.assert_allclose(out, 0.4, atol=1e-6)  # only deck A is audible
    st = deck.state()
    assert isinstance(st, DeckState)
    assert st.a_frame == 4.0   # rate 1.0 * 4
    assert st.b_frame == 8.0   # rate 2.0 * 4 — deck B keeps playing even when silent
    assert st.rate_a == 1.0
    assert st.rate_b == 2.0
    assert st.xfader == 0.0


def test_minideck_low_eq_cut_filters_audible_deck() -> None:
    t = np.arange(4096, dtype=np.float32) / 44_100.0
    bass = np.sin(2.0 * np.pi * 80.0 * t).astype(np.float32)
    src = np.column_stack([bass, bass])
    neutral = MiniDeck(src, src, rate_a=1.0, rate_b=1.0, xfader=0.0)
    cut = MiniDeck(src, src, rate_a=1.0, rate_b=1.0, xfader=0.0)

    neutral.render_block(1024)
    cut.set_eq("A", low=0)
    cut.render_block(1024)  # coefficient-change crossfade block

    neutral_out = neutral.render_block(1024)
    cut_out = cut.render_block(1024)

    neutral_rms = float(np.sqrt(np.mean(np.square(neutral_out[:, 0]))))
    cut_rms = float(np.sqrt(np.mean(np.square(cut_out[:, 0]))))
    assert cut_rms < neutral_rms * 0.55
