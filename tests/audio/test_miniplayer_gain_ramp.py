# SPDX-License-Identifier: Apache-2.0
"""MiniDeck ramping regression tests."""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.audio.miniplayer import MiniDeck, _do_scale_block


def _stereo(values: np.ndarray) -> np.ndarray:
    return np.column_stack((values, values)).astype(np.float32)


def test_xfader_change_ramps_from_previous_block_gain() -> None:
    src_a = np.ones((64, 2), dtype=np.float32)
    src_b = np.zeros((64, 2), dtype=np.float32)
    deck = MiniDeck(src_a, src_b, rate_a=1.0, rate_b=1.0, xfader=0.0)

    before = deck.render_block(8)
    deck.xfader = 1.0
    after = deck.render_block(8)

    seam = np.concatenate(([before[-1, 0]], after[:, 0]))
    assert after[0, 0] == pytest.approx(before[-1, 0], abs=1e-5)
    assert after[-1, 0] == pytest.approx(0.0, abs=1e-5)
    assert np.max(np.abs(np.diff(seam))) < 0.25


def test_rate_change_integrates_ramped_rate_into_cursor() -> None:
    src = np.zeros((128, 2), dtype=np.float32)
    deck = MiniDeck(src, src, rate_a=1.0, rate_b=1.0, xfader=0.5)

    deck.render_block(8)
    deck.rate_b = 0.94
    deck.render_block(10)

    expected_b = 8.0 + float(np.sum(np.linspace(1.0, 0.94, 10, dtype=np.float64)))
    assert deck.state().b_frame == pytest.approx(expected_b)


def test_scale_block_rate_ramp_is_monotone_and_continuous() -> None:
    src = _stereo(np.arange(128, dtype=np.float32))

    out, next_frame = _do_scale_block(src, 4.0, 0.94, 10, prev_rate=1.0)

    positions = out[:, 0]
    per_frame_steps = np.diff(positions)
    assert np.all(per_frame_steps > 0)
    assert np.all(np.diff(per_frame_steps) <= 1e-6)
    assert per_frame_steps[0] == pytest.approx(1.0, abs=1e-6)
    assert per_frame_steps[-1] < 1.0
    assert next_frame == pytest.approx(
        4.0 + float(np.sum(np.linspace(1.0, 0.94, 10, dtype=np.float64)))
    )


def test_steady_rate_scale_block_matches_scalar_path() -> None:
    src = _stereo(np.linspace(-1.0, 1.0, 128, dtype=np.float32))

    ramped, ramped_next = _do_scale_block(src, 3.25, 1.125, 24, prev_rate=1.125)
    scalar, scalar_next = _do_scale_block(src, 3.25, 1.125, 24)

    np.testing.assert_array_equal(ramped, scalar)
    assert ramped_next == pytest.approx(scalar_next)
