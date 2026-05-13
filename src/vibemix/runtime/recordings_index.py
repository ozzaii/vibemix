# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 03 — RecordingsIndex + run_retention_sweep.

The Python sidecar side of the recording browser. Three responsibilities:

1. **List sessions** — `RecordingsIndex.list()` returns a deterministic
   newest-first tuple of `RecordingSummary` covering both:
   * Phase 15-02 sessions with a `session.json` metadata file.
   * Legacy dirs (Phase 2-13) without session.json — synthesized from the
     dir name + WAV header + JSONL line count per RESEARCH Pitfall 9.

2. **Delete** — `RecordingsIndex.delete(name)` validates the session_dir
   name with two layers of defense:
   * Regex `^\\d{8}-\\d{6}$` rejects anything that isn't the basename shape.
   * `Path.is_relative_to(recordings_root.resolve())` rejects symlink escape
     after path resolution.
   Then `shutil.rmtree(target, ignore_errors=True)` per RESEARCH Pattern 3.
   Post-delete existence verification surfaces Windows file-in-use as
   "locked_or_in_use" rather than a silent partial failure.

3. **Compute usage** — `RecordingsIndex.compute_usage()` returns
   `(sessions_count, bytes_total)`. Single `os.scandir` pass per session
   using `entry.stat().st_size` — cached on Windows per PEP 471, single
   syscall on POSIX. No `os.walk`, no per-file extra stat call.

4. **Read events** — `RecordingsIndex.read_events(name)` returns
   `(events_list, None)` or `(None, error_code)` discriminated tuple.
   Same regex + is_relative_to gate as delete. Malformed JSON lines are
   silently skipped (logged at DEBUG, not WARNING — legacy files may have
   partial lines from process crashes).

The colocated `run_retention_sweep(root, retention_days, *, now=None)`
function is the verbatim Pattern 3 sweep body. Sentinel
`retention_days >= 36500` short-circuits before any filesystem work
(matches the Phase 12 retention-slider ∞ stop). Per-entry rmtree failures
log and continue — never raise.

Threat model:
  T-15-03-01 / T-15-03-08 — path traversal on session_dir.
    Mitigated at TWO layers: regex (rejects anything that doesn't match
    the basename shape) + is_relative_to after path resolution (rejects
    symlink escape). Defense in depth — the schema layer (Plan 15-01)
    is the first gate; this is the second.
  T-15-03-05 — symlink redirect.
    Path.resolve() follows symlinks before is_relative_to compares — a
    symlink pointing outside recordings_root resolves and is rejected.
  T-15-03-07 — Windows file-in-use on rmtree.
    `ignore_errors=True` + post-delete existence verification —
    locked dirs surface as "locked_or_in_use" and are retried on the
    next sweep trigger; never raise into SessionLoop.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from vibemix.ui_bus.messages import RecordingSummary

log = logging.getLogger("vibemix.runtime.recordings_index")


# ---------------------------------------------------------------------------
# session_dir regex — the V12 path-traversal gate at the runtime layer.
# Mirror of the schema-layer regex in tauri/ui/src/ipc/messages.schema.json
# (Plan 15-01). Both gates fire — schema rejects malformed IPC at the wire
# boundary; this rejects the same shape at the file-system boundary.
# ---------------------------------------------------------------------------


SESSION_DIR_RE: re.Pattern[str] = re.compile(r"^\d{8}-\d{6}$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scandir_size_sum(d: Path) -> int:
    """Return the sum of file sizes inside ``d`` via a single scandir pass.

    Per RESEARCH (scandir-based size summation): `entry.stat().st_size` is
    cached on Windows (PEP 471) and a single syscall on POSIX. Faster than
    `os.walk` + `Path.stat()`. Per-file stat failures (transient locks,
    permission errors) are swallowed — partial sums are better than None
    on the disk-usage line.
    """
    total = 0
    try:
        with os.scandir(d) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    try:
                        total += entry.stat().st_size
                    except OSError:
                        # Transient lock or perm error — continue past it.
                        continue
    except OSError:
        # Dir disappeared / permission denied — treat as empty.
        return 0
    return total


def _dir_name_to_iso(dir_name: str) -> Optional[str]:
    """Parse ``YYYYMMDD-HHMMSS`` into an ISO-8601 local-time string.

    Returns None if the name doesn't match SESSION_DIR_RE.
    """
    if not SESSION_DIR_RE.match(dir_name):
        return None
    try:
        dt = datetime.strptime(dir_name, "%Y%m%d-%H%M%S")
    except ValueError:
        return None
    return dt.isoformat(timespec="seconds")


def _dir_name_to_unix(dir_name: str) -> float:
    """Parse the dir name to a unix timestamp (local time) for sort ordering."""
    if not SESSION_DIR_RE.match(dir_name):
        return 0.0
    try:
        dt = datetime.strptime(dir_name, "%Y%m%d-%H%M%S")
    except ValueError:
        return 0.0
    return dt.timestamp()


def _wav_duration_seconds(wav_path: Path) -> float:
    """Return the duration of a WAV file in seconds, or 0.0 on any error.

    Pitfall 5 — crashed WAVs have wrong RIFF header lengths. wave.open
    parses the header at open() time; broken headers raise wave.Error.
    Swallow the exception and surface duration=0.0 so the UI still
    renders the row (just with "0s" duration). Pitfall 9 also covers
    "file doesn't exist" as a duration=0.0 case.
    """
    try:
        with wave.open(str(wav_path), "rb") as w:
            frames = w.getnframes()
            sr = w.getframerate()
            if sr <= 0:
                return 0.0
            return round(frames / float(sr), 3)
    except Exception:
        return 0.0


def _count_jsonl_lines(jsonl_path: Path) -> int:
    """Count non-empty lines in a JSONL file. Missing file → 0."""
    try:
        with jsonl_path.open(encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def _synthesize_legacy_summary(session_dir: Path) -> Optional[RecordingSummary]:
    """Build a RecordingSummary for a legacy (pre-Phase-15) directory.

    Falls back when session.json is absent OR malformed. Pitfall 9.
    Returns None only if the dir name doesn't match SESSION_DIR_RE — that
    way the list() filter never surfaces noise dirs (e.g., a stray ``.DS_Store``).
    """
    name = session_dir.name
    started_iso = _dir_name_to_iso(name)
    if started_iso is None:
        return None
    duration_s = _wav_duration_seconds(session_dir / "voice.wav")
    event_count = _count_jsonl_lines(session_dir / "events.jsonl")
    bytes_total = _scandir_size_sum(session_dir)
    return RecordingSummary(
        session_dir=name,
        started_at_iso=started_iso,
        duration_s=duration_s,
        event_count=event_count,
        bytes_total=bytes_total,
        crashed=False,
    )


def _read_session_summary(session_dir: Path) -> Optional[RecordingSummary]:
    """Build a RecordingSummary from session.json + a fresh scandir.

    Falls back to legacy synth on FileNotFoundError or JSONDecodeError
    (the malformed-session.json case is Pitfall 9 defensive — bad JSON
    is treated as "no session.json present" so the row still surfaces).

    bytes_total ALWAYS comes from a fresh scandir (not session.json's
    cached counts) so ongoing-session rows display live disk usage
    even though session.json was written at __init__ with placeholder
    zeros.
    """
    name = session_dir.name
    if not SESSION_DIR_RE.match(name):
        return None
    meta_path = session_dir / "session.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            raise ValueError("session.json root is not an object")
    except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError):
        return _synthesize_legacy_summary(session_dir)

    # Prefer the dir-name-derived iso for stable ordering / display; fall
    # back to session.json's started_at_iso if the dir name is somehow
    # divergent (shouldn't happen, but defensive).
    started_iso = _dir_name_to_iso(name) or str(meta.get("started_at_iso", ""))

    # Duration: session.json's authoritative if present + non-None; else
    # try the WAV header; else 0.0.
    duration_meta = meta.get("duration_s")
    if isinstance(duration_meta, (int, float)) and duration_meta >= 0:
        duration_s = float(duration_meta)
    else:
        duration_s = _wav_duration_seconds(session_dir / "voice.wav")

    event_count_meta = meta.get("event_count", 0)
    try:
        event_count = max(int(event_count_meta), 0)
    except (TypeError, ValueError):
        event_count = _count_jsonl_lines(session_dir / "events.jsonl")

    bytes_total = _scandir_size_sum(session_dir)
    crashed = bool(meta.get("crashed", False))

    return RecordingSummary(
        session_dir=name,
        started_at_iso=started_iso,
        duration_s=round(duration_s, 3),
        event_count=event_count,
        bytes_total=bytes_total,
        crashed=crashed,
    )


# ---------------------------------------------------------------------------
# RecordingsIndex — single-recordings_root facade for the IPC handlers
# ---------------------------------------------------------------------------


class RecordingsIndex:
    """Scandir-based recording browser index.

    Constructed once per ``SessionLoop`` (the recordings_root is stable
    for the lifetime of the process). The 4 surfaces are all stateless
    — every call reads from disk fresh — so concurrent calls from
    different IPC handlers are safe.
    """

    def __init__(self, recordings_root: Path) -> None:
        self.recordings_root = Path(recordings_root)

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------

    def list(self) -> tuple[RecordingSummary, ...]:
        """Return all sessions, newest-first by started_at_unix.

        On a non-existent recordings_root, returns an empty tuple (the
        fresh-install case where the OS-data dir hasn't been created
        yet). On a scandir OSError, also returns empty — never raises
        into the IPC handler.
        """
        if not self.recordings_root.exists():
            return ()
        try:
            entries = list(os.scandir(self.recordings_root))
        except OSError:
            return ()

        summaries: list[RecordingSummary] = []
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            if not SESSION_DIR_RE.match(entry.name):
                continue
            summary = _read_session_summary(Path(entry.path))
            if summary is not None:
                summaries.append(summary)

        # Newest first by dir-name-derived unix timestamp. Stable across
        # boots / OSes since the dir name is the canonical sort key (no
        # mtime-based ordering — mtimes drift on rsync-style migrations).
        summaries.sort(key=lambda s: _dir_name_to_unix(s.session_dir), reverse=True)
        return tuple(summaries)

    # ------------------------------------------------------------------
    # compute_usage
    # ------------------------------------------------------------------

    def compute_usage(self) -> tuple[int, int]:
        """Return ``(sessions_count, bytes_total)`` for the drawer's disk line.

        sessions_count = number of dirs matching SESSION_DIR_RE.
        bytes_total = sum of every file's st_size across every session
                      (via single-scandir-per-session — RESEARCH
                      scandir-based size summation).
        """
        if not self.recordings_root.exists():
            return (0, 0)
        try:
            entries = list(os.scandir(self.recordings_root))
        except OSError:
            return (0, 0)

        sessions_count = 0
        bytes_total = 0
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            if not SESSION_DIR_RE.match(entry.name):
                continue
            sessions_count += 1
            bytes_total += _scandir_size_sum(Path(entry.path))
        return (sessions_count, bytes_total)

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def delete(self, session_dir_name: str) -> tuple[bool, Optional[str]]:
        """Delete ``recordings_root/<session_dir_name>`` if and only if the name
        is safe.

        Two-layer path-traversal gate:
          1. SESSION_DIR_RE rejects anything that isn't the basename shape.
          2. Path.resolve().is_relative_to(self.recordings_root.resolve())
             rejects symlink escape (resolve follows symlinks).

        Returns:
            (True, None) on successful delete (dir removed).
            (False, "path_traversal_rejected") on either gate failure.
            (False, "not_found") if the regex matches but the dir doesn't
                exist on disk.
            (False, "locked_or_in_use") if rmtree silently leaves the dir
                behind (Windows file-in-use case — verified via
                post-delete existence check per RESEARCH Pattern 3).
        """
        if not isinstance(session_dir_name, str):
            return (False, "path_traversal_rejected")
        if not SESSION_DIR_RE.match(session_dir_name):
            return (False, "path_traversal_rejected")
        try:
            target = (self.recordings_root / session_dir_name).resolve()
            root_resolved = self.recordings_root.resolve()
        except OSError:
            return (False, "path_traversal_rejected")
        if not target.is_relative_to(root_resolved):
            return (False, "path_traversal_rejected")
        if target == root_resolved:
            # Defensive: refuse to delete the recordings root itself.
            return (False, "path_traversal_rejected")
        if not target.exists():
            return (False, "not_found")
        shutil.rmtree(target, ignore_errors=True)
        if target.exists():
            log.warning(
                "recordings_index: %s still present after rmtree (file in use?)",
                session_dir_name,
            )
            return (False, "locked_or_in_use")
        return (True, None)

    # ------------------------------------------------------------------
    # read_events
    # ------------------------------------------------------------------

    def read_events(
        self, session_dir_name: str
    ) -> tuple[Optional[list[dict]], Optional[str]]:
        """Read ``<recordings_root>/<name>/events.jsonl`` and return parsed records.

        Discriminated return:
          * (events_list, None) on success — events_list may be empty if
            the session dir / events.jsonl don't exist on disk OR if all
            lines failed to parse.
          * (None, "path_traversal_rejected") if the name fails the regex
            OR the path resolves outside recordings_root.

        Malformed JSON lines are silently skipped (logged at DEBUG to
        avoid noise on legacy / partial files where mid-line crashes are
        expected).
        """
        if not isinstance(session_dir_name, str):
            return (None, "path_traversal_rejected")
        if not SESSION_DIR_RE.match(session_dir_name):
            return (None, "path_traversal_rejected")
        try:
            target = (self.recordings_root / session_dir_name).resolve()
            root_resolved = self.recordings_root.resolve()
        except OSError:
            return (None, "path_traversal_rejected")
        if not target.is_relative_to(root_resolved):
            return (None, "path_traversal_rejected")
        if target == root_resolved:
            return (None, "path_traversal_rejected")

        # Regex matched + path safe but dir doesn't exist on disk → well-defined
        # empty outcome (UI surfaces "no events recorded for this session").
        if not target.exists():
            return ([], None)

        events_path = target / "events.jsonl"
        if not events_path.exists():
            return ([], None)

        events: list[dict] = []
        try:
            with events_path.open(encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        rec = json.loads(s)
                    except json.JSONDecodeError as e:
                        log.debug(
                            "read_events: skipped malformed line in %s: %s",
                            session_dir_name,
                            e,
                        )
                        continue
                    if isinstance(rec, dict):
                        events.append(rec)
                    # Non-dict JSON lines (e.g., a bare number) are dropped
                    # silently — they're never produced by VoiceRecorder and
                    # surfacing them through events_result would break the
                    # IPC schema (events[] elements MUST be objects).
        except OSError:
            # Unreadable file (transient lock) — return empty rather than
            # a partial list that might mislead the renderer.
            return ([], None)
        return (events, None)


# ---------------------------------------------------------------------------
# run_retention_sweep — colocated; verbatim Pattern 3
# ---------------------------------------------------------------------------


def run_retention_sweep(
    recordings_root: Path,
    retention_days: int,
    *,
    now: Optional[datetime] = None,
) -> list[str]:
    """Walk recordings_root and delete dirs older than retention_days.

    Returns the list of deleted session_dir names. Sentinel
    `retention_days >= 36500` (Phase 12 retention-slider ∞ stop) returns
    an empty list WITHOUT scanning — explicit short-circuit so the
    drawer's "infinite retention" choice has zero filesystem cost.

    `now` defaults to `datetime.now()` (no tz — matches the dir name
    format which is local-time per recorder.py:200's strftime).

    Per-entry rmtree failures log + continue — RESEARCH Pitfall 4. The
    sweep is best-effort; a Windows file-in-use blocking one entry must
    NOT prevent the others from being pruned.

    Threat T-15-03-06: the live session's dir is created mid-sweep at
    `started_at = now()`. Its dir name parses to a time strictly newer
    than `cutoff = now - retention_days`, so the active dir is never a
    sweep candidate. (For retention_days=0, cutoff=now, and the dir
    started_at is >= now-ε ≥ cutoff — still excluded.)
    """
    if retention_days >= 36500:
        return []
    recordings_root = Path(recordings_root)
    if not recordings_root.exists() or not recordings_root.is_dir():
        return []

    current = now if now is not None else datetime.now()
    cutoff = current - timedelta(days=retention_days)
    deleted: list[str] = []
    try:
        entries = list(os.scandir(recordings_root))
    except OSError:
        return []

    for entry in entries:
        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        try:
            session_start = datetime.strptime(entry.name, "%Y%m%d-%H%M%S")
        except ValueError:
            # Unrecognized name format — never delete (defensive against
            # stray dirs like ".DS_Store" or user-placed folders).
            continue
        if session_start >= cutoff:
            continue
        try:
            shutil.rmtree(entry.path, ignore_errors=True)
            # Post-delete existence verification — Windows file-in-use may
            # leave the dir behind silently (per RESEARCH Pattern 3).
            if not Path(entry.path).exists():
                deleted.append(entry.name)
            else:
                log.warning(
                    "retention sweep: %s still present after rmtree (file in use?)",
                    entry.name,
                )
        except OSError as e:
            # Outer try/except for the rare case where rmtree itself raises
            # (e.g., a parent path permission flip). Never propagate into
            # the SessionLoop / SettingsApplier callers.
            log.warning("retention sweep failure on %s: %s", entry.name, e)
    return deleted


__all__ = [
    "RecordingsIndex",
    "SESSION_DIR_RE",
    "run_retention_sweep",
]
