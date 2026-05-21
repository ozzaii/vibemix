# SPDX-License-Identifier: Apache-2.0
"""Phase 59 (DECK-01) — DeckTrack / DeckState honest-default model.

Pins the "typed empties on absence, no false-confident key by construction"
contract (mirrors library.rekordbox.TrackEntry's bpm=0.0-not-None shape):

- DeckTrack() defaults: source="unknown", every harmonic field None/0.0 — a
  default deck reads as honest unknown, never a fabricated key.
- DeckState() defaults: decks={} (empty), updated_at=0.0.
- MusicState().deck_state is an empty DeckState — an empty MusicState produces
  zero deck output anywhere (golden-equivalence; see
  test_coach_prompt_grounding.py for the evidence_line byte-identity proof).
"""

from __future__ import annotations

from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.music_state import MusicState


def test_deck_track_defaults_are_honest_unknown():
    """A bare DeckTrack carries NO key/camelot/bpm/energy and source='unknown'
    — there is no false-confident default key by construction."""
    dt = DeckTrack()
    assert dt.title is None
    assert dt.track_id is None
    assert dt.bpm == 0.0
    assert dt.key is None
    assert dt.camelot is None
    assert dt.open_key is None
    assert dt.energy is None
    assert dt.loaded_at == 0.0
    assert dt.confidence == 0.0
    assert dt.source == "unknown"


def test_deck_track_accepts_resolved_values():
    """A populated DeckTrack carries the resolved fields (raw tag + camelot)."""
    dt = DeckTrack(
        title="Strobe",
        track_id="42",
        bpm=128.0,
        key="Am",
        camelot="8A",
        open_key="1m",
        energy=7,
        loaded_at=12.5,
        confidence=0.8,
        source="rekordbox_xml",
    )
    assert dt.title == "Strobe"
    assert dt.track_id == "42"
    assert dt.bpm == 128.0
    assert dt.key == "Am"
    assert dt.camelot == "8A"
    assert dt.open_key == "1m"
    assert dt.energy == 7
    assert dt.loaded_at == 12.5
    assert dt.confidence == 0.8
    assert dt.source == "rekordbox_xml"


def test_deck_state_defaults_empty():
    """A bare DeckState holds an empty decks dict and updated_at=0.0."""
    ds = DeckState()
    assert ds.decks == {}
    assert ds.updated_at == 0.0


def test_deck_state_decks_is_per_instance():
    """default_factory=dict — two DeckState instances do NOT share the dict
    (the classic mutable-default footgun)."""
    a = DeckState()
    b = DeckState()
    a.decks["A"] = DeckTrack()
    assert b.decks == {}


def test_music_state_carries_empty_deck_state():
    """MusicState().deck_state is an empty DeckState — additive, default-empty,
    so an empty MusicState produces zero deck output anywhere."""
    m = MusicState()
    assert isinstance(m.deck_state, DeckState)
    assert m.deck_state.decks == {}
    assert m.deck_state.updated_at == 0.0


def test_music_state_deck_state_is_per_instance():
    """Two MusicState instances get independent deck_state holders (no shared
    mutable default leaking across the single source of truth)."""
    m1 = MusicState()
    m2 = MusicState()
    m1.deck_state.decks["A"] = DeckTrack(title="x")
    assert m2.deck_state.decks == {}
