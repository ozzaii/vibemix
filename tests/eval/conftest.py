# SPDX-License-Identifier: Apache-2.0
"""Phase 27 — shared eval test fixtures.

Provides:
    - synthetic_session(tmp_path): self-contained 5s synthetic session dir
      (input.wav + events.jsonl + responses/ + genre.txt) suitable for the
      replay harness happy-path test.
    - cassettes_dir: placeholder VCR.py cassette dir for Plan 02 judges.
    - synthetic_session_fixture_dir: persistent fixture under
      tests/eval/fixtures/synthetic_session/ that the harness CLI smoke
      test invokes via --corpus tests/eval/fixtures.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
SYNTH_SESSION_DIR = FIXTURES_ROOT / "synthetic_session"


def _write_synthetic_wav(path: Path, *, sr: int = 16000, seconds: float = 5.0) -> None:
    """Write a 5s mono 16kHz PCM16 WAV: 1s silence + 4s of 440Hz sine.

    Mirrors the Plan 27-01 verify command's WAV recipe so the same fixture is
    produced inside conftest (fresh-clone regeneration; not committed to git
    LFS for a 5s sine wave that costs ~160KB).
    """
    silence_samples = int(sr * 1.0)
    sine_samples = int(sr * (seconds - 1.0))
    t = np.arange(0, sine_samples) / sr
    sine = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
    pcm = np.concatenate([np.zeros(silence_samples, dtype=np.int16), sine])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _write_synthetic_events(path: Path) -> None:
    """3 ground-truth events spanning the 5s synthetic session."""
    events = [
        {
            "id": "evt001",
            "type": "TRACK_CHANGE",
            "t_session": 1.0,
            "session": "synthetic_session",
            "payload": {"new_track": "fixture_track_a"},
        },
        {
            "id": "evt002",
            "type": "PHRASE_BOUNDARY",
            "t_session": 2.5,
            "session": "synthetic_session",
            "payload": {"phrase": 4},
        },
        {
            "id": "evt003",
            "type": "MIX_MOVE",
            "t_session": 4.0,
            "session": "synthetic_session",
            "payload": {"control": "filter_low"},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _ensure_synth_session(session_dir: Path) -> Path:
    """Idempotently materialize the synthetic_session fixture directory."""
    session_dir.mkdir(parents=True, exist_ok=True)
    wav_path = session_dir / "input.wav"
    events_path = session_dir / "events.jsonl"
    responses_dir = session_dir / "responses"
    genre_path = session_dir / "genre.txt"

    if not wav_path.exists():
        _write_synthetic_wav(wav_path)
    if not events_path.exists():
        _write_synthetic_events(events_path)
    responses_dir.mkdir(exist_ok=True)
    (responses_dir / ".gitkeep").touch(exist_ok=True)
    if not genre_path.exists():
        genre_path.write_text("techno\n", encoding="utf-8")
    return session_dir


@pytest.fixture
def synthetic_session(tmp_path: Path) -> Path:
    """Build a one-shot synthetic session under tmp_path. Returns the session dir."""
    session_dir = tmp_path / "synth_one"
    return _ensure_synth_session(session_dir)


@pytest.fixture(scope="session", autouse=True)
def synthetic_session_fixture_dir() -> Path:
    """Materialize tests/eval/fixtures/synthetic_session/ for the CLI smoke test.

    Runs once per test session. This is what ``--corpus tests/eval/fixtures``
    walks during the CLI smoke test in test_replay_harness.py.
    """
    return _ensure_synth_session(SYNTH_SESSION_DIR)


@pytest.fixture
def cassettes_dir() -> Path:
    """Placeholder VCR.py cassettes dir (used by Plan 02 judges)."""
    cdir = Path(__file__).parent / "cassettes"
    cdir.mkdir(exist_ok=True)
    return cdir
