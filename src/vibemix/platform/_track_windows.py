# SPDX-License-Identifier: Apache-2.0
"""TrackWindows — TrackInfoBackend impl for Windows via winsdk SMTC.

SMTC = System Media Transport Controls — Windows' equivalent of macOS's Now
Playing surface. Reads currently-playing media via:

    winsdk.windows.media.control
        .GlobalSystemMediaTransportControlsSessionManager
        .request_async()
        .get_current_session()
        .try_get_media_properties_async()

Polling cadence: 1Hz (matches macOS ``nowplaying-cli`` subprocess). Bridges
winsdk's awaitable API via ``asyncio.run`` inside a synchronous executor
thread — CONTEXT Decision §TrackWindows: simpler than introducing new async
event-loop machinery; matches the macOS subprocess pattern.

Graceful fallback: when SMTC has no current session (no media app reporting),
``poll()`` returns None. djay Pro on Windows is known to NOT expose to SMTC
in all builds — Kaan documented this as an accepted v1 limitation
(see CONTEXT Decisions §TrackWindows). Phase 9 / Phase 11 may introduce a
Windows-specific djay scraper if ergonomics block.

Critical Constraint 3: ``import winsdk.windows.media.control`` lives only
inside ``_poll_smtc_sync``. Importing this module on macOS does NOT pull
``winsdk`` into ``sys.modules`` — verified by tests/test_track_windows.py
and the no-leak guard in tests/test_platform_selector.py.

Output format parity with macOS: SMTC's artist+title combine to
``f"{artist} - {title}"`` (matches v4 macOS convention). When one side is
empty, the non-empty value is used alone. When both are empty, ``poll()``
returns None.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time

from vibemix.platform.track import NowPlayingSnapshot


class _SmtcState:
    """Thread-safe v4-dict-shape SMTC title cache.

    Mirrors ``vibemix.platform._track_macos.TrackInfo`` in shape so
    ``state_refresh_loop`` can call ``.snapshot()`` and read the same
    ``{title, prev_title, title_changed_at}`` dict regardless of OS.

    ``_has_logged_unavailable`` is the log-once flag for the graceful
    fallback path (when winsdk raises): we want a single stderr line
    on first failure, not 1Hz log spam.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.title_changed_at: float = 0.0
        self._has_logged_unavailable = False

    def update(self, full_title: str) -> None:
        """Record a freshly-read SMTC title. Updates prev_title +
        title_changed_at only when the value actually changed.
        """
        if not full_title:
            return
        with self._lock:
            if full_title != self.title:
                self.prev_title = self.title
                self.title = full_title
                self.title_changed_at = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "title_changed_at": self.title_changed_at,
            }


class TrackWindows:
    """TrackInfoBackend impl for Windows.

    Public surface (Phase 1 Protocol + macOS-impl parity):
    - ``is_available() -> bool`` — True iff winsdk imports successfully.
    - ``poll() -> NowPlayingSnapshot | None`` — synchronous best-effort
      poll. Bridges the async winsdk API via ``asyncio.run`` (CONTEXT
      Decision). Returns None when SMTC has no current session or
      raises.
    - ``track_info`` — exposes the internal ``_SmtcState`` instance so
      ``state_refresh_loop`` can call ``track_info.snapshot()`` and get
      the v4 dict shape directly (parity with macOS).
    - ``async run_poll_loop(stop_event)`` — 1Hz polling loop via
      ``run_in_executor`` (offloads the asyncio.run-inside-thread to a
      worker thread so the main event loop stays free).

    Critical Constraint 3: ``winsdk`` is imported only inside
    ``_poll_smtc_sync`` so importing this module on macOS does NOT pull
    winsdk into sys.modules.
    """

    def __init__(self):
        self._state = _SmtcState()
        # Alias for v4-shape consumers (state_refresh_loop reads via
        # ``.track_info.snapshot()`` in macOS — Windows must match).
        self.track_info = self._state

    # ---------- winsdk lazy-import availability check ----------

    def is_available(self) -> bool:
        """Lazy try-import the winsdk control module. Cached so subsequent
        calls don't re-pay the import cost."""
        try:
            import winsdk.windows.media.control  # noqa: F401

            return True
        except ImportError:
            return False

    # ---------- Sync executor target — the meat of the impl ----------

    def _poll_smtc_sync(self) -> str | None:
        """Synchronous SMTC poll — runs inside an executor thread.

        Bridges winsdk's awaitable API by spinning a private asyncio loop
        with ``asyncio.run`` (CONTEXT Decision §TrackWindows: matches the
        macOS ``subprocess.check_output`` pattern, no new event-loop
        machinery in the main thread).

        Returns the formatted f"{artist} - {title}" string (or the
        non-empty side, or None), or None when:
        - winsdk is not installed
        - SMTC has no current session
        - any exception was raised by winsdk (logged once)
        """
        try:
            import winsdk.windows.media.control as wmc
        except ImportError:
            return None

        async def _inner():
            mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = mgr.get_current_session()
            if session is None:
                return None
            props = await session.try_get_media_properties_async()
            artist = (props.artist or "").strip()
            title = (props.title or "").strip()
            if artist and title:
                return f"{artist} - {title}"
            return artist or title or None

        try:
            return asyncio.run(_inner())
        except Exception as e:
            # Log once, then stay silent — 1Hz log spam is unhelpful.
            if not self._state._has_logged_unavailable:
                print(f"-> SMTC unavailable: {e}", file=sys.stderr)
                self._state._has_logged_unavailable = True
            return None

    # ---------- Phase 1 Protocol surface ----------

    def poll(self) -> NowPlayingSnapshot | None:
        """Synchronous best-effort poll. Returns a NowPlayingSnapshot or
        None.

        macOS-impl parity: when a title is resolved, ``artist`` field is
        None — the combined ``f"{artist} - {title}"`` string lives in
        ``title`` (state_refresh_loop reads it that way).
        """
        full = self._poll_smtc_sync()
        if not full:
            return None
        self._state.update(full)
        return NowPlayingSnapshot(
            title=full,
            artist=None,
            album=None,
            duration_sec=None,
            position_sec=None,
        )

    async def run_poll_loop(self, stop_event: asyncio.Event) -> None:
        """1Hz polling loop, offloads the blocking ``_poll_smtc_sync`` via
        ``run_in_executor``. Mirrors ``TrackMacOS.run_poll_loop``.

        Stops cooperatively when ``stop_event`` is set.
        """
        loop = asyncio.get_running_loop()
        while not stop_event.is_set():
            try:
                full = await loop.run_in_executor(None, self._poll_smtc_sync)
                if full:
                    self._state.update(full)
            except Exception as e:
                print(f"[track poll err] {e}", file=sys.stderr)
            await asyncio.sleep(1.0)


__all__ = ["TrackWindows"]
