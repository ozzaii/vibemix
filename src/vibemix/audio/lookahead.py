# SPDX-License-Identifier: Apache-2.0
"""Three-second file-based lookahead window for anti-slop latency masking.

Verbatim port of cohost_v4_tr.py:624-770 — adapted to package conventions
(typing, sys.stderr logging, absolute paths to brew-installed binaries).
The class is per-session: instantiate alongside `clean_audio_buf` in
`__main__.py` and pass into `DJCoHostAgent(..., lookahead=provider)`.

Pipeline:
    1. `nowplaying-cli get-raw` → current track + elapsedTime + playbackRate.
    2. `mdfind -name "<title>"` → local file path via Spotlight (cached per
       title for the session — streaming-only titles map to None and never
       re-query mdfind).
    3. `ffmpeg -ss <seek> -i <path> -t <duration> -ac 1 -ar 16000 -f wav` →
       18-second mono 16kHz WAV bytes that END 3 seconds past the current
       playhead. The `-ss` before `-i` is input-seek (file-index math, no
       decode) — ~270ms wall-clock per snapshot on local SSD.

Anti-slop principle: the LLM+TTS cascade typically takes 700-1500ms.
Feeding Gemini ~3s of audio the audience has NOT yet heard makes the
reaction land timed to the moment it describes, instead of trailing it
by a perceptible gap. The AI is never told the audio is future — that
labeling would invite prediction-shaped commentary (v4:1788 anti-pattern).

Every entry point returns ``(None, meta)`` on every failure path
(streaming-only source, missing nowplaying data, ffmpeg error,
TimeoutExpired, malformed JSON, etc.). The caller's main loop must
branch on ``if lookahead_wav:`` — never on exceptions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time

from vibemix.audio.constants import INPUT_SR_TARGET

# ---- Module-level constants (NOT in audio/constants.py — they live with the
# provider per CONTEXT §Claude's Discretion). ----
LOOKAHEAD_SECONDS: float = 3.0
"""Pencerenin SONU bu kadar onde — LLM+TTS latency offset (v4_tr:150)."""

LOOKAHEAD_WINDOW_SECONDS: float = 18.0
"""Total pencere uzunlugu (15s past context + 3s future) (v4_tr:151)."""

LOOKAHEAD_SAMPLE_RATE: int = INPUT_SR_TARGET
"""16kHz mono — matches the existing Part-1 audio_wav format (v4_tr:152)."""

LOOKAHEAD_TIMEOUT_S: float = 4.0
"""ffmpeg subprocess wall-clock ceiling — Pitfall 4 (malformed file) defense."""


class LookaheadProvider:
    """Peeks N seconds ahead into the audio file currently playing in djay Pro.

    Pipeline: ``nowplaying-cli`` (title + elapsed + playback rate) → Spotlight
    (``mdfind``) for file path → ``ffmpeg`` to decode WINDOW seconds at
    (position + lookahead*rate) → 16 kHz mono WAV bytes ready for Gemini.

    Every entry point returns ``(None, meta)`` on any failure (streaming source
    with no local file, bad ffmpeg, scrubbed past EOF, missing nowplaying
    fields, etc.) so the caller's main loop is never broken — lookahead just
    stops being attached until conditions recover.

    Thread-safety: a single ``threading.Lock`` guards the title→path cache and
    the ``_last_raw`` extrapolation state. Multiple threads may safely call
    ``snapshot_wav`` concurrently; the cache is a per-instance / per-session
    dict that grows monotonically over a set.
    """

    _AUDIO_EXTS = (".mp3", ".m4a", ".aiff", ".aif", ".wav", ".flac", ".ogg", ".aac")

    def __init__(
        self,
        lookahead_sec: float = LOOKAHEAD_SECONDS,
        window_sec: float = LOOKAHEAD_WINDOW_SECONDS,
        sample_rate: int = LOOKAHEAD_SAMPLE_RATE,
    ) -> None:
        self.lookahead_sec = lookahead_sec
        self.window_sec = window_sec
        self.sample_rate = sample_rate
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"
        self._ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self._title_to_path: dict[str, str | None] = {}
        self._last_raw: dict | None = None
        self._last_raw_wall: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Private helpers — verbatim port from cohost_v4_tr.py:652-720
    # ------------------------------------------------------------------

    def _poll_raw(self) -> dict | None:
        """Run ``nowplaying-cli get-raw``; drop heavy artwork blob; return JSON dict.

        Returns ``None`` on any subprocess failure or JSON parse error. The
        artwork field is stripped because it carries the album-cover image
        bytes (kMRMediaRemoteNowPlayingInfoArtworkData) which we never use.
        """
        try:
            out = subprocess.check_output(
                [self._cli, "get-raw"], timeout=1.5, stderr=subprocess.DEVNULL,
            )
            raw = json.loads(out)
            # Drop heavy artwork blob — we only need the metadata fields.
            return {k: v for k, v in raw.items() if "art" not in k.lower()}
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
            json.JSONDecodeError,
        ):
            return None

    def _resolve_file(self, title: str) -> str | None:
        """Spotlight-search for a local audio file matching ``title``.

        Returns the best-matching path, or ``None`` for streaming-only tracks
        (no Spotlight hit). Per-title result is cached for the lifetime of
        the provider — ``None`` is cached too, so we don't re-query mdfind
        on every snapshot for a streaming-only set.

        Match ranking (in order):
            1. Exact stem match (case-insensitive).
            2. Substring containment (title in stem or stem in title).
            3. First candidate by mdfind order (fallback).
        """
        with self._lock:
            if title in self._title_to_path:
                return self._title_to_path[title]
        path: str | None = None
        try:
            r = subprocess.run(
                ["mdfind", "-name", title],
                capture_output=True,
                timeout=2.0,
                text=True,
            )
            candidates = [p for p in r.stdout.splitlines() if p.strip()]
            candidates = [p for p in candidates if p.lower().endswith(self._AUDIO_EXTS)]
            if candidates:
                # Prefer exact stem match, else longest matching substring,
                # else first.
                t_low = title.lower()
                best: str | None = None
                for p in candidates:
                    stem = os.path.splitext(os.path.basename(p))[0].lower()
                    if stem == t_low:
                        best = p
                        break
                if best is None:
                    for p in candidates:
                        stem = os.path.splitext(os.path.basename(p))[0].lower()
                        if t_low in stem or stem in t_low:
                            best = p
                            break
                path = best or candidates[0]
        except Exception:  # noqa: BLE001 — graceful degrade, never raise
            path = None
        with self._lock:
            self._title_to_path[title] = path
        return path

    def _current_position(self) -> tuple[str | None, float | None, float]:
        """Return (title, elapsed_seconds, playback_rate).

        Extrapolation guard (Pitfall 2 — nowplaying-cli stale on app switch):
        if the previous poll had the SAME title with the SAME elapsed value,
        nowplaying-cli is reporting cached data — extrapolate by
        ``(wall_delta * playback_rate)`` so we don't snapshot the same window
        repeatedly. On title change we always return the FRESH elapsed value
        (no extrapolation) — load-bearing IP per ``test_extrapolation_guard_on_title_change``.
        """
        raw = self._poll_raw()
        if not raw:
            return (None, None, 1.0)
        title = raw.get("kMRMediaRemoteNowPlayingInfoTitle")
        elapsed = raw.get("kMRMediaRemoteNowPlayingInfoElapsedTime")
        rate = raw.get("kMRMediaRemoteNowPlayingInfoPlaybackRate", 1.0) or 1.0
        # nowplaying-cli reports the last sample djay published — extrapolate
        # forward by (wall delta * playback rate) when the elapsed field is
        # unchanged across consecutive polls. NEVER extrapolate across a title
        # change (Pitfall 2: that's djay just landing on a new track).
        now = time.time()
        with self._lock:
            prev = self._last_raw
            prev_t = self._last_raw_wall
            self._last_raw = raw
            self._last_raw_wall = now
        if elapsed is not None and prev is not None:
            prev_title = prev.get("kMRMediaRemoteNowPlayingInfoTitle")
            prev_elapsed = prev.get("kMRMediaRemoteNowPlayingInfoElapsedTime")
            if prev_title == title and prev_elapsed == elapsed:
                elapsed = elapsed + (now - prev_t) * rate
        return (title, elapsed, rate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot_wav(self) -> tuple[bytes | None, dict]:
        """Snapshot an 18s window of audio ending 3s past the current playhead.

        Returns ``(wav_bytes, meta)`` on success or ``(None, meta)`` on any
        failure path. ``meta`` always carries ``"ok": bool`` and ``"reason": str``
        keys; on success it also carries ``"title"``, ``"file"``, ``"seek_sec"``,
        ``"pos_sec"``, ``"window_end_sec"``, ``"duration_sec"``, ``"delta_sec"``
        for diagnostic / events.jsonl logging.

        Failure modes (each returns ``(None, meta)``, never raises):

        - ``"no nowplaying"`` — ``nowplaying-cli`` returned no title / elapsed.
        - ``"no file"`` — Spotlight had no match for the title (streaming-only).
        - ``"ffmpeg rc=<n> <stderr>"`` — non-zero ffmpeg exit (e.g. moov atom
          not found on partial-download .m4a — Pitfall 4).
        - ``"ffmpeg timeout"`` — ffmpeg exceeded ``LOOKAHEAD_TIMEOUT_S`` (4s).
        - ``"ffmpeg exc: <e>"`` — any other ffmpeg exception.
        """
        meta: dict = {
            "ok": False,
            "reason": "init",
            "title": None,
            "file": None,
            "seek_sec": None,
            "rate": 1.0,
        }
        title, pos, rate = self._current_position()
        meta["title"] = title
        meta["rate"] = rate
        if not title or pos is None:
            meta["reason"] = "no nowplaying"
            return (None, meta)
        path = self._resolve_file(title)
        meta["file"] = path
        if not path or not os.path.exists(path):
            meta["reason"] = "no file"
            return (None, meta)
        # Pencere SONU pos + lookahead*rate (file-sec). Pencere uzunlugu
        # window_sec file-sec. Pencere BASI = end - window. Track basinda
        # negatif olursa 0'a clamp, duration kisalir.
        end_file_sec = pos + self.lookahead_sec * rate
        seek = max(0.0, end_file_sec - self.window_sec)
        duration = max(0.5, end_file_sec - seek)
        meta["seek_sec"] = seek
        meta["pos_sec"] = pos
        meta["window_end_sec"] = end_file_sec
        meta["duration_sec"] = duration
        meta["delta_sec"] = end_file_sec - pos
        try:
            proc = subprocess.run(
                [
                    self._ffmpeg, "-loglevel", "error",
                    "-ss", f"{seek:.3f}",           # ← BEFORE -i: fast input seek
                    "-i", path,
                    "-t", f"{duration:.3f}",
                    "-ac", "1",                      # mono
                    "-ar", str(self.sample_rate),    # 16kHz
                    "-f", "wav",                     # WAV container (audio/wav mime)
                    "-y", "pipe:1",
                ],
                capture_output=True,
                timeout=LOOKAHEAD_TIMEOUT_S,
            )
            if proc.returncode != 0 or not proc.stdout:
                err = (
                    proc.stderr.decode(errors="replace")[:120] if proc.stderr else ""
                )
                meta["reason"] = f"ffmpeg rc={proc.returncode} {err}"
                return (None, meta)
            meta["ok"] = True
            meta["reason"] = "ok"
            return (proc.stdout, meta)
        except subprocess.TimeoutExpired:
            meta["reason"] = "ffmpeg timeout"
            return (None, meta)
        except Exception as e:  # noqa: BLE001 — graceful degrade per contract
            meta["reason"] = f"ffmpeg exc: {e}"
            print(f"[lookahead err] {e}", file=sys.stderr)
            return (None, meta)


__all__ = [
    "LOOKAHEAD_SAMPLE_RATE",
    "LOOKAHEAD_SECONDS",
    "LOOKAHEAD_TIMEOUT_S",
    "LOOKAHEAD_WINDOW_SECONDS",
    "LookaheadProvider",
]
