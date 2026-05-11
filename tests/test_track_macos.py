# SPDX-License-Identifier: Apache-2.0
"""TrackMacOS tests — mocked subprocess.check_output.

Exercises the two-line parse (title + artist), the four catch-all error modes,
the legacy v4 dict-shape snapshot, the Phase 1 NowPlayingSnapshot Protocol
conversion, and isinstance(TrackInfoBackend).
"""

from __future__ import annotations

import subprocess

import pytest

from vibemix.platform import NowPlayingSnapshot, TrackInfoBackend, TrackMacOS
from vibemix.platform._track_macos import TrackInfo


def test_track_macos_satisfies_protocol():
    assert isinstance(TrackMacOS(), TrackInfoBackend) is True


def test_track_info_parses_title_and_artist(mocker):
    mocker.patch(
        "vibemix.platform._track_macos.subprocess.check_output",
        return_value=b"Around the World\nDaft Punk\n",
    )
    mocker.patch("vibemix.platform._track_macos.time.time", return_value=1000.0)
    ti = TrackInfo()
    ti.poll_once()
    snap = ti.snapshot()
    assert snap["title"] == "Daft Punk - Around the World"
    assert snap["prev_title"] == ""
    assert snap["title_changed_at"] == 1000.0


def test_track_info_parses_title_only_when_artist_missing(mocker):
    """`f'{artist} - {title}' if (artist and title) else title` — empty
    artist falls through to title-only."""
    mocker.patch(
        "vibemix.platform._track_macos.subprocess.check_output",
        return_value=b"Around the World\n\n",
    )
    ti = TrackInfo()
    ti.poll_once()
    snap = ti.snapshot()
    assert snap["title"] == "Around the World"


def test_track_info_records_prev_on_change(mocker):
    mock_run = mocker.patch("vibemix.platform._track_macos.subprocess.check_output")
    mocker.patch("vibemix.platform._track_macos.time.time", return_value=1000.0)

    mock_run.return_value = b"First\nDP\n"
    ti = TrackInfo()
    ti.poll_once()
    assert ti.snapshot()["title"] == "DP - First"

    mock_run.return_value = b"Second\nDP\n"
    ti.poll_once()
    snap = ti.snapshot()
    assert snap["title"] == "DP - Second"
    assert snap["prev_title"] == "DP - First"


def test_track_info_no_change_skips_update(mocker):
    mock_run = mocker.patch("vibemix.platform._track_macos.subprocess.check_output")
    mocker.patch("vibemix.platform._track_macos.time.time", return_value=1000.0)
    mock_run.return_value = b"First\nDP\n"
    ti = TrackInfo()
    ti.poll_once()
    first_ts = ti.snapshot()["title_changed_at"]

    mocker.patch("vibemix.platform._track_macos.time.time", return_value=1010.0)
    ti.poll_once()
    # Title unchanged → title_changed_at NOT updated.
    assert ti.snapshot()["title_changed_at"] == first_ts


@pytest.mark.parametrize(
    "exc",
    [
        subprocess.TimeoutExpired(cmd="nowplaying-cli", timeout=1.5),
        subprocess.CalledProcessError(returncode=1, cmd="nowplaying-cli"),
        FileNotFoundError("not found"),
        OSError("os error"),
    ],
)
def test_track_info_swallows_subprocess_errors(mocker, exc):
    """v4:550-551 catch list — all four error modes silently no-op."""
    mocker.patch(
        "vibemix.platform._track_macos.subprocess.check_output",
        side_effect=exc,
    )
    ti = TrackInfo()
    # Should not raise.
    ti.poll_once()
    assert ti.snapshot()["title"] == ""  # unchanged from default


def test_track_macos_poll_returns_nowplaying_snapshot(mocker):
    mocker.patch(
        "vibemix.platform._track_macos.subprocess.check_output",
        return_value=b"Around the World\nDaft Punk\n",
    )
    t = TrackMacOS()
    snap = t.poll()
    assert isinstance(snap, NowPlayingSnapshot)
    assert snap.title == "Daft Punk - Around the World"
    # album/duration/position always None for `get title artist`.
    assert snap.album is None
    assert snap.duration_sec is None
    assert snap.position_sec is None


def test_track_macos_poll_returns_none_when_unavailable(mocker):
    """No title resolved → poll() returns None."""
    mocker.patch(
        "vibemix.platform._track_macos.subprocess.check_output",
        side_effect=FileNotFoundError("not found"),
    )
    t = TrackMacOS()
    assert t.poll() is None


def test_track_macos_is_available_when_cli_exists(mocker):
    mocker.patch("vibemix.platform._track_macos.Path.is_file", return_value=True)
    assert TrackMacOS().is_available() is True


def test_track_macos_is_unavailable_when_cli_missing(mocker):
    mocker.patch("vibemix.platform._track_macos.Path.is_file", return_value=False)
    assert TrackMacOS().is_available() is False


def test_track_macos_exposes_track_info_for_state_refresh_loop():
    """state_refresh_loop reads via track_info.snapshot() (v4 dict shape).
    The wrapper must expose the TrackInfo instance."""
    t = TrackMacOS()
    assert isinstance(t.track_info, TrackInfo)
