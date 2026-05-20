# SPDX-License-Identifier: Apache-2.0
from spikes.vibe_mix_slice0.confidence_gate import gate_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def _cand(conf: float, num: int = 1) -> CueCandidate:
    return CueCandidate(
        track_location="file://localhost/tmp/x.mp3",
        name="DROP", type="cue", start_s=30.0, number=num, confidence=conf,
    )


def test_drops_below_threshold():
    cands = [_cand(0.9, 1), _cand(0.5, 2), _cand(0.86, 3)]
    kept = gate_cues(cands, threshold=0.85)
    assert [c.number for c in kept] == [1, 3]


def test_empty_when_all_below():
    # No cue beats a wrong cue: an empty result is a valid, safe outcome.
    assert gate_cues([_cand(0.1)], threshold=0.85) == []


def test_default_threshold_is_conservative():
    # A 0.8-confidence cue is NOT good enough by default.
    assert gate_cues([_cand(0.8)]) == []
