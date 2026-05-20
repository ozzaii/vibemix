# SPDX-License-Identifier: Apache-2.0
"""BPM-to-bus grounding regression (BRINGUP-02).

The live BPM=200 bug: a harmonic-leak autocorr trace (~66% @130, ~28% @194-200,
scatter) was flipping the bus-facing ``state.bpm`` to a subdivision lock. The
fix shipped in ``fd25337`` as the ``_stabilize_bpm`` median-ring stabilizer
(refresh.py:84) — this test does NOT re-implement it. It DRIVES the existing
chain (``estimate_bpm`` -> ``bpm_ring`` -> ``_stabilize_bpm`` -> ``validate_bpm``)
through ``_tick_once`` and asserts the value that actually reaches the wire
(``state.bpm``, read directly by ws_bus.py) never exceeds ``BPM_VALID_MAX``.

The bus reads ``state.bpm`` verbatim (ws_bus.py:272 mascot frame; ws_bus.py:127
snapshot ``raw_bpm``), so "state.bpm <= BPM_VALID_MAX" IS the bus-facing
invariant. We assert it for both the techno AND the psytrance active profile —
psytrance's bpm_range [138,150] must not let ``validate_bpm`` re-introduce an
out-of-range value.
"""

from __future__ import annotations

import random
from statistics import median

import pytest

from vibemix.audio.constants import BPM_VALID_MAX
from vibemix.state import MusicState
from vibemix.state.genre import list_profiles, set_active_profile
from vibemix.state.refresh import _tick_once

from tests.state.test_refresh import _audible_buf, _ctrl_mock, _track_mock


@pytest.fixture(autouse=True)
def _reset_active_profile():
    """Wipe the active-profile singleton before+after each test (no leak)."""
    from vibemix.state.genre import profile as _mod

    _mod._ACTIVE_PROFILE = None
    yield
    _mod._ACTIVE_PROFILE = None


def _harmonic_leak_sequence(n: int = 300, seed: int = 0) -> list[float]:
    """The exact measured bimodal psytrance distribution from
    test_bpm_stabilize.py: ~66% @130, ~28% @{194,200}, ~6% @{103,130,176}.
    These are the RAW autocorr estimates BEFORE stabilization."""
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n):
        r = rng.random()
        if r < 0.66:
            samples.append(130.0)
        elif r < 0.94:
            samples.append(rng.choice([194.0, 200.0]))
        else:
            samples.append(rng.choice([103.0, 130.0, 176.0]))
    return samples


def _replay_through_tick(monkeypatch, profile_name: str | None) -> list[float]:
    """Drive _tick_once over the harmonic-leak trace, threading a real bpm_ring
    + bpm_cache + last_bpm_at exactly like state_refresh_loop does. Returns the
    list of bus-facing state.bpm values recorded after each tick.

    estimate_bpm is monkeypatched to pop successive RAW samples from the trace,
    so we exercise the real stabilizer + validate_bpm chain — not the estimator.
    """
    if profile_name is not None:
        set_active_profile(profile_name)
    else:
        set_active_profile(None)

    samples = iter(_harmonic_leak_sequence())

    def _fake_estimate_bpm(audio_buf, seconds=6.0):  # noqa: ANN001, ARG001
        return next(samples)

    # Patch the name as bound inside refresh.py.
    monkeypatch.setattr("vibemix.state.refresh.estimate_bpm", _fake_estimate_bpm)

    state = MusicState()
    audio_buf = _audible_buf()  # rms ~0.35 -> currently_loud True every tick
    ctrl = _ctrl_mock()
    track = _track_mock()

    bpm_ring: list[float] = []
    bpm_cache = 0.0
    last_bpm_at = 0.0
    last_high = 0.0
    last_low = 0.0
    recorded: list[float] = []

    now = 1000.0
    # 300 samples in the trace; step now by >3.0s each tick so the BPM gate
    # fires on every iteration (now - last_bpm_at > 3.0 AND currently_loud).
    for _ in range(300):
        now += 3.5
        last_high, last_low, bpm_cache, last_bpm_at = _tick_once(
            state,
            audio_buf,
            ctrl,
            track,
            now=now,
            last_audible_high=last_high,
            last_audible_low=last_low,
            bpm_cache=bpm_cache,
            last_bpm_at=last_bpm_at,
            bpm_ring=bpm_ring,
        )
        recorded.append(state.bpm)

    return recorded


def test_state_bpm_never_exceeds_max_techno(monkeypatch):
    """The 200 BPM never reaches the bus with techno active — driving the
    SHIPPED stabilizer chain, not a re-implementation."""
    recorded = _replay_through_tick(monkeypatch, "techno")
    assert recorded, "expected recorded state.bpm values"
    for v in recorded:
        assert v == 0.0 or 0.0 < v <= BPM_VALID_MAX, f"out-of-range state.bpm leaked: {v}"
    assert max(recorded) <= BPM_VALID_MAX, f"max state.bpm {max(recorded)} > {BPM_VALID_MAX}"


def test_state_bpm_never_exceeds_max_psytrance(monkeypatch):
    """Same bound holds with psytrance active — validate_bpm's [138,150] snap
    must not re-introduce an out-of-range value. Depends on psytrance.json
    (Plan 52-02). Skipped (with a TODO) if the profile is not yet present."""
    if "psytrance" not in list_profiles():
        pytest.skip("psytrance.json not present yet (Plan 52-02); techno bound is unconditional")
    recorded = _replay_through_tick(monkeypatch, "psytrance")
    assert recorded, "expected recorded state.bpm values"
    for v in recorded:
        assert v == 0.0 or 0.0 < v <= BPM_VALID_MAX, f"out-of-range state.bpm leaked: {v}"
    assert max(recorded) <= BPM_VALID_MAX, f"max state.bpm {max(recorded)} > {BPM_VALID_MAX}"


def test_steady_state_bpm_tracks_real_tempo(monkeypatch):
    """Sanity: the bus value tracks the REAL tempo (~130), not the 200
    subdivision lock — so the guard isn't just clamping to a wrong-but-in-range
    value."""
    recorded = _replay_through_tick(monkeypatch, "techno")
    nonzero = [v for v in recorded if v > 0.0]
    assert nonzero, "expected at least one non-zero state.bpm"
    assert median(nonzero) == pytest.approx(130.0, abs=1.0), (
        f"steady-state median {median(nonzero)} should track the real ~130 tempo"
    )
