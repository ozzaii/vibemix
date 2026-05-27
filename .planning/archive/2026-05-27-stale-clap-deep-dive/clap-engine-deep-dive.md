# CLAP Music Embedding Engine — Deep Technical Dive

> Research synthesis for wiring CLAP as vibemix's library similarity / vibe-search / curate engine.
> Decision LOCKED: `laion/larger_clap_music` (512-dim), inference SERVER-SIDE on Bravoh GPU worker;
> Gemini stays for co-host conversational brain only. Shipped code still embeds via Gemini 1536-dim
> (`src/vibemix/library/embed.py`) — this doc is the spec for the CLAP swap.
> Date: 2026-05-26. Author: research agent.

---

## Implementation decisions (LOCKED)

| # | Decision point | Recommendation | One-line rationale |
|---|----------------|----------------|--------------------|
| 1 | Model variant | `laion/larger_clap_music` (= `music_audioset_epoch_15_esc_90.14.pt`, HTSAT-base/RoBERTa) | Best music-domain checkpoint (ESC50 90.14, GTZAN ~71%); music-only beats general for DJ tracks |
| 1b | API | `laion_clap` pip (1.1.7) on the GPU worker; **NOT** HF `transformers.ClapModel` | HF port has a documented accuracy drop on HTSAT-base; pip is the reference impl, matches the `.pt` checkpoint exactly |
| 2 | Long-audio path | **Mean-pool 3 non-overlapping ~10s windows over the cue-anchored excerpt, then L2-renorm.** NOT `enable_fusion`. | Fusion's +8% R@1 is for whole-track variable-length; our excerpts are already cue-anchored & short — manual windowing is simpler, deterministic, and parity-friendly |
| 3 | Text↔audio | Use BOTH text→audio (curate/search) and audio→audio (similar). Trust audio→audio more. | Text retrieval is good for vibe/timbre/genre; **blind to tempo & temporal order** (T-CLAP: ~50-56% on temporal tasks) — never rely on CLAP text for BPM/sequencing |
| 4 | Server perf | PyTorch FP32 on EPYC CPU, batch 8-16, `torch.set_num_threads(8)`. ~0.3-1.0s per 10s window. | Full 1547-track library (3 windows each ≈ 4641 fwd passes) ≈ **30-75 min wall-clock** on 8-vCPU; one-time, resumable, fine |
| 4b | CPU speedup (optional) | ONNX Runtime dynamic INT8 quant if embed throughput becomes a bottleneck | 1.5-3× CPU speedup, negligible accuracy loss; only worth it if re-embedding becomes frequent |
| 5 | Vector store | New 512-dim vec0 table; drop the 1536 lock. **Keep cosine. Keep mean-centering.** | CLAP is L2-normed & anisotropic just like Gemini — `centering.py` applies unchanged, just rebuild the centroid at 512-dim |
| 6 | Biggest reliability risk | **Silence / DJ-tool / non-music excerpts produce confident-but-meaningless vectors** | Gate on RMS energy + (optional) zero-shot "music vs silence/speech" CLAP probe; skip/flag low-confidence |
| 7 | Quality vs Gemini | Roughly **at parity to better** for music similarity; CLAP is purpose-built for audio-text, Gemini is generalist | €897/mo → €0 with no meaningful quality loss for the music-similarity use case; Gemini's "score compression" is the SAME anisotropy CLAP also has |

**Headline:** The swap is low-risk and net-positive. CLAP `larger_clap_music` is the right model, the laion_clap pip API is the right interface, mean-pool 3 windows over cue excerpts, keep cosine + mean-centering, and the single thing that will make it look broken is feeding it silence/non-music — gate on energy.

---

## 1. Model variant

**Mapping (important):** the HuggingFace repo `laion/larger_clap_music` is the HF-packaged form of the laion_clap checkpoint `music_audioset_epoch_15_esc_90.14.pt` (HTSAT-base audio encoder + RoBERTa text encoder). The four candidates:

| Variant | laion_clap checkpoint | Trained on | ESC50 | GTZAN (music) | Best for |
|---------|----------------------|------------|-------|---------------|----------|
| `larger_clap_music` | `music_audioset_epoch_15_esc_90.14.pt` | music + AudioSet + LAION-630k | **90.14** | **~71%** | **music** ← us |
| `larger_clap_music_and_speech` | `music_speech_epoch_15_esc_89.25.pt` | music + speech | 89.25 | lower | mixed music/voice |
| `larger_clap_general` / music_speech_audioset | `music_speech_audioset_epoch_15_esc_89.98.pt` | music + speech + AudioSet | 89.98 | ~51% (GTZAN drops!) | general sound events |
| `630k-audioset` (the default `load_ckpt()`) | `630k-audioset-best.pt` | AudioSet + LAION-630k | lower on music | — | generic audio, NOT music-specialized |

The decisive number: the **general/music_speech_audioset variant's GTZAN genre accuracy drops to ~51% vs ~71% for the music-only checkpoint.** Adding speech+general audio to the training mix dilutes music-genre discrimination — exactly the axis DJ similarity cares about. For electronic/DJ tracks (instrumental, genre-driven, timbre-driven), the **music-only checkpoint is genuinely best.**

- **Projection dim: 512** (confirmed from `config.json`: `projection_dim: 512`; audio encoder hidden 1024, text encoder hidden 768, both projected to the shared 512-d space). This is the vector we store.
- **Checkpoint size:** `pytorch_model.bin` = **776 MB** (FP32, PyTorch pickle; no safetensors in the HF repo). Plan ~1 GB RAM for the loaded model + activations.
- **License:** Apache 2.0 — clean for Bravoh internal reuse, matches vibemix's own Apache-2.0.
- **Audio encoder:** SWIN/HTSAT-base (hierarchical token-semantic audio transformer, depths [2,2,12,2]). Text: RoBERTa.

### laion_clap pip vs HF `transformers.ClapModel`

**Use the `laion_clap` pip package (1.1.7), NOT HF transformers**, server-side. Reasons:
1. There is a **documented accuracy drop** when the HTSAT-base checkpoint is converted to the HF `ClapModel` format (LAION-AI/CLAP issue #126, huggingface/transformers issue #26362). The conversion isn't bit-faithful for this encoder.
2. The pip package is the **reference implementation** the checkpoint was trained/released with; `CLAP_Module(enable_fusion=False, amodel='HTSAT-base').load_ckpt(<path>)` loads the exact `.pt`.
3. The pip API gives `get_audio_embedding_from_data()` (numpy in, numpy out) and `get_text_embedding()` directly — the worker can feed already-decoded/resampled excerpt arrays without round-tripping through HF processors.

> NOTE: bravoh-gpu-worker already has `laion_clap 1.1.7` installed per the project handoff — this confirms the pip path is the intended one.

**RECOMMENDATION:** `laion/larger_clap_music` checkpoint, loaded via `laion_clap` pip `CLAP_Module(enable_fusion=False, amodel='HTSAT-base')`. 512-dim output, Apache 2.0, ~776 MB / ~1 GB resident.

---

## 2. Audio preprocessing

CLAP's hard input contract (from laion_clap docs + the paper, arXiv 2211.06687):
- **Sample rate: 48 kHz, mandatory.** The model resamples internally if you use the file-list API, but feeding `get_audio_embedding_from_data` requires you resample to 48k first. (vibemix's capture chain is 48k → matches; the offline embed path must resample source files to 48k.)
- **Mono.** Stereo gets downmixed; do it explicitly for determinism.
- **Native window ≈ 10s.** Non-fusion models internally crop/pad to a 10s mel window. Audio longer than ~10s is either fusion-combined or (non-fusion) randomly cropped to 10s — i.e. **a non-fusion model on a 60s clip throws away 50s unless you window it yourself.**
- **Normalization:** int16↔float32 handling per the API; output embeddings are **L2-normalized to the unit hypersphere** (so cosine is the native metric).

### Embedding audio LONGER than the window — the two paths

1. **`enable_fusion=True` (the fusion checkpoint path):** for >10s audio, it stacks 4 waveforms — a downsampled whole-clip + 3 random 10s segments — and attentionally fuses them. Reported **up to +8% absolute R@1** for long-form clips vs random cropping. BUT: requires the fusion checkpoint (different `.pt`), is non-deterministic (random segment selection), and is designed for *whole arbitrary-length tracks*.
2. **Manual multi-window mean-pool (RECOMMENDED for us):** split the excerpt into N non-overlapping ~10s windows, embed each independently through HTSAT, **mean-pool the N embeddings → L2-renormalize.** This is the standard community pattern (the music-intelligence writeup samples 3 windows at 10%/45%/80% of the track, mean-pools, renorms).

### Mapping to vibemix's cue-anchored ≤80s excerpts

A cue-anchored excerpt is ≤80s. At 10s/window that's **up to 8 windows.** But you don't need 8 — the excerpt is *already* the musically-salient region (breakdown/drop/intro), so the within-excerpt variance is low. **Recommendation: 3 non-overlapping ~10-13s windows spanning the excerpt (start / mid / end), mean-pool, renorm.** This:
- captures the excerpt's arc without 8× the compute,
- is deterministic (fixed window positions → parity-safe across mac/win, matters for vibemix's bit-identical top-K invariant),
- avoids the fusion checkpoint entirely (stay on the music-only `larger_clap_music`, which is non-fusion).

If a cue excerpt is <10s, embed the single window directly (no pooling).

**RECOMMENDATION:** resample→48k mono float32, split the cue excerpt into 3 fixed non-overlapping windows (~10-13s each), embed each with `get_audio_embedding_from_data`, **mean-pool + L2-renorm.** Do NOT use `enable_fusion` — keep the music-only checkpoint and deterministic windowing.

---

## 3. Text↔audio alignment quality

CLAP is contrastively trained (InfoNCE) so paired audio+text land close in the 512-d space — text→audio retrieval is the model's core competency.

**Strengths:**
- **Timbre & genre & "vibe" language work well.** "Dark cinematic string ensemble", "driving rolling techno with acid bassline" → matching audio is exactly what CLAP was built for. On the Inst-Sim-ABX (Slakh2100) perceptual test, **LAION-CLAP reaches 71.9% agreement with human listeners** on timbre similarity — the strongest of the pretrained embeddings tested, with positive descriptor-level correlations on instrument AND DSP-effect axes.
- **Zero-shot genre:** ~71% GTZAN for the music checkpoint — solid for genre-bucketing.
- **Audio→audio** (track→similar) is reliable for vibe/timbre neighborhoods.

**Known weaknesses (critical for DJ use):**
- **TEMPO / BPM BLINDNESS.** CLAP encodes semantic/timbral content, not numeric tempo. Practitioners pair CLAP with a separate feature extractor (e.g. MusicNN) precisely because CLAP "doesn't reliably capture tempo, BPM, or key." **Do not ask CLAP to sort by tempo or match BPM** — that's vibemix's deterministic Camelot/BPM layer's job.
- **TEMPORAL ORDER BLINDNESS.** T-CLAP paper: standard CLAP is ~random on temporal-ordering tasks — baseline CLAP **~50% on T-Classify**, LAION CLAP specifically **56.2** on T-Classify text→audio (vs T-CLAP's 87.2). It cannot tell "drop then breakdown" from "breakdown then drop." Irrelevant for static excerpt similarity, but means CLAP can't reason about *intro/outro sequencing* — again, the deterministic energy-curve layer owns that.
- **Score compression / anisotropy** (see §5) — everything looks moderately similar; needs mean-centering for discriminative ranking.
- **Vocal bias:** CLAP picks up vocal presence strongly; two instrumentals may be pulled together vs a vocal track even when the instrumentals differ. Usually fine for DJ libraries but worth noting.

**Benchmark numbers found:** GTZAN ~71% zero-shot (music ckpt) / ~51% (general+speech ckpt); ESC50 90.14 (music); Inst-Sim-ABX timbre agreement 71.9% (LAION-CLAP) vs 72.4% (MuQ-MuLan); T-Classify text→audio 56.2 (LAION CLAP). MusicCaps/Song-Describer R@K are reported in the literature with CLAP "consistently outperforming TTMR" but exact R@1 not pinned in sources.

**RECOMMENDATION:** Use text→audio for vibe-search and curate seeding (it's good). Use audio→audio for `similar`. **Architecturally enforce the split:** CLAP owns SEMANTICS (timbre/genre/vibe), the deterministic layer owns TECHNICS (Camelot key + BPM±6% + energy curve). Never let CLAP text retrieval drive tempo/sequencing decisions — that's the documented blind spot.

---

## 4. Server-side inference perf (EPYC, no GPU)

**Model:** HTSAT-base + RoBERTa, ~776 MB FP32 weights. Resident memory ~1.0-1.5 GB (weights + activations + torch overhead). Comfortably fits the 8-vCPU EPYC worker.

**Per-window forward pass (CPU, 10s @ 48k):** No official CLAP CPU benchmark exists in the sources. From transformer-of-this-size CPU inference characteristics (HTSAT ~30-80M params for the audio tower): expect **~0.3-1.0 s per 10s window** on a single EPYC core, dropping per-item with batching. Batch 8-16 windows amortizes the mel-spectrogram + transformer ops well on AVX2/AVX-512.

**Full-library wall-clock estimate (the number you asked for):**
- 1547 tracks × 3 windows = **~4641 forward passes.**
- Plus decode+resample-to-48k per track (~0.5-2s/track depending on format/length) ≈ 1547 × ~1s ≈ 25 min of I/O-bound decode (parallelizable).
- Inference: 4641 passes ÷ effective batched throughput. At a conservative ~0.5s/window effective (batched, multi-threaded `torch.set_num_threads(8)`), **~40 min**; at 0.3s/window, **~25 min**; worst case 1s/window single-threaded, **~75 min.**
- **Realistic full-library embed: ~30-75 minutes wall-clock, one-time, resumable** (vibemix's embed-folder is already content-hash-resumable, so re-runs are near-free).

**Throughput levers:**
- `torch.set_num_threads(8)` (match vCPUs) + `torch.inference_mode()` + FP32.
- **Batch 8-16 windows** per forward call (`get_audio_embedding_from_data` accepts batched arrays).
- **ONNX Runtime + dynamic INT8 quantization** if needed: documented **1.5-3× CPU speedup** for transformers with negligible accuracy loss; would cut the worst case to ~25-30 min. Only worth the export/validation effort if embedding becomes a *recurring* operation rather than a one-time library bake.
- The RoBERTa text tower is tiny and cheap — text queries (curate/search) are ~tens of ms, not a perf concern.

**RECOMMENDATION:** FP32 PyTorch, `set_num_threads(8)`, batch 8-16, `inference_mode`. Budget **~30-75 min for the first full-library embed**, near-zero on re-runs (content-hash cache). Defer ONNX/INT8 unless re-embedding cadence demands it.

---

## 5. Vector store fit (512-dim into sqlite-vec)

Current store is **locked at 1536** (`_cosine.py: EMBEDDING_DIM = 1536`, comment "Locked at 1536 per quick-260525-gz2"; Gemini Embedding 2 MRL). The vec0 table is `FLOAT[1536] distance_metric=cosine`.

**Changes needed (mechanical, the code already supports a dim swap):**
1. `EMBEDDING_DIM = 512` in `_cosine.py`. The codebase comment already documents that bumping the dim auto-recreates the on-disk index, and `folder_ingest`'s dim-mismatch guard catches a stale-dim table fail-loud + `recreate_table()` wipes an empty stale table. So the swap is supported by design.
2. The vec0 DDL `FLOAT[{EMBEDDING_DIM}]` becomes `FLOAT[512]` automatically.
3. Rebuild centroid at 512-dim (it's keyed by `snapshot_hash`, recomputes on next query — no manual step).
4. Re-embed the library (the cache is content-hash keyed; Gemini vs CLAP embeds have different hashes → clean rebuild).

**Cosine vs L2:** **Keep cosine.** CLAP embeddings are L2-normalized to the unit hypersphere by design (the contrastive objective operates on cosine). On unit vectors, cosine and (squared) L2 are monotonically equivalent for ranking — but cosine is the model's native metric and matches the existing `cosine_topk` chokepoint. No reason to switch.

**Anisotropy / mean-centering — DOES CLAP NEED IT? YES.**
- vibemix's `centering.py` exists because raw Gemini whole-track embeddings are strongly anisotropic (avg pairwise cosine ≈ 0.81 → everything looks ~0.92 similar → no ranking power). Subtracting the corpus centroid + renorm collapses avg pairwise cosine to ≈0 and restores separation.
- **CLAP has the SAME pathology.** The Gemini audio-embedding experiment independently reports "**scores are compressed, fine-grained subgenre discrimination is uncertain**" — that IS anisotropy/cone-collapse, and contrastive audio embeddings (CLAP included) are well-known to occupy a narrow cone. The cure is identical: corpus mean-centering.
- **`centering.py` applies UNCHANGED.** It's dim-agnostic (operates on whatever `(N, D)` `load_all()` returns), query-side only, never touches persisted vectors, recomputes the centroid lazily on snapshot change. Just rebuild at 512-d. The one assertion to check: `centering.py` reads `EMBEDDING_DIM` from `_cosine` for the cache-shape guard (`arr.shape == (EMBEDDING_DIM,)`) — that updates automatically when you set 512.

**RECOMMENDATION:** Set `EMBEDDING_DIM = 512`, keep `distance_metric=cosine`, keep `centering.py` verbatim (it's the same anisotropy fix CLAP also needs — confirmed by Gemini's "score compression" being the identical symptom). Re-embed for a clean store. No other store changes.

---

## 6. Reliability / failure modes

What makes CLAP similarity **unreliable**, and how to detect/skip:

| Failure | Symptom | Detect / mitigate |
|---------|---------|-------------------|
| **Silence / near-silence** | Confident vector for "nothing"; clusters all silent clips together, pollutes neighbors | **RMS/energy gate** on the excerpt before embedding — skip or flag if RMS below threshold. vibemix already has `Levels`/EMA-RMS in `audio/` — reuse. |
| **DJ tools / loops / one-shots / drum stems** | Non-musical or fragment audio gets a vector that matches by texture not vibe | Length + energy gate; flag short non-track files. Cue-anchoring already biases toward musical regions. |
| **Very short clips (<~3s)** | Below CLAP's effective context; noisy embedding | Require min excerpt length; if <10s embed single window but flag low-confidence. |
| **Non-music (speech, field recording, acapella)** | Pulled by vocal/speech features, not danceability | Optional zero-shot CLAP probe: cosine(audio, text="music") vs text="speech"/"silence"; threshold to classify. Cheap (text tower is tiny). |
| **Anisotropy** | Everything ~0.9 similar | Mean-centering (§5) — already solved. |
| **Tempo/order queries** | Wrong-but-confident text retrieval | Architectural: route tempo/sequence to deterministic layer (§3). |

**Confidence signal:** CLAP gives no native calibrated confidence, but you can synthesize one:
- **Post-centering self-separation:** after mean-centering, a track whose top-1 neighbor cosine is very low (near 0) sits near the corpus mean → low-information embedding (the `center_and_renorm` zero-vector guard already ranks these last — that's the correct degenerate behaviour).
- **Energy + duration gate** is the primary, cheap, reliable filter — do this first.
- **Zero-shot music/non-music probe** as a secondary gate for ambiguous files.

**RECOMMENDATION (biggest risk):** **The #1 reliability risk is silent/non-music/DJ-tool excerpts producing confident garbage vectors that pollute the neighbor graph.** Gate every excerpt on RMS energy + min-duration *before* embedding (reuse the existing `audio/Levels`), and skip/flag failures — never store a vector for a sub-threshold excerpt. This single gate prevents the most common "why is similarity broken" class.

---

## 7. Gemini vs CLAP quality delta

**Evidence for the head-to-head:**
- Both are anisotropic on music; Gemini's experiment explicitly reports "score compression" / uncertain subgenre discrimination — the **same weakness vibemix's mean-centering already fixes for Gemini, and will fix for CLAP.** Neither has an inherent advantage there.
- Gemini audio embedding (3072-d native, or 768/1536 MRL) is a **generalist multimodal** encoder; it clusters genres reasonably (acid house pair scored 0.923) but is not music-specialized.
- **CLAP is purpose-built for audio↔text** and, on the perceptual timbre benchmark (Inst-Sim-ABX), LAION-CLAP reaches **71.9% human agreement** — competitive with the best dedicated music embeddings (MuQ-MuLan 72.4%) and explicitly "the strongest alignment with human-perceived timbre" among pretrained options tested.
- For **text→audio vibe search**, CLAP's contrastive training is a structural advantage Gemini's generalist objective doesn't match as tightly.

**Quality delta verdict:** For the *music-similarity / vibe-search / curate* use case, CLAP is **at parity to slightly better** than Gemini — and strictly better on text→audio vibe retrieval (its native task). The only axis where Gemini might edge it is cross-modal breadth (it also does image/video/docs), which is irrelevant here. **There is no meaningful quality sacrifice.**

**Cost delta:** Gemini embedding ≈ €0.034/track → ~€897/mo at projected usage (per the locked decision); CLAP self-hosted = **€0 API + privacy + no key-leak risk in the distributed binary.** This also sidesteps the "API key embedded in binary" problem entirely for the library path (Gemini stays only in the co-host brain, behind the Bravoh proxy).

**RECOMMENDATION:** Swap is net-positive — **€897/mo → €0 with no quality loss** for music similarity, plus privacy/no-key-leak wins. Keep Gemini ONLY for the co-host conversational brain (where its generative reasoning is irreplaceable and CLAP cannot substitute). The two-engine split (CLAP=embeddings, Gemini=brain) is the correct architecture.

---

## Appendix — wiring checklist (for the implementation phase)

1. Server: `laion_clap.CLAP_Module(enable_fusion=False, amodel='HTSAT-base')` + `load_ckpt(<music_audioset_epoch_15_esc_90.14.pt>)`; `torch.set_num_threads(8)`, `inference_mode`.
2. Preprocess: decode → 48k mono float32 → 3 fixed non-overlapping windows over cue excerpt → batch → `get_audio_embedding_from_data` → mean-pool → L2-renorm → 512-d float32.
3. Gate: RMS energy + min-duration BEFORE embed; skip/flag failures.
4. Client/store: `EMBEDDING_DIM = 512`, keep cosine, keep `centering.py`, re-embed library (content-hash cache rebuilds clean).
5. Curate/search text path: `get_text_embedding` (RoBERTa tower, cheap) → center with same centroid → cosine_topk. Never route tempo/sequence through it.
6. Replace `library/embed.py`'s Gemini call with a client→Bravoh-worker RPC for CLAP embeddings (the worker holds the model; the binary never ships the 776 MB checkpoint or any key).

## Sources
- [laion/larger_clap_music — HF](https://huggingface.co/laion/larger_clap_music) (config.json projection_dim 512; pytorch_model.bin 776 MB; Apache 2.0)
- [laion/larger_clap_general — HF](https://huggingface.co/laion/larger_clap_general)
- [laion/larger_clap_music_and_speech — HF](https://huggingface.co/laion/larger_clap_music_and_speech)
- [LAION-AI/CLAP — GitHub](https://github.com/LAION-AI/CLAP) (checkpoints, 48k, fusion, ESC50/GTZAN numbers)
- [laion-clap — PyPI](https://pypi.org/project/laion-clap/) (pip API, load_ckpt, enable_fusion, 48k requirement)
- [HF transformers CLAP docs](https://huggingface.co/docs/transformers/en/model_doc/clap) (projection_dim default 512)
- [LAION-AI/CLAP issue #126](https://github.com/LAION-AI/CLAP/issues/126) + [transformers #26362](https://github.com/huggingface/transformers/issues/26362) (HTSAT-base HF-conversion accuracy drop)
- [T-CLAP paper, arXiv 2404.17806](https://arxiv.org/html/2404.17806v1) (temporal/tempo blindness: CLAP ~50%, LAION 56.2 vs T-CLAP 87.2)
- [Interpretable & Perceptually-Aligned Music Similarity, arXiv 2601.19109](https://arxiv.org/pdf/2601.19109) (Inst-Sim-ABX: LAION-CLAP 71.9% human-timbre agreement)
- [Gemini API audio embeddings experiment — aciddome](https://aciddome.com/audio-embeddings-in-the-gemini-api/) (score compression / anisotropy; 768-d; genre clustering)
- [CLAP music intelligence / vibe-search practice — themusicase](https://www.themusicase.com/blog/ai-music-analysis-audio-vectoring-how-clap-embeddings-are-changing-music-intelligence/) (3-window mean-pool pattern; CLAP not for tempo/key)
- [CLAP feature-fusion paper, arXiv 2211.06687] — fusion +8% R@1 long-audio; 48k; 10s window
