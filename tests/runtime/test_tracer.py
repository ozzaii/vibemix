# SPDX-License-Identifier: Apache-2.0
"""Unit tests for SessionTracer — the comprehensive per-session trace.jsonl.

All tests use a tmp session dir (never the real ~/.cache or recordings root)
and a tiny fake recorder, so they are offline + hermetic + fast.
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from vibemix.runtime.tracer import SessionTracer


class _FakeRecorder:
    """Minimal stand-in for VoiceRecorder — only the attributes SessionTracer
    reads: ``session_dir``, ``start_time``, ``_lock``."""

    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.start_time = time.time()
        self._lock = threading.Lock()


@pytest.fixture
def rec(tmp_path):
    d = tmp_path / "20260525-230000"
    d.mkdir()
    return _FakeRecorder(d)


def _read_lines(rec) -> list[dict]:
    p = rec.session_dir / "trace.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]


def test_attach_enabled_by_default(rec, monkeypatch):
    monkeypatch.delenv("VIBEMIX_TRACE", raising=False)
    t = SessionTracer.attach(rec)
    assert t.enabled is True
    assert (rec.session_dir / "trace.jsonl").exists()


def test_disabled_via_env_is_noop(rec, monkeypatch):
    monkeypatch.setenv("VIBEMIX_TRACE", "0")
    t = SessionTracer.attach(rec)
    assert t.enabled is False
    t.event("emit", type="HEARTBEAT")
    # No file written, no crash.
    assert not (rec.session_dir / "trace.jsonl").exists()


def test_none_recorder_is_safe_noop(monkeypatch):
    monkeypatch.delenv("VIBEMIX_TRACE", raising=False)
    t = SessionTracer.attach(None)
    assert t.enabled is False
    # Every method must be callable without raising.
    t.audio("x")
    t.state("x")
    t.event("x")
    t.midi("x")
    t.ai_call("x")
    t.ai_resp("x")
    t.tts("x")
    t.suggestion("x")
    t.ws("x")
    t.error("x")
    t.note_change("STATE", "phase", "k", "v")
    t.close()


def test_record_schema_and_categories(rec):
    t = SessionTracer.attach(rec)
    t.event("emit", type="TRACK_CHANGE", deck="A")
    t.midi("move", label="A_play→ON")
    rows = _read_lines(rec)
    assert len(rows) == 2
    for row in rows:
        assert set(row.keys()) == {"ts_iso", "t_rel_s", "category", "event", "detail"}
        assert isinstance(row["t_rel_s"], (int, float))
        assert "T" in row["ts_iso"]  # ISO timestamp
    ev_row = rows[0]
    assert ev_row["category"] == "EVENT"
    assert ev_row["event"] == "emit"
    assert ev_row["detail"]["type"] == "TRACK_CHANGE"
    assert rows[1]["category"] == "MIDI"
    assert rows[1]["detail"]["label"] == "A_play→ON"


def test_note_change_debounces_unchanged_values(rec):
    t = SessionTracer.attach(rec)
    t.note_change("STATE", "phase", "state.phase", "groove")
    t.note_change("STATE", "phase", "state.phase", "groove")  # unchanged → no line
    t.note_change("STATE", "phase", "state.phase", "drop")  # changed → line
    rows = _read_lines(rec)
    assert len(rows) == 2
    assert rows[0]["detail"]["to"] == "groove"
    assert rows[0]["detail"]["from"] is None
    assert rows[1]["detail"]["from"] == "groove"
    assert rows[1]["detail"]["to"] == "drop"


def test_note_change_tracks_none_distinctly(rec):
    """None is a real tracked value, distinct from 'never seen'."""
    t = SessionTracer.attach(rec)
    t.note_change("STATE", "track", "state.audible_track", None)  # first-ever None → line
    t.note_change("STATE", "track", "state.audible_track", None)  # still None → no line
    t.note_change("STATE", "track", "state.audible_track", "Song A")  # change → line
    rows = _read_lines(rec)
    assert len(rows) == 2


def test_secret_scrub_by_key_and_value(rec):
    t = SessionTracer.attach(rec)
    t.ai_call(
        "llm_invoke",
        api_key="AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
        authorization="Bearer secret",
        prompt=(
            "play track with token "
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkthYW4ifQ."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ),
        bpm=128,
    )
    rows = _read_lines(rec)
    assert len(rows) == 1
    d = rows[0]["detail"]
    assert d["api_key"] == "***"  # redacted by key name
    assert d["authorization"] == "***"  # redacted by key name
    assert "eyJ" not in d["prompt"]  # JWT redacted by value shape
    assert "***" in d["prompt"]
    assert d["bpm"] == 128  # benign value untouched


def test_scrub_nested_and_bounded(rec):
    t = SessionTracer.attach(rec)
    t.ai_call("x", detail={"creds": {"token": "abc"}, "list": [{"secret": "v"}]})
    rows = _read_lines(rec)
    d = rows[0]["detail"]["detail"]
    assert d["creds"]["token"] == "***"
    assert d["list"][0]["secret"] == "***"


def test_trace_never_raises_on_bad_payload(rec):
    """A non-serializable payload must not propagate — fail-soft swallow."""
    t = SessionTracer.attach(rec)

    class Unserializable:
        pass

    # Should not raise even though the object isn't JSON-serializable.
    t.event("weird", obj=Unserializable())
    # The bad line is simply dropped; tracer stays usable afterward.
    t.event("ok", type="HEARTBEAT")
    rows = _read_lines(rec)
    assert any(r["detail"].get("type") == "HEARTBEAT" for r in rows)


def test_shares_recorder_lock(rec):
    """The tracer must write through the recorder's lock so trace.jsonl and
    events.jsonl never interleave mid-line."""
    t = SessionTracer.attach(rec)
    assert t._lock is rec._lock


def test_close_is_idempotent(rec):
    t = SessionTracer.attach(rec)
    t.event("emit", type="X")
    t.close()
    t.close()  # second close must be safe
    # After close, further writes are no-ops (enabled flipped False).
    t.event("emit", type="Y")
    rows = _read_lines(rec)
    # trace_close line + the first emit; the post-close emit is dropped.
    assert any(r["event"] == "trace_close" for r in rows)
    assert not any(r["detail"].get("type") == "Y" for r in rows)


def test_concurrent_writes_are_line_safe(rec):
    """Many threads writing concurrently must produce valid, non-corrupt JSONL."""
    t = SessionTracer.attach(rec)

    def worker(n):
        for i in range(50):
            t.event("emit", thread=n, i=i)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    rows = _read_lines(rec)  # parsing every line proves none got interleaved
    assert len(rows) == 4 * 50
