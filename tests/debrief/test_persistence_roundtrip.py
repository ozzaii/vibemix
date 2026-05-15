# SPDX-License-Identifier: Apache-2.0
"""Persistence: atomic write + sha256 cache-invalidation read."""

from __future__ import annotations

from pathlib import Path

from vibemix.debrief import read_debrief, write_debrief


def test_roundtrip_returns_same_dict(tmp_path: Path):
    sess = tmp_path / "sess1"
    sess.mkdir()
    payload = {"chapters": [{"id": "track-01"}], "drills": []}
    mp3 = b"FAKEMP3DATA" * 100
    write_debrief(sess, payload, mp3)
    out = read_debrief(sess)
    assert out is not None
    assert out["chapters"] == payload["chapters"]
    assert out["tldr_sha256"]
    assert out["tldr_path"] == "debrief_tldr.mp3"
    assert out["schema_version"] == "v1"
    assert "generated_at" in out


def test_modified_mp3_invalidates_cache(tmp_path: Path):
    sess = tmp_path / "sess2"
    sess.mkdir()
    write_debrief(sess, {"chapters": []}, b"originalmp3bytes")
    # Tamper the mp3 — read_debrief should detect via sha256 mismatch.
    (sess / "debrief_tldr.mp3").write_bytes(b"tampered-different-bytes")
    out = read_debrief(sess)
    assert out is None


def test_missing_mp3_returns_none(tmp_path: Path):
    sess = tmp_path / "sess3"
    sess.mkdir()
    write_debrief(sess, {"chapters": []}, b"abc")
    (sess / "debrief_tldr.mp3").unlink()
    assert read_debrief(sess) is None


def test_missing_json_returns_none(tmp_path: Path):
    sess = tmp_path / "sess4"
    sess.mkdir()
    write_debrief(sess, {"chapters": []}, b"abc")
    (sess / "session_debrief.json").unlink()
    assert read_debrief(sess) is None


def test_atomic_write_no_tmp_leftover(tmp_path: Path):
    sess = tmp_path / "sess5"
    sess.mkdir()
    write_debrief(sess, {"chapters": []}, b"abc")
    leftover = list(sess.glob("*.tmp"))
    assert leftover == []


def test_malformed_json_returns_none(tmp_path: Path):
    sess = tmp_path / "sess6"
    sess.mkdir()
    write_debrief(sess, {"chapters": []}, b"abc")
    (sess / "session_debrief.json").write_text("{not json", encoding="utf-8")
    assert read_debrief(sess) is None
