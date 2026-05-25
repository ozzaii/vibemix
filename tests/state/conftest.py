# SPDX-License-Identifier: Apache-2.0
"""Shared synthetic fixtures for Phase 78 PERCEIVE tests.

Two builders, no live API, no GEMINI_API_KEY:

- ``perceive_state_pair`` — a (prior, current) ``MusicState`` pair with
  controllable scalar deltas, for the PERCEIVE-01/02 single-writer + render
  tests. The current state carries a ``prev_perceive`` dict mirroring the prior
  tick's scalars (the shape the refresh loop will write).
- ``synthetic_corpus`` — N L2-normalized 1536-dim vectors sharing a common
  direction (the anisotropic shape from tests/library/test_centering.py), with
  folder-style genre labels, for the PERCEIVE-03 prototype tests.

Both are intentionally cheap dataclass / numpy constructions — €0, deterministic.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize


def _anisotropic_corpus(n: int, seed: int = 0) -> np.ndarray:
    """N L2-normalized vectors sharing a strong common direction (high avg
    pairwise cosine) plus small per-vector noise — mimics real anisotropic
    whole-track Gemini embeddings. Copied from tests/library/test_centering.py
    so the PERCEIVE-03 prototype tests exercise the same centering separation."""
    rng = np.random.default_rng(seed)
    shared = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
    rows = []
    for _ in range(n):
        noise = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
        rows.append(l2_normalize((shared + 0.4 * noise).astype(np.float32)))
    return np.stack(rows)


@pytest.fixture
def perceive_state_pair():
    """Factory → (prior_scalars, current_state) with a controllable delta.

    Usage::

        prior, state = perceive_state_pair(rms_delta=+0.05)

    ``prior`` is the dict the prior tick would have stored in
    ``state.prev_perceive``; ``current_state`` is a fresh audible ``MusicState``
    whose live scalars sit ``*_delta`` above the prior. The current state's
    ``prev_perceive`` is seeded with ``prior`` (the shape Plan 02 will render
    deltas against). Defaults give an above-floor RMS rise.
    """
    from vibemix.state import MusicState

    def _build(
        *,
        rms_delta: float = 0.05,
        sub_delta: float = 0.10,
        bpm_delta: float = 0.0,
        seed_prev: bool = True,
    ):
        prior = {
            "rms": 0.040,
            "sub": 0.08,
            "low": 0.30,
            "mid": 0.30,
            "high": 0.20,
            "bpm": 126.0,
            "onset_density": 2.0,
            "crest": 4.0,
        }
        cur_bands = {
            "sub": prior["sub"] + sub_delta,
            "low": prior["low"],
            "mid": prior["mid"],
            "high": prior["high"],
        }
        kwargs = dict(
            audible=True,
            rms=prior["rms"] + rms_delta,
            bands=cur_bands,
            bpm=prior["bpm"] + bpm_delta,
        )
        if seed_prev:
            # prev_perceive does not exist on MusicState until Plan 02 lands;
            # the tests that seed it are xfail-strict, so a TypeError here is
            # the intended RED trigger, not a fixture bug.
            kwargs["prev_perceive"] = dict(prior)
        return prior, MusicState(**kwargs)

    return _build


@pytest.fixture
def synthetic_corpus():
    """Factory → (vectors, ids, label_of) for PERCEIVE-03 prototype tests.

    ``vectors`` is an (N, 1536) float32 L2-normalized anisotropic corpus;
    ``ids`` are ``t000``-style; ``label_of`` maps id → folder-style genre label
    cycling over a small label set (so each label gets ≥2 members → a real
    centered mean prototype).
    """

    def _build(n: int = 12, labels: tuple[str, ...] = ("hardtechno", "house", "trance"), seed: int = 0):
        vectors = _anisotropic_corpus(n, seed=seed)
        ids = [f"t{i:03d}" for i in range(n)]
        label_of = {tid: labels[i % len(labels)] for i, tid in enumerate(ids)}
        return vectors, ids, label_of

    return _build
