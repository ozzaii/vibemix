# SPDX-License-Identifier: Apache-2.0
"""ipc.learn.waveform_ready envelope contract."""
from __future__ import annotations

import json

from vibemix.ui_bus.learn_messages import LearnWaveformReady
from vibemix.ui_bus.messages import _VALIDATOR


def test_waveform_ready_roundtrips_own_track_source_metadata() -> None:
    env = LearnWaveformReady.make(
        sample_rate=44_100,
        beat_interval_s=0.46875,
        decks={
            "A": {
                "track_id": "seed",
                "title": "Seed Track",
                "artist": "Library Artist",
                "source": "library_save_mode",
                "source_start_s": 32.5,
                "bpm": 128.0,
                "duration_s": 30.0,
                "peaks": ((16, 32, 64), (24, 48, 96)),
                "cues": (
                    {"label": "intro", "start_s": 0.0, "end_s": 8.0},
                ),
            },
        },
    )
    wire = json.loads(env.to_json())

    deck = wire["payload"]["decks"]["A"]
    assert deck["track_id"] == "seed"
    assert deck["title"] == "Seed Track"
    assert deck["artist"] == "Library Artist"
    assert deck["source"] == "library_save_mode"
    assert deck["source_start_s"] == 32.5
    _VALIDATOR.validate(wire)
