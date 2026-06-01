# SPDX-License-Identifier: Apache-2.0
"""Real-CLAP retrieval regression guard - runs over COMMITTED real embeddings.

This is the test the suite was missing (2026-05-31 singularity audit, the #1
system-wide reliability risk): a real-model ranking regression that ships GREEN
because every other CLAP test mocks the embedder. Here the corpus is real
512-dim CLAP embeddings of real in-repo DJ tracks (``tests/bench/data/*.mp3``),
committed once via ``python scripts/eval/clap_retrieval.py --build``. The test
itself needs NO model and NO onnxruntime - it loads ``vectors.npz`` and runs the
PRODUCTION ranking primitives, so it is $0 and offline in CI, yet a regression in
mean-centering / cosine ranking / the embedding itself moves these numbers.

Ground truth: each track is embedded at two DISJOINT audio windows; window B
(held-out query) must retrieve window A (corpus) of the SAME track. Two halves
of one track being each other's nearest neighbour is the minimum a working
similarity engine must do. The retrieval guard tracks the PRODUCTION path
(centered cosine = ``store.search_centered``).

What this proved at build time (2026-05-31, 6 real tracks):
  * Anisotropy is REAL on actual CLAP: raw mean pairwise cosine ~= 0.85 (one
    cone), centering collapses it to ~= -0.15. First verification of the
    ``centering.py`` fix on real 512-d embeddings, not a synthetic corpus.
  * Centered retrieval: recall@1 ~= 0.67 (4/6), recall@5 = 1.0, MRR ~= 0.74.
  * Honest caveat - at N=6 the corpus centroid is a tiny, noisy estimate, so
    centering does NOT *improve* retrieval here (it slightly trims recall@3 vs
    raw). Centering's RETRIEVAL benefit needs a larger corpus; its anisotropy
    collapse is already proven. Growing this fixture to 12-20 clips is the
    roadmap follow-up (singularity roadmap section 3c). This guard is a no-regression
    floor, NOT a published benchmark.

Floors are locked BELOW the measured values - they assert "no catastrophic
regression" (e.g. a broken model collapsing recall toward random 1/6), not
"exactly today's number".
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.eval.clap_retrieval import score_fixture

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "library"
    / "fixtures"
    / "clap_real_corpus"
)

# Locked floors - set below the values measured at build time (centered =
# production path). Bump ONLY upward, and only after re-running --build confirms
# the gain is real. Random-chance recall@1 on 6 tracks ~= 0.17, so 0.5 cleanly
# separates "working" from "regressed".
MIN_RECALL_AT_1 = 0.5    # measured 0.667 (4/6)
MIN_RECALL_AT_5 = 0.83   # measured 1.0
MIN_MRR = 0.55           # measured 0.742
MIN_ANISOTROPY_RAW = 0.5     # measured 0.85 - real CLAP music sits in one cone
MIN_ANISOTROPY_GAP = 0.3     # measured 0.997 - centering collapses that cone


@pytest.fixture(scope="module")
def report() -> dict:
    if not (FIXTURE_DIR / "vectors.npz").exists():
        pytest.skip(
            "clap_real_corpus fixture not built - run "
            "`python scripts/eval/clap_retrieval.py --build`"
        )
    return score_fixture(FIXTURE_DIR)


def test_corpus_is_anisotropic_and_centering_collapses_it(report: dict) -> None:
    """THE headline: the shipped mean-centering reduces the real corpus pairwise
    cosine - verified on REAL 512-d CLAP embeddings (not the synthetic corpus
    `test_centering.py` uses). This is the quality fix `centering.py` exists for."""
    aniso = report["anisotropy"]
    assert aniso["raw"] >= MIN_ANISOTROPY_RAW
    assert aniso["centered"] < aniso["raw"]
    assert aniso["gap"] >= MIN_ANISOTROPY_GAP


def test_held_out_excerpt_retrieves_its_own_track(report: dict) -> None:
    """recall@1 (centered/production path): a held-out window finds its own
    track's other window well above random chance (~=0.17 on 6 tracks)."""
    assert report["centered"]["recall"][1] >= MIN_RECALL_AT_1


def test_right_track_stays_in_top5_and_mrr_above_floor(report: dict) -> None:
    """The true match is reliably near the top (recall@5) and ranks high on
    average (MRR) - catches a ranking/embedding regression that buries it."""
    assert report["centered"]["recall"][5] >= MIN_RECALL_AT_5
    assert report["centered"]["mrr"] >= MIN_MRR
