# Parity corpus — 100 tracks × 768-dim

Used by `tests/library/test_embeddings_parity.py` (Plan 41-05 Task 2) to
pin the determinism contract of `vibemix.library._cosine.cosine_topk`.

## Regenerate

```bash
python tests/library/fixtures/parity_corpus_100/_generate.py
```

Output: `vectors.npz` (100 × 768 float32, each row L2-normalized) and
`track_ids.json` (100 ids of the form `parity-NNN`).

## Determinism contract

Generated from `numpy.random.default_rng(SEED=42)`. The seed is locked
in `_generate.py` — bumping it requires updating the parity test
expectations.

## Why synthetic, not real Embedding 2 output?

The local-math parity layer is what Phase 41-05 ships. End-to-end Gemini
Embedding 2 parity (real model output, real corpus) is a heavyweight
VCR-cassette concern punted to Plan 41-07 integration.
