# SPDX-License-Identifier: Apache-2.0
"""Plan 29-08 Task 1 — cache-hit path returns within 1 second.

The orchestrator's cache-hit fast path skips Gemini entirely when
``session_debrief.json`` + ``debrief_tldr.mp3`` exist with matching
sha256. This test verifies the elapsed time + that the mock Gemini
client was NEVER called.
"""

from __future__ import annotations

import hashlib
import json
import time
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.e2e


def _build_cached_session(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "recordings"
    root.mkdir()
    sess = root / "20260515-cached"
    sess.mkdir()
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 100.0, "kind": "event", "type": "TRACK_CHANGE"},
        {"t": 600.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    (sess / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    wav = sess / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00" * 24000 * 2)

    from vibemix.debrief.persistence import write_debrief

    mp3 = b"CACHEDMP3" * 50
    debrief = {
        "chapters": [{"id": "track-01", "start": 0, "end": 600,
                      "label": "Track 1", "kind": "track",
                      "citation_event_id": "ev:TRACK_CHANGE@0"}],
        "drills": [
            {"situation": "S", "behavior": "B [ev:M@1]",
             "impact": "I [ev:P@2]", "action_recommended": "A [track:t]",
             "citation": "[ev:M@1]"} for _ in range(3)
        ],
    }
    write_debrief(sess, debrief, mp3)
    return root, sess


def test_cache_hit_returns_within_1s(tmp_path: Path):
    """run() with cache present must return within 1s without invoking Gemini."""
    from vibemix.debrief.main import run

    root, sess = _build_cached_session(tmp_path)
    client = MagicMock()
    t0 = time.perf_counter()
    state = run(sess, client=client, recordings_root=root, serve=False)
    elapsed = time.perf_counter() - t0

    assert state["cache_hit"] is True
    assert elapsed < 1.0, f"cache-hit path took {elapsed:.2f}s — should be < 1s"
    client.models.generate_content.assert_not_called()


def test_cache_invalidation_on_modified_mp3(tmp_path: Path):
    """If the MP3 is tampered after persistence, the cache is invalidated."""
    from vibemix.debrief.persistence import read_debrief

    root, sess = _build_cached_session(tmp_path)
    # Read OK first.
    assert read_debrief(sess) is not None
    # Tamper.
    (sess / "debrief_tldr.mp3").write_bytes(b"tampered-bytes-do-not-match")
    assert read_debrief(sess) is None
