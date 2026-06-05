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
    LAST_KNOWN_CONTEXT_CONF,
    NOWPLAYING_PLAYBACK_CONF,
    XML_CONF_FLOOR,
    DeckPoller,
)
from vibemix.state.deck_state import DeckTrack

# ---------------------------------------------------------------------- #
# Test fixtures — a tiny in-memory RekordboxLibrary (no XML parse, no DB) #
# ---------------------------------------------------------------------- #


def _entry(
    track_id: str,
    title: str,
    *,
    artist: str = "Artist",
    key: str = "Am",
    bpm: float = 128.0,
    filepath: str = "",
    genre: str = "",
    key_source: str = "",
    bpm_source: str = "",
) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist=artist,
        album="",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=filepath,
        genre=genre,
        key_source=key_source,
        bpm_source=bpm_source,
    )


def _lib(*entries: TrackEntry) -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {e.track_id: e for e in entries}
    lib.xml_path = "/tmp/collection.xml"
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


class _FakeActivityController(_FakeController):
    def __init__(self, snap: dict, activity: dict[str, object]):
        super().__init__(snap)
        self._activity = activity

    def activity_snapshot(self) -> dict[str, object]:
        return self._activity


class _FakeTrackInfo:
    def __init__(
        self,
        title: str = "",
        *,
        client_bundle_id: str | None = None,
        position_sec: float | None = None,
        playback_rate: float = 1.0,
    ):
        self._title = title
        self._client_bundle_id = client_bundle_id
        self._position_sec = position_sec
        self._playback_rate = playback_rate

    def snapshot(self) -> dict:
        return {
            "title": self._title,
            "prev_title": "",
            "title_changed_at": 0.0,
            "client_bundle_id": self._client_bundle_id,
            "position_sec": self._position_sec,
            "playback_rate": self._playback_rate,
        }


class _MutableController:
    def __init__(self, snap: dict):
        self.snap = snap

    def deck_snapshot(self) -> dict:
        return self.snap


class _MutableTrackInfo:
    def __init__(self, title: str):
        self.title = title

    def snapshot(self) -> dict:
        return {
            "title": self.title,
            "prev_title": "",
            "title_changed_at": 0.0,
            "client_bundle_id": "com.pioneerdj.rekordbox",
        }


# ---------------------------------------------------------------------- #
# Shape + read-only producer contract                                     #
# ---------------------------------------------------------------------- #


def test_snapshot_returns_dict_of_decktrack():
    p = DeckPoller(
        library=_lib(), controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo()
    )
    snap = p.snapshot()
    assert isinstance(snap, dict)
    assert all(isinstance(v, DeckTrack) for v in snap.values())


def test_poller_has_own_lock():
    p = DeckPoller(
        library=_lib(), controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo()
    )
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


def test_xml_match_carries_source_genre_metadata():
    lib = _lib(_entry("1", "Strobe", genre="psytrance"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap(vol_a=127, vol_b=0, xfader=0)),
        track_info=_FakeTrackInfo("Strobe"),
    )

    p.poll_once()

    assert p.snapshot()["A"].genre == "psytrance"


def test_folder_cache_match_carries_folder_source(tmp_path):
    lib = _lib(_entry("folder:abc", "Strobe", key="", bpm=0.0))
    lib.xml_path = str(tmp_path)
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Strobe"),
    )

    p.poll_once()

    assert p.snapshot()["A"].source == "folder_cache"


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


def test_nowplaying_artist_title_resolves_against_rekordbox_title_and_artist():
    """TrackInfo emits "Artist - Title"; cached Rekordbox rows store fields separately."""
    lib = _lib(_entry("1", "Strobe", artist="Deadmau5", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Deadmau5 - Strobe"),
    )

    p.poll_once()

    snap = p.snapshot()
    assert "A" in snap
    assert snap["A"].track_id == "1"
    assert snap["A"].source == "rekordbox_xml"


def test_non_deck_nowplaying_source_does_not_resolve_deck_identity():
    """A browser/global player title must not become a deck identity."""
    lib = _lib(_entry("1", "Strobe", artist="Deadmau5", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.apple.WebKit.GPU",
        ),
    )

    p.poll_once()

    assert p.snapshot() == {}
    status = p.source_snapshot()
    assert status["library"] == "present"
    assert status["library_tracks"] == "1"
    assert status["library_source"] == "rekordbox_xml"
    assert status["library_match"] == "not_attempted_non_deck_nowplaying"
    assert status["nowplaying"] == "blocked_non_deck_owner"
    assert status["nowplaying_owner"] == "com.apple.webkit.gpu"
    assert status["resolution"] == "blocked_non_deck_nowplaying"
    assert status["screen_vision"] == "disabled"


def test_controller_connection_status_distinguishes_disconnected_controller():
    """`controller=present` means the reader is wired, not that hardware is live."""
    p = DeckPoller(
        library=_lib(_entry("1", "Strobe")),
        controller=_FakeController(_ctrl_snap(connected=False)),
        track_info=_FakeTrackInfo("Strobe"),
    )

    p.poll_once()

    assert p.snapshot() == {}
    status = p.source_snapshot()
    assert status["controller"] == "present"
    assert status["controller_connection"] == "disconnected"
    assert status["resolution"] == "no_single_attributable_deck"


def test_source_status_distinguishes_visible_controller_with_no_midi_traffic():
    """A connected port with zero frames is a setup state, not proof of deck moves."""
    p = DeckPoller(
        library=_lib(_entry("1", "Strobe")),
        controller=_FakeActivityController(
            _ctrl_snap(connected=True),
            {
                "connected": True,
                "messages_seen_total": 0,
                "events_seen_total": 0,
                "moves_seen_total": 0,
            },
        ),
        track_info=_FakeTrackInfo("Strobe"),
    )

    p.poll_once()

    status = p.source_snapshot()
    assert status["controller_connection"] == "connected"
    assert status["controller_midi_activity"] == "connected_no_midi_traffic"
    assert status["controller_midi_messages"] == "0"
    assert status["controller_midi_events"] == "0"
    assert status["controller_midi_moves"] == "0"


def test_nowplaying_playback_seeds_deck_when_controller_has_no_midi_motion():
    """A DJ-app nowplaying title can seed receipts without becoming citable deck proof."""
    p = DeckPoller(
        library=_lib(_entry("1", "Strobe", artist="Deadmau5", key="Am")),
        controller=_FakeActivityController(
            _ctrl_snap(vol_a=0, vol_b=0, xfader=64, connected=True),
            {
                "connected": True,
                "messages_seen_total": 0,
                "events_seen_total": 0,
                "moves_seen_total": 0,
            },
        ),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.pioneerdj.rekordbox",
            position_sec=42.0,
            playback_rate=1.0,
        ),
    )

    p.poll_once()

    snap = p.snapshot()
    assert snap["A"].track_id == "1"
    assert snap["A"].confidence == pytest.approx(NOWPLAYING_PLAYBACK_CONF)
    assert snap["A"].confidence < DECK_CITE_MIN_CONF
    status = p.source_snapshot()
    assert status["audible_deck"] == "A"
    assert status["audible_deck_source"] == "nowplaying_playback"
    assert status["nowplaying_playback"] == "playing"
    assert status["resolution"] == "nowplaying_playback_library_match"
    assert status["resolved_side_rule"] == "nominal_nowplaying_seed_not_physical_deck_proof"
    assert status["controller_midi_activity"] == "connected_no_midi_traffic"


def test_audio_estimated_key_does_not_become_live_deck_proof():
    """Offline K-S keys can score suggestions, but they are not citable deck tags."""
    lib = _lib(
        _entry(
            "1",
            "Strobe",
            artist="Deadmau5",
            key="Am",
            key_source="numpy_ks",
        )
    )
    p = DeckPoller(
        library=lib,
        controller=_FakeActivityController(
            _ctrl_snap(vol_a=0, vol_b=0, xfader=64, connected=True),
            {
                "connected": True,
                "messages_seen_total": 0,
                "events_seen_total": 0,
                "moves_seen_total": 0,
            },
        ),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.pioneerdj.rekordbox",
            position_sec=12.0,
            playback_rate=1.0,
        ),
    )

    p.poll_once()

    decks = p.snapshot()
    assert decks["A"].track_id == "1"
    assert decks["A"].key is None
    assert decks["A"].camelot is None


def test_audio_estimated_bpm_does_not_become_live_deck_proof():
    """Offline BPM can score Viber sets, but it is not a citable live deck tag."""
    lib = _lib(
        _entry(
            "1",
            "Strobe",
            artist="Deadmau5",
            bpm=138.0,
            bpm_source="kick_ac",
        )
    )
    p = DeckPoller(
        library=lib,
        controller=_FakeActivityController(
            _ctrl_snap(vol_a=0, vol_b=0, xfader=64, connected=True),
            {
                "connected": True,
                "messages_seen_total": 0,
                "events_seen_total": 0,
                "moves_seen_total": 0,
            },
        ),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.pioneerdj.rekordbox",
            position_sec=12.0,
            playback_rate=1.0,
        ),
    )

    p.poll_once()

    decks = p.snapshot()
    assert decks["A"].track_id == "1"
    assert decks["A"].bpm == 0.0


def test_nowplaying_playback_fallback_requires_active_position():
    p = DeckPoller(
        library=_lib(_entry("1", "Strobe", artist="Deadmau5", key="Am")),
        controller=_FakeController(_ctrl_snap(vol_a=0, vol_b=0, xfader=64, connected=True)),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.pioneerdj.rekordbox",
            position_sec=None,
            playback_rate=1.0,
        ),
    )

    p.poll_once()

    assert p.snapshot() == {}
    assert p.source_snapshot()["resolution"] == "no_single_attributable_deck"


def test_dj_nowplaying_source_can_resolve_deck_identity():
    lib = _lib(_entry("1", "Strobe", artist="Deadmau5", key="Am"))
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo(
            "Deadmau5 - Strobe",
            client_bundle_id="com.pioneerdj.rekordbox",
        ),
    )

    p.poll_once()

    assert p.snapshot()["A"].track_id == "1"
    status = p.source_snapshot()
    assert status["controller_connection"] == "connected"
    assert status["nowplaying"] == "deck_candidate"
    assert status["library_match"] == "matched"
    assert status["resolution"] == "library_match"
    assert status["resolved_side"] == "A"
    assert status["second_deck_source"] == "suppressed_requires_independent_source"


def test_ambiguous_bare_title_abstains_but_artist_title_disambiguates():
    lib = _lib(
        _entry("1", "Strobe", artist="Deadmau5", key="Am"),
        _entry("2", "Strobe", artist="Other Artist", key="Em"),
    )
    ambiguous = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Strobe"),
    )
    disambiguated = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Deadmau5 - Strobe"),
    )

    ambiguous.poll_once()
    disambiguated.poll_once()

    assert ambiguous.snapshot() == {}
    assert disambiguated.snapshot()["A"].track_id == "1"
    assert ambiguous.source_snapshot()["library_match"] == "ambiguous_label"
    assert ambiguous.source_snapshot()["resolution"] == "library_miss"
    assert disambiguated.source_snapshot()["library_match"] == "matched"


def test_nowplaying_filename_stem_resolves_folder_cache_row(tmp_path):
    lib = _lib(
        _entry(
            "folder:1",
            "Clean Metadata Title",
            artist="",
            filepath=str(tmp_path / "Rave Tool 01.wav"),
        )
    )
    lib.xml_path = str(tmp_path)
    p = DeckPoller(
        library=lib,
        controller=_FakeController(_ctrl_snap()),
        track_info=_FakeTrackInfo("Rave Tool 01"),
    )

    p.poll_once()

    snap = p.snapshot()
    assert snap["A"].track_id == "folder:1"
    assert snap["A"].source == "folder_cache"


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


def test_previous_deck_identity_returns_as_last_known_context_not_proof():
    """A previously resolved deck can ride as context, but never as citable proof."""
    lib = _lib(
        _entry("1", "Strobe", key="Am"),
        _entry("2", "Signal", key="Em"),
    )
    controller = _MutableController(_ctrl_snap(vol_a=127, vol_b=0, xfader=0))
    track_info = _MutableTrackInfo("Strobe")
    p = DeckPoller(library=lib, controller=controller, track_info=track_info)

    p.poll_once()
    assert p.snapshot()["A"].track_id == "1"

    controller.snap = _ctrl_snap(vol_a=0, vol_b=127, xfader=127)
    track_info.title = "Signal"
    p.poll_once()
    snap = p.snapshot()

    assert snap["B"].track_id == "2"
    assert snap["B"].source == "rekordbox_xml"
    assert snap["A"].track_id == "1"
    assert snap["A"].source == "last_known"
    assert snap["A"].confidence == pytest.approx(LAST_KNOWN_CONTEXT_CONF)
    assert snap["A"].confidence < DECK_CITE_MIN_CONF
    status = p.source_snapshot()
    assert status["last_known_sides"] == "A"
    assert status["last_known_rule"] == "context_only_not_current_identity_proof"
    assert status["second_deck_source"] == "suppressed_requires_independent_source"


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
    p = DeckPoller(
        library=None, controller=_FakeController(_ctrl_snap()), track_info=_FakeTrackInfo("X")
    )
    p.poll_once()
    snap = p.snapshot()
    for dt in snap.values():
        assert dt.source != "rekordbox_xml"
    status = p.source_snapshot()
    assert status["library"] == "missing"
    assert status["library_tracks"] == "0"
    assert status["library_source"] == "none"
    assert status["library_match"] == "library_missing"
    assert status["resolution"] == "library_miss"


# ---------------------------------------------------------------------- #
# Confidence-floor constants are sane                                     #
# ---------------------------------------------------------------------- #


def test_cite_floor_constants_ordered():
    assert 0.0 < XML_CONF_FLOOR <= 1.0
    assert 0.0 < DECK_CITE_MIN_CONF <= 1.0
