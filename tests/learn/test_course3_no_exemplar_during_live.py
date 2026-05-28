# SPDX-License-Identifier: Apache-2.0
"""Phase 96 Plan 03 — EXEMPLAR-06 active-session guard.

Pins the runtime guard that prevents exemplar playback while the
user is mid-set. Course 3 = verbal coaching only; exemplar audio
is restricted to between-set lessons. The guard sits in
``ExemplarPlayer.can_play``; the lesson runtime + state/refresh.py
cooperate to set ``state.session_active=True`` only during active
Course 3 lessons with at least one audible deck.

Truth table for the guard:

  session_active | audible_deck | can_play
  True           | "A"          | False  (mid-set, deck audible)
  True           | "B"          | False
  True           | "mix"        | False
  True           | "none"       | True   (between-track gap)
  False          | "A"          | True   (lens off, exemplar OK)
  False          | "none"       | True   (cold path)

REQ-ID: EXEMPLAR-06.
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from vibemix.learn.audio_cue import ExemplarPlayer
from vibemix.state.music_state import MusicState


def _make_player(state) -> ExemplarPlayer:
    # device_index=-1 is fine; we never invoke .play() with a real audio
    # path so no sd stream lands.
    return ExemplarPlayer(device_index=-1, state=state)


@pytest.mark.parametrize("audible_deck", ["A", "B", "mix"])
def test_guard_refuses_when_session_active_and_deck_audible(
    audible_deck: str,
) -> None:
    state = dataclasses.replace(
        MusicState(),
        session_active=True,
        audible_deck=audible_deck,
    )
    player = _make_player(state)
    assert player.can_play() is False, (
        f"EXEMPLAR-06 violation — exemplar playback permitted while "
        f"session_active=True AND audible_deck={audible_deck!r}"
    )


def test_guard_permits_when_session_active_but_silent() -> None:
    """Between-track gap during a Course 3 lesson — exemplar is fine."""
    state = dataclasses.replace(
        MusicState(),
        session_active=True,
        audible_deck="none",
    )
    player = _make_player(state)
    assert player.can_play() is True


def test_guard_permits_when_lens_off_even_if_deck_audible() -> None:
    """Lens off (NOT Course 3 active lesson) — exemplar permitted
    regardless of audible_deck. Between-lesson reviews / Course 1
    EQ-as-tutor playback is the use case."""
    state = dataclasses.replace(
        MusicState(),
        session_active=False,
        audible_deck="A",
    )
    player = _make_player(state)
    assert player.can_play() is True


def test_guard_permits_cold_path() -> None:
    """Default MusicState — cold path; lens off, deck silent. Always OK."""
    state = MusicState()
    player = _make_player(state)
    assert player.can_play() is True


def test_guard_accepts_duck_typed_state() -> None:
    """A duck-typed state object exposing the two attrs satisfies the guard.
    Mirrors the getattr-with-default contract from P93."""
    active = SimpleNamespace(session_active=True, audible_deck="A")
    inactive = SimpleNamespace(session_active=False, audible_deck="A")
    assert _make_player(active).can_play() is False
    assert _make_player(inactive).can_play() is True


def test_guard_defaults_when_state_lacks_fields() -> None:
    """A state object missing the fields is treated as default-False /
    default-'none' per the getattr fallback. Permits playback (safe
    default — the guard is a refuser, not a granter)."""
    bare = SimpleNamespace()  # no session_active, no audible_deck
    assert _make_player(bare).can_play() is True


def test_play_no_op_when_guard_refuses() -> None:
    """The existing audio_cue.py ``if not self.can_play(): return``
    guard short-circuits ``.play()`` into a no-op when can_play returns
    False. Verify by calling .play() under the guard — no stream
    attribute set, no exception raised."""
    state = dataclasses.replace(
        MusicState(),
        session_active=True,
        audible_deck="A",
    )
    player = _make_player(state)
    # Call .play() with a deliberately-non-existent path; since can_play
    # returns False, the early return fires before audio_decode runs.
    player.play("/nonexistent/path.wav")
    # Stream must be None (no OutputStream was created).
    assert player._stream is None, (
        "play() did not short-circuit despite can_play=False"
    )


def test_play_attempts_decode_when_guard_permits() -> None:
    """Positive-control symmetry test — when can_play returns True,
    .play() does NOT short-circuit at the guard; it proceeds toward the
    decode step. Since the file is bogus, decode will fail downstream
    (FileNotFoundError or PyAV error) — but the guard branch did not
    fire. The downstream failure proves we got past can_play.
    """
    state = MusicState()  # cold path, lens off → can_play=True
    player = _make_player(state)
    # The play() call will raise/fail at decode; we don't care what
    # exact exception fires, only that SOMETHING happened past can_play
    # (vs. the silent return-None-without-attempting case).
    with pytest.raises(Exception):
        player.play("/nonexistent/path.wav")
