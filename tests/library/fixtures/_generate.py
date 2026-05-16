# SPDX-License-Identifier: Apache-2.0
"""Plan 28-02 — generate the parity fixture corpus.

Deterministic via the locked seed. Re-running this script must produce
byte-identical output (numpy seed + sorted ground-truth).

Usage:
    python tests/library/fixtures/_generate.py

Outputs:
    tests/library/fixtures/synthetic_embeddings.npy   # (1000, 768) float32 L2-normalized
    tests/library/fixtures/synthetic_queries.json     # 50 queries + ground-truth top-10
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize

SEED = 2826
N_TRACKS = 1000
N_QUERIES = 50
TOP_K = 10

OUT_DIR = Path(__file__).parent
EMBEDDINGS_PATH = OUT_DIR / "synthetic_embeddings.npy"
QUERIES_PATH = OUT_DIR / "synthetic_queries.json"


def main() -> None:
    rng = np.random.default_rng(SEED)

    # 1000 × 768 corpus, L2-normalized.
    corpus = rng.standard_normal((N_TRACKS, EMBEDDING_DIM)).astype(np.float32)
    corpus = np.stack([l2_normalize(row) for row in corpus])
    np.save(EMBEDDINGS_PATH, corpus, allow_pickle=False)
    print(f"wrote {EMBEDDINGS_PATH} shape={corpus.shape} dtype={corpus.dtype}")

    track_ids = [f"t{i:04d}" for i in range(N_TRACKS)]

    # 50 queries + ground-truth top-10 computed via the SAME cosine_topk that
    # the production code uses. Self-referential check ensures the parity
    # tests catch backend math drift, not fixture drift.
    queries = rng.standard_normal((N_QUERIES, EMBEDDING_DIM)).astype(np.float32)
    queries = np.stack([l2_normalize(q) for q in queries])

    out: list[dict] = []
    for i, q in enumerate(queries):
        topk = cosine_topk(q, corpus, track_ids, k=TOP_K)
        out.append(
            {
                "id": f"q{i:03d}",
                "vector": [float(x) for x in q],
                # Full-precision similarity so parity tests can compare
                # exactly via rounded match (no fixture-side rounding loss).
                "top_k": [
                    {"track_id": tid, "similarity": float(s)}
                    for tid, s in topk
                ],
            }
        )

    with QUERIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {QUERIES_PATH} queries={len(out)} top_k={TOP_K}")


if __name__ == "__main__":
    main()
