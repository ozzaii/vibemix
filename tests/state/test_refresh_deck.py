# SPDX-License-Identifier: Apache-2.0
"""_tick_once deck-state wiring tests (Phase 59-04 DECK-04).

These pin the single-writer integration of the deck poller:
- ``state.deck_state.decks`` is copied from ``deck_source.snapshot()`` ONLY
  inside the ``with state._lock:`` batch of ``_tick_once`` (single-writer).
- ``camelot`` is normalized via ``harmonics.to_camelot`` inside that lock.
- change-only, confidence-gated ``key:``/``track:`` registry writes (no spam).
- ``deck_source=None`` (default) leaves the deck path untouched — every existing
  direct ``_tick_once`` test still passes.
- a static single-writer grep invariant: ``deck_state.decks =`` is assigned only
  in refresh.py.
"""

from __future__ import annotations

import pathlib
import re
from unittest.mock import MagicMock

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.state import MusicState
from vibemix.state.deck_context import midi_evidence_key
from vibemix.state.deck_state import DeckTrack
from vibemix.state.refresh import _tick_once


def _audible_buf() -> AudioBuffer:
    buf = AudioBuffer(seconds=140.0, sr=16000)
    pcm = int16_sine(freq_hz=440.0, duration_sec=6.0, sample_rate=16000, amplitude=0.5)
    buf.push(pcm)
    return buf


def _ctrl_mock(connected: bool = True) -> MagicMock:
    m = MagicMock()
    m.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 0,
        "connected": connected,
    }
    m.moves_since.return_value = []
    return m


def _track_mock(title: str = "") -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"title": title, "prev_title": "", "title_changed_at": 0.0}
    return m


def _deck_source(decks: dict[str, DeckTrack]) -> MagicMock:
    """A fake deck source whose snapshot() returns the given DeckTrack map."""
    m = MagicMock()
    # Return fresh copies each call so _tick_once mutating camelot does not leak.
    def _snap():
        return {
            s: DeckTrack(
                title=d.title, track_id=d.track_id, bpm=d.bpm, key=d.key,
                camelot=d.camelot, open_key=d.open_key, energy=d.energy,
                loaded_at=d.loaded_at, confidence=d.confidence, source=d.source,
            )
            for s, d in decks.items()
        }
    m.snapshot.side_effect = _snap
    m.source_snapshot.return_value = {}
    return m


def _tick(
    state,
    *,
    deck_source=None,
    evidence_registry=None,
    now=1000.0,
    controller_state=None,
    evidence_dedupe=None,
):
    return _tick_once(
        state,
        _audible_buf(),
        controller_state or _ctrl_mock(),
        _track_mock(),
        now=now,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
        deck_source=deck_source,
        evidence_registry=evidence_registry,
        evidence_dedupe=evidence_dedupe,
    )


# ---------------------------------------------------------------------- #
# Single-writer copy + camelot normalization inside the lock              #
# ---------------------------------------------------------------------- #


def test_deck_snapshot_copied_into_state():
    state = MusicState()
    ds = _deck_source(
        {"A": DeckTrack(title="Strobe", track_id="1", key="Am", bpm=128.0, confidence=0.8, source="rekordbox_xml")}
    )
    _tick(state, deck_source=ds)
    assert "A" in state.deck_state.decks
    assert state.deck_state.decks["A"].title == "Strobe"
    assert state.deck_state.updated_at == 1000.0


def test_deck_source_status_copied_into_state():
    state = MusicState()
    ds = _deck_source({})
    ds.source_snapshot.return_value = {
        "nowplaying": "blocked_non_deck_owner",
        "nowplaying_owner": "com.apple.webkit.gpu",
        "resolution": "blocked_non_deck_nowplaying",
    }

    _tick(state, deck_source=ds)

    assert state.deck_state.source_status == {
        "nowplaying": "blocked_non_deck_owner",
        "nowplaying_owner": "com.apple.webkit.gpu",
        "resolution": "blocked_non_deck_nowplaying",
    }


def test_camelot_normalized_inside_tick():
    """The poller leaves camelot=None; _tick_once normalizes via to_camelot."""
    state = MusicState()
    ds = _deck_source(
        {"A": DeckTrack(title="Strobe", track_id="1", key="Am", camelot=None, bpm=128.0, confidence=0.8, source="rekordbox_xml")}
    )
    _tick(state, deck_source=ds)
    assert state.deck_state.decks["A"].camelot == "8A"  # Am -> 8A


def test_camelot_none_for_unrecognized_key():
    state = MusicState()
    ds = _deck_source(
        {"A": DeckTrack(title="X", track_id="1", key="not-a-key", bpm=128.0, confidence=0.8, source="rekordbox_xml")}
    )
    _tick(state, deck_source=ds)
    assert state.deck_state.decks["A"].camelot is None


def test_no_deck_source_leaves_deck_state_empty():
    """deck_source=None (default) → deck path untouched, deck_state stays empty."""
    state = MusicState()
    _tick(state, deck_source=None)
    assert state.deck_state.decks == {}


# ---------------------------------------------------------------------- #
# change-only, confidence-gated key:/track: registry writes               #
# ---------------------------------------------------------------------- #


def test_key_and_track_registry_writes_on_confident_deck():
    state = MusicState()
    reg = MagicMock()
    ds = _deck_source(
        {"A": DeckTrack(title="Strobe", track_id="42", key="Am", bpm=128.0, confidence=0.9, source="rekordbox_xml")}
    )
    _tick(state, deck_source=ds, evidence_registry=reg)
    writes = [c.args for c in reg.write.call_args_list]
    assert ("key", "A:8A") == writes_pick(writes, "key")
    assert ("track", "42") == writes_pick(writes, "track")


def writes_pick(writes, source):
    for args in writes:
        if len(args) >= 2 and args[0] == source:
            return (args[0], args[1])
    return None


def test_low_confidence_deck_no_key_write():
    """A deck below DECK_CITE_MIN_CONF gets NO key: write → uncitable."""
    state = MusicState()
    reg = MagicMock()
    ds = _deck_source(
        {"A": DeckTrack(title="Strobe", track_id="1", key="Am", bpm=128.0, confidence=0.2, source="screen_vision")}
    )
    _tick(state, deck_source=ds, evidence_registry=reg)
    key_writes = [c.args for c in reg.write.call_args_list if c.args and c.args[0] == "key"]
    assert key_writes == []


def test_change_only_no_duplicate_key_write_when_unchanged():
    """Same (side, camelot) across two ticks → only ONE key: write."""
    state = MusicState()
    reg = MagicMock()
    dt = DeckTrack(title="Strobe", track_id="1", key="Am", bpm=128.0, confidence=0.9, source="rekordbox_xml")
    ds = _deck_source({"A": dt})
    _tick(state, deck_source=ds, evidence_registry=reg, now=1000.0)
    _tick(state, deck_source=ds, evidence_registry=reg, now=1001.0)
    key_writes = [c.args for c in reg.write.call_args_list if c.args and c.args[0] == "key" and c.args[1] == "A:8A"]
    assert len(key_writes) == 1


def test_change_writes_again_when_camelot_changes():
    """A new (side, camelot) on a later tick DOES write again."""
    state = MusicState()
    reg = MagicMock()
    ds1 = _deck_source({"A": DeckTrack(title="Strobe", track_id="1", key="Am", bpm=128.0, confidence=0.9, source="rekordbox_xml")})
    ds2 = _deck_source({"A": DeckTrack(title="Other", track_id="2", key="Em", bpm=130.0, confidence=0.9, source="rekordbox_xml")})
    _tick(state, deck_source=ds1, evidence_registry=reg, now=1000.0)
    _tick(state, deck_source=ds2, evidence_registry=reg, now=1001.0)
    key_bodies = [c.args[1] for c in reg.write.call_args_list if c.args and c.args[0] == "key"]
    assert "A:8A" in key_bodies  # Am
    assert "A:9A" in key_bodies  # Em -> 9A


def test_registry_write_failure_does_not_kill_tick():
    """A raising registry.write must not propagate out of _tick_once."""
    state = MusicState()
    reg = MagicMock()
    reg.write.side_effect = RuntimeError("boom")
    ds = _deck_source({"A": DeckTrack(title="Strobe", track_id="1", key="Am", bpm=128.0, confidence=0.9, source="rekordbox_xml")})
    # Should NOT raise.
    _tick(state, deck_source=ds, evidence_registry=reg)
    assert "A" in state.deck_state.decks  # the copy still landed


def test_live_grounding_evidence_writes_move_route_and_audio_delta_once():
    state = MusicState(audible=True, set_start_at=990.0)
    state.prev_perceive = {
        "rms": 0.9,
        "sub": 0.9,
        "low": 0.9,
        "mid": 0.9,
        "high": 0.9,
        "onset_density": 9.0,
    }
    reg = MagicMock()
    dedupe: set[str] = set()
    ctrl = _ctrl_mock()
    ctrl.moves_since.side_effect = [
        [(0.4, "A_low: flat→killed (big twist)")],
        [(0.5, "A_low: flat→killed (big twist)")],
    ]

    _tick(state, evidence_registry=reg, controller_state=ctrl, evidence_dedupe=dedupe)
    first_delta = list(state.audio_delta)
    _tick(
        state,
        evidence_registry=reg,
        controller_state=ctrl,
        evidence_dedupe=dedupe,
        now=1000.1,
    )

    writes = [c.args for c in reg.write.call_args_list]
    move_key = midi_evidence_key("A_low: flat→killed (big twist)")
    assert ("midi", move_key, 9.6) in writes
    assert ("mix", "deck_audio_support=single_deck_A", 10.0) in writes
    assert first_delta
    assert any(args[0] == "mix" and str(args[1]).startswith("move_effect=") for args in writes)
    assert len([args for args in writes if args[:2] == ("midi", move_key)]) == 1


# ---------------------------------------------------------------------- #
# Single-writer invariant — deck_state.decks assigned only in refresh.py  #
# ---------------------------------------------------------------------- #


def test_deck_state_decks_assigned_only_in_refresh():
    src_root = pathlib.Path(__file__).resolve().parents[2] / "src" / "vibemix"
    offenders = []
    pat = re.compile(r"\.deck_state\.decks\s*=")
    for py in src_root.rglob("*.py"):
        if py.name == "refresh.py":
            continue
        text = py.read_text(encoding="utf-8")
        if pat.search(text):
            offenders.append(str(py.relative_to(src_root)))
    assert offenders == [], f"deck_state.decks assigned outside refresh.py: {offenders}"
