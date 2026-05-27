# Auto-Cue Engine — Current Product Spec

**Date:** 2026-05-26
**Status:** current source truth after the CUE-DETR pivot.

Auto-cue produces `CueAnchor` records for cue-anchored embedding, ingest, export,
and future live suggestions. The product entry point is
`vibemix.library.cue_engine.detect_cues_auto()`.

## Current Pipeline

```
audio file
  -> cue_detr.detect_cue_positions()      # local CUE-DETR ONNX producer
  -> cue_refine.refine_cue_positions()    # downbeat/phrase snap + dedup
  -> cue_engine.build_cue_anchors()       # coarse labels + <=80s windows
  -> CueAnchor(label, start_s, end_s, confidence, source="auto")
```

If CUE-DETR cannot run because the ONNX file or optional runtime packages are
missing, `detect_cues_auto()` falls back to the dep-free heuristic in
`cue_detect.detect_cues()`. Both paths return the same `CueAnchor` seam.

## Model And Runtime

- Primary producer: CUE-DETR ONNX fp32 at
  `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx` or `VIBEMIX_CUE_ONNX_PATH`.
- Runtime: `onnxruntime` plus lazy cue-preprocessing packages. No torch is used
  for inference.
- Setup status: `uv run python -m vibemix library models --json` reports the
  CUE-DETR cache state. CUE-DETR is not auto-downloaded yet; the installer path
  waits for a stable hosted ONNX artifact.
- Preprocessing must stay local. `cue_detr.py` constructs the DETR processor
  config inline; no `from_pretrained()` network/cache lookup is allowed on the
  cue path.

## Contract

`src/vibemix/library/cue_types.py` owns the cross-session contract:

```python
CueAnchor(label, start_s, end_s, confidence, source)
```

Labels are `intro`, `build`, `breakdown`, `drop`, and `outro`. `end_s - start_s`
is the mixable excerpt window and must stay <=80 seconds. `confidence` is
currently position/downbeat-lock trust, not fine label certainty.

## Current Limitations

- Labels are intentionally coarse. Positions and mixable windows are the product
  value today; a Zehren-style downbeat-quantized classifier can replace the
  energy/position labeler later.
- The phrase lock is local and deterministic, built from existing DSP. madmom or
  a richer downbeat model is optional future work, not a bundled dependency.
- Heuristic fallback is honest fallback only. Do not present it as the premium
  cue engine when CUE-DETR is unavailable.

## Verification Surface

Focused checks:

```bash
uv run pytest -q tests/library/test_cue_engine.py tests/library/test_cue_refine.py
uv run ruff check src/vibemix/library/cue_detr.py tests/library/test_cue_engine.py
```

Product checks:

```bash
uv run python -m vibemix library models --json
uv run python -m vibemix library ingest --help
```

The active implementation map is
`.planning/research/CODEX-full-product-sweep-map.md`.
