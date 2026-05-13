# SPDX-License-Identifier: Apache-2.0
"""Per-session WAV/JSONL recorder.

Lifted from cohost_v4.py:771-850 with three improvements:

1. Configurable recording root (constructor `root: Path | None`) — fixes the
   v4:773 ``Path(__file__).parent / "recordings"`` anti-pattern that would
   write WAVs into site-packages on a packaged install.
2. Session dir created with mode=0o700 (RESEARCH.md Security V8 — recordings
   contain Kaan's voice, matches the HARD privacy rule in ~/CLAUDE.md).
3. Phase 15 — `session.json` two-write pattern + crashed-session boot sweep.
   At __init__ a placeholder session.json is written (ended_at_iso=None,
   crashed=False). At close() it's rewritten atomically with the final
   timestamps + byte counts. If the process dies between the two writes,
   the next launch's `sweep_crashed_sessions` walks recordings/, finds
   session.json files with ended_at_iso=None AND mtime older than 30s
   (anything younger is the active session of *this* run), and rewrites
   them with crashed=True. Atomic write recipe mirrors ConfigStore.save()
   at runtime/config_store.py:229-234 (tmp + os.replace, atomic on POSIX
   + Windows ReplaceFileW).

WAV/JSONL writers wrap in try/except: pass per v4 — recording is best-effort
and must never block the live audio pipeline. session.json is NOT best-effort:
atomic write errors surface so a half-written meta is never visible to the
sweep on the next boot.
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

from vibemix import __version__
from vibemix.audio.constants import INPUT_SR_TARGET, OUTPUT_SR

# Phase 15 — session.json schema version. Bump on breaking shape changes;
# new optional fields can land without a bump. Surfaced to the UI via the
# `session_json_version` field on every session.json write.
SESSION_JSON_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Atomic JSON write — mirrors runtime/config_store.py:229-234
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomically write ``data`` to ``path`` via ``tmp + os.replace``.

    Atomic on POSIX (rename(2)) and Windows (ReplaceFileW). A mid-write
    failure leaves the original file content intact — the tmp file may
    linger but the canonical path is never half-written.

    Raises ``OSError`` on disk failure — recorder code paths that call
    this MUST decide whether to suppress (best-effort) or propagate. For
    Phase 15: __init__ propagates (session.json absence breaks sweep);
    close() suppresses (recorder shutdown is best-effort per POC parity).
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, indent=2, sort_keys=True)
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Crashed-session sweep — boot-time only (autonomous resolution #4)
# ---------------------------------------------------------------------------


def sweep_crashed_sessions(
    recordings_root: Path,
    *,
    mtime_age_s: int = 30,
    now: datetime | None = None,
) -> list[str]:
    """Walk ``recordings_root/*/session.json`` and mark stale unended sessions.

    A session is "crashed" iff:
      1. session.json's ``ended_at_iso`` is None, AND
      2. session.json's mtime is older than ``mtime_age_s`` seconds ago.

    Both conditions must hold — (1) alone could be the active session of
    THIS run; (2) alone is just a stale-but-cleanly-closed session.

    Skips:
      - dirs without session.json (Phase 2-13 legacy dirs — Pitfall 9)
      - dirs whose session.json fails to parse (best-effort, no raise)
      - already-marked crashed sessions (ended_at_iso is set, so they
        don't match predicate 1 → idempotent)

    Returns: list of session_dir names that were marked crashed this call.

    ``now`` defaults to ``datetime.now().astimezone()`` (test injection
    point — pass a fixed datetime to make the mtime cutoff deterministic).
    """
    if not recordings_root.exists() or not recordings_root.is_dir():
        return []

    now = now if now is not None else datetime.now().astimezone()
    cutoff_unix = now.timestamp() - mtime_age_s
    marked: list[str] = []

    try:
        entries = list(os.scandir(recordings_root))
    except OSError:
        return []

    for entry in entries:
        if not entry.is_dir(follow_symlinks=False):
            continue
        session_json = Path(entry.path) / "session.json"
        if not session_json.exists():
            continue  # legacy dir (Phase 2-13)
        try:
            stat = session_json.stat()
        except OSError:
            continue
        if stat.st_mtime > cutoff_unix:
            continue  # too young — could be the active session

        try:
            meta = json.loads(session_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue  # busted JSON — leave alone

        if not isinstance(meta, dict):
            continue
        if meta.get("ended_at_iso") is not None:
            continue  # cleanly closed OR already marked crashed

        # Derive ended_at from mtime — best signal we have for when the
        # process died.
        ended_unix = round(stat.st_mtime, 3)
        ended_dt = datetime.fromtimestamp(stat.st_mtime).astimezone()
        meta["ended_at_iso"] = ended_dt.isoformat(timespec="milliseconds")
        meta["ended_at_unix"] = ended_unix
        try:
            duration = ended_unix - float(meta.get("started_at_unix") or ended_unix)
        except (TypeError, ValueError):
            duration = 0.0
        meta["duration_s"] = round(max(duration, 0.0), 3)
        meta["crashed"] = True

        try:
            _atomic_write_json(session_json, meta)
        except OSError:
            continue  # disk locked / permission — skip; next sweep will retry

        marked.append(entry.name)

    return marked


# ---------------------------------------------------------------------------
# VoiceRecorder — per-session WAV + JSONL + session.json writer
# ---------------------------------------------------------------------------


class VoiceRecorder:
    """Per-session WAV + JSONL writer.

    Layout (verbatim from v4 + Phase 15 session.json addition):
        recordings/<YYYYMMDD-HHMMSS>/
            ├── voice.wav            # 24kHz mono int16 — AI replies
            ├── input.wav            # 16kHz mono int16 — BlackHole captured music + mic mix
            ├── events.jsonl         # JSONL timeline, timestamped from session start
            └── session.json         # Phase 15 — meta (started/ended/voice/mode/genre/...)

    Thread-safe — single `threading.Lock` guards all four writers. Audio-thread
    callbacks (`push_input` / `push_voice`) and asyncio writers (`log_event`)
    share the lock; the WAV/JSONL module-internal buffering is the rate-limiter,
    not us.

    Phase 15 constructor kwargs ``voice_id`` / ``mode`` / ``genre`` /
    ``user_level`` are ALL optional — `cohost_v4.py` still constructs
    `VoiceRecorder()` with zero args (POC compatibility rule).
    """

    def __init__(
        self,
        root: Path | None = None,
        *,
        voice_id: str | None = None,
        mode: str | None = None,
        genre: str | None = None,
        user_level: str | None = None,
    ) -> None:
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

        # Phase 15 — session.json placeholder. Held in-memory for close()
        # so we can rewrite atomically without re-reading from disk (which
        # would race the sweep if it ran concurrently — though sweep is
        # boot-only so the race is theoretical).
        self._session_meta: dict = {
            "session_json_version": SESSION_JSON_VERSION,
            "vibemix_version": __version__,
            "started_at_iso": wall_start.isoformat(timespec="milliseconds"),
            "started_at_unix": round(wall_start.timestamp(), 3),
            "ended_at_iso": None,
            "ended_at_unix": None,
            "duration_s": None,
            "voice": voice_id,
            "mode": mode,
            "genre": genre,
            "user_level": user_level,
            "event_count": 0,
            "voice_wav_bytes": 0,
            "input_wav_bytes": 0,
            "events_jsonl_bytes": 0,
            "crashed": False,
        }
        # __init__ propagates atomic-write errors — a missing session.json
        # would break the sweep on the next boot. close() suppresses (best-
        # effort shutdown per POC parity).
        _atomic_write_json(self.session_dir / "session.json", self._session_meta)

        print(
            f"-> recording session -> {self.session_dir.name}/  "
            f"(voice.wav + input.wav + events.jsonl + session.json)"
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
        session start (rounded to 3 decimals). v4:831-836.

        Phase 15: also increments the in-memory ``event_count`` cache so the
        finalizer can write it to session.json without re-scanning the JSONL.
        DO NOT rewrite session.json on every event — disk-write amplification
        is exactly the RESEARCH Pitfall 4 concern.
        """
        rel = time.time() - self.start_time
        rec = {"t": round(rel, 3), "kind": kind, **fields}
        with self._lock:
            self._write_event_locked(rec)
            # Mirror the JSONL write count. session_start is line 0 written
            # by __init__ BEFORE this counter exists — it intentionally
            # isn't counted here (matches what a re-scan would NOT find
            # easily; the finalizer reads the actual line count anyway).
            try:
                self._session_meta["event_count"] = (
                    int(self._session_meta.get("event_count", 0)) + 1
                )
            except (TypeError, ValueError):
                pass

    def _finalize_session_meta(self) -> None:
        """Rewrite session.json with ended_at + duration + byte counts.

        Called from close() AFTER the WAV/JSONL handles are closed so
        st_size returns the final flushed sizes (wave.close() patches the
        RIFF length header at this point).

        Best-effort: a final-meta rewrite failure is logged-and-swallowed
        rather than re-raised. The session.json from __init__ still exists
        with ended_at_iso=None; the next-boot sweep will rewrite it as
        crashed=True. That's the worst-case outcome — better than leaving
        the recorder shutdown half-done.
        """
        try:
            ended_dt = datetime.now().astimezone()
            ended_unix = round(ended_dt.timestamp(), 3)
            started_unix = float(self._session_meta.get("started_at_unix") or ended_unix)

            self._session_meta["ended_at_iso"] = ended_dt.isoformat(
                timespec="milliseconds"
            )
            self._session_meta["ended_at_unix"] = ended_unix
            self._session_meta["duration_s"] = round(
                max(ended_unix - started_unix, 0.0), 3
            )

            for fname, key in (
                ("voice.wav", "voice_wav_bytes"),
                ("input.wav", "input_wav_bytes"),
                ("events.jsonl", "events_jsonl_bytes"),
            ):
                try:
                    self._session_meta[key] = (self.session_dir / fname).stat().st_size
                except OSError:
                    pass  # leave previous value (likely 0)

            # Re-count events.jsonl lines as a belt-and-braces measure —
            # the in-memory counter misses session_start (line 0) and
            # could drift if log_event ever throws under the lock. The
            # actual JSONL line count is authoritative.
            try:
                with open(self.events_path, encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                # session_start sits on line 0; user-facing event_count
                # is line_count - 1 (session_start is a marker, not an
                # event). Clamp to non-negative.
                self._session_meta["event_count"] = max(line_count - 1, 0)
            except OSError:
                pass

            _atomic_write_json(
                self.session_dir / "session.json", self._session_meta
            )
        except Exception as e:
            # POC parity — recorder shutdown stays best-effort.
            print(f"[recorder finalize err] {e}")

    def close(self) -> None:
        """Close all four handles. Best-effort — never raises. v4:838-850 +
        Phase 15 session.json finalize."""
        with self._lock:
            with contextlib.suppress(Exception):
                self.voice_wav.close()
            with contextlib.suppress(Exception):
                self.input_wav.close()
            with contextlib.suppress(Exception):
                self.events_f.close()
        # session.json finalize OUTSIDE the lock — its own atomic-write
        # is the synchronization point. Calling under self._lock would
        # serialize the (rare) close with audio-thread callbacks for no
        # gain.
        self._finalize_session_meta()
