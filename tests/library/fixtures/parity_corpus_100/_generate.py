# SPDX-License-Identifier: Apache-2.0
"""Regenerate the Plan 41-05 parity corpus fixture.

100 deterministic synthetic ``(track_id, 768-dim float32 L2-normalized
vector)`` rows. Seed locked at 42 — any contributor can regenerate the
fixture byte-identically by running this script.

Run:
    python tests/library/fixtures/parity_corpus_100/_generate.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

EMBEDDING_DIM = 768
N_TRACKS = 100
SEED = 42


def main() -> None:
    here = Path(__file__).parent
    rng = np.random.default_rng(SEED)

    # Generate 100 random vectors, L2-normalize each.
    raw = rng.standard_normal((N_TRACKS, EMBEDDING_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    vectors = (raw / norms).astype(np.float32)

    # Sanity: every row should be unit length now.
    final_norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(final_norms, 1.0, atol=1e-5), final_norms

    track_ids = [f"parity-{i:03d}" for i in range(N_TRACKS)]

    np.savez(here / "vectors.npz", vectors=vectors)
    (here / "track_ids.json").write_text(json.dumps(track_ids, indent=2) + "\n")
    print(
        f"Wrote {N_TRACKS} tracks × {EMBEDDING_DIM} dims to "
        f"{here / 'vectors.npz'}"
    )


if __name__ == "__main__":
    main()
