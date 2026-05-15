# SPDX-License-Identifier: Apache-2.0
"""Session-loader edge: SessionTooShort raised for < 5min sessions."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from vibemix.debrief import SessionTooShort, load_session


def _make_session(tmp_path: Path, duration_s: float) -> Path:
    sess = tmp_path / "20260515-000000"
    sess.mkdir()
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": duration_s, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    # Add a tiny voice.wav header so the loader can still read meta.
    wav_path = sess / "voice.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000 * 2)  # 1 second silence
    return sess


def test_120s_session_raises_session_too_short(tmp_path: Path):
    sess = _make_session(tmp_path, duration_s=120.0)
    with pytest.raises(SessionTooShort) as ei:
        load_session(sess)
    assert ei.value.reason == "session_too_short"
    assert ei.value.duration_s == pytest.approx(120.0)


def test_299s_just_under_threshold_raises(tmp_path: Path):
    sess = _make_session(tmp_path, duration_s=299.0)
    with pytest.raises(SessionTooShort):
        load_session(sess)


def test_301s_just_over_threshold_passes(tmp_path: Path):
    sess = _make_session(tmp_path, duration_s=301.0)
    events, evi, voice_meta = load_session(sess)
    assert len(events) == 2
    assert isinstance(evi, dict)
    assert voice_meta is not None
