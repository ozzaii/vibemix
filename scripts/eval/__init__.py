# SPDX-License-Identifier: Apache-2.0
"""Phase 27 — vibemix eval harness package.

Single-binary deterministic replay harness + 2-judge cross-check (Plan 02) +
corpus diversity validator (Plan 03) + threshold-lock CI gate (Plan 04).

Public modules:
    - replay_harness: CLI entry point (``python -m scripts.eval.replay_harness``)
    - f1: precision/recall/F1 with ±tolerance windowing
    - scorecard: markdown + JSON scorecard renderer
    - corpus_manifest: corpus diversity + integrity validator
    - judge: (Plan 02) Gemini Pro 6-axis JSON + Flash binary cross-check
    - cited_relevance: (Plan 02) cosine filter via Gemini Embedding 2

This package is the autonomous hallucination-proxy gate (CONTEXT EVAL-01..08).
"""
