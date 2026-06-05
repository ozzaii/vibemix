# SPDX-License-Identifier: Apache-2.0
"""derive_audible_deck + derive_audible_track — verbatim port of cohost_v4.py:1093-1159.

Two free functions (matching v4's free-function shape) that produce the
controller-derived "which deck am I hearing" inference and the
nowplaying-cli-cross-referenced track label.

KNOWN ISSUE (Phase 9):
    The Pioneer DDJ-FLX4 firmware sometimes consumes the PLAY button press locally without
    forwarding ``note_on`` to other listeners when djay Pro is the active controlling app.
    That means ``deck['play']`` may stay at the boot default ``False``. Channel fader +
    crossfader are therefore the primary audible-deck evidence; if that evidence cannot
    name a deck confidently, ``derive_audible_track`` omits the nowplaying title.

The named-track gate:
    - ``0.5`` (this module, line below): the floor for naming the
      nowplaying title. Below that, we omit the title so prompt builders print
      ``track=unknown`` instead of anchoring Sven on the wrong deck.
    - ``0.5`` (``TRACK_CHANGE_MIN_CONFIDENCE`` in ``vibemix.audio.constants``):
      the floor for ``EventDetector`` to fire a ``TRACK_CHANGE`` event.
"""

from __future__ import annotations


def derive_audible_deck(
    deck_a: dict, deck_b: dict, xfader: int, connected: bool
) -> tuple[str, float]:
    """Returns (audible_deck, confidence). 'A' / 'B' / 'mix' / 'none'.
    Confidence considers play state, channel volume, and crossfader position."""
    # KNOWN ISSUE (Phase 9): deck['play'] may stay False for the Pioneer DDJ-FLX4
    # when djay Pro is active — see module docstring. Phase 3 reproduces v4 verbatim.
    if not connected:
        return "none", 0.0

    # Per-side weight = play * vol * xfader_factor
    def xfader_factor(side: str) -> float:
        if side == "A":
            if xfader >= 112:
                return 0.0
            if xfader >= 80:
                return 0.3
            if xfader >= 48:
                return 0.7
            return 1.0
        else:  # B
            if xfader < 16:
                return 0.0
            if xfader < 48:
                return 0.3
            if xfader <= 80:
                return 0.7
            return 1.0

    def deck_weight(d: dict, side: str) -> float:
        # 2026-05-21 (Kaan: "ensure a/b is working") — dropped the hard
        # play-gate. Phase 9 known issue: djay Pro doesn't write play-state
        # back to the DDJ-FLX4, so d['play'] stays False during a live mix,
        # which zeroed every weight and collapsed audible_deck to 'none'
        # (no single / double / transition awareness reached the LLM). The
        # channel fader (vol) + crossfader side are the RELIABLE grounded
        # signals: a fader up on the audible side of the xfader means that
        # deck is sounding, play-LED desync or not. vol<0.1 = fader down =
        # silent is still honoured — we never guess a silent deck audible.
        vol = d.get("vol", 0) / 127.0
        if vol < 0.1:
            return 0.0
        return vol * xfader_factor(side)

    wa = deck_weight(deck_a, "A")
    wb = deck_weight(deck_b, "B")

    if wa < 0.05 and wb < 0.05:
        return "none", 0.0
    if wa > 0.3 and wb < 0.1:
        return "A", min(1.0, wa)
    if wb > 0.3 and wa < 0.1:
        return "B", min(1.0, wb)
    if wa > 0.2 and wb > 0.2:
        return "mix", min(0.5, max(wa, wb))
    # One dominant but other non-zero — call dominant with reduced confidence
    if wa > wb:
        return "A", max(0.4, wa - wb)
    return "B", max(0.4, wb - wa)


def derive_audible_track(
    track_title: str | None,
    audible_deck: str,
    deck_confidence: float,
    audio_audible: bool,
    *,
    track_deck: str | None = None,
) -> tuple[str | None, float]:
    """Combines nowplaying-cli's title with controller-derived audible deck
    to produce a confidence-tagged track. Conservative — would rather say
    `unknown` than name a track that isn't actually playing.

    nowplaying-cli only gives ONE current title. If a deck source can attribute
    that title to a concrete side, it must agree with the audible deck; otherwise
    omit the title rather than anchoring Sven on the wrong deck."""
    if not audio_audible or not track_title:
        return None, 0.0
    if audible_deck == "none":
        # Audio is heard but controller says no deck is active — controller may
        # be disconnected or in a weird state. Don't anchor on the title.
        return None, 0.0
    if audible_deck == "mix":
        # Two decks playing — nowplaying-cli may have latched either side.
        return None, 0.0
    if track_deck is not None:
        source_deck = track_deck.strip().upper()
        if source_deck in {"A", "B"} and audible_deck.upper() != source_deck:
            return None, 0.0
    # Single dominant deck. Trust the title roughly proportional to confidence.
    if deck_confidence < 0.5:
        return None, 0.0
    return track_title, min(0.85, deck_confidence)
