# SPDX-License-Identifier: Apache-2.0
"""Real-audio cue detection regression guard."""

from __future__ import annotations

import shutil

import pytest
from scripts.eval.cue_detect import evaluate_cue_detection


def test_real_audio_cue_detection_matches_committed_manifest() -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required for real-audio cue detection eval")

    report = evaluate_cue_detection()

    assert report["ok"], report
    assert report["n_tracks"] == 6
    assert report["label_recall"] == 1.0
    assert report["unexpected_labels"] == 0
    assert report["timing_misses"] == 0
