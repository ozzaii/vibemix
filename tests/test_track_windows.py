# SPDX-License-Identifier: Apache-2.0
"""TrackWindows tests — mocked winsdk.windows.media.control surface.

Pins:
- Module imports cleanly on macOS without pulling winsdk into sys.modules
  (Critical Constraint 3: winsdk lives only inside method bodies).
- TrackWindows() structurally satisfies TrackInfoBackend Protocol.
- poll() bridges winsdk's awaitable API via asyncio.run inside a sync
  executor (CONTEXT Decision: matches macOS subprocess pattern, no new
  event-loop machinery).
- SMTC title parsing: artist + title → "{artist} - {title}"; artist-only
  or title-only fall through to the non-empty value; both empty → None.
- Graceful fallback: no current session → None; winsdk raises → None +
  logs ONCE on first failure (no log spam).

Patched surfaces:
- ``winsdk`` packages injected via ``monkeypatch.setitem(sys.modules,
  "winsdk", fake)`` plus its submodule chain
  (``winsdk.windows``, ``winsdk.windows.media``,
  ``winsdk.windows.media.control``) — the lazy import inside the executor
  thread resolves to the fake.
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import MagicMock

import pytest

from vibemix.platform import NowPlayingSnapshot, TrackInfoBackend
from vibemix.platform._track_windows import TrackWindows


# ---------- Module import discipline ----------


def test_module_imports_on_macos_without_pulling_winsdk():
    """Critical Constraint 3 — importing _track_windows must NOT add
    winsdk to sys.modules. Lazy-import discipline mirror of _screen_windows."""
    assert "winsdk" not in sys.modules


# ---------- Protocol satisfaction ----------


def _install_fake_winsdk(monkeypatch, *, session_or_none, raise_on_request=False):
    """Inject a fake ``winsdk.windows.media.control`` module into sys.modules.

    ``session_or_none`` — either None (simulates no current SMTC session)
    or a MagicMock acting as the GlobalSystemMediaTransportControlsSession.

    ``raise_on_request`` — when True, the manager's ``request_async`` raises
    RuntimeError, exercising the graceful-fallback path.

    Returns the fake control module (so tests can assert on call counts).
    """
    # Build a futures-friendly "awaitable" — winsdk uses asyncio-compatible
    # awaitables under the hood. asyncio.run can await coroutines OR
    # futures-with-an-event-loop; here we wrap return values in coroutines
    # so `await mgr.request_async()` works.
    fake_control = types.ModuleType("winsdk.windows.media.control")

    if raise_on_request:

        async def _request_async():
            raise RuntimeError("SMTC unavailable for test")

    else:

        async def _request_async():
            mgr = MagicMock()
            mgr.get_current_session.return_value = session_or_none
            return mgr

    fake_manager_cls = MagicMock()
    fake_manager_cls.request_async = _request_async
    fake_control.GlobalSystemMediaTransportControlsSessionManager = fake_manager_cls

    # Assemble the parent module chain so ``import winsdk.windows.media.control``
    # works under Python's import machinery (parent modules must exist).
    fake_winsdk = types.ModuleType("winsdk")
    fake_windows = types.ModuleType("winsdk.windows")
    fake_media = types.ModuleType("winsdk.windows.media")
    fake_winsdk.windows = fake_windows
    fake_windows.media = fake_media
    fake_media.control = fake_control

    monkeypatch.setitem(sys.modules, "winsdk", fake_winsdk)
    monkeypatch.setitem(sys.modules, "winsdk.windows", fake_windows)
    monkeypatch.setitem(sys.modules, "winsdk.windows.media", fake_media)
    monkeypatch.setitem(sys.modules, "winsdk.windows.media.control", fake_control)
    return fake_control


def _make_session_with_props(artist: str, title: str):
    """Build a MagicMock SMTC session whose ``try_get_media_properties_async``
    resolves to an object with .artist + .title."""
    session = MagicMock()
    props = MagicMock()
    props.artist = artist
    props.title = title

    async def _try_get_media_properties_async():
        return props

    session.try_get_media_properties_async = _try_get_media_properties_async
    return session


def test_track_windows_satisfies_protocol():
    """structural Protocol satisfaction — exposes is_available + poll."""
    assert isinstance(TrackWindows(), TrackInfoBackend) is True


# ---------- poll() — SMTC parsing ----------


def test_poll_returns_snapshot_when_smtc_has_session(monkeypatch):
    """Happy path: SMTC session exists with artist + title → poll()
    returns a NowPlayingSnapshot whose title is "{artist} - {title}"."""
    session = _make_session_with_props("Daft Punk", "One More Time")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    snap = TrackWindows().poll()
    assert isinstance(snap, NowPlayingSnapshot)
    assert snap.title == "Daft Punk - One More Time"
    # macOS-impl parity: artist is None (combined in title); album/duration/
    # position always None for SMTC's title+artist surface.
    assert snap.artist is None
    assert snap.album is None
    assert snap.duration_sec is None
    assert snap.position_sec is None


def test_poll_returns_none_when_no_current_session(monkeypatch):
    """``get_current_session()`` returns None → poll() returns None."""
    _install_fake_winsdk(monkeypatch, session_or_none=None)
    assert TrackWindows().poll() is None


def test_poll_returns_none_when_winsdk_raises(monkeypatch, capsys):
    """If ``request_async`` raises (SMTC unavailable on the box), poll() must
    return None — graceful fallback, no exception propagates. Logs ONCE."""
    _install_fake_winsdk(monkeypatch, session_or_none=None, raise_on_request=True)
    t = TrackWindows()
    assert t.poll() is None
    # Second call must also return None and must NOT log again (log-once flag).
    assert t.poll() is None
    captured = capsys.readouterr()
    # The "SMTC unavailable" message must appear at most once across the two calls.
    assert captured.err.count("SMTC unavailable") <= 1


def test_poll_returns_artist_only_when_title_empty(monkeypatch):
    """artist="Foo", title="" → snapshot.title == "Foo" (artist-only fallback)."""
    session = _make_session_with_props("Foo", "")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    snap = TrackWindows().poll()
    assert snap is not None
    assert snap.title == "Foo"


def test_poll_returns_title_only_when_artist_empty(monkeypatch):
    """artist="", title="Bar" → snapshot.title == "Bar" (title-only fallback)."""
    session = _make_session_with_props("", "Bar")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    snap = TrackWindows().poll()
    assert snap is not None
    assert snap.title == "Bar"


def test_poll_returns_none_when_both_empty(monkeypatch):
    """artist="" + title="" → no resolvable title → poll() returns None."""
    session = _make_session_with_props("", "")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    assert TrackWindows().poll() is None


# ---------- is_available() ----------


def test_is_available_true_when_winsdk_mocked(monkeypatch):
    """is_available() returns True when winsdk imports successfully."""
    _install_fake_winsdk(monkeypatch, session_or_none=None)
    assert TrackWindows().is_available() is True


def test_is_available_false_when_winsdk_missing(monkeypatch):
    """When winsdk import fails → is_available() False (graceful fallback)."""
    # Drop any prior winsdk entries and block re-import.
    for k in list(sys.modules):
        if k == "winsdk" or k.startswith("winsdk."):
            monkeypatch.delitem(sys.modules, k, raising=False)

    class _Blocker:
        def find_spec(self, name, _path=None, _target=None):
            if name == "winsdk" or name.startswith("winsdk."):
                raise ImportError("blocked for test")
            return None

    monkeypatch.setattr(sys, "meta_path", [_Blocker(), *sys.meta_path])
    assert TrackWindows().is_available() is False


# ---------- Internal _SmtcState v4 dict-shape parity ----------


def test_track_info_exposes_v4_dict_snapshot(monkeypatch):
    """state_refresh_loop reads track_info.snapshot() in the v4 dict shape
    {title, prev_title, title_changed_at} regardless of OS. TrackWindows
    must expose a ``track_info`` alias that returns this shape."""
    session = _make_session_with_props("Artist", "Track")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    t = TrackWindows()
    # Wire a poll first so state populates.
    t.poll()
    snap = t.track_info.snapshot()
    assert isinstance(snap, dict)
    assert set(snap.keys()) == {"title", "prev_title", "title_changed_at"}
    assert snap["title"] == "Artist - Track"
    assert snap["prev_title"] == ""


def test_track_info_records_prev_on_change(monkeypatch):
    """When the SMTC title changes, _SmtcState records the previous one and
    updates title_changed_at — same contract as macOS TrackInfo."""
    # First poll: "Artist1 - First"
    session1 = _make_session_with_props("Artist1", "First")
    _install_fake_winsdk(monkeypatch, session_or_none=session1)
    t = TrackWindows()
    t.poll()
    assert t.track_info.snapshot()["title"] == "Artist1 - First"

    # Second poll: change to "Artist1 - Second" — prev should update.
    session2 = _make_session_with_props("Artist1", "Second")
    _install_fake_winsdk(monkeypatch, session_or_none=session2)
    t.poll()
    snap = t.track_info.snapshot()
    assert snap["title"] == "Artist1 - Second"
    assert snap["prev_title"] == "Artist1 - First"


# ---------- async run_poll_loop semantics ----------


def test_run_poll_loop_offloads_via_executor_and_stops_on_event(monkeypatch):
    """run_poll_loop wraps the sync _poll_smtc_sync via run_in_executor at
    1Hz. When stop_event is set, the loop exits cleanly. We verify by
    running one iteration with a very short sleep monkeypatch."""
    session = _make_session_with_props("A", "B")
    _install_fake_winsdk(monkeypatch, session_or_none=session)

    async def _runner():
        t = TrackWindows()
        stop = asyncio.Event()

        # Patch the loop sleep so the test doesn't wait 1s per iteration.
        original_sleep = asyncio.sleep

        async def _short_sleep(_secs):
            await original_sleep(0)

        monkeypatch.setattr("vibemix.platform._track_windows.asyncio.sleep", _short_sleep)

        # Schedule a stop after a tiny delay so the loop body runs at least once.
        async def _set_stop():
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            stop.set()

        await asyncio.gather(t.run_poll_loop(stop), _set_stop())
        return t

    t = asyncio.run(_runner())
    snap = t.track_info.snapshot()
    assert snap["title"] == "A - B"


def test_poll_is_sync_method():
    """poll() is a synchronous method (Phase 1 Protocol contract: blocking
    + offload to executor by caller). It must NOT be a coroutine."""
    t = TrackWindows()
    # Calling poll() should NOT return a coroutine.
    import inspect

    assert not inspect.iscoroutinefunction(t.poll)
