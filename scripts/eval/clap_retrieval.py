# SPDX-License-Identifier: Apache-2.0
"""Real-CLAP retrieval evaluation - the regression guard the suite was missing.

Closes the #1 system-wide reliability risk from the 2026-05-31 singularity audit:
EVERY existing CLAP/library test mocks the embedder, scripts the store, or uses
synthetic/8-dim vectors (``grep InferenceSession tests/`` = 0 real invocations),
so a real-model ranking regression - a broken mean-centering, a text-to-track
collapse, a cue-to-section drift - ships GREEN and reaches the user. The product
bar ("real DJ friend, no slop") rides entirely on Kaan's ear. This module is the
committed, $0-CI metric that catches such a regression mechanically.

Design (mirrors the ``parity_corpus_100`` fixture pattern):
  * ``--build`` (needs the model + ffmpeg, run ONCE locally): for each real
    track in ``tests/bench/data/*.mp3`` it embeds TWO disjoint audio windows via
    the SHIPPED ``ClapEngine.embed_audio_file`` - window A -> corpus, window B ->
    held-out query. Two disjoint halves of the same track SHOULD be each other's
    nearest neighbour in a working engine, giving honest recall ground truth from
    real audio. It writes ``vectors.npz`` + ``manifest.json`` to the fixture dir.
  * The committed ``vectors.npz`` is then read by ``tests/library/
    test_clap_real_retrieval.py`` with NO model - it runs the PRODUCTION ranking
    primitives (``cosine_topk`` + ``compute_centroid`` / ``center_and_renorm``)
    and asserts locked recall / MRR / anisotropy floors. CI stays $0 and offline.

The evaluator rides the production primitives on purpose: a metric here can only
move if the shipped ranking math moves.

Privacy: the fixture stores only embeddings + opaque track ids (the source mp3s
already live in-repo under ``tests/bench/data/``); no user paths.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.library._cosine import (  # noqa: E402
    EMBEDDING_DIM,
    cosine_topk,
    l2_normalize,
)
from vibemix.library.centering import (  # noqa: E402
    center_and_renorm,
    compute_centroid,
)

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "library" / "fixtures" / "clap_real_corpus"
DEFAULT_AUDIO_DIR = ROOT / "tests" / "bench" / "data"
# Two disjoint windows of each 75s track: A is the first third, B the last third,
# leaving a guard gap so the windows share no audio. Integer seconds keep the
# ffmpeg args locale-safe (this Mac is tr_TR - comma decimals break -ss).
WINDOW_A = (5, 30)   # corpus vector
WINDOW_B = (45, 70)  # held-out query vector


# --------------------------------------------------------------------------- #
# Pure metric core (unit-tested in tests/library/test_clap_retrieval_eval.py)  #
# --------------------------------------------------------------------------- #
def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize each row of an ``(N, D)`` matrix (idempotent on unit rows)."""
    out = np.empty_like(vectors, dtype=np.float32)
    for i in range(vectors.shape[0]):
        out[i] = l2_normalize(vectors[i].astype(np.float32, copy=False))
    return out


def mean_pairwise_cosine(vectors: np.ndarray) -> float:
    """Mean cosine over all distinct pairs of (already-or-now unit) rows.

    For L2-normalized rows cosine == dot, so this is the mean of the strict
    upper triangle of ``V @ V.T``. Returns 0.0 for fewer than 2 rows.
    """
    v = _unit_rows(np.asarray(vectors, dtype=np.float32))
    n = v.shape[0]
    if n < 2:
        return 0.0
    sims = v @ v.T
    iu = np.triu_indices(n, k=1)
    return float(sims[iu].mean())


def anisotropy_gap(vectors: np.ndarray) -> dict[str, float]:
    """How much corpus mean-centering collapses the average pairwise cosine.

    Returns ``{"raw", "centered", "gap"}`` where ``gap = raw - centered``. A
    healthy CLAP corpus is anisotropic (high ``raw``); the shipped centering
    must drive ``centered`` below ``raw`` (positive ``gap``) - that is the whole
    point of ``centering.py``. N < 2 -> all zeros (no centroid possible).
    """
    v = _unit_rows(np.asarray(vectors, dtype=np.float32))
    raw = mean_pairwise_cosine(v)
    centroid = compute_centroid(v)
    if centroid is None:
        return {"raw": raw, "centered": raw, "gap": 0.0}
    centered = mean_pairwise_cosine(center_and_renorm(v, centroid))
    return {"raw": raw, "centered": centered, "gap": round(raw - centered, 6)}


def evaluate_retrieval(
    corpus_vectors: np.ndarray,
    corpus_ids: list[str],
    query_vectors: np.ndarray,
    gt_ids: list[str],
    *,
    centered: bool = True,
    k_values: tuple[int, ...] = (1, 3, 5),
) -> dict:
    """Rank the corpus for each query and score recall@k + MRR vs ground truth.

    Rides the PRODUCTION ranking path: rows are L2-normalized, then (when
    ``centered``) the seed AND every candidate are centered with the SAME corpus
    centroid - byte-identical to ``store.search_centered`` - before
    ``cosine_topk``. ``gt_ids[i]`` is the single correct corpus id for query i.

    Returns ``{"recall": {k: rate}, "mrr", "n_queries", "centered"}``.
    """
    corpus = _unit_rows(np.asarray(corpus_vectors, dtype=np.float32))
    queries = _unit_rows(np.asarray(query_vectors, dtype=np.float32))
    n = corpus.shape[0]
    q = queries.shape[0]
    if n == 0 or q == 0:
        return {"recall": {k: 0.0 for k in k_values}, "mrr": 0.0, "n_queries": q, "centered": centered}

    if centered:
        centroid = compute_centroid(corpus)
        if centroid is not None:
            corpus_rank = center_and_renorm(corpus, centroid)
            query_rank = center_and_renorm(queries, centroid)
        else:  # N < 2 - no centroid, fall back to raw (matches production)
            corpus_rank, query_rank = corpus, queries
    else:
        corpus_rank, query_rank = corpus, queries

    hits = {k: 0 for k in k_values}
    rr_sum = 0.0
    for i in range(q):
        ranked = cosine_topk(query_rank[i], corpus_rank, corpus_ids, k=n)
        ranked_ids = [tid for tid, _ in ranked]
        try:
            rank = ranked_ids.index(gt_ids[i]) + 1
        except ValueError:  # gt not in corpus - counts as a miss
            continue
        rr_sum += 1.0 / rank
        for k in k_values:
            if rank <= k:
                hits[k] += 1

    return {
        "recall": {k: round(hits[k] / q, 6) for k in k_values},
        "mrr": round(rr_sum / q, 6),
        "n_queries": q,
        "centered": centered,
    }


# --------------------------------------------------------------------------- #
# Fixture build (needs the shipped ONNX CLAP model + ffmpeg) - run ONCE locally #
# --------------------------------------------------------------------------- #
def _slice_to_wav(src: Path, start_s: int, end_s: int, dst: Path) -> None:
    """Extract ``[start_s, end_s)`` of ``src`` to a 48k mono wav via ffmpeg.

    LC_ALL=C: this Mac is tr_TR; a comma-decimal -ss would break ffmpeg. The
    window bounds are integers so this is belt-and-suspenders.
    """
    env = {**os.environ, "LC_ALL": "C"}
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error", "-y",
        "-ss", str(start_s), "-to", str(end_s),
        "-i", str(src),
        "-ac", "1", "-ar", "48000",
        str(dst),
    ]
    subprocess.run(cmd, check=True, env=env)


def build_fixture(
    audio_dir: Path = DEFAULT_AUDIO_DIR,
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
) -> dict:
    """Embed two disjoint windows of every ``*.mp3`` in ``audio_dir`` and write
    ``vectors.npz`` + ``manifest.json`` to ``fixture_dir``. Returns a summary."""
    from vibemix.library.clap_engine import ClapEngine

    engine = ClapEngine()
    mp3s = sorted(audio_dir.glob("*.mp3"))
    if not mp3s:
        msg = f"no .mp3 files in {audio_dir}"
        raise SystemExit(msg)

    corpus_vecs: list[np.ndarray] = []
    query_vecs: list[np.ndarray] = []
    track_ids: list[str] = []
    fixture_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        for mp3 in mp3s:
            tid = mp3.stem
            a_wav = tmpd / f"{tid}_a.wav"
            b_wav = tmpd / f"{tid}_b.wav"
            _slice_to_wav(mp3, *WINDOW_A, a_wav)
            _slice_to_wav(mp3, *WINDOW_B, b_wav)
            va = l2_normalize(engine.embed_audio_file(str(a_wav)).astype(np.float32))
            vb = l2_normalize(engine.embed_audio_file(str(b_wav)).astype(np.float32))
            if va.shape != (EMBEDDING_DIM,) or vb.shape != (EMBEDDING_DIM,):
                msg = f"{tid}: bad embed shape {va.shape}/{vb.shape}"
                raise SystemExit(msg)
            corpus_vecs.append(va)
            query_vecs.append(vb)
            track_ids.append(tid)
            print(f"  embedded {tid}  A{WINDOW_A} + B{WINDOW_B}")

    corpus = np.stack(corpus_vecs).astype(np.float32)
    queries = np.stack(query_vecs).astype(np.float32)
    np.savez(fixture_dir / "vectors.npz", corpus_vectors=corpus, query_vectors=queries)
    manifest = {
        "schema": "clap_real_corpus_v1",
        "embedding_dim": EMBEDDING_DIM,
        "track_ids": track_ids,
        "window_a_s": list(WINDOW_A),
        "window_b_s": list(WINDOW_B),
        "ground_truth": "query i (window B of track i) -> corpus i (window A of track i)",
        "source": "tests/bench/data/*.mp3 (in-repo real DJ tracks)",
    }
    (fixture_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    measured = score_fixture(fixture_dir)
    print(f"\nWrote {len(track_ids)} tracks -> {fixture_dir / 'vectors.npz'}")
    print(json.dumps(measured, indent=2))
    return measured


def score_fixture(fixture_dir: Path = DEFAULT_FIXTURE_DIR) -> dict:
    """Load the committed fixture and compute the full metric report (no model)."""
    data = np.load(fixture_dir / "vectors.npz")
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    corpus = data["corpus_vectors"].astype(np.float32)
    queries = data["query_vectors"].astype(np.float32)
    ids = list(manifest["track_ids"])
    return {
        "n_tracks": len(ids),
        "centered": evaluate_retrieval(corpus, ids, queries, ids, centered=True),
        "raw": evaluate_retrieval(corpus, ids, queries, ids, centered=False),
        "anisotropy": anisotropy_gap(corpus),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="embed audio -> fixture (needs model+ffmpeg)")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    args = parser.parse_args(argv)

    if args.build:
        build_fixture(args.audio_dir, args.fixture_dir)
        return 0
    report = score_fixture(args.fixture_dir)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
