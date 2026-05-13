# SPDX-License-Identifier: Apache-2.0
"""Phase 15 — shared fixtures for tests/recording/.

`tmp_recordings_dir` — a clean recordings/ root rooted in tmp_path. Every test
that needs a recordings folder uses this so we never collide on the real
`_app_data_dir() / "recordings"` (which would pollute Kaan's actual app-data
on macOS).

`make_fake_session` — factory for building a synthetic session subdir with a
session.json on disk and a controllable mtime. Phase 15 tests need to assert
the crashed-session sweep behavior across a matrix of (ended_at_iso set vs
None) × (mtime young vs old) without spinning up a real `VoiceRecorder`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def tmp_recordings_dir(tmp_path: Path) -> Path:
    """Fresh recordings/ root inside tmp_path — mkdir parents on first access."""
    root = tmp_path / "recordings"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def make_fake_session(tmp_recordings_dir: Path) -> Callable[..., Path]:
    """Factory: builds `tmp_recordings_dir/<name>/session.json` with controllable shape.

    Args:
        name: subdir name (defaults to a stable 20260513-210410 sentinel).
        ended: when True, populate ended_at_iso/ended_at_unix/duration_s.
        age_seconds: how far back to set the session.json mtime via os.utime.
            0 = "just now" (file is the active session — sweep must leave it).
        crashed: whether to mark the session.json crashed=True up-front.

    Returns the session_dir Path. The session.json is shaped as the production
    writer would write it (16 fields, alphabetically sorted via json.dumps
    sort_keys=True — sweep tests cannot assume ordering matters since
    json.load returns a dict either way).
    """

    def _factory(
        name: str = "20260513-210410",
        ended: bool = True,
        age_seconds: int = 0,
        crashed: bool = False,
    ) -> Path:
        session_dir = tmp_recordings_dir / name
        session_dir.mkdir(parents=True, exist_ok=True)

        started_dt = datetime.now().astimezone()
        started_unix = round(started_dt.timestamp(), 3)
        if ended:
            ended_unix = started_unix + 60.0
            ended_iso = datetime.fromtimestamp(ended_unix).astimezone().isoformat(
                timespec="milliseconds"
            )
            duration_s = round(ended_unix - started_unix, 3)
        else:
            ended_unix = None
            ended_iso = None
            duration_s = None

        meta = {
            "session_json_version": "1.0",
            "vibemix_version": "0.1.0-dev0",
            "started_at_iso": started_dt.isoformat(timespec="milliseconds"),
            "started_at_unix": started_unix,
            "ended_at_iso": ended_iso,
            "ended_at_unix": ended_unix,
            "duration_s": duration_s,
            "voice": None,
            "mode": None,
            "genre": None,
            "user_level": None,
            "event_count": 0,
            "voice_wav_bytes": 0,
            "input_wav_bytes": 0,
            "events_jsonl_bytes": 0,
            "crashed": crashed,
        }

        session_json = session_dir / "session.json"
        session_json.write_text(
            json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
        )

        if age_seconds:
            now = datetime.now().timestamp()
            target = now - age_seconds
            os.utime(session_json, (target, target))

        return session_dir

    return _factory
