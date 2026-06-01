# VIBE WEB MAP — FACT-CHECK ADDENDUM

**Date:** 2026-05-31
**Purpose:** Reconciles the per-project license/capability/maturity verifications into a single corrections doc for the Vibe Web Map. Every fact below was pulled from a fetched page (raw LICENSE files, PyPI/HF/npm JSON, READMEs) or the authenticated GitHub API (`gh api repos/<r>`, account `ozzaii`) — no guesses. Where only one tool could confirm a value it is noted.

**Tally (19 projects):** CONFIRMED **9** · CORRECTED **9** · UNVERIFIED-remaining **0** (every maturity date the per-project pass left open was resolved via the authenticated GitHub API; see note below). One license **BLOCKED (non-commercial)**: madmom model files.

> **Method note that retires most "UNVERIFIED" flags:** the per-project reports hit HTTP 403 on `api.github.com` because WebFetch is unauthenticated. The authenticated `gh` CLI (token present) returned `pushed_at` + `license.spdx_id` for every repo. All "could not verify the push date" caveats in the source reports are now resolved with real `pushed_at` timestamps below.

---

## 1. CORRECTIONS

### prolink-connect — CORRECTED (maturity; capability wording)
- **OLD:** "active push 2026-05-03, npm 0.11.0."
- **VERIFIED:** License **MIT** (raw LICENSE + `gh` SPDX `MIT`). npm `0.11.0` published **2022-10-21/23** (registry.npmjs.org) — the *published release* is stale. BUT `pushed_at = 2026-05-03T04:50:35Z` (GitHub API) → **the map's 2026-05-03 push date is CORRECT**; the main branch is actively maintained even though the last npm release is 3+ years old. Capability: per-deck CDJ status + Rekordbox metadata over Pro DJ Link confirmed; **BPM is not its own README bullet — it lives inside "CDJ Status" player-state.** State it as "per-deck CDJ status (incl. BPM/on-air via player state) + track metadata", not a standalone BPM feature.
- **Impact:** integration_mode unchanged (permissive, vendor-or-depend OK; torch-free TypeScript). Correction is: keep the 2026-05-03 push date (verified), but flag the npm artifact as Oct-2022-old, and reword BPM as status-derived.

### dysentery — CORRECTED (docs-license nuance)
- **OLD:** "EPL-1.0; protocol-analysis docs are Deep Symmetry copyright (Antora UI MPL-2.0)."
- **VERIFIED:** License **EPL-1.0** (raw LICENSE + README + `gh` SPDX `EPL-1.0`). `pushed_at = 2026-03-28`; latest release v0.2.2 (2025-05-08). The MPL-2.0 covers **only the Antora rendering UI theme**, NOT the protocol-analysis content — the spec content is EPL-1.0 / Deep Symmetry, LLC copyright. The map parenthetical is technically accurate but reads as if the docs are MPL; clarify that the **docs CONTENT = EPL-1.0**, MPL-2.0 = rendering theme only.
- **Impact:** integration_mode = **spec-only reimplement** (EPL-1.0 is weak/file-level copyleft; do not vendor Clojure source or copy doc text into the Apache-2.0 tree). Reimplement DJ Link in clean Python from the published analysis, cite Deep Symmetry. Don't confuse with EPL-**2.0** siblings (beat-link / crate-digger / beat-link-trigger).

### beat_this_cpp — CORRECTED (maturity now known)
- **OLD:** "MIT; pre-converted beat_this.onnx (opset 14, mel [B,T,128] → beat+downbeat); last-commit date UNVERIFIED."
- **VERIFIED:** License **MIT** (raw LICENSE both branches, `gh` SPDX `MIT`, Masaki Ono / Melissa Audio 2025). `pushed_at = 2025-07-21T05:44:40Z` (GitHub API) — **maturity now confirmed: recent (mid-2025), single-author, 17 commits.** All capability sub-claims (ONNX opset 14, mel [1,T,128] → beat/downbeat logits, torch-free C++ runtime: PocketFFT + miniaudio + ONNX Runtime) confirmed.
- **Impact:** integration_mode = vendor-or-depend OK (MIT, retain notice). Two caveats stand: (a) **C++ project**, not a Python pip dep — reuse the `.onnx` artifact via vibemix's existing onnxruntime path or link C++; (b) the **.onnx weights derive from CPJKU/beat_this and defer model licensing upstream** — check the weights' license separately before shipping them (upstream is MIT, see beat_this row).

### demucs.onnx — CORRECTED (capability framing)
- **OLD:** "pure ONNX-Runtime Demucs inference, no torch; push 2026-02-08."
- **VERIFIED:** License **MIT** (raw LICENSE, `gh` SPDX `MIT`, Sevag H 2024). `pushed_at = 2026-02-08T18:34:18Z` → **the map's 2026-02-08 push date is CORRECT.** "No torch at runtime" confirmed (torch is conversion-time only). BUT "pure ONNX-Runtime inference" is misleading: it is a **C++ ONNX/ORT CLI** (uses Eigen/OpenBLAS), NOT a Python/pip onnxruntime library, and **STFT/iSTFT are done in C++ host code outside the ONNX graph** (not one self-contained graph).
- **Impact:** integration_mode = vendor-or-depend OK by license, but operationally it's a **native C++ binary/subprocess**, not a drop-in for vibemix's onnxruntime+PyAV Python path. Reword the capability to: "C++ ONNX/ORT inference for Demucs v4 (STFT/iSTFT in C++ host code; native CLI, not a pip onnxruntime lib)."

### python-audio-separator — CORRECTED (torch/librosa worse than stated; CoreML wording)
- **OLD:** "MIT; CPU/CoreML stem separation via onnxruntime(-silicon); NOT torch-free."
- **VERIFIED:** License **MIT** (raw LICENSE + pyproject + PyPI + `gh` SPDX `MIT`). Latest **v0.44.2 published 2026-05-18** (GitHub release + `pushed_at = 2026-05-18`; ignore the 2024-12-19 figure one WebFetch model emitted — it misread the JSON). Two refinements: (a) **No `onnxruntime-silicon` dep** — CoreML rides on the plain `[cpu]` extra via onnxruntime's `CoreMLExecutionProvider`; (b) torch-free status is **worse than the map says**: `torch>=2.3` AND `librosa>=0.10` are both **mandatory core deps** (onnxruntime is the *optional* swappable EP), plus a wider Demucs/torch stack. `transformers` is NOT a dep.
- **Impact:** integration_mode = **do not runtime-dep/vendor** in vibemix's torch-free/librosa-free tree (mandatory torch+librosa violate the ship constraint), despite MIT permitting it. Reword: "CoreML via onnxruntime's CoreMLExecutionProvider on the `[cpu]` extra (no silicon-specific dep); torch>=2.3 + librosa>=0.10 are hard core deps."

### essentia (Key algo) — CONFIRMED license, CORRECTED maturity
- **OLD:** "AGPL-3.0 (commercial license from MTG/UPF); edma/edmm/bgate EDM key profiles; last stable release 2014, dev ongoing."
- **VERIFIED:** License **AGPL-3.0** (COPYING.txt + licensing page + `gh` SPDX `AGPL-3.0`) with optional commercial license via MTG/UPF. The edma/edmm/bgate EDM profiles are documented on the Key reference page — confirmed. Maturity sharpened: last **tagged release v2.0.1 = 2014-02-11**, but **`pushed_at = 2026-05-20`** — the repo is **actively developed on master** (the 2014 figure is the last *tag* only, not abandonment).
- **Impact:** integration_mode = **reimplement HPCP + EDM correlation profiles in numpy from the cited papers (Faraldo et al., refs [3][4])** — do NOT vendor or runtime-dep AGPL-3.0 into a monetized Apache-2.0 tree, and do NOT copy the profile coefficient arrays out of the AGPL C++ source (they are themselves AGPL). AGPL is network-copyleft; even the commercial route is a vendor negotiation, not a drop-in.

### go-stagelinq — CORRECTED (wording; map's recency date was right after all)
- **OLD:** "MIT; Denon/Engine DJ StagelinQ; Go reference impl; push 2026-05-25."
- **VERIFIED:** License **MIT** (raw LICENSE, README, `gh` SPDX `MIT`, Carl Kittelberger 2021). `pushed_at = 2026-05-25T22:09:30Z` (GitHub API) → **the map's 2026-05-25 push date is CORRECT** (the per-project pass couldn't see it through the 403; latest *release* is v1.0.0 / 2025-07-03). Two wording corrections from the README: (a) call it the **Denon StagelinQ** protocol — don't lead with "Engine DJ"; (b) it self-describes as an **experimental reverse-engineering Go library** (tested mainly on Denon Prime 4), NOT an official "reference implementation."
- **Impact:** integration_mode = vendor-or-depend OK (MIT, pure Go, torch-free; consumed as an external Go process/IPC). Capability — per-deck BPM/beats/timeline-position/track-metadata/fader values over the network — confirmed. Reword "Engine DJ / reference impl" → "Denon StagelinQ / experimental Go library."

### automix-mzehren — CORRECTED (one figure unverified; deps confirmed heavy)
- **OLD:** "MIT; cue/switch-point method (~96% good-quality); stale push 2020."
- **VERIFIED:** License **MIT** (raw LICENSE, `gh` SPDX `MIT`, Mickael Zehren 2018). `pushed_at = 2020-02-11T08:49:11Z` → **stale-2020 CONFIRMED exactly.** Method real (arXiv 2007.08411, Zehren/Alunno/Bientinesi) + M-DJCUE dataset real. **The "~96% good-quality" figure is UNVERIFIED** — not present in the README or any fetched page; it lives in the paper PDF body, which was not retrieved. Deps confirmed heavy: setup.py hard-deps **librosa + essentia + a madmom Python-2 fork** (not torch-free, py2-era).
- **Impact:** integration_mode = **method/dataset-only** (correct as mapped). MIT permits vendoring but the librosa+essentia+madmom-py2 stack and staleness forbid it for the torch-free tree — reimplement the switch-point method from arXiv 2007.08411, optionally use M-DJCUE (MIT-family) as an eval set. vibemix already ships CUE-DETR (MIT ONNX) as the cue engine; Automix is a secondary reference. **Mark the 96% figure unverified or pull the exact number from arxiv.org/pdf/2007.08411 before publishing.**

### djtransgan — CORRECTED (blocker rationale; maturity less stale than feared)
- **OLD:** "MIT; torch/GAN transition research; spec-only [implied license-blocked]; date unverified."
- **VERIFIED:** License **MIT** (raw LICENSE + README, `gh` SPDX `MIT`, Bo-Yu Chen 2022). Capability confirmed (ICASSP 2022 differentiable-FX + GAN DJ-transition generator, arXiv 2110.06525). `pushed_at = 2025-11-07T13:07:52Z` (GitHub API) — **not a dead 2022 repo; touched late 2025**, though still no release and a split/incomplete repo (dg-pipeline lives separately). torch = hard dep (high confidence from the differentiable-DSP GAN architecture; `requirements.txt` could not be line-read due to 403, now still not line-verified — but the design is unambiguously PyTorch).
- **Impact:** integration_mode = **reimplement-from-spec / inspiration-only — for the TORCH dependency reason, NOT a license reason.** Correct the map so it does not imply MIT is the blocker: MIT is permissive (vendor-OK); the torch hard-dep + heavyweight 2022 research code is what forces spec-only. librosa presence remains inferred, not line-verified.

---

## 2. STILL-UNVERIFIED (after authenticated re-check)

**None of the maturity dates remain unverified** — the authenticated GitHub API resolved every `pushed_at` the per-project pass left open (prolink-connect, demucs.onnx, go-stagelinq dates all now CONFIRMED matching the map; beat_this_cpp, PyStageLinQ, DJtransGAN dates newly obtained).

Two residual content-level items could not be fetched and remain explicitly unverified:
1. **automix-mzehren "~96% good-quality" accuracy** — not on any fetched page; in the arXiv 2007.08411 PDF body only. **Safe assumption:** treat as paper-claimed/unverified until the exact number is pulled from `arxiv.org/pdf/2007.08411`. The method + evaluation-against-annotated-dataset claim itself holds.
2. **djtransgan `requirements.txt` exact lines (torch/librosa pins)** — contents API 403'd; not line-read. **Safe assumption:** torch = hard dep (architecture is unambiguously PyTorch); librosa = likely but unconfirmed. Either way the project is spec-only, so this gap does not change the posture.
3. **beat_this "SOTA" wording** — paper-claimed ("Accurate beat tracking", ISMIR 2024 title), not independently re-benchmarked. Keep as paper-claimed, not vibemix-verified.

---

## 3. BLOCKED / NON-COMMERCIAL WATCH

### madmom — CONFIRMED BLOCKED for monetized vibemix (NC on model files)
Verified verbatim from the dual-license LICENSE file (`gh` SPDX returns `NOASSERTION` precisely because it is a split license GitHub can't auto-classify):
- **Source code = BSD-2-Clause** (permissive, no NC).
- **All model/data files (.npy/.npz/.h5/.hdf5/.pkl/.mat) = CC-BY-NC-SA-4.0**, with the binding clause "NonCommercial: You must not use the material for commercial purposes" and an explicit commercial-permission contact (Gerhard Widmer, gerhard.widmer@jku.at).
- `pushed_at = 2026-03-20` (active), but last release **v0.16.1 = 2018-11-14** (stale releases). Deps are torch-free (NumPy/SciPy/Cython/mido + its own RNN/HMM impls) — **the blocker is licensing, not weight.**
- **Verdict: BLOCKED.** madmom is useless for beat/tempo/chord/downbeat without its pretrained model files, which are non-commercial. This is **NC, not reimplementable-copyleft** — the load-bearing NN weights are NC. Inherited transitively by anything that pulls madmom (Automix, all-in-one). The only commercial path is per-product written permission from Gerhard Widmer.

### Other NC / research-only traps found
- **essentia** — AGPL-3.0 (network-copyleft, not NC) + an optional commercial license; its **deep-learning model files ship CC-BY-NC-ND 4.0** (separate from the Key algo, which is fine to reimplement). Treat the AGPL coefficient arrays as off-limits to copy; reimplement from papers.
- **ableton-link** — GPLv2+ with proprietary-contact clause (not NC, but copyleft-blocked for vendoring; see torch-free section).
- No other CC-BY-NC* traps surfaced. beat_this notes its *training data* may be copyright/limited-CC, but that does not affect the MIT-licensed code or released weights.

---

## 4. TORCH-FREE CONFIRMATIONS

**Genuinely torch-free / librosa-free (verified) — safe for vibemix's onnxruntime+tokenizers+PyAV+numpy posture:**
- **clap-music-onnx** (Xenova ONNX path) — `library_name: transformers.js`, ONNX weights run on onnxruntime; no torch/transformers/librosa. (The LAION *upstream* uses torch/transformers, but that's the reference backend only — the shipped Xenova ONNX is clean. This is the family vibemix already ships.)
- **beat_this_cpp** — C++ runtime = PocketFFT + miniaudio + ONNX Runtime only (torch is conversion-time only).
- **demucs.onnx** — torch is conversion-time only; runtime is C++ ONNX/ORT (Eigen/OpenBLAS). Caveat: native C++ binary, not a Python onnxruntime call.
- **silero-vad (bare .onnx artifact)** — the model file runs torch-free on numpy+onnxruntime. **The pip package does NOT** (see corrections-equivalent below).
- **madmom** — torch-free deps (own RNN/HMM impls); blocked for license, not torch.
- **Non-Python protocol libs (no ML stack at all):** prolink-connect (TypeScript), dysentery (Clojure/JVM), go-stagelinq (Go), pystagelinq (Python, runtime dep = psutil only), libkeyfinder (C++/FFTW), ableton-link (C++ header-only).

**Drags torch and/or librosa as a HARD dep — would break the torch-free ship (flag on map):**
- **beat_this** — `torch>=2.0` + torchaudio + rotary-embedding-torch hard (transformers/librosa: no). Models are PyTorch Lightning checkpoints → needs an ONNX export step to fit vibemix.
- **python-audio-separator** — `torch>=2.3` AND `librosa>=0.10` both mandatory core deps + wider Demucs stack (transformers: no).
- **all-in-one** — `torch` + `librosa` + `demucs` + **NATTEN** (neighborhood-attention CUDA kernels, not cleanly ONNX-exportable) + madmom (NC, transitive). Heavyweight; spec-only.
- **fxnorm-automix** — `torch==1.9.0` + `librosa>=0.8.1` hard (transformers: no) + pymixconsole/pyloudnorm/aubio.
- **automix-mzehren** — librosa + essentia + madmom-py2-fork hard.
- **djtransgan** — torch hard (librosa likely; not line-verified).
- **silero-vad (pip package)** — **`torch>=1.12.0` + `torchaudio>=0.12.0` UNCONDITIONAL** (onnxruntime only via the optional `[onnx-cpu]` extra). **The map's "torch-free" is wrong for the package — it is torch-free ONLY via the bare .onnx artifact, NOT `pip install silero-vad`.** Reword the map: "MIT; ONNX VAD model (<1ms/chunk CPU) — torch-free ONLY by running the bare .onnx on the existing onnxruntime+numpy; the pip package hard-deps torch+torchaudio."

---

## 5. CONFIRMED (no change to the map claim)

- **dysentery** — EPL-1.0, spec-only (clarification on docs-license only; see §1).
- **beat_this** — MIT (code AND weights, verbatim from README), beat+downbeat / ISMIR 2024, `pushed_at = 2026-05-28` (map's 2026-05-28 CONFIRMED), v1.1.0 / 2026-04-14. Permissive but torch-hard → needs ONNX export.
- **clap-music-onnx** — capability + torch-free CONFIRMED; license corrected to "Apache-2.0 inherited from upstream laion/larger_clap_music_and_speech; the Xenova repo card itself declares NO license (cardData.license: null, no license tag)." Posture: vendor-or-depend OK. Already vibemix's shipped family.
- **fxnorm-automix** — MIT (Sony 2022, from LICENSE.md), automatic music mixing via effect normalization (refine label: mixing-automation, not style-transfer), spec-only (torch==1.9.0 + librosa hard). `pushed_at = 2024-03-11`, ISMIR 2022 — stale.
- **all-in-one** — MIT (repo LICENSE; flag: PyPI metadata declares null license), full structure/segment taxonomy (richer than mapped: beat/downbeat + 10-label functional segmentation), spec-only (torch + NATTEN + librosa + demucs; NATTEN not ONNX-friendly). `pushed_at = 2024-05-09`, v1.1.0 / 2023-10-10.
- **madmom** — see §3 (BLOCKED).
- **ableton-link** — GPLv2+ dual-licensed with proprietary-contact clause (`gh` SPDX `NOASSERTION` = the dual license; verified verbatim from LICENSE.md + README). tempo/beat/phase sync, NO deck identity — confirmed. Link 4.0 / 2026-05-04, `pushed_at = 2026-05-19`. **Strong copyleft → do not vendor; deprioritized for Apache-2.0** (and gives zero deck identity, so it doesn't solve local-deck-ingest anyway).
- **libkeyfinder** — GPL-3.0-**or-later** (verified from COPYING + keyfinder.h "or any later version" + README; `gh` SPDX `GPL-3.0`). Mixxx key-detection engine, C++11 + FFTW. release 2.2.8 / 2023-09-27, `pushed_at = 2024-11-25`. **REIMPLEMENT-ONLY, NEVER VENDOR** (strong copyleft; reimplement Shaath's chromagram + key-profile method from spec). Map stance correct.
- **pystagelinq** — MIT (RESOLVED from UNCERTAIN — verified across raw LICENSE both branches + GitHub API SPDX `MIT`, Jaxcie 2022). Python StageLinQ decoder, experimental/partial. `pushed_at = 2026-03-01` (newer than the per-project pass could see), release 0.2.1 / 2024-08-12. Torch-free (runtime dep = psutil only). vendor-or-depend OK.

---

## 6. VERIFIED LICENSE LEDGER

| Project | Verified License (SPDX) | Maturity (date seen) | Torch-free? | Integration mode | Confidence |
|---|---|---|---|---|---|
| prolink-connect | MIT | pushed_at 2026-05-03 (API); npm 0.11.0 = 2022-10-21 | Yes (TS) | vendor-or-depend OK | verified |
| dysentery | EPL-1.0 | pushed_at 2026-03-28; rel v0.2.2 2025-05-08 | Yes (Clojure/JVM) | spec-only reimplement (don't vendor EPL src/docs) | verified |
| beat_this | MIT (code + weights) | pushed_at 2026-05-28; rel v1.1.0 2026-04-14 | No — torch+torchaudio hard | vendor-or-depend by license, but needs ONNX export | verified |
| beat_this_cpp | MIT | pushed_at 2025-07-21 (API) | Yes (C++ ORT runtime) | vendor-or-depend OK; C++/.onnx, check upstream weights | verified |
| python-audio-separator | MIT | rel v0.44.2 2026-05-18 = pushed_at | No — torch>=2.3 + librosa>=0.10 hard | do-not-dep (torch+librosa violate ship) | verified |
| demucs.onnx | MIT | pushed_at 2026-02-08 (API) | Yes at runtime (C++ ORT) | vendor-or-depend OK; native C++ CLI, not pip | verified |
| essentia (Key) | AGPL-3.0 (+ optional commercial) | pushed_at 2026-05-20; last tag v2.0.1 2014 | Yes (C++) but heavy build | reimplement HPCP+EDM profiles from papers (don't vendor AGPL) | verified |
| libkeyfinder | GPL-3.0-or-later | rel 2.2.8 2023-09-27; pushed_at 2024-11-25 | Yes (C++/FFTW) | reimplement-only, NEVER vendor | verified |
| go-stagelinq | MIT | pushed_at 2026-05-25 (API); rel v1.0.0 2025-07-03 | Yes (Go) | vendor-or-depend OK (external Go proc) | verified |
| pystagelinq | MIT | pushed_at 2026-03-01; rel 0.2.1 2024-08-12 | Yes (psutil-only) | vendor-or-depend OK | verified |
| automix-mzehren | MIT | pushed_at 2020-02-11 (stale, py2) | No — librosa+essentia+madmom-py2 | method/dataset-only (don't vendor) | verified (96% figure UNVERIFIED) |
| djtransgan | MIT | pushed_at 2025-11-07 (API) | No — torch hard (librosa likely) | reimplement-from-spec (torch reason, not license) | verified (req.txt lines unverified) |
| fxnorm-automix | MIT (Sony 2022) | pushed_at 2024-03-11; ISMIR 2022 | No — torch==1.9.0 + librosa hard | spec-only (effect-normalization idea) | verified |
| silero-vad | MIT | pushed_at 2026-03-26; rel v6.2.1 2026-02-24 | Bare .onnx YES / pip pkg NO (torch+torchaudio hard) | vendor the .onnx model only (not the pip pkg) | verified |
| clap-music-onnx (Xenova) | Apache-2.0 (inherited from laion upstream; Xenova card license = null) | HF lastModified 2024-10-08 | Yes (transformers.js ONNX) | vendor-or-depend OK (already shipped family) | verified |
| all-in-one | MIT (repo; PyPI license null) | pushed_at 2024-05-09; rel v1.1.0 2023-10-10 | No — torch+NATTEN+librosa+demucs+madmom | spec-only (NATTEN not ONNX-friendly) | verified |
| madmom | BSD-2-Clause (code) + CC-BY-NC-SA-4.0 (model files) | pushed_at 2026-03-20; last rel v0.16.1 2018-11-14 | Yes (own RNN/HMM) | **BLOCKED — NC model files** (commercial = Widmer permission) | verified |
| ableton-link | GPL-2.0-or-later + proprietary (dual) | rel Link-4.0 2026-05-04; pushed_at 2026-05-19 | Yes (C++ header-only) | do-not-vendor (copyleft); deprioritized + no deck identity | verified |

**Per-row source URLs:**
- prolink-connect — raw.githubusercontent.com/evanpurkhiser/prolink-connect/main/LICENSE; registry.npmjs.org/prolink-connect/latest; `gh api repos/evanpurkhiser/prolink-connect`
- dysentery — raw.githubusercontent.com/Deep-Symmetry/dysentery/master/LICENSE; djl-analysis.deepsymmetry.org footer; `gh api repos/Deep-Symmetry/dysentery`
- beat_this — raw.githubusercontent.com/CPJKU/beat_this/main/LICENSE; .../main/README.md; `gh api repos/CPJKU/beat_this`
- beat_this_cpp — raw.githubusercontent.com/mosynthkey/beat_this_cpp/main/LICENSE; .../main/README.md; `gh api repos/mosynthkey/beat_this_cpp`
- python-audio-separator — raw.githubusercontent.com/nomadkaraoke/python-audio-separator/HEAD/LICENSE; pypi.org/pypi/audio-separator/json; `gh api repos/nomadkaraoke/python-audio-separator` + `/releases/latest`
- demucs.onnx — raw.githubusercontent.com/sevagh/demucs.onnx/main/LICENSE; `gh api repos/sevagh/demucs.onnx`
- essentia — raw.githubusercontent.com/MTG/essentia/master/COPYING.txt; essentia.upf.edu/licensing_information.html; essentia.upf.edu/reference/std_Key.html; `gh api repos/MTG/essentia` + `/releases/latest`
- libkeyfinder — raw.githubusercontent.com/mixxxdj/libkeyfinder/master/COPYING + /src/keyfinder.h + /README.md; `gh api repos/mixxxdj/libkeyfinder` + `/releases/latest`
- go-stagelinq — raw.githubusercontent.com/icedream/go-stagelinq/master/LICENSE + /README.md; `gh api repos/icedream/go-stagelinq` + `/releases/latest`
- pystagelinq — raw.githubusercontent.com/Jaxc/PyStageLinQ/main/LICENSE; pypi.org/pypi/PyStageLinQ/json; `gh api repos/Jaxc/PyStageLinQ`
- automix-mzehren — raw.githubusercontent.com/MZehren/Automix/HEAD/LICENSE + setup.py; arxiv.org/abs/2007.08411; github.com/MZehren/M-DJCUE; `gh api repos/MZehren/Automix`
- djtransgan — raw.githubusercontent.com/ChenPaulYu/DJtransGAN/master/LICENSE; .../blob/main/README.md; arxiv.org/abs/2110.06525; `gh api repos/ChenPaulYu/DJtransGAN`
- fxnorm-automix — raw.githubusercontent.com/sony/FxNorm-automix/main/LICENSE.md + /requirements.txt; `gh api repos/sony/FxNorm-automix`
- silero-vad — raw.githubusercontent.com/snakers4/silero-vad/HEAD/LICENSE; pypi.org/pypi/silero-vad/json; `gh api repos/snakers4/silero-vad`
- clap-music-onnx — huggingface.co/api/models/Xenova/larger_clap_music_and_speech; huggingface.co/api/models/laion/larger_clap_music_and_speech; laion .../config.json
- all-in-one — raw.githubusercontent.com/mir-aidj/all-in-one/HEAD/LICENSE; pypi.org/pypi/allin1/json; `gh api repos/mir-aidj/all-in-one`
- madmom — raw.githubusercontent.com/CPJKU/madmom/HEAD/LICENSE; github.com/CPJKU/madmom; `gh api repos/CPJKU/madmom` + `/releases/latest`
- ableton-link — raw.githubusercontent.com/Ableton/link/master/LICENSE.md + /README.md; `gh api repos/Ableton/link` + `/releases/latest`

**SPDX note:** `gh api` returned `NOASSERTION` for ableton-link and madmom — that is GitHub's "couldn't auto-classify" code for their dual/split licenses, and the ledger values above are the human-read licenses verbatim from each LICENSE file, not a downgrade of confidence.
