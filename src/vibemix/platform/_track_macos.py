# SPDX-License-Identifier: Apache-2.0
"""TrackMacOS — TrackInfoBackend implementation for macOS via ``nowplaying-cli``.

Verbatim port of cohost_v4.py:532-577 (TrackInfo class + track_poll_loop).

Polling cadence: ~1Hz (subprocess is heavy enough we don't want it faster).
Subprocess invocation: ``nowplaying-cli get title artist`` — two newline-
separated lines (title, then artist), NOT JSON, NOT ``get-raw``. Format string
``f"{artist} - {title}"`` when both present.

Graceful degradation: TimeoutExpired / CalledProcessError / FileNotFoundError /
OSError all swallow silently — TrackInfo.snapshot() returns the last known
state (empty string title if never resolved). No log spam.

Phase boundary:
- Phase 3 (this commit): Quartz-free subprocess pattern.
- Phase 7: Windows port (_track_windows.py) wraps SMTC.
- Phase 19/20: installer bundles nowplaying-cli or substitutes a Swift helper.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from vibemix.platform.track import NowPlayingSnapshot


class TrackInfo:
    """Polls macOS Now Playing every 1s for djay's current title.
    Doesn't know which deck owns it — MusicState infers that from controller.

    Verbatim from cohost_v4.py:532-567.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.title_changed_at: float = 0.0
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"

    def poll_once(self) -> None:
        try:
            out = (
                subprocess.check_output(
                    [self._cli, "get", "title", "artist"],
                    timeout=1.5,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
                .splitlines()
            )
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            OSError,
        ):
            return
        title = out[0].strip() if len(out) > 0 else ""
        artist = out[1].strip() if len(out) > 1 else ""
        full = f"{artist} - {title}" if (artist and title) else title
        with self._lock:
            if full and full != self.title:
                self.prev_title = self.title
                self.title = full
                self.title_changed_at = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "title_changed_at": self.title_changed_at,
            }


class TrackMacOS:
    """TrackInfoBackend impl wrapping the v4 TrackInfo class.

    Exposes:
    - ``track_info`` (the v4-shape TrackInfo instance) so state_refresh_loop
      can call ``.snapshot()`` directly for the legacy dict shape it reads.
    - ``poll()`` returning a frozen Phase 1 ``NowPlayingSnapshot`` dataclass
      for Protocol consumers (album/duration/position always None — the
      ``get title artist`` subcommand only returns title + artist).
    - ``run_poll_loop`` (the v4:570-577 async loop) for callers that want
      automatic 1Hz polling.
    """

    def __init__(self):
        self.track_info = TrackInfo()
        self._cli = self.track_info._cli

    def is_available(self) -> bool:
        return Path(self._cli).is_file()

    def poll(self) -> NowPlayingSnapshot | None:
        """Synchronous best-effort poll — returns a NowPlayingSnapshot or None.

        Protocol surface: callers offload to an executor when in an async
        context (subprocess.check_output is blocking). Returns ``None`` when
        the CLI is unavailable or returns no parseable output.
        """
        self.track_info.poll_once()
        snap = self.track_info.snapshot()
        title = snap.get("title") or None
        if title is None:
            return None
        # The combined "{artist} - {title}" string is in title; we don't
        # round-trip-split it here (state_refresh_loop reads via track_info.snapshot()
        # which returns the v4 dict shape directly).
        return NowPlayingSnapshot(
            title=title,
            artist=None,
            album=None,
            duration_sec=None,
            position_sec=None,
        )

    async def run_poll_loop(self, stop_event: asyncio.Event) -> None:
        """v4:570-577 verbatim — 1Hz polling via run_in_executor."""
        loop = asyncio.get_running_loop()
        while not stop_event.is_set():
            try:
                await loop.run_in_executor(None, self.track_info.poll_once)
            except Exception as e:
                print(f"[track poll err] {e}", file=sys.stderr)
            await asyncio.sleep(1.0)
