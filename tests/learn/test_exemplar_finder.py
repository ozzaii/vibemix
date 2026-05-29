# SPDX-License-Identifier: Apache-2.0
"""EXEMPLAR-01 + EXEMPLAR-02 ``ExemplarFinder.find()`` regression tests.

``ExemplarFinder.find(band, k=1, t_session=...)`` is the public engine API
that the lesson runtime calls. It is **pure-compute** over the side-car
``band_shares`` table; falls back to the packaged CC-BY bank when ≤3
tracks pass the band-floor.

Contract (from 93-RESEARCH.md §Code Example 1):

    - Returns ``list[ExemplarPick]`` of length ≤ k.
    - For every picked track, calls ``registry.write("exemplar", track_id,
      t_session)`` BEFORE returning so the LLM's subsequent
      ``[exemplar:<track_id>]`` cite resolves (Invariant #2 grounding contract).
    - When library < ``_LIBRARY_FLOOR=3``, falls back to packaged bank;
      synthetic track_id ``_packaged:<band>:<filename_stem>``;
      reason copy = "Your library doesn't have a great example of this — listen to this one we packaged".
    - When both library AND bank empty: returns ``[]`` (degraded install).

REQ-ID: EXEMPLAR-01 + EXEMPLAR-02 (engine + kick-guard wiring + grounding).
"""
from __future__ import annotations

import pytest

from vibemix.learn.exemplar import ExemplarFinder, ExemplarPick
from vibemix.state.evidence_registry import EvidenceRegistry


def test_find_returns_top_k_from_library_when_floor_met(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4 synthetic library rows ≥ _LIBRARY_FLOOR=3 → ``find('low', k=2)``
    returns 2 ExemplarPick instances in deterministic DESC band-share order.
    """
    fake_rows = [
        ("track:alpha", 0.55, 0.10),
        ("track:beta",  0.70, 0.20),
        ("track:gamma", 0.30, 0.30),
        ("track:delta", 0.45, 0.40),
    ]
    monkeypatch.setattr(
        "vibemix.learn.exemplar.top_for_band",
        lambda conn, band, k=3, max_kick_corr=0.8: fake_rows[: k],
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=2)
    assert len(picks) == 2, f"expected 2 picks, got {len(picks)}"
    assert all(isinstance(p, ExemplarPick) for p in picks), (
        f"every pick must be an ExemplarPick dataclass; got {picks!r}"
    )


def test_find_falls_back_when_under_library_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only 2 rows < ``_LIBRARY_FLOOR=3`` → engine engages the packaged-bank
    fallback path and surfaces the honest-null reason copy verbatim.
    """
    monkeypatch.setattr(
        "vibemix.learn.exemplar.top_for_band",
        lambda conn, band, k=3, max_kick_corr=0.8: [
            ("track:thin1", 0.30, 0.10),
            ("track:thin2", 0.20, 0.20),
        ],
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=1)
    assert picks, "packaged low-band fallback must ship with the Learn module"
    assert (
        "Your library doesn't have a great example of this — listen to this one we packaged"
        in picks[0].reason
    ), (
        f"fallback pick must surface verbatim honest-null reason; "
        f"got reason={picks[0].reason!r}"
    )


def test_find_writes_to_evidence_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For every picked track, ``find()`` must call
    ``registry.write("exemplar", track_id, t_session)``.

    Invariant #2 grounding contract: the LLM's ``[exemplar:<track_id>]``
    cite has to resolve to an observation that was written BEFORE the cite
    was emitted; ``find()`` is the only path that schedules those writes.
    """
    monkeypatch.setattr(
        "vibemix.learn.exemplar.top_for_band",
        lambda conn, band, k=3, max_kick_corr=0.8: [
            ("track:alpha", 0.55, 0.10),
            ("track:beta",  0.70, 0.20),
            ("track:gamma", 0.30, 0.30),
        ],
    )

    registry = EvidenceRegistry()
    finder = ExemplarFinder(registry=registry)
    picks = finder.find("low", k=1, t_session=42.0)
    assert picks, "expected at least one pick"
    track_id = picks[0].track_id
    assert registry.has("exemplar", track_id, 42.0, tol=2.0), (
        f"engine must call registry.write('exemplar', {track_id!r}, 42.0); "
        "the grounding contract for Invariant #2 — without this write, the "
        "LLM's [exemplar:<id>] cite gets stripped as un-grounded."
    )


def test_find_synthetic_id_format_for_packaged_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback ``track_id`` shape must be ``_packaged:<band>:<filename_stem>``
    so it cannot collide with real library track ids — deterministic
    contract per RESEARCH §Pattern 5.
    """
    monkeypatch.setattr(
        "vibemix.learn.exemplar.top_for_band",
        lambda conn, band, k=3, max_kick_corr=0.8: [],  # empty library
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=1)
    assert picks, "packaged low-band fallback must ship with the Learn module"
    assert picks[0].track_id.startswith("_packaged:low:"), (
        f"fallback track_id must start with '_packaged:low:', "
        f"got {picks[0].track_id!r}"
    )


def test_find_empty_library_and_no_bank_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both library AND packaged bank empty → return ``[]`` (degraded-install
    behavior per RESEARCH §Code Example 1).

    We force the empty-library path via the ``top_for_band`` monkeypatch and
    force the empty-bank path by monkeypatching ``_fallback_for_band`` to
    return None — simulates a stripped wheel without the bank assets.
    """
    monkeypatch.setattr(
        "vibemix.learn.exemplar.top_for_band",
        lambda conn, band, k=3, max_kick_corr=0.8: [],
    )
    monkeypatch.setattr(
        "vibemix.learn.exemplar._fallback_for_band",
        lambda band: None,
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=1)
    assert picks == [], (
        f"empty library + empty bank must return []; got {picks!r}"
    )
