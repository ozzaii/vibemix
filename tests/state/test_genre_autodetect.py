# SPDX-License-Identifier: Apache-2.0
"""Grounded DSP genre auto-detector — anti-slop test suite (GENRE-01).

Pins the central directive: a pure-numpy detector that picks the active profile
from the features ALREADY computed each tick (stabilized BPM + band shares +
crest factor), scoring nearest-match across ``list_profiles()`` — no heavy
embedding models in the realtime DSP loop, no new heavy deps.

Anti-slop (non-negotiable, [[project_anti_slop_grounded_gemini_thesis]]):
- confidence gate + ``unknown`` fallback — NEVER a false-confident guess;
- hysteresis so the detected genre does not flicker bar-to-bar;
- env override wins when the user pins a genre.

The regression that matters: a PSYTRANCE-shaped vector must score 'psytrance',
NOT 'techno' (Kaan's bug). An out-of-library / ambiguous vector must score
'unknown'.
"""

from __future__ import annotations

import pytest

from vibemix.state.genre import list_profiles, load_profile
from vibemix.state.genre.genre_autodetect import (
    GENRE_CONFIDENCE_MIN,
    GenreHysteresis,
    apply_genre_hysteresis,
    is_auto_enabled,
    score_genre,
    set_auto_enabled,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset the active-profile singleton + the auto-enabled flag around each
    test so cross-test pollution can't leak."""
    from vibemix.state.genre import profile as _mod

    _mod._ACTIVE_PROFILE = None
    set_auto_enabled(True)
    yield
    _mod._ACTIVE_PROFILE = None
    set_auto_enabled(True)


def _profiles() -> list:
    return [load_profile(n) for n in list_profiles()]


def _midpoint_bands(name: str) -> dict[str, float]:
    """Build a band vector at the midpoint of a profile's band_signature."""
    prof = load_profile(name)
    assert prof is not None
    return {b: (lo + hi) / 2.0 for b, (lo, hi) in prof.band_signature.items()}


def _mid_bpm(name: str) -> float:
    prof = load_profile(name)
    assert prof is not None
    lo, hi = prof.bpm_range
    return (lo + hi) / 2.0


def _mid_crest(name: str) -> float:
    prof = load_profile(name)
    assert prof is not None
    lo, hi = prof.expected_crest_factor
    return (lo + hi) / 2.0


# ---------- score_genre: each shipped profile scores itself ----------


@pytest.mark.parametrize("name", ["disco", "drum_and_bass", "house", "pop", "psytrance", "techno"])
def test_midpoint_vector_scores_its_own_profile(name: str):
    """Each profile's midpoint feature vector scores that profile at or above
    the confidence gate. (Some profiles overlap heavily on BPM bands — the
    band/crest axes must still resolve the right one for non-overlapping ones;
    overlapping pairs may legitimately tie -> we assert the picked name is the
    profile itself OR unknown-with-the-right-runner-up is NOT acceptable here:
    the midpoint of a profile must be closest to ITSELF.)"""
    bands = _midpoint_bands(name)
    bpm = _mid_bpm(name)
    crest = _mid_crest(name)
    picked, conf = score_genre(bpm, bands, crest, _profiles())
    assert picked == name, f"{name} midpoint scored {picked} (conf {conf:.2f})"
    assert conf >= GENRE_CONFIDENCE_MIN, f"{name} conf {conf:.2f} below gate"


def test_psytrance_vector_scores_psytrance_not_techno():
    """THE regression for Kaan's bug: a clearly-psy vector (heavy sub, 144 BPM,
    crest 5.5) scores 'psytrance', never 'techno'."""
    bands = {"sub": 0.40, "low": 0.27, "mid": 0.14, "high": 0.10}
    picked, conf = score_genre(144.0, bands, 5.5, _profiles())
    assert picked == "psytrance", f"psy vector scored {picked} (conf {conf:.2f})"
    assert conf >= GENRE_CONFIDENCE_MIN


def test_techno_vector_scores_techno():
    bands = {"sub": 0.35, "low": 0.27, "mid": 0.17, "high": 0.10}
    picked, conf = score_genre(132.0, bands, 5.0, _profiles())
    assert picked == "techno", f"techno vector scored {picked} (conf {conf:.2f})"
    assert conf >= GENRE_CONFIDENCE_MIN


# ---------- anti-slop: unknown fallback ----------


def test_out_of_library_vector_scores_unknown():
    """A vector genuinely far from every profile — 100 BPM, a high-band-dominant
    spectrum (0.50 high, sparse sub) that no shipped genre exhibits, low crest —
    returns ('unknown', conf < gate). No false-confident pick on alien audio."""
    bands = {"sub": 0.10, "low": 0.15, "mid": 0.25, "high": 0.50}
    picked, conf = score_genre(100.0, bands, 2.0, _profiles())
    assert picked == "unknown", f"out-of-library scored {picked} (conf {conf:.2f})"
    assert conf < GENRE_CONFIDENCE_MIN


def test_no_bpm_lock_scores_unknown():
    """bpm <= 0 (no BPM lock yet) must not yield a confident genre."""
    bands = {"sub": 0.40, "low": 0.27, "mid": 0.14, "high": 0.10}
    picked, conf = score_genre(0.0, bands, 5.5, _profiles())
    assert picked == "unknown"
    assert conf < GENRE_CONFIDENCE_MIN


def test_tie_within_margin_scores_unknown():
    """When the best and second-best are within GENRE_TIE_MARGIN, the detector
    refuses to guess and returns 'unknown' — anti-slop tie-break.

    Construct a 2-profile world of two near-identical clones differing only
    slightly in band centre, then feed the exact point between them so both
    score high and tie within the margin -> unknown."""
    techno = load_profile("techno")
    assert techno is not None
    # Two clones: same everything, band centres nudged +/- a hair so the
    # midpoint between them ties both within GENRE_TIE_MARGIN.
    from dataclasses import replace

    clone_a = replace(
        techno,
        name="clone_a",
        band_signature={
            "sub": (0.30, 0.40),
            "low": (0.22, 0.30),
            "mid": (0.12, 0.20),
            "high": (0.06, 0.12),
        },
    )
    clone_b = replace(
        techno,
        name="clone_b",
        band_signature={
            "sub": (0.32, 0.42),  # +0.02 centre shift
            "low": (0.22, 0.30),
            "mid": (0.12, 0.20),
            "high": (0.06, 0.12),
        },
    )
    # The point exactly between the two sub centres (0.36) -> equidistant.
    bands = {"sub": 0.36, "low": 0.26, "mid": 0.16, "high": 0.09}
    picked, conf = score_genre(140.0, bands, 5.0, [clone_a, clone_b])
    assert picked == "unknown", f"tie did not collapse to unknown: {picked} ({conf:.3f})"


# ---------- hysteresis: no flicker ----------


def test_hysteresis_does_not_flip_before_dwell():
    """Feeding a single off-label raw value must NOT flip the committed genre
    until the dwell is met (mirrors the phase HysteresisState)."""
    hs = GenreHysteresis(current_label="techno")
    # One tick of 'psytrance' is not enough to flip.
    out = apply_genre_hysteresis("psytrance", hs)
    assert out == "techno", "flipped on a single off-label tick"
    out = apply_genre_hysteresis("psytrance", hs)
    assert out == "techno", "flipped before dwell met"


def test_hysteresis_flips_after_dwell():
    """After the dwell of consistent raw values, the committed genre flips."""
    hs = GenreHysteresis(current_label="techno")
    last = None
    for _ in range(5):
        last = apply_genre_hysteresis("psytrance", hs)
    assert last == "psytrance", "did not flip after sustained dwell"


def test_hysteresis_oscillation_does_not_flip():
    """Alternating borderline raw labels must not flip — the dwell counter
    resets on a new pending value."""
    hs = GenreHysteresis(current_label="techno")
    seq = ["psytrance", "house", "psytrance", "house", "psytrance"]
    out = "techno"
    for raw in seq:
        out = apply_genre_hysteresis(raw, hs)
    assert out == "techno", f"oscillation flipped to {out}"


def test_unknown_commits_immediately():
    """A below-threshold raw ('unknown') commits immediately like 'silent' in
    the phase detector — anti-hallucination: when we lose confidence we say so
    at once, we don't keep claiming the old genre."""
    hs = GenreHysteresis(current_label="techno")
    out = apply_genre_hysteresis("unknown", hs)
    assert out == "unknown", "unknown did not commit immediately"


# ---------- env override (Task 4) ----------


def test_auto_enabled_default_true():
    assert is_auto_enabled() is True


def test_set_auto_enabled_toggles():
    set_auto_enabled(False)
    assert is_auto_enabled() is False
    set_auto_enabled(True)
    assert is_auto_enabled() is True


# ---------- env override at the _tick_once boundary (Task 4) ----------
#
# These drive the real _tick_once gate. score_genre is monkeypatched to a
# deterministic ('psytrance', high-conf) so we test the FLAG GATE, not the
# scorer (the scorer's correctness is pinned above).


def _drive_tick_with_forced_genre(monkeypatch, forced=("psytrance", 0.9)):
    from tests.state.test_refresh import _audible_buf, _ctrl_mock, _track_mock
    from vibemix.state import MusicState
    from vibemix.state.genre import set_active_profile
    from vibemix.state.refresh import _tick_once

    # Pin the active profile to techno (the "wrong" profile for psy audio).
    set_active_profile("techno")
    monkeypatch.setattr("vibemix.state.refresh.score_genre", lambda *a, **k: forced)

    state = MusicState()
    hs = GenreHysteresis(current_label=forced[0])  # already committed -> writes through
    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=144.0,
        last_bpm_at=0.0,
        genre_hysteresis=hs,
    )
    return state


def test_env_pinned_does_not_flip_active_profile_but_surfaces_detection(monkeypatch):
    """set_auto_enabled(False) (user pinned a genre): the scorer picks psytrance
    but the ACTIVE profile stays techno (set_active_profile NOT called), while
    detected_genre/genre_confidence ARE still surfaced for honesty."""
    from vibemix.state.genre import get_active_profile

    set_auto_enabled(False)
    state = _drive_tick_with_forced_genre(monkeypatch)

    active = get_active_profile()
    assert active is not None and active.name == "techno", "env pin was overridden"
    assert state.detected_genre == "psytrance", "detection not surfaced under env pin"
    assert state.genre_confidence == 0.9


def test_auto_enabled_flips_active_profile_to_detected(monkeypatch):
    """set_auto_enabled(True): the active profile DOES flip to the committed
    detected genre (psytrance)."""
    from vibemix.state.genre import get_active_profile

    set_auto_enabled(True)
    state = _drive_tick_with_forced_genre(monkeypatch)

    active = get_active_profile()
    assert active is not None and active.name == "psytrance", "auto-detect did not flip profile"
    assert state.detected_genre == "psytrance"


# ---------- no heavy deps ----------


def test_genre_autodetect_imports_no_heavy_deps():
    """Grep the IMPORT lines (not prose) — the module may name CLAP/MERT in its
    docstring to explain WHY they are excluded, but must not actually import any
    heavy audio-ML dep."""
    import vibemix.state.genre.genre_autodetect as mod

    with open(mod.__file__, encoding="utf-8") as f:
        import_lines = [
            ln.strip().lower()
            for ln in f
            if ln.strip().startswith(("import ", "from "))
        ]
    forbidden = ("clap", "mert", "openl3", "torch", "transformers", "tensorflow", "librosa")
    for ln in import_lines:
        for dep in forbidden:
            assert dep not in ln, f"heavy dep imported: {ln!r}"
