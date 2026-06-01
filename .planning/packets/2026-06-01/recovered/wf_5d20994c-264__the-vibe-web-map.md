# THE VIBE WEB MAP

**Date:** 2026-05-31
**Purpose:** The open-source DJ + music-information-retrieval (MIR) ecosystem mapped to vibemix's known gaps — what to learn, reimplement, reuse, or interop, with every license and capability claim pulled from a fetched page.

**Counts:** 14 finds kept (4 inherited from the fact-check packet + 10 new this run).
**By integration_mode:** `protocol_interop` 4 · `learn_algorithm` (reimplement-from-spec) 4 · `model_reuse` 3 · `runtime_dep / vendor-or-depend` 3.
**License posture:** 9 permissive (MIT/Apache/BSD) · 3 EPL (weak-copyleft, file-level) · 2 AGPL/GPL (reimplement-only) · 1 mixed dual-license caution. Zero finds are research-only/non-commercial-blocked except where flagged in §4.

---

## 2. THE LEVEL-UPS (ranked by leverage)

### #1 — prolink-connect (Pioneer Pro DJ Link, live deck identity off-the-wire)
- **Unlocks:** The single biggest gap. Today Gemini only gets the global mix WAV. prolink-connect gives vibemix per-deck ground truth straight off the network: per-CDJ status (`CDJStatus.State`), which deck is master, on-air status, BPM, plus full Rekordbox track metadata (artist/title/key/beatgrid) for the loaded track on each player. This is the "trust the audio" invariant (#3) upgraded to "trust the wire" — the AI stops guessing which deck moved.
- **Gap filled:** live deck identity + per-deck track/BPM/beatgrid context.
- **License:** MIT (`The MIT License (MIT)`, Copyright 2013 Evan Purkhiser — fetched LICENSE). **integration_mode: protocol_interop** (it is TypeScript, not Python — but the wire protocol is the asset; either run it as a Node sidecar/IPC source, or reimplement the UDP packet parsing in Python from the same spec).
- **Torch-free:** Yes, irrelevant to torch — pure network I/O, zero ML.
- **First step:** Stand up prolink-connect as a tiny Node helper emitting deck-state JSON onto the existing ws bus (`127.0.0.1:8765` is taken; use a side channel) and feed it into `state/deck_context.py` as a new evidence source. Or reimplement the ~handful of UDP packet types in Python using the dysentery spec (#3 below).
- **Maturity:** Active — last push 2026-05-03; npm `0.11.0` (2022-10-23) is the published package but the repo is fresher.

### #2 — DJ Link Ecosystem Analysis ("dysentery" / djl-analysis.deepsymmetry.org)
- **Unlocks:** The language-independent, reverse-engineered Pro DJ Link **protocol spec** — beat packets, BPM, absolute position, Channels-On-Air, master handoff, detailed device status, metadata queries. This is the document that lets vibemix reimplement deck-identity in **pure Python** (no Node, no native dep) and stay clean. It is the spec behind both prolink-connect and beat-link.
- **Gap filled:** live deck identity (the from-scratch path) + beatgrid/position semantics.
- **License:** The analysis prose is `Copyright © 2016–2023 Deep Symmetry, LLC` published as docs (the Antora UI is MPL-2.0); the dysentery tool itself is **EPL-1.0** (fetched). Reimplementing a wire protocol from a published analysis is the textbook `learn_algorithm` path — facts about a packet format are not copyrightable. **integration_mode: learn_algorithm / protocol_interop.**
- **Torch-free:** Yes — a Python `asyncio` UDP listener, no deps beyond stdlib + numpy.
- **First step:** Implement the beat + CDJ-status + on-air packet parsers (UDP ports per the spec) as `platform/_prolink_*.py`, gated behind a feature flag, graceful-fallback when no DJ Link network present (mirrors the existing DDJ-FLX4 optional pattern).

### #3 — beat_this (CPJKU) + the mosynthkey ONNX port (real beatgrids/downbeats for beatmatch grading)
- **Unlocks:** State-of-the-art beat **and downbeat** tracking (ISMIR 2024, "without DBN postprocessing"). This is the missing primitive for beatmatch grading and "did they mix on the phrase/downbeat?" — the Vibe Judge needs real downbeats, not just a BPM number. The upstream is torch-only, BUT `mosynthkey/beat_this_cpp` ships a **pre-converted `beat_this.onnx`** (opset 14, input `input_spectrogram` [B, T, 128] mel → outputs `beat` + `downbeat` logits [B, T]) — exactly vibemix's onnxruntime + mel pattern.
- **Gap filled:** beatgrid/downbeat for beatmatch + feeds drop/phrase structure.
- **License:** upstream code **and published model weights are MIT** (`MIT License, Copyright (c) 2024 Institute of Computational Perception, JKU Linz` — fetched LICENSE; README: "code and the published model weights are released under the MIT license"). The C++/ONNX port is **MIT** (`Copyright (c) 2025 Masaki Ono / Melissa Audio` — fetched LICENSE). **integration_mode: model_reuse** (vendor the ONNX weights + reimplement the mel front-end + logit post-processing in numpy).
- **Torch-free:** Yes via the ONNX port — keeps the ship constraint. (The official `pip install beat-this` pulls PyTorch 2.0 + `rotary-embedding-torch`; do NOT take that path.)
- **First step:** Pull `beat_this.onnx` into `~/.cache/vibemix/` (new optional model under `library models --install`), write the mel→onnxruntime→beat/downbeat numpy wrapper, and grid-align it against the live-detected BPM. Both repos actively maintained (upstream pushed 2026-05-28).

### #4 — python-audio-separator (per-deck/per-stem audio isolation, torch-free path)
- **Unlocks:** Per-deck audio isolation is on the gap list, and the deeper unlock is **per-stem** isolation — splitting the mix into vocals/drums/bass/other so the co-host can say "you brought the vocal in over the drop" with evidence. Supports CPU-only and **CoreML on Apple Silicon** via onnxruntime.
- **Gap filled:** per-deck/per-stem audio isolation.
- **License:** MIT (fetched repo license). **integration_mode: runtime_dep** (optional `[ai-local]`/new extra; it is a real pip dep, not vendored).
- **Torch-free:** **Partial — this is the catch.** Its dependency list is `torch, onnx, onnxruntime, numpy, librosa, ...` and the README's per-architecture table shows MDX-Net / VR / Demucs / MDXC **all** list `torch` + `onnxruntime`. So the convenient package pulls torch + librosa, breaking the ship constraint. The clean alternative: `sevagh/demucs.onnx` (**MIT**, "C++ ONNX/ORT inference for Demucs", pushed 2026-02-08) — pure ONNX-Runtime Demucs with no torch — as the torch-free reference to wrap, OR run separator as an **offline set-prep job** behind an opt-in extra where torch is tolerated, never in the live torch-free path.
- **First step:** Spike `demucs.onnx` model export for a single 2-stem (vocal/instrumental) pass on CPU; if RTF is acceptable, wrap as offline pre-analysis feeding the evidence registry. Keep it out of the live loop.

### #5 — essentia Key (edma/edmm/bgate EDM profiles) — source-key detection accuracy
- **Unlocks:** Accurate source-key detection (the upstream of vibemix's existing deterministic Camelot table). HPCP chromagram + selectable EDM-tuned profile bank (edma/edmm/bgate beat Shaath's on electronic music).
- **Gap filled:** key detection.
- **License:** **AGPL-3.0** (+ optional commercial license from MTG/UPF). **integration_mode: learn_algorithm** — reimplement HPCP + profile-correlation + the published edma/bgate profile vectors in numpy. Do NOT vendor AGPL source, and do NOT take essentia as a runtime dep (it is a heavyweight C++/FFmpeg/Eigen binary outside the onnxruntime+PyAV+numpy footprint).
- **Torch-free:** Reimplementation is pure numpy DSP — torch-free and light. The binary dep is not.
- **First step:** Implement HPCP (12-bin chroma) + Krumhansl-style correlation against the edma profile vector as `state/detectors/key_estimate.py`; validate against Rekordbox-tagged keys you already import.

### #6 — go-stagelinq + PyStageLinQ (Denon deck identity — the other half the install base)
- **Unlocks:** Live deck state for **Denon/Engine DJ** gear (the Pioneer-equivalent for the other big hardware ecosystem): per-deck BPM, current/total beats, timeline position, track metadata, fader values, play state. Covers Denon Prime users that prolink-connect cannot.
- **Gap filled:** live deck identity (Denon side).
- **License:** go-stagelinq **MIT** (fetched: "This code is licensed under the MIT license"); PyStageLinQ (Jaxc) is the Python option (read track info, crossfader/channel/pitch faders, BPM). **integration_mode: protocol_interop** — PyStageLinQ is directly importable Python; go-stagelinq is the cleaner reference impl + its blog writeup documents the protocol for reimplementation.
- **Torch-free:** Yes — network I/O only.
- **First step:** Evaluate PyStageLinQ as an optional Python dep behind a `denon` extra feeding `deck_context.py`, mirroring the prolink path; fail-closed when no Denon device on the LAN. (Both are flagged **experimental** reverse-engineering — gate behind a feature flag, never assume presence.)

### #7 — Automix + the cue-point paper (MZehren, transition-quality / cue grounding)
- **Unlocks:** A published, MIT-licensed methodology for **cue/switch-point detection** with a measured quality bar ("about 96% of the points generated by our methodology are of good quality for use in a DJ mix" — fetched arXiv 2007.08411), plus the M-DJCUE annotated dataset. This is a spec for the Vibe Judge's transition-quality scoring and for grounding "this was a clean cue" claims — complements vibemix's existing CUE-DETR engine with a rules-from-DJ-interviews second opinion.
- **Gap filled:** transition-quality/automix + cue grounding.
- **License:** MIT (`Copyright (c) 2018 Mickael Zehren` — fetched LICENSE). **integration_mode: learn_algorithm** — the value is the method + dataset, not the code (the repo is a madmom fork, Python-2-era drum model, last push 2020 → do not depend on it).
- **Torch-free:** Reimplemented (novelty analysis on existing features) is light; the original depends on madmom (see §4 license note).
- **First step:** Lift the novelty-curve cue-detection method as a validation cross-check against CUE-DETR outputs; pull M-DJCUE as a labeled eval set for the Judge.

---

## 3. PER-GAP MAP

| vibemix gap | best OSS option(s) | the call |
|---|---|---|
| **per-deck audio isolation** | `python-audio-separator` (MIT) / `sevagh/demucs.onnx` (MIT) | Use `demucs.onnx` as the torch-free reference; run stem-split as an **offline set-prep** job, never in the live torch-free loop. The convenient pip package drags in torch+librosa — avoid in-tree. |
| **live deck identity** | `prolink-connect` (MIT, Pioneer) + `dysentery` spec (EPL/docs) ; `go-stagelinq`/`PyStageLinQ` (MIT, Denon) | Reimplement Pro DJ Link UDP parsing in pure Python from the dysentery spec (cleanest, no native dep). Add Denon via PyStageLinQ behind an optional extra. Both feature-flagged + fail-closed. **Highest-leverage gap.** |
| **beatgrid/downbeat for beatmatch** | `beat_this` ONNX port (MIT weights + MIT port) | Vendor `beat_this.onnx`, reimplement mel front-end + logit post-proc in numpy. Best torch-free downbeat primitive available. |
| **drop/structure/phrase** | All-In-One (MIT spec) [inherited] + `beat_this` downbeats | Keep All-In-One as the segment-taxonomy SPEC (it's torch+NATTEN, not shippable); pair with beat_this downbeats for the runtime phrase grid. |
| **key detection** | `essentia` Key edma/bgate (AGPL — reimplement) ; `libKeyFinder` (GPL-3.0 — reimplement) | Reimplement HPCP + EDM key profiles in numpy from essentia's spec. libKeyFinder is the GPL-3.0 cross-reference (Mixxx's own key engine, FFTW C++) — learn-the-algorithm only, never vendor. |
| **transition-quality / automix** | `Automix` + cue-point paper (MIT, ~96% claim) ; `DJtransGAN` (MIT) ; `FxNorm-automix` (MIT) | Lift Automix's novelty cue method + M-DJCUE dataset as a Judge cross-check/eval. DJtransGAN/FxNorm are torch/GAN research — spec-only, not runtime. |
| **torch-free runtime** | Silero VAD (MIT) [inherited] ; Xenova/onnx-community CLAP `larger_clap_music` (Apache-2.0) [inherited] | VAD = mic-gating / self-voice rejection (anti-loopback). CLAP `music` variant = drop-in 512-dim swap for better genre separation. Both already fit the onnxruntime stack. |

**Tempo/beat-sync interop side-note:** Ableton **Link** (dual GPLv2+/proprietary) and `aalink` (GPL-3.0) sync tempo/beat/phase across apps. Tempo-only, no deck identity. GPL + a commercial-contact clause for closed apps → for vibemix (open-source Apache-2.0 app) GPL linking is a license-compatibility question; given it adds only tempo (which vibemix already detects), **deprioritize** — the deck-identity protocols above deliver far more per the same network effort.

---

## 4. LICENSE LEDGER

| project | license | integration_mode | can we use it, and how |
|---|---|---|---|
| prolink-connect | MIT | protocol_interop | Free to vendor/depend. TS → run as sidecar or reimplement protocol in Python. |
| dysentery / djl-analysis | EPL-1.0 (tool) + Deep Symmetry docs | learn_algorithm | Reimplement the **protocol** in Python from the published analysis (packet facts aren't copyrightable). Don't copy the Clojure source. |
| beat_this (upstream) | MIT (code + weights) | model_reuse | Free to vendor weights + reimplement front-end. Avoid the torch pip path. |
| beat_this_cpp ONNX port | MIT (Masaki Ono / Melissa Audio) | model_reuse | Free to take the `beat_this.onnx` artifact. |
| python-audio-separator | MIT | runtime_dep | Free to depend — but **drags torch+librosa**; keep offline-only (see §5). |
| sevagh/demucs.onnx | MIT | learn_algorithm / model_reuse | Free; torch-free ONNX Demucs reference to wrap for stems. |
| essentia (Key/HPCP) | **AGPL-3.0** (+ commercial) | learn_algorithm | **Reimplement from spec ONLY.** Never vendor source; do not take the C++ binary as a dep. |
| libKeyFinder | **GPL-3.0-or-later** | learn_algorithm | **Reimplement from spec ONLY** (Mixxx's key engine). Never vendor. |
| go-stagelinq | MIT | protocol_interop | Free; Go reference impl + protocol writeup for reimplementation. |
| PyStageLinQ (Jaxc) | MIT (per fetched LICENSE) | protocol_interop / runtime_dep | Free to depend (Python). Flagged experimental — feature-gate. |
| Automix (MZehren) | MIT | learn_algorithm | Free; lift the cue method + M-DJCUE dataset. Repo itself is stale (madmom fork, 2020). |
| DJtransGAN | MIT | learn_algorithm | Free; torch/GAN research — spec only. |
| FxNorm-automix (Sony) | MIT | learn_algorithm | Free; torch research — spec only. |
| Silero VAD [inherited] | MIT | model_reuse | Free; torch-free ONNX. |
| Xenova/onnx CLAP music [inherited] | Apache-2.0 | model_reuse | Free; drop-in 512-dim swap. |
| All-In-One [inherited] | MIT | learn_algorithm | Free; spec only (torch+NATTEN, not shippable). |
| Ableton Link | dual GPLv2+/proprietary | (deprioritized) | GPL + closed-app contact clause; low marginal value (tempo only). |
| aalink | GPL-3.0 | (deprioritized) | GPL Python binding for Link; same low-value verdict. |
| **madmom** (transitive via Automix/All-In-One) | **BLOCKED for runtime** | — | **Dual license: BSD code BUT model/data files are CC BY-NC-SA 4.0 — "You must not use the material for commercial purposes"** (fetched LICENSE). For vibemix's monetized Free/Pro/Studio posture, **do not ship madmom models.** Reimplement or use MIT-weighted beat_this instead. |
| beat-link / crate-digger (Deep Symmetry, Java) | EPL-2.0 (crate-digger: EPL-2.0 + secondary MPL-2.0/LGPL-3.0) | reference | Java; not a direct dep. Useful as protocol/ANLZ-parsing reference alongside pyrekordbox (which vibemix already uses). |

**BLOCKED flags:** `madmom` model weights (CC BY-NC-SA, non-commercial) — avoid in any shipped artifact. `essentia` and `libKeyFinder` are not blocked but are reimplement-only (AGPL/GPL). Everything else is clear for vibemix's commercial posture.

---

## 5. TORCH-FREE GUARD

Finds that would break the torch-free / transformers-free / librosa-free ship constraint if taken naively, with the lighter path:

- **beat_this (official pip):** pulls **PyTorch 2.0 + rotary-embedding-torch + torchaudio**. → **Lighter path:** the `mosynthkey/beat_this_cpp` **MIT ONNX export** (`beat_this.onnx`, opset 14) run on onnxruntime + a numpy mel front-end. ✅ ships clean.
- **python-audio-separator:** dependency list is `torch, onnx, onnxruntime, numpy, **librosa**` and every architecture (MDX/VR/Demucs/MDXC) lists torch. → **Lighter path:** `sevagh/demucs.onnx` (MIT, pure ORT, no torch) wrapped for stems, OR run separation as an **offline set-prep extra** where torch is acceptable — never the live loop.
- **All-In-One [inherited]:** PyTorch + Demucs + **NATTEN** (neighborhood-attention ops complicate ONNX export). → **Lighter path:** use only as the segment-taxonomy SPEC; get the runtime beat/downbeat grid from beat_this ONNX.
- **essentia:** C++ binary with FFmpeg/Eigen/TagLib — a heavyweight native dep outside the onnxruntime+PyAV+numpy footprint (not torch, but still a footprint break). → **Lighter path:** reimplement HPCP + EDM key profiles in numpy (also dodges AGPL).
- **libKeyFinder:** C++11 + **FFTW3** native dep. → **Lighter path:** numpy FFT chromagram (no FFTW), reimplemented from the same Krumhansl/Shaath-profile method.
- **Automix / DJtransGAN / FxNorm-automix / aalink:** madmom / torch / GAN / C++ Link binding respectively. → Spec/method only; nothing enters the runtime.

**Clean as-is (no torch, fit the stack):** prolink-connect (network), dysentery-spec reimpl (stdlib+numpy), go-stagelinq/PyStageLinQ (network), beat_this.onnx (onnxruntime), demucs.onnx (ORT), Silero VAD (ONNX), CLAP music variant (ONNX).

---

## 6. FULL TABLE

| lane | project | license | integration_mode | local_feasible | value | gap | url |
|---|---|---|---|---|---|---|---|
| live deck identity (Pioneer) | prolink-connect | MIT | protocol_interop | yes (TS sidecar or PY reimpl; torch-free) | high | live deck identity | https://github.com/evanpurkhiser/prolink-connect |
| live deck identity (spec) | dysentery / DJ Link Ecosystem Analysis | EPL-1.0 tool + Deep Symmetry docs | learn_algorithm | yes (pure-Python UDP reimpl) | high | live deck identity + beatgrid/position | https://djl-analysis.deepsymmetry.org/ |
| beatgrid/downbeat | beat_this (CPJKU) | MIT (code + weights) | model_reuse | via ONNX port only (official path is torch) | high | beatgrid/downbeat for beatmatch | https://github.com/CPJKU/beat_this |
| beatgrid/downbeat (torch-free) | mosynthkey/beat_this_cpp (beat_this.onnx) | MIT | model_reuse | yes (onnxruntime, opset 14, mel→logits) | high | beatgrid/downbeat for beatmatch | https://github.com/mosynthkey/beat_this_cpp |
| per-deck/stem isolation | python-audio-separator | MIT | runtime_dep | CPU/CoreML yes BUT pulls torch+librosa | medium | per-deck audio isolation | https://github.com/nomadkaraoke/python-audio-separator |
| per-deck/stem isolation (torch-free) | sevagh/demucs.onnx | MIT | learn_algorithm / model_reuse | yes (pure ONNX/ORT, no torch) | medium | per-deck audio isolation | https://github.com/sevagh/demucs.onnx |
| key detection | essentia Key (edma/bgate) | AGPL-3.0 (+commercial) | learn_algorithm | reimpl pure-numpy yes; binary dep no | high | key detection | https://essentia.upf.edu/reference/std_Key.html |
| key detection (GPL ref) | libKeyFinder (mixxxdj) | GPL-3.0-or-later | learn_algorithm | reimpl yes; native FFTW dep no | medium | key detection | https://github.com/mixxxdj/libkeyfinder |
| live deck identity (Denon) | go-stagelinq | MIT | protocol_interop | yes (network; Go ref) | high | live deck identity | https://github.com/icedream/go-stagelinq |
| live deck identity (Denon, Python) | PyStageLinQ (Jaxc) | MIT | protocol_interop / runtime_dep | yes (Python, experimental) | medium | live deck identity | https://github.com/Jaxc/PyStageLinQ |
| transition-quality / cue | Automix + cue-point paper (M-DJCUE) | MIT | learn_algorithm | method/dataset yes; repo stale (madmom/py2) | medium | transition-quality / cue grounding | https://github.com/MZehren/Automix |
| transition-quality | DJtransGAN | MIT | learn_algorithm | spec only (torch/GAN) | low | transition-quality/automix | https://github.com/ChenPaulYu/DJtransGAN |
| transition-quality | FxNorm-automix (Sony) | MIT | learn_algorithm | spec only (torch) | low | automix/mixing | https://github.com/sony/FxNorm-automix |
| torch-free runtime (VAD) | Silero VAD [inherited] | MIT | model_reuse | yes (ONNX, <1ms/chunk CPU) | high | self-voice/mic-gating | https://github.com/snakers4/silero-vad |
| torch-free runtime (embed) | Xenova/onnx CLAP larger_clap_music [inherited] | Apache-2.0 | model_reuse | yes (onnxruntime, 512-dim) | medium | strengthen CLAP genre separation | https://huggingface.co/Xenova/larger_clap_music_and_speech |
| drop/structure/phrase | All-In-One (mir-aidj) [inherited] | MIT | learn_algorithm | spec only (torch+NATTEN) | medium | drop/structure/phrase | https://github.com/mir-aidj/all-in-one |
| key detection (source profiles) | essentia (HPCP primitive) [inherited] | AGPL-3.0 | learn_algorithm | reimpl pure-numpy | high | key detection | https://essentia.upf.edu/reference/std_Key.html |
| tempo sync (deprioritized) | Ableton Link / aalink | GPLv2+ dual / GPL-3.0 | (deprioritized) | GPL + commercial-clause | low | tempo sync (low marginal value) | https://github.com/Ableton/link |

---

**Honesty / caveats:**
- **Maturity proven from fetched pages:** prolink-connect (push 2026-05-03), go-stagelinq (2026-05-25), beat_this (2026-05-28, v1.1.0 2026-04-14), beat_this_cpp (MIT, 2025 copyright), demucs.onnx (2026-02-08), libKeyFinder (2024-11-25, GPL-3.0), DJtransGAN (2025-11-07), crate-digger (2026-03-13, EPL-2.0). Automix is **stale** (last push 2020-02-11, madmom/Python-2 fork) — use as spec, not code.
- **PyStageLinQ license** read as MIT from search-surfaced fetches; the direct GitHub LICENSE API returned 403/404 this run — **verify the exact SPDX from the repo before depending.** go-stagelinq MIT is verified from the fetched README + pkg.go.dev licenses tab.
- **madmom non-commercial trap is the load-bearing license finding:** its model/data files are CC BY-NC-SA 4.0 (verified verbatim) — it sits transitively under Automix and All-In-One and must not enter any shipped vibemix artifact.
- **essentia/libKeyFinder are reimplement-only** under the project hard rule (AGPL/GPL) — the HPCP+EDM-profile method is the asset, not the binary.
- **The #1 leverage move is deck identity off-the-wire** (Pro DJ Link + StagelinQ) — MIT/permissive protocols, torch-free, and it directly fixes the documented live slop bug (ungrounded "you brought the faders up" with `recent_moves=[]`): the wire knows which deck moved when the global-mix WAV cannot.
