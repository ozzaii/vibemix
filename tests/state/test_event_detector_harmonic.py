# SPDX-License-Identifier: Apache-2.0
"""Harmonic detector branches — gate + firing + cross-deck suppression + default-off.

Phase 60 Plan 02 (HARMONIC-02 / HARMONIC-03). These tests prove the conservatism
contract at the EventDetector layer:

  - The detector is OFF by default (``harmonic_clash_enabled=False``) — a fully
    set-up clash returns None until the flag flips (the Kaan-ear ship gate,
    mirroring ``DeckPoller._vision_enabled``).
  - ``_melodic_overlap_gate(state)`` runs BEFORE any clash branch and is built
    ENTIRELY from shipped MusicState signals: it suppresses single-deck,
    breakdown/silent/low phase, percussive/atonal (no tonal band share),
    acapella (``vocal_active``), and sub-LOW_RMS sections.
  - Cross-deck + cite-floor suppression: a clash requires BOTH decks
    independently resolved (camelot present) AND both confidence ≥
    DECK_CITE_MIN_CONF (0.6). A sub-floor or missing 2nd deck → no fire.
  - KEY_CLASH fires ONLY on ``is_clash()==True`` (deterministic verdict). A safe
    pair (8A/9A — adjacent perfect fifth) never fires.
  - The 28s KEY_CLASH cooldown is inherited from MIN_EVENT_GAP_PER_TYPE (Phase 59
    registered it) — we exercise it, we do NOT re-implement it.

Construction mirrors tests/state/test_event_detector.py: the music-presence gate
is satisfied by setting ``_audible_since`` directly + a patched clock, so the
change-detection refs are not polluted by ``_reset_change_refs``.
"""

from __future__ import annotations

from vibemix.state import EventDetector, MusicState
from vibemix.state.deck_state import DeckState, DeckTrack


def _patch_time(mocker, value: float):
    return mocker.patch("vibemix.state.event_detector.time.time", return_value=value)


def _deck(camelot: str | None, confidence: float) -> DeckTrack:
    return DeckTrack(camelot=camelot, confidence=confidence, source="rekordbox_xml")


def _clash_state(
    *,
    audible_deck: str = "mix",
    phase: str = "groove",
    rms: float = 0.06,
    vocal_active: bool = False,
    bands: dict | None = None,
    a_camelot: str | None = "8A",
    a_conf: float = 0.8,
    b_camelot: str | None = "3A",
    b_conf: float = 0.8,
    recent_moves: list | None = None,
    decks: dict | None = None,
) -> MusicState:
    """A MusicState that — with the flag flipped — would PASS the melodic-overlap
    gate AND present a clash pair (8A vs 3A → same-letter hour-distance 5 → CLASH).

    Each kwarg lets a single test opt INTO one suppression path (single-deck,
    breakdown, percussive, sub-floor deck, safe pair, ...)."""
    ms = MusicState()
    ms.audible = True
    ms.bpm = 130.0
    ms.audible_deck = audible_deck
    ms.phase = phase
    ms.rms = rms
    ms.vocal_active = vocal_active
    # Tonal mid/high share present by default so the gate's tonal floor passes.
    ms.bands = bands if bands is not None else {"sub": 0.15, "low": 0.2, "mid": 0.35, "high": 0.3}
    ms.recent_moves = recent_moves if recent_moves is not None else []
    if decks is not None:
        ms.deck_state = DeckState(decks=decks)
    else:
        ms.deck_state = DeckState(
            decks={
                "A": _deck(a_camelot, a_conf),
                "B": _deck(b_camelot, b_conf),
            }
        )
    return ms


def _prime(d: EventDetector, mocker, *, t0: float = 1000.0):
    """Satisfy _music_truly_playing on the next detect() call without polluting
    change-detection refs (mirror test_event_detector._prime_music_playing)."""
    t = _patch_time(mocker, t0 + 5.0)
    d._audible_since = t0
    return t


def _enabled_detector() -> EventDetector:
    """A detector with the harmonic clash gate flipped ON (the Kaan-ear veto
    state). Accept either the kwarg or the attribute — both are part of the
    contract."""
    return EventDetector(harmonic_clash_enabled=True)


# ---------- Default-off flag (the ship gate) ----------


def test_detector_gated_by_default(mocker):
    """Flag False (default) → a full clash setup returns None. The detector ships
    quiet until the Kaan-ear veto flips the flag."""
    d = EventDetector()  # default: harmonic_clash_enabled is False
    assert d._harmonic_clash_enabled is False
    ms = _clash_state()
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


# ---------- _melodic_overlap_gate suppression paths ----------


def test_no_clash_single_deck(mocker):
    """audible_deck != "mix" → only one deck contributing → no overlap → None."""
    d = _enabled_detector()
    ms = _clash_state(audible_deck="A")
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


def test_no_clash_in_breakdown(mocker):
    """phase ∈ {breakdown, silent, low} → harmony dropped out → None."""
    d = _enabled_detector()
    for ph in ("breakdown", "silent", "low"):
        ms = _clash_state(phase=ph)
        _prime(d, mocker)
        ev = d.detect(ms, kaan_just_spoke=False, manual=False)
        assert ev is None or ev.type != "KEY_CLASH", f"fired in phase={ph}"


def test_no_clash_percussive(mocker):
    """vocal_active True (acapella) and/or no tonal band share → None."""
    d = _enabled_detector()
    ms = _clash_state(vocal_active=True)
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"

    d2 = _enabled_detector()
    # Drum-only / atonal: nearly all energy in sub/low, negligible mid+high.
    ms2 = _clash_state(bands={"sub": 0.55, "low": 0.4, "mid": 0.03, "high": 0.02})
    _prime(d2, mocker)
    ev2 = d2.detect(ms2, kaan_just_spoke=False, manual=False)
    assert ev2 is None or ev2.type != "KEY_CLASH"


def test_no_clash_below_rms_floor(mocker):
    """rms < LOW_RMS (0.040) → a dropped-out section disguises a clash → None."""
    d = _enabled_detector()
    ms = _clash_state(rms=0.02)
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


# ---------- cross-deck + cite-floor suppression ----------


def test_no_clash_subfloor_deck(mocker):
    """deck B confidence < DECK_CITE_MIN_CONF (0.6) → cross-deck suppression → None."""
    d = _enabled_detector()
    ms = _clash_state(b_conf=0.4)
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


def test_no_clash_missing_second_deck(mocker):
    """decks.get("B") absent → unresolved 2nd deck → uncitable → None."""
    d = _enabled_detector()
    ms = _clash_state(decks={"A": _deck("8A", 0.8)})
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


def test_no_clash_unresolved_camelot(mocker):
    """deck B camelot None (resolved deck but no key) → uncitable → None."""
    d = _enabled_detector()
    ms = _clash_state(b_camelot=None)
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


# ---------- is_clash verdict gate ----------


def test_no_clash_safe_pair(mocker):
    """Both decks resolved + cited but is_clash False (8A/9A — adjacent perfect
    fifth, SAFE) → None."""
    d = _enabled_detector()
    ms = _clash_state(a_camelot="8A", b_camelot="9A")
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "KEY_CLASH"


def test_clash_fires_when_all_conditions_met(mocker):
    """Flag True + full gate pass + is_clash True (8A/3A → hour-distance 5 →
    1 semitone clash) → Event("KEY_CLASH") with the cited extra."""
    d = _enabled_detector()
    ms = _clash_state(a_camelot="8A", b_camelot="3A")
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "KEY_CLASH"
    assert ev.extra["a_side"] == "A"
    assert ev.extra["a_camelot"] == "8A"
    assert ev.extra["b_side"] == "B"
    assert ev.extra["b_camelot"] == "3A"
    assert ev.extra["semitones"] == 1


def test_clash_respects_cooldown(mocker):
    """A second consecutive tick within the 28s KEY_CLASH cooldown → None.
    The cooldown is inherited from MIN_EVENT_GAP_PER_TYPE; we do not re-implement
    it — we only prove the branch honors _cooldown_ok."""
    d = _enabled_detector()
    ms = _clash_state(a_camelot="8A", b_camelot="3A")
    t = _prime(d, mocker)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev1 is not None and ev1.type == "KEY_CLASH"
    # Advance only 10s — inside the 28s KEY_CLASH gap → no re-fire.
    t.return_value = 1015.0
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev2 is None or ev2.type != "KEY_CLASH"


# ---------- TRANSITION_OPPORTUNITY (retrospective, groundable-only) ----------


def test_transition_silent_without_structural_move(mocker):
    """No recent structural xfader/EQ move → nothing groundable → silent."""
    d = _enabled_detector()
    # Safe pair so KEY_CLASH cannot fire; no structural move so TRANSITION can't either.
    ms = _clash_state(a_camelot="8A", b_camelot="9A", recent_moves=[])
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type not in ("KEY_CLASH", "TRANSITION_OPPORTUNITY")


def test_transition_silent_when_decks_unresolved(mocker):
    """A blend move happened but the 2nd deck is unresolved → uncitable → silent
    (silence over a guess)."""
    d = _enabled_detector()
    ms = _clash_state(
        a_camelot="8A",
        b_camelot=None,
        recent_moves=[(1.0, "xfader→full-B")],
    )
    _prime(d, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "TRANSITION_OPPORTUNITY"
