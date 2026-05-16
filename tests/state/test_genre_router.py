# SPDX-License-Identifier: Apache-2.0
"""GenreRouter + per-genre chain registry coverage (Plan 17-05 Task 1).

The router holds a per-genre dict-of-detector-chains and atomically swaps the
active chain when ``state.active_genre`` changes — no session restart, no
in-flight detection interruption. Backward compatibility with the v4 baseline
EventDetector is preserved by ``build_baseline_chain()`` returning ``[]``: the
per-genre chains ADD detectors on top of the v4 baseline rules, never replace.

Tests:
    1. default active genre is ``"unknown"``
    2. swap to "house" returns the house chain
    3. swap to unregistered genre falls back to baseline + WARN log
    4. swap is idempotent (no chain re-instantiation)
    5. swap atomicity (single attribute reassign, no half-state)
    6. baseline chain is empty
    7. house chain contains SubLayerArrival + PhraseBoundary
    8. techno chain contains all 5 kick-side detectors
    9. hard_tek chain mirrors techno (Plan 06 lands the per-detector cooldown
       overrides; this plan ships the override mechanism)
    10. GENRE_REGISTRY keys are a SUPERSET of GENRE_BPM_BANDS keys
"""

from __future__ import annotations

import logging

from vibemix.audio.constants import GENRE_BPM_BANDS
from vibemix.events.genres import (
    GENRE_REGISTRY,
    build_baseline_chain,
    build_hard_tek_chain,
    build_house_chain,
    build_techno_chain,
)
from vibemix.state.detectors import (
    AcidLineEntryDetector,
    BreakdownKickKillDetector,
    DistortionClimbDetector,
    KickDensityShiftDetector,
    KickSwapDetector,
    PhraseBoundaryDetector,
    ReentryKickLandDetector,
    SubLayerArrivalDetector,
)
from vibemix.state.genre_router import GenreRouter


# ---------- Test 1 ----------


def test_genre_router_default_active_genre_is_unknown():
    """Fresh ``GenreRouter()`` exposes ``current_genre == "unknown"`` and
    ``active_chain()`` returns the baseline chain (empty list)."""
    router = GenreRouter()
    assert router.current_genre == "unknown"
    chain = router.active_chain()
    assert chain == []


# ---------- Test 2 ----------


def test_genre_router_swap_to_house_returns_house_chain():
    """``router.swap("house")`` flips ``current_genre``; subsequent
    ``active_chain()`` returns the house chain (SubLayerArrival + PhraseBoundary)."""
    router = GenreRouter()
    swapped = router.swap("house")
    assert swapped is True
    assert router.current_genre == "house"
    chain = router.active_chain()
    types = [type(d) for d in chain]
    assert SubLayerArrivalDetector in types
    assert PhraseBoundaryDetector in types


# ---------- Test 3 ----------


def test_genre_router_swap_to_unknown_genre_falls_back_to_baseline(caplog):
    """``router.swap("dubstep")`` (not in registry) → ``current_genre ==
    "unknown"`` (NOT "dubstep" — refuses to register a chain we don't have);
    ``active_chain()`` returns baseline. Logged at WARN level."""
    router = GenreRouter()
    # Pre-flip to house so we can verify the bad swap forces back to "unknown"
    router.swap("house")
    assert router.current_genre == "house"

    with caplog.at_level(logging.WARNING, logger="vibemix.state.genre_router"):
        router.swap("dubstep")
    assert router.current_genre == "unknown"
    assert router.active_chain() == []
    # WARN was emitted with the bogus name
    warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("dubstep" in r.getMessage() for r in warn_records)


# ---------- Test 4 ----------


def test_genre_router_swap_is_idempotent():
    """Two consecutive ``router.swap("house")`` calls — second is a no-op
    (no chain re-instantiation; verified by checking ``active_chain() is
    active_chain()`` returns True across the second swap — same Python id)."""
    router = GenreRouter()
    router.swap("house")
    chain_before = router.active_chain()
    swapped_again = router.swap("house")
    chain_after = router.active_chain()
    assert swapped_again is False  # idempotent — no swap happened
    assert chain_after is chain_before  # same Python object id (no re-instantiation)


# ---------- Test 5 ----------


def test_genre_router_swap_atomic_no_inflight_break():
    """Atomicity contract — call ``router.swap("techno")`` between two
    ``active_chain()`` calls; both calls return their respective chains
    without raising. (Atomicity is structural — single attribute reassign —
    but the test pins it.)"""
    router = GenreRouter()
    router.swap("house")
    chain_house = router.active_chain()
    assert SubLayerArrivalDetector in [type(d) for d in chain_house]

    router.swap("techno")
    chain_techno = router.active_chain()
    assert KickSwapDetector in [type(d) for d in chain_techno]
    # The two chains are distinct lists (router rebuilt on swap)
    assert chain_techno is not chain_house


# ---------- Test 6 ----------


def test_baseline_chain_is_empty():
    """``build_baseline_chain()`` returns ``[]``. Baseline EventDetector
    rules in ``event_detector.py`` carry the v4 detection; the per-genre
    chain ADDS detectors on top, doesn't replace."""
    chain = build_baseline_chain()
    assert chain == []


# ---------- Test 7 ----------


def test_house_chain_contains_sub_layer_arrival_and_phrase_boundary():
    """House chain is sub-arrival + phrase boundary because house is
    harmonically rich + structural — the kick rarely "swaps" in a meaningful
    way."""
    chain = build_house_chain()
    types = [type(d) for d in chain]
    assert SubLayerArrivalDetector in types
    assert PhraseBoundaryDetector in types
    # Exactly 2 detectors in the house chain
    assert len(chain) == 2


# ---------- Test 8 ----------


def test_techno_chain_contains_all_kick_detectors():
    """``build_techno_chain()`` returns 5 detectors — KickSwap,
    KickDensityShift, BreakdownKickKill, ReentryKickLand (paired with the
    kill instance from the same chain), PhraseBoundary (with kill_detector
    dep)."""
    chain = build_techno_chain()
    types = [type(d) for d in chain]
    assert KickSwapDetector in types
    assert KickDensityShiftDetector in types
    assert BreakdownKickKillDetector in types
    assert ReentryKickLandDetector in types
    assert PhraseBoundaryDetector in types
    assert len(chain) == 5

    # Pair contract — find the kill detector and verify reentry + phrase
    # share the SAME instance (no globals, no shared mutable state across
    # genre swaps).
    kill = next(d for d in chain if isinstance(d, BreakdownKickKillDetector))
    reentry = next(d for d in chain if isinstance(d, ReentryKickLandDetector))
    phrase = next(d for d in chain if isinstance(d, PhraseBoundaryDetector))
    assert reentry.kill_detector is kill
    assert phrase.kill_detector is kill

    # Order matters — kill MUST appear BEFORE reentry + phrase so that on a
    # single tick where the kill fires, the reentry/phrase detectors observe
    # the freshly-set ``last_kill_at`` on the same instance the chain shares.
    kill_idx = chain.index(kill)
    reentry_idx = chain.index(reentry)
    phrase_idx = chain.index(phrase)
    assert kill_idx < reentry_idx
    assert kill_idx < phrase_idx


# ---------- Test 9 ----------


def test_hard_tek_chain_is_techno_plus_overlay_detectors():
    """``build_hard_tek_chain()`` returns the techno baseline (5 detectors)
    PLUS the two Phase 30 SENSE-17/SENSE-18 overlay detectors
    (DISTORTION_CLIMB + ACID_LINE_ENTRY) — 7 total. The overlays NEVER appear
    in techno/house chains (verified via test 7 + test 8 above)."""
    chain = build_hard_tek_chain()
    types = [type(d) for d in chain]
    # Baseline 5 (same as techno):
    assert KickSwapDetector in types
    assert KickDensityShiftDetector in types
    assert BreakdownKickKillDetector in types
    assert ReentryKickLandDetector in types
    assert PhraseBoundaryDetector in types
    # Phase 30 overlays:
    assert DistortionClimbDetector in types
    assert AcidLineEntryDetector in types
    assert len(chain) == 7

    # Same pair contract as techno
    kill = next(d for d in chain if isinstance(d, BreakdownKickKillDetector))
    reentry = next(d for d in chain if isinstance(d, ReentryKickLandDetector))
    phrase = next(d for d in chain if isinstance(d, PhraseBoundaryDetector))
    assert reentry.kill_detector is kill
    assert phrase.kill_detector is kill

    # Overlay detectors come AFTER the kick-side detectors per chain-order
    # contract (CONTEXT D — anti-double-fire vs. KICK_SWAP).
    distortion = next(d for d in chain if isinstance(d, DistortionClimbDetector))
    acid = next(d for d in chain if isinstance(d, AcidLineEntryDetector))
    kick_swap = next(d for d in chain if isinstance(d, KickSwapDetector))
    assert chain.index(kick_swap) < chain.index(distortion)
    assert chain.index(kick_swap) < chain.index(acid)


def test_techno_chain_does_not_contain_hard_tek_overlays():
    """DISTORTION_CLIMB + ACID_LINE_ENTRY are Hard Tek-only. Techno chain
    must NOT contain them — the chain-selection IS the genre gate."""
    chain = build_techno_chain()
    types = [type(d) for d in chain]
    assert DistortionClimbDetector not in types
    assert AcidLineEntryDetector not in types


def test_house_chain_does_not_contain_hard_tek_overlays():
    """House chain must not include Hard Tek-only detectors."""
    chain = build_house_chain()
    types = [type(d) for d in chain]
    assert DistortionClimbDetector not in types
    assert AcidLineEntryDetector not in types


# ---------- Test 10 ----------


def test_genre_registry_keys_match_genre_bpm_bands():
    """The keys of ``GENRE_REGISTRY`` are a SUPERSET of
    ``GENRE_BPM_BANDS.keys()`` — every genre the writer can emit MUST have a
    chain builder registered (otherwise ``GenreRouter.swap()`` will fall back
    to baseline for known-good genres, breaking SENSE-15)."""
    bpm_band_keys = set(GENRE_BPM_BANDS.keys())
    registry_keys = set(GENRE_REGISTRY.keys())
    missing = bpm_band_keys - registry_keys
    assert not missing, (
        f"GENRE_REGISTRY missing chain builder for known genre(s): {missing} "
        f"(GENRE_BPM_BANDS={sorted(bpm_band_keys)}, "
        f"GENRE_REGISTRY={sorted(registry_keys)})"
    )
