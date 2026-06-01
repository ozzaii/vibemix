# clap_real_corpus - real-CLAP retrieval regression fixture

Committed real 512-dim CLAP embeddings of the in-repo DJ tracks under
`tests/bench/data/*.mp3`. This is the fixture behind
`tests/library/test_clap_real_retrieval.py` - the regression guard the suite was
missing (2026-05-31 singularity audit found the #1 system-wide reliability risk:
every other CLAP test mocks the embedder, so a real-model ranking regression
ships GREEN). The test needs **no model and no onnxruntime** - it loads
`vectors.npz` and runs the production ranking primitives.

## Files
- `vectors.npz` - `corpus_vectors` (Nx512) and `query_vectors` (Nx512), float32,
  L2-normalized. Window A of each track -> corpus; disjoint window B -> held-out query.
- `manifest.json` - track ids, window bounds, ground-truth statement.

## Ground truth
Each track is embedded at two **disjoint** audio windows (A = 5-30s, B = 45-70s of
each 75s track). Query i (window B of track i) must retrieve corpus i (window A of
track i): two halves of one track should be each other's nearest neighbour.

## Regenerate
```bash
python scripts/eval/clap_retrieval.py --build      # needs the ONNX CLAP model + ffmpeg
python scripts/eval/clap_retrieval.py              # score the committed fixture (no model)
```

## What it proved at build (2026-05-31, 6 real tracks)
- **Anisotropy is real on actual CLAP**: raw mean pairwise cosine ~= **0.85** (one
  cone); the shipped `centering.py` collapses it to ~= **-0.15** (gap ~= 1.0). First
  verification of the centering quality fix on real 512-d embeddings - every prior
  centering test used a synthetic corpus.
- **Centered retrieval** (production path): recall@1 ~= 0.67 (4/6), recall@5 = 1.0,
  MRR ~= 0.74.
- **Honest caveat**: at N=6 the corpus centroid is a small, noisy estimate, so
  centering does not *improve* retrieval here (it slightly trims recall@3 vs raw).
  Centering's retrieval benefit needs a larger corpus; its anisotropy collapse is
  proven. Growing this fixture to 12-20 clips is the roadmap follow-up
  (`.planning/singularity/2026-05-31/ROADMAP-SINGULARITY.md` section 3c). This is a
  no-regression floor, not a published benchmark.

## Privacy
Stores only embeddings + opaque track stems; the source mp3s already live in-repo.
No user paths.
