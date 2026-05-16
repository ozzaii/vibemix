# SPDX-License-Identifier: Apache-2.0
"""Plan 29-08 Task 1 — short session + missing events surface typed errors.

DEBRIEF-11 disable gate verified at the orchestrator boundary. The
renderer (Plan 29-05 ErrorBanner) maps the reason codes to user-facing
copy.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.debrief import EventsMissing, SessionTooShort
from vibemix.debrief.main import run

pytestmark = pytest.mark.e2e


def test_120s_session_raises_session_too_short(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-short"
    sess.mkdir()
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 60.0, "kind": "event", "type": "TRACK_CHANGE"},
        {"t": 120.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000)

    with pytest.raises(SessionTooShort) as ei:
        run(sess, client=MagicMock(), recordings_root=root, serve=False)
    assert ei.value.reason == "session_too_short"


def test_missing_events_jsonl_raises_events_missing(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-noev"
    sess.mkdir()
    # voice.wav exists but events.jsonl missing.
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000)

    with pytest.raises(EventsMissing) as ei:
        run(sess, client=MagicMock(), recordings_root=root, serve=False)
    assert ei.value.reason == "events_missing"
