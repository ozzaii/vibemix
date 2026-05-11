# SPDX-License-Identifier: Apache-2.0
"""Per-session WAV/JSONL recorder.

Lifted from cohost_v4.py:771-850 with two improvements:

1. Configurable recording root (constructor `root: Path | None`) — fixes the
   v4:773 ``Path(__file__).parent / "recordings"`` anti-pattern that would
   write WAVs into site-packages on a packaged install.
2. Session dir created with mode=0o700 (RESEARCH.md Security V8 — recordings
   contain Kaan's voice, matches the HARD privacy rule in ~/CLAUDE.md).

All writers wrap in try/except: pass per v4 — recording is best-effort and
must never block the live audio pipeline.
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

from vibemix.audio.constants import INPUT_SR_TARGET, OUTPUT_SR


class VoiceRecorder:
    """Per-session WAV + JSONL writer.

    Layout (verbatim from v4):
        recordings/<YYYYMMDD-HHMMSS>/
            ├── voice.wav            # 24kHz mono int16 — AI replies
            ├── input.wav            # 16kHz mono int16 — BlackHole captured music + mic mix
            └── events.jsonl         # JSONL timeline, timestamped from session start

    Thread-safe — single `threading.Lock` guards all three writers. Audio-thread
    callbacks (`push_input` / `push_voice`) and asyncio writers (`log_event`)
    share the lock; the WAV/JSONL module-internal buffering is the rate-limiter,
    not us.
    """

    def __init__(self, root: Path | None = None) -> None:
        rec_dir = root if root is not None else Path.cwd() / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Defensively chmod — mkdir(mode=) interacts with umask on some platforms
        with contextlib.suppress(OSError):
            os.chmod(rec_dir, 0o700)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_dir = rec_dir / ts
        self.session_dir.mkdir(mode=0o700)
        with contextlib.suppress(OSError):
            os.chmod(self.session_dir, 0o700)

        self.start_time = time.time()

        self.voice_wav = wave.open(str(self.session_dir / "voice.wav"), "wb")
        self.voice_wav.setnchannels(1)
        self.voice_wav.setsampwidth(2)
        self.voice_wav.setframerate(OUTPUT_SR)

        self.input_wav = wave.open(str(self.session_dir / "input.wav"), "wb")
        self.input_wav.setnchannels(1)
        self.input_wav.setsampwidth(2)
        self.input_wav.setframerate(INPUT_SR_TARGET)

        self.events_path = self.session_dir / "events.jsonl"
        self.events_f = open(self.events_path, "a", encoding="utf-8")
        self._lock = threading.Lock()

        wall_start = datetime.now().astimezone()
        self._write_event_locked(
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": wall_start.isoformat(timespec="milliseconds"),
                "wall_clock_unix": round(wall_start.timestamp(), 3),
                "session_dir": str(self.session_dir.name),
            }
        )

        print(
            f"-> recording session -> {self.session_dir.name}/  "
            f"(voice.wav + input.wav + events.jsonl)"
        )

    def push_voice(self, pcm_bytes: bytes) -> None:
        """Append AI voice PCM (24kHz mono int16) to voice.wav. Best-effort. v4:805-812."""
        if not pcm_bytes:
            return
        with self._lock:
            try:
                self.voice_wav.writeframes(pcm_bytes)
            except Exception:
                pass

    def push_input(self, pcm_bytes: bytes) -> None:
        """Append captured input PCM (16kHz mono int16) to input.wav. Best-effort. v4:814-821."""
        if not pcm_bytes:
            return
        with self._lock:
            try:
                self.input_wav.writeframes(pcm_bytes)
            except Exception:
                pass

    def _write_event_locked(self, rec: dict) -> None:
        """Caller MUST hold self._lock. Writes one JSONL line + flush. v4:823-829."""
        try:
            json.dump(rec, self.events_f, ensure_ascii=False)
            self.events_f.write("\n")
            self.events_f.flush()
        except Exception:
            pass

    def log_event(self, kind: str, **fields: object) -> None:
        """Append `{t, kind, **fields}` to events.jsonl with t = seconds since
        session start (rounded to 3 decimals). v4:831-836."""
        rel = time.time() - self.start_time
        rec = {"t": round(rel, 3), "kind": kind, **fields}
        with self._lock:
            self._write_event_locked(rec)

    def close(self) -> None:
        """Close all three handles. Best-effort — never raises. v4:838-850."""
        with self._lock:
            with contextlib.suppress(Exception):
                self.voice_wav.close()
            with contextlib.suppress(Exception):
                self.input_wav.close()
            with contextlib.suppress(Exception):
                self.events_f.close()
