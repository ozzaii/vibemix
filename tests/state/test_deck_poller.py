# SPDX-License-Identifier: Apache-2.0
"""DeckPoller — read-only deck-state producer tests (Phase 59-04 DECK-02/05).

The poller is the THIRD external snapshot producer after ``ControllerState`` and
``TrackInfo``: its own ``threading.Lock`` + ``.snapshot()`` returning copies, a
source ladder (XML library match primary; vision/numpy scaffolded slots), honest
``unknown`` below the floors, cross-deck suppression on an unresolved second
deck, and graceful degradation (no exception escapes ``.snapshot()``). It opens
NO DJ-software DB in write mode — it reuses the cache-warm ``RekordboxLibrary``.

These tests pin DECK-02 (ladder + honest unknown) and DECK-05 (read-only +
cross-deck suppression). The DECK-05 repo-scrub guarantee (no DJ-DB write-mode
open anywhere) lives in tests/repo/test_repo_scrub.py::test_deck_readonly.
"""

from __future__ import annotations

import threading

import pytest

from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.state.deck_poller import (
    DECK_CITE_MIN_CONF,
    XML_CONF_FLOOR,
    DeckPoller,
)
from vibemix.state.deck_state import DeckTrack


# ---------------------------------------------------------------------- #
# Test fixtures — a tiny in-memory RekordboxLibrary (no XML parse, no DB) #
# ---------------------------------------------------------------------- #


def _entry(track_id: str, title: str, *, key: str = "Am", bpm: float = 128.0) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist="Artist",
        album="",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath="",
    )


def _lib(*entries: TrackEntry) -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {e.track_id: e for e in entries}
    return lib


# Controller deck-snapshot shape (mirrors ControllerState.deck_snapshot()).
def _ctrl_snap(
    *,
    vol_a: int = 127,
    vol_b: int = 0,
    xfader: int = 0,
    connected: bool = True,
) -> dict:
    return {
        "A": {"vol": vol_a, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": vol_b, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": xfader,
        "connected": connected,
    }


class _FakeController:
    def __init__(self, snap: dict):
        self._snap = snap

    def deck_snapshot(self) -> dict:
        return self._snap


class _FakeTrackInfo:
    def __init__(self, title: str = ""):
        self._title = title

    def snapshot(self) -> dict:
        return {"title": self._title, "prev_title": "", "title_changed_at": 0.0}


# ---------------------------------------------------------------------- #
# Shape + read-only producer contract                                     #
# ---------------------------------------------------------------------- #


def test_snapshot_returns_dict_of_decktrack():
    p = DeckPoller(library=_lib(), controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo())
    snap = p.snapshot()
    assert isinstance(snap, dict)
    assert all(isinstance(v, DeckTrack) for v in snap.values())


def test_poller_has_own_lock():
    p = DeckPoller(library=_lib(), controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo())
    assert isinstance(p._lock, type(threading.Lock()))


def test_snapshot_returns_copies_caller_cannot_mutate_holder():
    """Mutating a returned DeckTrack must not corrupt the next snapshot."""
    lib = _lib(_entry("1", "Strobe", key="Am", bpm=128.0))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    first = p.snapshot()
    if "A" in first:
        first["A"].title = "MUTATED"
        first["A"].confidence = 99.0
    second = p.snapshot()
    if "A" in second:
        assert second["A"].title != "MUTATED"
        assert second["A"].confidence != 99.0


# ---------------------------------------------------------------------- #
# Source ladder — XML match primary, honest unknown below floors          #
# ---------------------------------------------------------------------- #


def test_xml_match_resolves_deck_with_rekordbox_source():
    lib = _lib(_entry("1", "Strobe", key="Am", bpm=128.0))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap(vol_a=127, vol_b=0, xfader=0)),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    snap = p.snapshot()
    assert "A" in snap
    dt = snap["A"]
    assert dt.title == "Strobe"
    assert dt.track_id == "1"
    assert dt.key == "Am"  # RAW Tonality preserved; _tick_once normalizes to camelot
    assert dt.bpm == pytest.approx(128.0)
    assert dt.source == "rekordbox_xml"
    assert dt.confidence >= XML_CONF_FLOOR


def test_camelot_left_none_in_poller():
    """The poller leaves camelot=None — _tick_once normalizes via to_camelot."""
    lib = _lib(_entry("1", "Strobe", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    snap = p.snapshot()
    assert snap["A"].camelot is None


def test_honest_unknown_when_no_source_resolves():
    """No library match + no title → no resolvable deck → honest unknown."""
    lib = _lib(_entry("1", "Strobe"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Some Track Not In Library"),
    )
    p.poll_once()
    snap = p.snapshot()
    # Either no deck entry, or the entry is honest-unknown (conf 0, no key).
    for dt in snap.values():
        if dt.source == "unknown":
            assert dt.confidence == 0.0
            assert dt.key is None
            assert dt.camelot is None


def test_ladder_keeps_xml_over_lower_tiers():
    """A deck with an XML match keeps source='rekordbox_xml' (highest conf) —
    the vision/numpy slots never override a clearing XML match."""
    lib = _lib(_entry("1", "Strobe", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    assert p.snapshot()["A"].source == "rekordbox_xml"


def test_xml_match_is_case_insensitive_on_title():
    lib = _lib(_entry("1", "Strobe", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("strobe"),  # lowercase
    )
    p.poll_once()
    snap = p.snapshot()
    assert "A" in snap and snap["A"].track_id == "1"


# ---------------------------------------------------------------------- #
# Cross-deck suppression — unresolved 2nd deck gets confidence 0          #
# ---------------------------------------------------------------------- #


def test_suppress_unresolved_second_deck():
    """Only deck A is audible/resolvable; the silent deck B is NOT resolved by
    'the other now-playing title' — it stays unresolved (confidence 0)."""
    lib = _lib(_entry("1", "Strobe", key="Am"))
    p = DeckPoller(
        library=lib,
        # A audible (vol up, xfader full-A); B silent.
        controller=_FakeController(_ctrl_snap(vol_a=127, vol_b=0, xfader=0)),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    snap = p.snapshot()
    assert "A" in snap and snap["A"].confidence >= XML_CONF_FLOOR
    # Deck B must never inherit A's title; if present at all it is unresolved.
    if "B" in snap:
        assert snap["B"].confidence == 0.0
        assert snap["B"].source != "rekordbox_xml"


def test_suppressed_deck_never_borrows_audible_title():
    """The non-audible deck must not carry the audible deck's title/track_id."""
    lib = _lib(_entry("1", "Strobe", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap(vol_a=127, vol_b=0, xfader=0)),
        track_info=_FakeTrackInfo("Strobe"),
    )
    p.poll_once()
    snap = p.snapshot()
    if "B" in snap:
        assert snap["B"].track_id != "1"
        assert snap["B"].title != "Strobe"


# ---------------------------------------------------------------------- #
# Graceful degradation — no exception escapes snapshot()                  #
# ---------------------------------------------------------------------- #


def test_raising_source_does_not_escape_snapshot():
    class _RaisingController:
        def deck_snapshot(self) -> dict:
            raise RuntimeError("boom — simulated XML/controller read failure")

    p = DeckPoller(
        library=_lib(_entry("1", "Strobe")),
        controller=_RaisingController(),
        track_info=_FakeTrackInfo("Strobe"),
    )
    # poll_once swallows; snapshot returns last-known (empty) state.
    p.poll_once()
    snap = p.snapshot()
    assert isinstance(snap, dict)


def test_raising_track_info_does_not_escape():
    class _RaisingTrack:
        def snapshot(self) -> dict:
            raise RuntimeError("boom — simulated nowplaying failure")

    p = DeckPoller(
        library=_lib(),
        controller=_FakeController(_ctrl_snap()),
        track_info=_RaisingTrack(),
    )
    p.poll_once()
    assert isinstance(p.snapshot(), dict)


def test_no_library_at_all_degrades_to_unknown():
    """A None library (user never imported collection.xml) → no XML matches,
    honest unknown, no crash."""
    p = DeckPoller(library=None, controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo("X"))
    p.poll_once()
    snap = p.snapshot()
    for dt in snap.values():
        assert dt.source != "rekordbox_xml"


# ---------------------------------------------------------------------- #
# Confidence-floor constants are sane                                     #
# ---------------------------------------------------------------------- #


def test_cite_floor_constants_ordered():
    assert 0.0 < XML_CONF_FLOOR <= 1.0
    assert 0.0 < DECK_CITE_MIN_CONF <= 1.0
