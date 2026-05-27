# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix Slice 1 — 3-track calibration over the embedding pool.

OUT of the src/vibemix grep gate (see spikes/__init__.py). Proves the
"genuinely new, cheap" piece of the historical prep-flow spike: from a
vibe-filtered pool of embedding vectors, surface 3 candidates from distinct
points across the vibe space so the DJ can pick the one closest to intent.
Reuses the SHIPPING cosine math (vibemix.library._cosine) for parity.
"""
