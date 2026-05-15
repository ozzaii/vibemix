# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — F1 / precision / recall math tests."""

from __future__ import annotations

import pytest

from scripts.eval.f1 import compute_f1


def _ev(type_: str, t: float, *, session: str = "s1", id_: str = "x") -> dict:
    return {"id": id_, "type": type_, "t_session": t, "session": session}


def test_perfect_match_returns_f1_1() -> None:
    """Test 4: identical predicted and ground_truth yields 1.0 across all metrics."""
    gt = [_ev("TRACK_CHANGE", 1.0, id_="g1"), _ev("MIX_MOVE", 4.0, id_="g2")]
    pred = [_ev("TRACK_CHANGE", 1.0, id_="p1"), _ev("MIX_MOVE", 4.0, id_="p2")]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert res["f1"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0


def test_within_tolerance_counts_as_tp() -> None:
    """Test 5: predicted at t=10.5 matches ground_truth at t=12.0 within ±2s."""
    gt = [_ev("TRACK_CHANGE", 12.0, id_="g1")]
    pred = [_ev("TRACK_CHANGE", 10.5, id_="p1")]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 0


def test_outside_tolerance_is_fp_and_fn() -> None:
    """Verify that a mismatch beyond tolerance produces both FP and FN (no match)."""
    gt = [_ev("TRACK_CHANGE", 12.0, id_="g1")]
    pred = [_ev("TRACK_CHANGE", 5.0, id_="p1")]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert res["tp"] == 0
    assert res["fp"] == 1
    assert res["fn"] == 1
    assert res["f1"] == 0.0


def test_different_types_never_match_within_tolerance() -> None:
    """Test 6: events of different types are never paired even at the same t_session."""
    gt = [_ev("TRACK_CHANGE", 5.0, id_="g1")]
    pred = [_ev("MIX_MOVE", 5.0, id_="p1")]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert res["tp"] == 0
    assert res["per_detector"]["TRACK_CHANGE"]["fn"] == 1
    assert res["per_detector"]["MIX_MOVE"]["fp"] == 1


def test_per_detector_dict_shape_matches_overall() -> None:
    """Test 7: per_detector entries have the same shape as the overall cell."""
    gt = [_ev("TRACK_CHANGE", 1.0), _ev("MIX_MOVE", 4.0)]
    pred = [_ev("TRACK_CHANGE", 1.0), _ev("MIX_MOVE", 4.0)]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert "per_detector" in res
    for cell in res["per_detector"].values():
        assert {"tp", "fp", "fn", "precision", "recall", "f1"} <= cell.keys()


def test_per_detector_per_genre_matrix_when_lookup_provided() -> None:
    """Test 8: genre_lookup callable populates per_detector_per_genre matrix."""
    gt = [
        _ev("TRACK_CHANGE", 1.0, session="techno_01", id_="g1"),
        _ev("TRACK_CHANGE", 1.0, session="house_01", id_="g2"),
        _ev("MIX_MOVE", 4.0, session="techno_01", id_="g3"),
    ]
    pred = [
        _ev("TRACK_CHANGE", 1.0, session="techno_01", id_="p1"),
        _ev("MIX_MOVE", 4.0, session="techno_01", id_="p2"),
    ]
    genre_map = {"techno_01": "techno", "house_01": "house"}

    def lookup(s: str) -> str:
        return genre_map.get(s, "unknown")

    res = compute_f1(pred, gt, tolerance_s=2.0, genre_lookup=lookup)

    matrix = res["per_detector_per_genre"]
    assert "TRACK_CHANGE" in matrix
    assert "MIX_MOVE" in matrix
    # techno cell for TRACK_CHANGE: 1 TP (t=1.0)
    assert matrix["TRACK_CHANGE"]["techno"]["tp"] == 1
    # house cell for TRACK_CHANGE: 1 FN (no prediction for house_01 g2)
    assert matrix["TRACK_CHANGE"]["house"]["fn"] == 1
    # techno cell for MIX_MOVE: 1 TP (t=4.0)
    assert matrix["MIX_MOVE"]["techno"]["tp"] == 1


def test_empty_inputs_yield_zero_metrics() -> None:
    """Defensive: empty lists return zero metrics, no division-by-zero."""
    res = compute_f1([], [], tolerance_s=2.0)
    assert res["tp"] == 0
    assert res["f1"] == 0.0
    assert res["precision"] == 0.0
    assert res["recall"] == 0.0


def test_each_gt_matches_at_most_one_prediction() -> None:
    """Two predictions near a single ground_truth — only one TP, the other FP."""
    gt = [_ev("TRACK_CHANGE", 5.0, id_="g1")]
    pred = [
        _ev("TRACK_CHANGE", 5.1, id_="p1"),
        _ev("TRACK_CHANGE", 4.9, id_="p2"),
    ]
    res = compute_f1(pred, gt, tolerance_s=2.0)
    assert res["tp"] == 1
    assert res["fp"] == 1
    assert res["fn"] == 0


def test_corpus_manifest_validator_rejects_high_hard_tek() -> None:
    """Test 9: hard_tek > 70% rejected."""
    import json
    from pathlib import Path

    from scripts.eval.corpus_manifest import validate_manifest

    bad = {
        "version": "1",
        "sessions": [
            {"id": f"hard_tek_{i:02d}", "genre": "hard_tek"} for i in range(8)
        ]
        + [{"id": "techno_01", "genre": "techno"}, {"id": "house_01", "genre": "house"}],
        "sessions_min": 6,
    }
    p = Path("/tmp/_bad_manifest.json")
    p.write_text(json.dumps(bad))
    res = validate_manifest(p)
    assert res["valid"] is False
    assert any("hard_tek_pct" in e for e in res["errors"])


def test_corpus_manifest_validator_rejects_few_genres() -> None:
    """Test 10: < 3 distinct genres rejected."""
    import json
    from pathlib import Path

    from scripts.eval.corpus_manifest import validate_manifest

    bad = {
        "version": "1",
        "sessions": [
            {"id": "h1", "genre": "hard_tek"},
            {"id": "h2", "genre": "hard_tek"},
            {"id": "t1", "genre": "techno"},
            {"id": "t2", "genre": "techno"},
            {"id": "t3", "genre": "techno"},
            {"id": "t4", "genre": "techno"},
        ],
        "sessions_min": 6,
    }
    p = Path("/tmp/_bad_manifest_genre.json")
    p.write_text(json.dumps(bad))
    res = validate_manifest(p)
    assert res["valid"] is False
    assert any("distinct genre" in e for e in res["errors"])


def test_corpus_manifest_validator_accepts_diverse_corpus() -> None:
    """Test 11: 6-session 3-genre well-formed manifest passes + returns 12-char hash."""
    import json
    from pathlib import Path

    from scripts.eval.corpus_manifest import validate_manifest

    good = {
        "version": "1",
        "sessions": [
            {"id": "h1", "genre": "hard_tek", "duration_s": 1800},
            {"id": "h2", "genre": "hard_tek", "duration_s": 1800},
            {"id": "t1", "genre": "techno", "duration_s": 1800},
            {"id": "t2", "genre": "techno", "duration_s": 1800},
            {"id": "ho1", "genre": "house", "duration_s": 1800},
            {"id": "ho2", "genre": "house", "duration_s": 1800},
        ],
        "hard_tek_pct": 2 / 6,
        "genre_distribution": {"hard_tek": 2, "techno": 2, "house": 2},
        "sessions_min": 6,
    }
    p = Path("/tmp/_good_manifest.json")
    p.write_text(json.dumps(good))
    res = validate_manifest(p)
    assert res["valid"] is True, res["errors"]
    assert len(res["manifest_hash"]) == 12


@pytest.fixture
def audio_buffer_filled_synth():
    """Helper: returns an AudioBuffer filled from a synthetic 5s 16kHz mono WAV.

    Used by the AudioBuffer.fill_from_wav verification test below.
    """
    import wave

    import numpy as np

    from vibemix.audio.buffers import AudioBuffer

    p = "/tmp/_p27_01_t.wav"
    sr = 16000
    sine = (
        np.sin(2 * np.pi * 440 * np.arange(0, 5, 1 / sr)) * 0.3 * 32767
    ).astype(np.int16)
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(sine.tobytes())
    buf = AudioBuffer(seconds=10.0, sr=sr)
    buf.fill_from_wav(p)
    return buf


def test_audio_buffer_fill_from_wav_populates_ring(audio_buffer_filled_synth) -> None:
    """Test 1: fill_from_wav populates the ring; snapshot_features sees non-zero rms.

    Note: snapshot_features is a module-level function (vibemix.audio.features),
    not an AudioBuffer method. The plan's verify command syntax is corrected
    here per Deviation Rule 1 (bug in plan's example).
    """
    from vibemix.audio.features import snapshot_features

    feats = snapshot_features(audio_buffer_filled_synth, seconds=4.0)
    assert feats.get("rms", 0) > 0, f"fill_from_wav did not populate ring: {feats}"


def test_audio_buffer_fill_from_wav_resamples_48k_stereo() -> None:
    """Test 2: 48kHz stereo WAV is resampled + downmixed to 16kHz mono."""
    import wave

    import numpy as np

    from vibemix.audio.buffers import AudioBuffer
    from vibemix.audio.features import snapshot_features

    sr_src = 48000
    duration = 2.0
    n = int(sr_src * duration)
    t = np.arange(n) / sr_src
    sine = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
    # Interleaved stereo
    stereo = np.empty(n * 2, dtype=np.int16)
    stereo[0::2] = sine
    stereo[1::2] = sine

    p = "/tmp/_p27_01_stereo48.wav"
    with wave.open(p, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr_src)
        w.writeframes(stereo.tobytes())

    buf = AudioBuffer(seconds=5.0, sr=16000)
    buf.fill_from_wav(p)
    feats = snapshot_features(buf, seconds=1.0)
    assert feats.get("rms", 0) > 0


def test_audio_buffer_fill_from_wav_does_not_block_without_audio_device() -> None:
    """Test 3: runs in a unit-test context without sounddevice / live audio device.

    The fact that the import path completes and the buffer fills proves no
    sounddevice initialization happens inside fill_from_wav.
    """
    import wave

    import numpy as np

    from vibemix.audio.buffers import AudioBuffer

    p = "/tmp/_p27_01_tiny.wav"
    sr = 16000
    sine = (np.sin(2 * np.pi * 440 * np.arange(0, 0.5, 1 / sr)) * 0.3 * 32767).astype(
        np.int16
    )
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(sine.tobytes())

    buf = AudioBuffer(seconds=1.0, sr=sr)
    buf.fill_from_wav(p)  # must not raise
    assert buf._filled > 0
