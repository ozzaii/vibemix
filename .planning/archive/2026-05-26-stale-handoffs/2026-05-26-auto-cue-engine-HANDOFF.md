# Auto-Cue Engine — HANDOFF (2026-05-26)

> Read this first if you're picking up the auto-cue engine. Companion to the design spec
> `2026-05-26-auto-cue-engine-design.md`. Status: **mid-pivot** — a shipped numpy heuristic
> exists but is being replaced by a literature-backed model (see DECISION — CUE-DETR adopted,
> exported to ONNX, runs LOCAL with NO torch; engine wired + verified end-to-end). Branch:
> `live-tuning-or-brain`. Nothing committed.

## What this is

Auto-cue = vibemix's moat: detect mixable cue points + structural function
(intro / build / breakdown / drop / outro) from RAW AUDIO, offline at ingest. Producer
session (`source="auto"`); ingest/consumer is a separate session. Shared seam = **fixed**:
`src/vibemix/library/cue_types.py` → `CueAnchor(label, start_s, end_s≤80s, confidence, source)`.

## The journey (so the next session doesn't repeat it)

1. **Shipped a pure-numpy/scipy heuristic** (`cue_detect.py`, upgraded from v0.5): sub-bass
   (20–100Hz) energy curve → kill/reentry edges → drop = kick re-entry after a sustained
   breakdown, breakdown = the bass-cut. Foote-novelty was tried and removed. CueAnchor
   migration done, `embed.py` consumer wired to `end_s`, `CueAnchor` exported, tests green
   (full suite 395 passed / 1 xfail).
2. **Ran it live on real tracks (Kaan's ear) — it failed.** Two confirmed problems:
   - On brick-walled hardtechno the energy contrast is tiny, so an energy-ranked "drop" is
     indistinguishable from the intro groove.
   - The sub-bass kill/reentry detector fires on brief bass *dips*, producing mechanically
     impossible structure — e.g. ANGER got "breakdown 2:02, **3 seconds after** drop 1:59".
3. **Root cause (confirmed by the literature):** a single-feature sub-band energy threshold
   is the textbook degenerate case. Zehren's 2024 interpretability paper shows **energy
   novelty alone cannot separate a breakdown from a drop** (both are big energy transitions —
   direction + surrounding structure matter), and every established method **quantizes
   candidates to downbeats and enforces 4-bar/phrase periodicity** before scoring. The
   heuristic had no downbeat backbone. → **Stop hand-tuning thresholds. Adopt the literature.**

## The established methods (research, all surveyed)

| System | What | License | Output | Notes |
|---|---|---|---|---|
| **CUE-DETR** (ETH-DISCO, ISMIR 2024) | DETR object-detection on log-Mel spectrogram, sliding window → conf threshold → phrase-radius peak | **MIT**, weights on HF `disco-eth/cue-detr` | cue **positions** (phrase-snapped), NOT labels | **F₁ 0.46 vs MIK 0.16 / Automix 0.15 (~3×).** Py3.11 + torch. Repo `github.com/ETH-DISCO/cue-detr`. |
| **Zehren Automix** (CMJ 2022) | downbeat-quantized, 4-bar periodic, multi-feature novelty (**energy + timbre + drum-onset + harmony**), gradient-boosted classifier | **MIT** (code), M-DJCUE dataset GPL-3.0 (eval-only) | **labels** (intro/build/breakdown/drop/outro) | Py2, unmaintained → **port the method**, not the code. The label engine CUE-DETR lacks. |
| **allin1** (mir-aidj, ISMIR 2023) | ML structure (Demucs→NATTEN transformer) + beats/downbeats | MIT, tiny weights | pop labels (intro/verse/chorus/bridge/inst/outro) + downbeats | Heavy (torch+demucs+NATTEN+madmom, ~2-3GB, py≤3.11). Labels are pop, need mapping. |
| **madmom** `DBNDownBeatTrackingProcessor` | RNN + DBN joint beat/downbeat | BSD | downbeat grid | **The mandatory backbone** both cue methods snap to. Old/fragile (Cython, py3.12 build wall) → server-side, isolated py3.11 env. |
| Eval | **Raveform** (TISMIR 2024, EDM, CC-BY-4.0) | — | EDM functional labels | the EDM yardstick. **EDM-CUE** (CUE-DETR's set): 4710 tracks, beat grids. |

Rejected: MSAF (cluster labels, not functional), DJtransGAN (generates transitions), CUE-DETR's
dataset is metadata-only (no redistributable audio).

## DECISION (made — adopt the literature model; runs LOCAL via ONNX)

**Replace the numpy heuristic with a literature model** — CUE-DETR, exported to ONNX and run LOCALLY
on `onnxruntime` with **no torch** (proven below, same runtime the CLAP model uses). Server-side
(`bravoh-gpu-worker`, CUDA) stays an *option* only for huge-library batch, not the default. The
`CueAnchor` seam is unchanged — only the producer's internals swap. Adopted stack: **CUE-DETR (MIT
weights) for cue positions + a downbeat grid + a Zehren-style multi-feature classifier for the
intro/build/breakdown/drop/outro labels** (the dep-free autocorr grid in `cue_refine` works today;
madmom is an optional server-side grid-quality upgrade).

The decision rests on **published SOTA evidence**, not a local bake-off: CUE-DETR reports **F₁ 0.46 vs
Mixed-In-Key 0.16 and Automix 0.15 (~3×)** on EDM-CUE, with released MIT weights — it is the only
open, evaluated, downbeat-aware cue detector. The heuristic's failure on Kaan's hardtechno (energy-only
threshold can't separate breakdown from drop; "breakdown 3s after drop" on ANGER) is the textbook
single-feature degenerate case the literature already solved with downbeat quantization + 4-bar
periodicity. There is no path where hand-tuned thresholds beat the published method, so the choice is
not contingent on the local runs.

## LIVE VALIDATION (2026-05-26) — ran it, it works

CUE-DETR was run for real on Kaan's library (isolated py3.11 env `/tmp/cuedetr-env`, MIT weights
`disco-eth/cue-detr` cached locally, 159 MB). Results across three genres:

- **ANGER (hardtechno):** CUE-DETR cues `2:00 2:12 2:24 2:36 …` — evenly spaced at **12.07 s = exactly
  8 bars @ ~159 BPM**. Monotonic, phrase-locked, **no overlaps**. The heuristic's impossible
  "breakdown 3 s after drop" is gone. Psy (Psykovsky) + house (Daft Punk, PNAU remix) also gave
  musically-sane anchors.
- **Speed (Apple M4 Max, CPU only — the script never touches the GPU):** model load 0.4 s; **~4.5 s per
  audio-minute** (a 5-min track ≈ 20 s); decode/prep < 1 s, the rest is DETR inference; ~366 MB RAM.
  Trivial server-side (CUDA → sub-second/track). ~1000 tracks ≈ 5.5 h on-device CPU — the only case
  that still argues for the GPU box. The torch install weight (torch + librosa/numba/llvmlite ≈ 2 GB)
  is what *would have* forced server-side — until the ONNX export (next section) dropped torch entirely
  → ~370 MB local, no server needed.
- **The real finding — the repo's peak-picker is crude.** At default sensitivity 0.9 it is too sparse on
  non-EDM (house tracks got 2 cues); at 0.5 it floods (32–55 cues/track) with **exact-duplicate
  timestamps** (`1:52 1:52`) because the script has **no beat grid** — its `-r 16` "radius in bars" is a
  fake frame-distance. This empirically confirms the planned stack: CUE-DETR positions are good, but a
  **downbeat grid + dedup** is mandatory on top.

### SHIPPED this session: the refine stage (`src/vibemix/library/cue_refine.py`)
The dep-free, client-side half of the engine is built + tested: `refine_cue_positions(audio_path,
candidates_s, *, phrase_bars=8) -> list[RefinedCue]` snaps each producer candidate to the downbeat/
phrase grid (reusing `cue_detect`'s autocorr BPM + `_phrase_dsp.lock_downbeat_phase` — **no torch, no
madmom**) and collapses near-coincident hits to one cue per phrase, keeping the higher-confidence lock.
Run on the real flooded CUE-DETR output it turned **32–55 raw candidates → 8–12 clean, nearly-all-snapped
phrase-locked cues** per house track. 8 unit tests (`tests/library/test_cue_refine.py`), pure-numpy,
`decode_to_mono` monkeypatched, all green; honest unsnapped fallback when no grid is found (anti-
hallucination). New disjoint files only — no shared-file collision with the concurrent ingest/v8.2
sessions (did NOT touch `embed.py`/`__init__.py`/`orphans.csv`).

### Local runs — the dependency lesson
The first two `/tmp` attempts (CUE-DETR `ad2bf26bcd9a0b986`, allin1+madmom `a98bf4b4c003fda9d`) stalled
not on method but on heavy-dependency download over slow home wifi (torch / `llvmlite`). The working run
reused the existing torch install; **madmom still would not build** (the classic 0.16.1 Cython
build-isolation wall) — fixable with `--no-build-isolation`, and it belongs server-side anyway. The
dep-free refine stage already produces clean phrase-locked cues without it.

## ONNX → RUNS LOCAL, NO TORCH (proven 2026-05-26)

The producer does NOT have to be server-side. CUE-DETR was exported to ONNX and runs on plain
`onnxruntime` (~15 MB) — **the torch tree (~2 GB) is gone at inference time**:

- **Export:** `torch.onnx.export(..., opset_version=16, dynamo=False)` — the legacy exporter (the new
  dynamo path choked on DETR's `Resize` op and wrote a broken 2 MB stub). Clean **167 MB** fp32 ONNX.
- **Parity: byte-exact.** ANGER/Bassline/FLOXY positions identical to the torch path (logits maxdiff
  2e-5, boxes 2e-6 — pure numerical noise). **Ship model = fp32 167 MB (Kaan's call: "mükemmeli tut").**
  Cached at `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx`; export recipe in `/tmp/cuedetr_onnx.py`.
- **Quantization ladder (tried, for the record):** int8 → 43 MB, runs, but ANGER perfect / Bassline+FLOXY
  drift ±1 s & ±1–2 cues (quant noise crosses the 0.9 peak-pick threshold). int16 → won't run
  (`ConvInteger` is int8-only). fp16 → 84 MB but DETR's `Cast`/`Add` dtype boundaries break the
  onnxruntime graph (fixable with an auto-mixed-precision pass; not worth blocking on). **Note:** the
  `cue_refine` stage re-snaps every position to the phrase grid, so int8's ±1 s drift would largely be
  *absorbed* — int8 (43 MB) is a viable smaller option if size ever matters; verify int8→refine vs
  fp32→refine convergence before shipping it.

### Unified local architecture (CLAP session converged here independently)
The concurrent CLAP session independently chose **on-device ONNX** too (`Xenova/larger_clap_music_and_speech`,
512-dim, q8 ≈ 205 MB). So both models ride **one `onnxruntime`**, no torch, no server:

| model | role | size |
|---|---|---|
| CLAP (Xenova) | embedding / curate / next-track | q8 ≈ 205 MB |
| CUE-DETR | cue positions (auto-cue) | fp32 167 MB |
| onnxruntime | the shared runtime both use | ~15 MB |

≈ 370 MB total, **no torch** — fits the one-click installer (lazy-download both models on first
library-analyze). Mel features: `librosa` today (pulls numba/llvmlite); a `scipy`/numpy mel would drop
that chain too if a fully-minimal client is wanted.

## NEXT STEPS (clear)

1. ✅ **DONE — CUE-DETR confirmed on Kaan's library** (techno/psy/house; see LIVE VALIDATION above).
2. ✅ **DONE — refine stage shipped** (`cue_refine.py` + 8 tests; flooded candidates → clean
   phrase-locked cues, dep-free, client-side).
3. ✅ **DONE — CUE-DETR exported to ONNX, runs LOCAL on `onnxruntime`, no torch** (167 MB fp32, byte-exact
   parity, cached at `~/.cache/vibemix/cue-detr-onnx/`). Producer recipe: mel-spectrogram → ONNX forward
   → `post_process_object_detection` → `find_peaks`. Build a `cue_detr` producer module wrapping this
   (lazy `onnxruntime` import; model is resolved from `VIBEMIX_CUE_ONNX_PATH` or the vibemix cache).
   Run at a LOW threshold (≈0.5) on purpose — the flood is fine because `cue_refine` cleans it.
   Shares the runtime the CLAP session brings.
4. ✅ **DONE — pipeline wired** in two new disjoint modules:
   - `src/vibemix/library/cue_detr.py` — the ONNX producer. `detect_cue_positions(audio) -> list[float]`
     (lazy onnxruntime/librosa/transformers, guarded → `CueProducerUnavailable`); pure-numpy
     `_positions_from_outputs` post-process (unit-tested). Model lazy-resolved (`VIBEMIX_CUE_ONNX_PATH`).
   - `src/vibemix/library/cue_engine.py` — `detect_cues_auto(audio) -> list[CueAnchor]`: producer →
     `refine_cue_positions` → `build_cue_anchors` (label + ≤80s window), **falling back to the
     dep-free `cue_detect.detect_cues` heuristic** when the producer is unavailable. The `CueAnchor`
     seam is unchanged; `embed.py`, `excerpt.py`, and `ingest.py` now call `detect_cues_auto`, so the
     old heuristic is fallback-only for those consumer paths.
   - Tests: `tests/library/test_cue_refine.py` (8) + `tests/library/test_cue_engine.py` (9), all green
     (30 across the cue island). **Verified end-to-end on real audio** through the actual ONNX path:
     ANGER → 12 CueAnchors, Digital Love → 11, `source="auto"`, windows ≤80s, positions CUE-DETR-aligned.
     Labels are the coarse interim (see note below).
5. **Labels (deferred, not critical per Kaan):** port Zehren's energy+timbre+drum-onset+harmony novelty
   (downbeat-quantized, 4-bar periodic) → classifier for intro/build/breakdown/drop/outro. Until then
   the engine emits clean POSITIONS; the naive energy-labeler is a rough placeholder, not the label
   engine. (Optional grid upgrade: madmom `DBNDownBeatTrackingProcessor`, `--no-build-isolation`,
   server-side — the dep-free autocorr grid already works.)
6. **Reliability:** eval against Raveform (EDM, CC-BY) + Kaan's ear (render clips a few sec BEFORE each
   cue to a FRESH timestamped folder — VLC caches overwritten files; use `LC_ALL=C` with `awk`/ffmpeg,
   the Turkish locale prints comma decimals ffmpeg can't parse).
7. **KAAN-ACTIONs:** (a) Rekordbox `collection.xml` export → free DJ-cue ground truth for cross-check
   (cue data is in SQLCipher `master.db`, untouched). (b) Decide if the server-side dep is acceptable
   vs a lighter on-device fallback.

## Gotchas the next session must know

- **Don't hand-tune DSP thresholds** — that's the proven dead end. Use the downbeat-backbone +
  multi-feature method.
- **VLC caches overwritten files** — render validation clips to a fresh/timestamped folder, quit VLC.
- **madmom won't build on py3.12** (project's pinned version) → isolated py3.11 env, server-side only.
- **Seam is frozen** — `cue_types.py` `CueAnchor` 5 fields; no neutral "section" label (non-dance →
  intro+outro only). Extend the seam only with the ingest session's agreement.
- Heuristic `cue_detect.py` is the current shipped fallback; keep it working until the model lands.
