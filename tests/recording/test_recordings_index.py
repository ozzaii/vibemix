# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 03 — RecordingsIndex tests (8 cases per plan Task 1 behavior).

Test 1: list() returns 3 RecordingSummary tuples sorted newest-first.
Test 2: list() synthesizes legacy-dir (no session.json) from WAV header + JSONL
        line count + dir-name parse (Pitfall 9).
Test 3: list() preserves crashed=True flag from session.json.
Test 4: delete() — valid removes dir; path-traversal rejected (3 variants); not_found.
Test 5: compute_usage() returns (sessions_count, bytes_total) summed via scandir.
Test 6: list() on a non-existent recordings_root returns empty tuple (fresh install).
Test 7: list() on a dir with malformed session.json falls back to legacy synth.
Test 8: read_events() — valid + malformed line skipped + missing file empty +
        path-traversal rejected.

Plan 15-06 appends:
Test 9 (perf gate, RESEARCH Q3 verification): list() against 200 fake sessions
        completes in <100ms locally (<500ms on CI runners — perf-gate-relaxed-on-ci
        per RESEARCH).
"""

from __future__ import annotations

import json
import os
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable

import pytest

from vibemix.runtime.recordings_index import (
    SESSION_DIR_RE,
    RecordingsIndex,
    run_retention_sweep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_silent_wav(path: Path, *, duration_s: float, sample_rate: int) -> None:
    """Write a real WAV file with `duration_s` seconds of silent int16 mono PCM."""
    n_frames = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


def _write_jsonl(path: Path, *records: dict) -> None:
    """Write a JSONL fixture file."""
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# Test 1 — list sorted newest-first across mixed (session.json + legacy)
# ---------------------------------------------------------------------------


def test_list_returns_three_summaries_sorted_newest_first(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    # Older sessions first so we exercise the sort, not insertion order.
    s_old = make_fake_session(name="20260510-100000", ended=True)
    s_mid = make_fake_session(name="20260512-120000", ended=True)
    # Legacy dir (no session.json) — must still appear in the list.
    legacy = tmp_recordings_dir / "20260513-210410"
    legacy.mkdir(parents=True)
    _write_silent_wav(legacy / "voice.wav", duration_s=0.5, sample_rate=24000)
    _write_jsonl(legacy / "events.jsonl", {"t": 0.0, "kind": "session_start"})

    idx = RecordingsIndex(tmp_recordings_dir)
    sessions = idx.list()

    assert isinstance(sessions, tuple)
    assert len(sessions) == 3
    names = [s.session_dir for s in sessions]
    # Sorted by started_at_unix descending — legacy is newest by dir name.
    assert names == ["20260513-210410", "20260512-120000", "20260510-100000"]


# ---------------------------------------------------------------------------
# Test 2 — legacy-dir synthesis (Pitfall 9)
# ---------------------------------------------------------------------------


def test_legacy_dir_synthesis_from_wav_header_and_jsonl(
    tmp_recordings_dir: Path,
) -> None:
    legacy = tmp_recordings_dir / "20260513-210410"
    legacy.mkdir(parents=True)
    # 0.5s silent voice.wav @24kHz mono int16 — wave.getnframes() / .getframerate()
    # yields exactly 0.5.
    _write_silent_wav(legacy / "voice.wav", duration_s=0.5, sample_rate=24000)
    _write_jsonl(
        legacy / "events.jsonl",
        {"t": 0.0, "kind": "session_start"},
        {"t": 1.5, "kind": "trigger", "reason": "manual"},
        {"t": 3.0, "kind": "ai_text", "text": "let's go"},
    )

    idx = RecordingsIndex(tmp_recordings_dir)
    sessions = idx.list()
    assert len(sessions) == 1
    s = sessions[0]
    assert s.session_dir == "20260513-210410"
    assert s.duration_s == pytest.approx(0.5, abs=0.01)
    assert s.event_count == 3
    # Dir-name parses to local-time isoformat.
    assert s.started_at_iso.startswith("2026-05-13T21:04:10")
    assert s.crashed is False


# ---------------------------------------------------------------------------
# Test 3 — crashed=True is preserved from session.json
# ---------------------------------------------------------------------------


def test_crashed_session_summary_preserves_flag(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    # ended=False simulates a session whose VoiceRecorder.close didn't run; then
    # mark crashed=True (the sweep_crashed_sessions on the next boot would write
    # this). For test purposes we set both ended + crashed via the factory.
    sd = make_fake_session(
        name="20260513-210410", ended=True, crashed=True
    )
    # Force crashed=true and ended_at to non-None — overwrite the fixture file
    # with the canonical "session ended cleanly but flagged crashed" shape.
    meta_path = sd / "session.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["crashed"] = True
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    idx = RecordingsIndex(tmp_recordings_dir)
    sessions = idx.list()
    assert len(sessions) == 1
    assert sessions[0].crashed is True


# ---------------------------------------------------------------------------
# Test 4 — delete: valid + path-traversal-rejected (3 attempts) + not_found
# ---------------------------------------------------------------------------


def test_delete_valid_session_removes_dir(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    sd = make_fake_session(name="20260513-210410")
    assert sd.exists()
    idx = RecordingsIndex(tmp_recordings_dir)
    ok, err = idx.delete("20260513-210410")
    assert ok is True
    assert err is None
    assert not sd.exists()


def test_delete_rejects_path_traversal(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    # Plant a sibling sentinel outside recordings_root that we expect to NEVER
    # be touched. (We assert it still exists at the end.)
    sentinel = tmp_recordings_dir.parent / "etc_passwd_sentinel.txt"
    sentinel.write_text("DO NOT DELETE\n", encoding="utf-8")

    # Also plant a legitimate session so we can confirm recordings_root content
    # is untouched too.
    legit = make_fake_session(name="20260513-210410")

    idx = RecordingsIndex(tmp_recordings_dir)
    for bad_name in (
        "../../etc/passwd",
        "../../../tmp/whatever",
        "20260513-210410/../../escape",
        "/etc/passwd",
        "20260513-210410\x00.evil",
        "..",
        ".",
    ):
        ok, err = idx.delete(bad_name)
        assert ok is False, f"name={bad_name!r} unexpectedly succeeded"
        assert err == "path_traversal_rejected", f"name={bad_name!r} -> err={err!r}"

    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == "DO NOT DELETE\n"
    assert legit.exists()


def test_delete_not_found_returns_distinct_error(tmp_recordings_dir: Path) -> None:
    idx = RecordingsIndex(tmp_recordings_dir)
    ok, err = idx.delete("20260101-000000")  # regex match but does not exist
    assert ok is False
    assert err == "not_found"


# ---------------------------------------------------------------------------
# Test 5 — compute_usage matches scandir sum across multiple sessions
# ---------------------------------------------------------------------------


def test_compute_usage_returns_count_and_byte_sum(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    # Three sessions with known file sizes — write deterministic padding so
    # the sum is reproducible.
    for name in ("20260510-100000", "20260512-120000", "20260513-210410"):
        sd = make_fake_session(name=name)
        # session.json was written by the fixture; add 2 more files.
        (sd / "voice.wav").write_bytes(b"X" * 1000)
        (sd / "events.jsonl").write_bytes(b"Y" * 500)

    idx = RecordingsIndex(tmp_recordings_dir)
    n_sessions, bytes_total = idx.compute_usage()
    assert n_sessions == 3

    # Cross-check via a fresh os.walk-style sum so the test isn't tautological.
    expected = 0
    for child in tmp_recordings_dir.iterdir():
        if child.is_dir():
            for f in child.iterdir():
                if f.is_file():
                    expected += f.stat().st_size
    assert bytes_total == expected


# ---------------------------------------------------------------------------
# Test 6 — non-existent recordings_root → empty tuple, no raise
# ---------------------------------------------------------------------------


def test_list_returns_empty_on_missing_recordings_root(tmp_path: Path) -> None:
    missing = tmp_path / "definitely-not-there"
    idx = RecordingsIndex(missing)
    sessions = idx.list()
    assert sessions == ()
    n_sessions, bytes_total = idx.compute_usage()
    assert n_sessions == 0
    assert bytes_total == 0


# ---------------------------------------------------------------------------
# Test 7 — malformed session.json falls back to legacy-synth
# ---------------------------------------------------------------------------


def test_malformed_session_json_falls_back_to_legacy_synth(
    tmp_recordings_dir: Path,
) -> None:
    sd = tmp_recordings_dir / "20260513-210410"
    sd.mkdir(parents=True)
    # Half-written / corrupted JSON — must not raise, must surface as a legacy
    # synth (Pitfall 9 defensive behavior).
    (sd / "session.json").write_text("{not json at all", encoding="utf-8")
    _write_silent_wav(sd / "voice.wav", duration_s=1.0, sample_rate=24000)
    _write_jsonl(
        sd / "events.jsonl",
        {"t": 0.0, "kind": "session_start"},
        {"t": 1.0, "kind": "trigger"},
    )

    idx = RecordingsIndex(tmp_recordings_dir)
    sessions = idx.list()
    assert len(sessions) == 1
    s = sessions[0]
    assert s.session_dir == "20260513-210410"
    # duration synthesized from WAV header (1.0s)
    assert s.duration_s == pytest.approx(1.0, abs=0.01)
    # event_count from JSONL line count (2 lines)
    assert s.event_count == 2
    assert s.crashed is False


# ---------------------------------------------------------------------------
# Test 8 — read_events: valid + malformed skipped + missing-file empty
#         + path-traversal rejected + regex-match-not-on-disk → ([], None)
# ---------------------------------------------------------------------------


def test_read_events_returns_parsed_list_skipping_malformed_lines(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    sd = make_fake_session(name="20260513-210410")
    events_path = sd / "events.jsonl"
    # 3 valid lines + 1 malformed (missing closing brace).
    events_path.write_text(
        '{"t": 0.0, "kind": "session_start"}\n'
        '{"t": 1.5, "kind": "trigger", "reason": "manual"}\n'
        '{"t": 5.0, "kind": "ai_text", "text": "hype"\n'  # malformed
        '{"t": 7.0, "kind": "controller_move", "control": "play_a"}\n',
        encoding="utf-8",
    )

    idx = RecordingsIndex(tmp_recordings_dir)
    events, err = idx.read_events("20260513-210410")
    assert err is None
    assert isinstance(events, list)
    assert len(events) == 3
    assert events[0]["kind"] == "session_start"
    assert events[1]["kind"] == "trigger"
    assert events[2]["kind"] == "controller_move"


def test_read_events_missing_file_returns_empty_list(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    # Session.json present, but no events.jsonl on disk.
    sd = make_fake_session(name="20260513-210410")
    (sd / "events.jsonl").unlink(missing_ok=True)

    idx = RecordingsIndex(tmp_recordings_dir)
    events, err = idx.read_events("20260513-210410")
    assert err is None
    assert events == []


def test_read_events_rejects_path_traversal(
    tmp_recordings_dir: Path,
) -> None:
    # Plant a sibling we expect to never be read.
    sibling = tmp_recordings_dir.parent / "secret.txt"
    sibling.write_text('{"t": 0.0, "kind": "leaked"}\n', encoding="utf-8")

    idx = RecordingsIndex(tmp_recordings_dir)
    for bad in (
        "../../etc/passwd",
        "../../../tmp/whatever",
        "20260513-210410/../../escape",
        "/etc/passwd",
    ):
        events, err = idx.read_events(bad)
        assert events is None, f"name={bad!r} unexpectedly returned events"
        assert err == "path_traversal_rejected"


def test_read_events_regex_match_but_missing_dir_returns_empty(
    tmp_recordings_dir: Path,
) -> None:
    idx = RecordingsIndex(tmp_recordings_dir)
    # Regex matches but the dir does not exist on disk — well-defined empty
    # outcome per plan behavior.
    events, err = idx.read_events("99999999-999999")
    assert err is None
    assert events == []


# ---------------------------------------------------------------------------
# Module-import + symbol smoke
# ---------------------------------------------------------------------------


def test_module_exports_symbols_for_consumers() -> None:
    from vibemix.runtime import recordings_index as mod

    assert hasattr(mod, "RecordingsIndex")
    assert hasattr(mod, "run_retention_sweep")
    assert hasattr(mod, "SESSION_DIR_RE")
    # Regex must accept canonical session-dir names and reject all path-traversal forms.
    assert SESSION_DIR_RE.match("20260513-210410")
    assert SESSION_DIR_RE.match("00000000-000000")
    assert not SESSION_DIR_RE.match("../../etc/passwd")
    assert not SESSION_DIR_RE.match("2026-05-13")
    assert not SESSION_DIR_RE.match("")


# ---------------------------------------------------------------------------
# Test 9 — Plan 15-06 perf gate: list() <100ms for 200 sessions
# (RESEARCH Open Question Q3 — empirical verification of the
# "scandir-based listing scales to drawer-realistic counts" claim that
# Plan 15-03 relied on when picking recompute-on-demand over a cache.)
# ---------------------------------------------------------------------------


def test_list_perf_200_sessions(
    tmp_recordings_dir: Path, make_fake_session: Callable[..., Path]
) -> None:
    """RecordingsIndex(root).list() against 200 fake sessions completes
    within the perf budget.

    Local-dev budget: <100ms. CI runner budget: <500ms (filesystems on
    GH Actions / GitLab runners are noticeably slower; relaxed-on-ci per
    plan behavior spec — keeps the gate green without dropping the
    real-world performance assertion).
    """
    # Build 200 sessions with monotonically incrementing dir names.
    # 20260101-000000, 20260101-000001, ... up to 200 distinct names.
    for i in range(200):
        # Spread across minute boundaries so all names are valid timestamps.
        hh = (i // 3600) % 24
        mm = (i // 60) % 60
        ss = i % 60
        name = f"20260101-{hh:02d}{mm:02d}{ss:02d}"
        make_fake_session(name=name, ended=True)

    idx = RecordingsIndex(tmp_recordings_dir)

    # Cold-cache timing — `os.scandir` may benefit from FS-cache warmth on
    # a subsequent call. Single measurement is what the IPC handler sees.
    start = time.perf_counter()
    sessions = idx.list()
    elapsed = time.perf_counter() - start

    assert len(sessions) == 200

    # perf-gate-relaxed-on-ci — GH Actions / CI filesystems are slower than
    # local dev. RESEARCH Q3 budget is 100ms local; allow 500ms on CI.
    on_ci = bool(os.environ.get("CI"))
    budget = 0.5 if on_ci else 0.1
    assert elapsed < budget, (
        f"list() against 200 sessions took {elapsed * 1000:.1f}ms "
        f"(budget {budget * 1000:.0f}ms on {'CI' if on_ci else 'local'})"
    )
