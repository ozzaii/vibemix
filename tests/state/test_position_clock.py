# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math

from vibemix.state.position_clock import virtual_position_sec


def test_virtual_position_dead_reckons_seconds_when_bpm_lock_is_trusted():
    out = virtual_position_sec(
        position_sec=64.5,
        position_sampled_at=999.5,
        now=1000.0,
        duration_sec=300.0,
        playback_rate=1.0,
        bpm=130.0,
        bpm_confidence=0.95,
        track_confidence=0.85,
    )

    assert math.isclose(out.position_sec or 0.0, 65.0)
    assert out.confidence == 0.85
    assert out.source == "dead_reckoned"


def test_virtual_position_uses_playback_rate_not_bpm_units():
    out = virtual_position_sec(
        position_sec=10.0,
        position_sampled_at=100.0,
        now=101.0,
        duration_sec=None,
        playback_rate=0.5,
        bpm=180.0,
        bpm_confidence=0.9,
        track_confidence=0.8,
    )

    assert math.isclose(out.position_sec or 0.0, 10.5)


def test_virtual_position_falls_back_to_raw_when_bpm_lock_is_weak():
    out = virtual_position_sec(
        position_sec=64.5,
        position_sampled_at=999.5,
        now=1000.0,
        duration_sec=300.0,
        playback_rate=1.0,
        bpm=130.0,
        bpm_confidence=0.4,
        track_confidence=0.85,
    )

    assert out.position_sec == 64.5
    assert out.confidence == 0.85
    assert out.source == "raw"


def test_virtual_position_falls_back_when_sample_is_stale():
    out = virtual_position_sec(
        position_sec=64.5,
        position_sampled_at=990.0,
        now=1000.0,
        duration_sec=300.0,
        playback_rate=1.0,
        bpm=130.0,
        bpm_confidence=0.95,
        track_confidence=0.85,
    )

    assert out.position_sec == 64.5
    assert out.source == "stale_raw"


def test_virtual_position_clamps_to_duration():
    out = virtual_position_sec(
        position_sec=299.8,
        position_sampled_at=999.5,
        now=1000.0,
        duration_sec=300.0,
        playback_rate=1.0,
        bpm=130.0,
        bpm_confidence=0.95,
        track_confidence=0.85,
    )

    assert out.position_sec == 300.0


def test_virtual_position_missing_raw_is_honest_none():
    out = virtual_position_sec(
        position_sec=None,
        position_sampled_at=999.5,
        now=1000.0,
        duration_sec=300.0,
        playback_rate=1.0,
        bpm=130.0,
        bpm_confidence=0.95,
        track_confidence=0.85,
    )

    assert out.position_sec is None
    assert out.confidence == 0.0
    assert out.source == "missing"
