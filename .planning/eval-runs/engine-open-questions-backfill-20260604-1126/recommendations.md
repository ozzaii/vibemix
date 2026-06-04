# Engine Open-Questions Backfill — 2026-06-04

Scope: backfill the three research questions that stayed unresolved in the Engine/DSP lane:
drop-detection accuracy bar, BPM/beatgrid approach, and loop licensing. This is an
eval/recommendation artifact, not product wiring.

## 1. Drop Detection Accuracy Bar

Recommendation:

- Keep live spoken "drop incoming" OFF until a local hardtechno/club-DJ benchmark clears a
  precision-first bar.
- Use CUE-DETR/ANLZ/heuristic drop or phrase anchors for offline cue receipts and pill
  explanations first; those surfaces can show uncertainty and do not interrupt the set.
- For a spoken live call, require a held-out Kaan library set with at least 20 tracks / 50
  hand-checked drop or phrase anchors, measured through `cue_agreement.py`.
- Suggested voice gate: precision >= 0.75 at the chosen timing tolerance, median absolute
  timing error <= 1 beat after beatgrid snap, and no "catastrophic early/late" calls on the
  reviewed set. Recall may be lower; false positives are worse than silence for Sven.
- Suggested visual/offline gate: beat current heuristic and reach at least the published
  phrase-level neighborhood of CUE-DETR on local material before making it default.

Grounding:

- CUE-DETR frames DJ cue-point estimation as object detection over spectrogram images and
  reports an EDM-CUE dataset of 4,710 EDM tracks / 21,461 expert cue annotations.
- Its published evaluation uses 101 held-out tracks / 607 cue annotations.
- The paper's strongest phrase-aligned F1 is 0.46 for 16-bar phrasing with the 8-bar
  postprocess radius; strict cue-only F1 is lower (0.39 at one-beat tolerance for the same
  radius, 0.27 at half-beat tolerance).
- That supports offline "candidate structure receipt" usage, but it does not justify a live
  voice trigger without a local precision-first bench.

Sources:

- https://ar5iv.org/html/2407.06823v1 — CUE-DETR method, EDM-CUE dataset, and evaluation
  table.
- https://arxiv.org/abs/2407.06823 — arXiv record for "Cue Point Estimation using Object
  Detection".
- Local proof: `.planning/eval-runs/anlz-cue-agreement-local-20260604-111746/report.json`
  showed ANLZ supply (`45` matched cached tracks, `360` PSSI anchors) but zero local DJ cue
  references, so no local agreement score can yet be claimed.

## 2. BPM / Beatgrid Approach

Recommendation:

- Source priority for product:
  1. DJ software beatgrid/TEMPO nodes from Rekordbox/ANLZ when present.
  2. A constant-grid estimate only when the track lacks DJ truth, with `bpm_source` preserved.
  3. BeatThis only as an eval candidate until bench numbers exist and the PyTorch packaging
     cost is explicitly accepted.
- The current bench is blocked honestly: `scripts/eval/beatgrid_compare.py` exists, but the
  truth manifest is missing. No BPM/beatgrid accuracy claim is shippable until
  `tests/bench/data/bpm_truth_manifest.json` (or equivalent Kaan Rekordbox truth export) is
  supplied.
- Bench metrics:
  - tempo exact within +/-1%;
  - alias accounting for half/double and 3:2 / 4:3 errors;
  - optional beat/downbeat F1 when beat positions are available;
  - per-genre breakdown, because the user failure mode is hardtechno/club material, not a
    generic pop benchmark.
- Implementation posture:
  - Keep the production ingest path torch-free unless the bench proves the PyTorch model is
    worth packaging.
  - Use BeatThis as a parallel eval executable first, then decide whether to host it,
    distill it, or keep it as a dev-bench only.

Grounding:

- BeatThis is the official ISMIR 2024 implementation, MIT licensed for code and published
  weights, but it requires PyTorch for inference.
- The BeatThis authors explicitly warn that evaluation can be unfairly good on training data
  and provide reproducible metric commands only with the correct annotation/spectrogram setup.
- The paper states it beats prior F1 without DBN postprocessing, while still failing on
  difficult/underrepresented genres and weaker continuity metrics. That maps well to an
  eval candidate, not a blind product swap.

Sources:

- https://github.com/CPJKU/beat_this — official implementation, requirements, evaluation
  commands, MIT license notice.
- https://arxiv.org/abs/2407.21658 — "Beat this! Accurate beat tracking without DBN
  postprocessing".
- Local proof: `.planning/eval-runs/beatgrid-bench-current-blocked-20260604-110711/`
  records the missing-manifest blocker for `scripts/eval/beatgrid_compare.py`.

## 3. Loop Licensing

Recommendation:

- Do not bundle commercial sample-pack loops, Splice/Loopmasters loops, or CC-NC/CC-ND
  loops as app assets or lesson examples.
- Safe default for bundled Learn/practice loops:
  1. original in-house recordings/rendered synth loops owned by Kaan/vibemix;
  2. commissioned loops with explicit assignment or redistribution rights;
  3. CC0 assets after provenance review;
  4. CC-BY only if attribution UX/docs are complete and the risk is acceptable.
- User-imported loops/tracks can remain local inputs; vibemix should not redistribute them,
  train on them, or export raw isolated samples unless the user explicitly owns that right.
- Treat "royalty-free for musical compositions" as not enough for bundling isolated loop
  files in a commercial app. That is redistribution/sublicensing risk, not normal song
  composition use.

Grounding:

- Freesound uses CC licenses and its FAQ distinguishes CC0/CC-BY/CC-BY-NC; NC cannot be used
  for money-making work, and user-upload provenance is not guaranteed.
- Creative Commons warns that NC prohibits commercial use, ND prohibits sharing adaptations,
  and CC licenses do not guarantee every right needed for a use case.
- Loopmasters allows commercial use of sounds as part of musical compositions with other
  sounds, which is not the same as bundling raw loops as app assets.
- Splice terms include non-commercial restrictions for free Create Tool stacks and restrict
  sublicensing/redistribution in ways that are unsuitable for shipping raw loop assets.

Sources:

- https://freesound.org/help/faq/ — Freesound licensing FAQ.
- https://creativecommons.org/faq/ — Creative Commons license element and rights-scope FAQ.
- https://help.loopmasters.com/hc/en-us/articles/7718328554772-Loopmasters-License-Agreement
  — Loopmasters license terms.
- https://splice.com/terms — Splice Terms of Use.

## Controller Profile Status

The requested "one more MIDI controller profile" cannot be landed inside the current island:
production profiles live under `src/vibemix/midi/**`, while the active island allows
`src/vibemix/platform/_hid_*.py` / `_audio_*.py`, `src/vibemix/library/**`,
`src/vibemix/intel/**`, `src/vibemix/audio/**`, `src/vibemix/__main__.py`
(capture/device only), `scripts/eval/**`, and their tests. The safe next move is either:

- widen the island to include `src/vibemix/midi/**` plus `tests/midi/**`, then add the
  controller profile from a manufacturer MIDI PDF cross-checked against Mixxx facts; or
- keep this lane on eval/proof work and leave profile authoring to the MIDI/profile lane.
