# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix Slice 3 — automatic cue detection (numpy/scipy DSP only).

OUT of the src/vibemix grep gate (see spikes/__init__.py). Proves the "easy
half" of the killer feature: find the structural cue points (intro / breakdown
/ drop) from the audio itself, snapped to the beat grid, each with a confidence
so the anti-slop gate can drop anything uncertain. Pure numpy + scipy — NO
librosa / aubio / CLAP (Gemini-only-AI + one-click-install-green constraints;
deterministic DSP is allowed and is how vibemix already grounds phase).

Feeds Slice 0's writer: detected CueCandidates -> confidence gate -> Rekordbox
XML. Together with Slice 1 (calibration) + Slice 2 (arc) this closes the
hand-placed-cue gap so the demo cues become REAL drops.
"""
