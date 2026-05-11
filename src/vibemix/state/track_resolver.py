# SPDX-License-Identifier: Apache-2.0
"""derive_audible_deck + derive_audible_track — verbatim port of cohost_v4.py:1093-1159.

Two free functions (matching v4's free-function shape) that produce the
controller-derived "which deck am I hearing" inference and the
nowplaying-cli-cross-referenced track label.

KNOWN ISSUE (Phase 9):
    The Pioneer DDJ-FLX4 firmware sometimes consumes the PLAY button press
    locally without forwarding ``note_on`` to other listeners when djay Pro is
    the active controlling app. That means ``deck['play']`` stays at the boot
    default ``False``, so ``derive_audible_deck`` returns ``"none"``, so
    ``derive_audible_track`` caps confidence at ``0.3``, so the
    ``TRACK_CHANGE`` event (which requires ``audible_track_confidence >=
    TRACK_CHANGE_MIN_CONFIDENCE = 0.5``) never fires.

    Phase 3 reproduces this v4 behavior verbatim. Phase 9 will fix it by
    cross-referencing with nowplaying-cli's playback-state or with an
    audio-side "deck has signal energy" fallback.

The TWO confidence thresholds (do not confuse):
    - ``0.3`` (this module, line below): the floor for evidence-line track
      quoting in ``AICoach``. Below 0.3 the prompt prints ``track=unknown``.
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
        if not d.get("play"):
            return 0.0
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
) -> tuple[str | None, float]:
    """Combines nowplaying-cli's title with controller-derived audible deck
    to produce a confidence-tagged track. Conservative — would rather say
    `unknown` than name a track that isn't actually playing.

    nowplaying-cli only gives ONE current title (whichever deck cued/loaded
    most recently). When the controller says audio is coming primarily from
    a single deck, we trust the title. Otherwise we lower confidence."""
    if not audio_audible or not track_title:
        return None, 0.0
    if audible_deck == "none":
        # Audio is heard but controller says no deck is active — controller may
        # be disconnected or in a weird state. Don't anchor on the title.
        return track_title, 0.3
    if audible_deck == "mix":
        # Two decks playing — title may be either. Mark unsure.
        return track_title, 0.4
    # Single dominant deck. Trust the title roughly proportional to confidence.
    return track_title, min(0.85, max(0.5, deck_confidence))
