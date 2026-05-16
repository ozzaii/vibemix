# SPDX-License-Identifier: Apache-2.0
"""Plan 29-00 Task 2 Part C — shared pytest fixtures for all Phase 29 tests.

These fixtures provide a realistic, self-contained session-dir layout so
later Phase 29 plans (chapters / TLDR / drills / stripper / IPC schema /
WS server / e2e) can run without depending on a real DJ session being
present on the developer machine.

Fixture inventory:
  - sample_session_dir           — tmp_path / "20260515-112139" with all 4 files
  - sample_events_jsonl_path     — path to the trimmed real-session events.jsonl
  - sample_evidence_registry_path — synthesized snapshot derived from events
  - sample_voice_wav_path        — 5s silent voice.wav (24kHz mono int16)
"""

from __future__ import annotations

import json
import shutil
import struct
import wave
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_events_jsonl_path() -> Path:
    """Trimmed (20-line) real-session events.jsonl. Committed to the repo."""
    p = FIXTURES_DIR / "sample_events.jsonl"
    assert p.exists(), f"missing fixture {p}"
    return p


@pytest.fixture
def sample_evidence_registry_path() -> Path:
    """Synthesized EvidenceRegistry snapshot in `{source: {key: [t,...]}}` form.

    Mirrors what `EvidenceRegistry.snapshot()` produces — `tuple` round-trips
    to JSON `list`. Built from the event kinds in `sample_events.jsonl` so the
    citation linter can resolve [ev:HEARTBEAT@687.9] against this fixture.
    """
    p = FIXTURES_DIR / "sample_evidence_registry.json"
    assert p.exists(), f"missing fixture {p}"
    return p


@pytest.fixture
def sample_voice_wav_path() -> Path:
    """5-second silent voice.wav (24kHz mono int16). Committed to the repo."""
    p = FIXTURES_DIR / "sample_voice.wav"
    assert p.exists(), f"missing fixture {p}"
    return p


@pytest.fixture
def sample_session_dir(
    tmp_path: Path,
    sample_events_jsonl_path: Path,
    sample_evidence_registry_path: Path,
    sample_voice_wav_path: Path,
) -> Path:
    """Assemble a complete recordings/<YYYYMMDD-HHMMSS>/ layout in tmp_path.

    Contains: events.jsonl + evidence_registry.json + voice.wav +
    a 0-byte input.wav placeholder + a minimal session.json. Returns the
    session-dir path. Each test gets a fresh copy under its own tmp_path.
    """
    sess = tmp_path / "20260515-112139"
    sess.mkdir(parents=True, exist_ok=True)
    shutil.copy(sample_events_jsonl_path, sess / "events.jsonl")
    shutil.copy(sample_evidence_registry_path, sess / "evidence_registry.json")
    shutil.copy(sample_voice_wav_path, sess / "voice.wav")
    (sess / "input.wav").write_bytes(b"")
    (sess / "session.json").write_text(
        json.dumps(
            {
                "session_json_version": 1,
                "started_at_iso": "2026-05-15T11:21:39.656+03:00",
                "ended_at_iso": "2026-05-15T11:51:39.656+03:00",
                "duration_s": 1800.0,
                "voice": "Achird",
                "mode": "live",
                "genre": "house",
                "user_level": "intermediate",
                "event_count": 20,
                "crashed": False,
            }
        ),
        encoding="utf-8",
    )
    return sess
