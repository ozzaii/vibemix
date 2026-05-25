# Local On-Device Embedding Stack for vibemix's Next-Song Engine — Research & Recommendation

**Date:** 2026-05-25 · **Repo:** `/Users/ozai/projects/dj-set-ai` · **Author:** research agent (read-only)
**Reverses:** the prior `feedback_no_clap_use_gemini_embedding` decision — intentional, cost-driven.

---

## 0. TL;DR verdict

- **License is the gate, not quality.** The two best-quality local music embedders — **MERT** and **MuQ/MuQ-MuLan** — are **CC-BY-NC (non-commercial)** and are **disqualified** for a commercially-distributed Apache-2.0 binary. **Essentia's pretrained models are CC-BY-NC-SA AND the Essentia core lib is AGPLv3** → double-disqualified for bundling. This is decisive and surprised the obvious picks.
- **The clean commercial-licensed local audio embedder is LAION-CLAP (`larger_clap_music`, Apache-2.0).** It is also the *only* candidate that keeps **text→audio crossmodal search** (the thing Gemini-embedding-2 gave you). OpenL3 (MIT) is the audio-only fallback if CLAP proves too heavy.
- **Genre / BPM / KEY are ALREADY solved on-device in this repo, with ZERO new deps** — custom numpy DSP, not Essentia/librosa (which, despite CLAUDE.md prose, are **NOT** in `pyproject.toml`). Do not add Essentia. Keep what's there.
- **The local move only needs to replace ONE thing: the audio *embedding*.** Genre/BPM/key stay. The store/search layer (`search_centered`) is model-agnostic and slots a local embedder in as a drop-in for `LibraryEmbedder`.
- **Install cost of the recommended stack: +~150-250 MB** (CLAP int8 ONNX ~190 MB + onnxruntime ~40 MB), no torch needed at runtime if exported to ONNX. This is the real price of the €0/track win.

---

## 1. What the repo ALREADY has (verified, not assumed)

| Capability | Where | How | Cost |
|---|---|---|---|
| **Live BPM** | `state/genre/bpm_validator.py` + `state/refresh.py::estimate_bpm` | autocorrelation numpy, half/double snap to genre profile | €0, on-device |
| **Genre (live + per-track)** | `state/genre/genre_autodetect.py` (`score_genre`) | pure-numpy profile scoring on BPM + 4 band shares + crest factor, with anti-slop confidence gate + hysteresis | €0, on-device |
| **Key → Camelot** | `state/harmonics.py` (`to_camelot`, `is_clash`) | deterministic lookup table from the track's **tag** (Rekordbox `Tonality`); LLM never computes keys | €0, on-device — **but reads tags, does NOT detect key from raw audio** |
| **Audio→audio + text→audio similarity** | `library/embed.py` (`LibraryEmbedder`) + `library/store.py` (`search_centered`) | **Gemini Embedding 2** audio Part, 1536-dim, mean-centered cosine | **~€0.0125/audio-embed (USD), ~€0.034/track at 3-excerpt — the cost being attacked** |

**Critical correction to CLAUDE.md:** the GSD prose claims "Essentia, librosa, aubio" are installed. **They are not in `pyproject.toml` and not imported in `src/`.** All DSP is hand-rolled numpy/scipy. This is good news — there is no Essentia AGPL liability today, and we must not introduce one.

**So the ONLY thing Gemini is doing that we'd move local = the embedding vector.** Genre/BPM are already free and local. Key-from-audio is the one *new* capability a local model could add (today key comes from tags only).

---

## 2. COMPARISON TABLE — local music embedding models (2026-current)

| Model | Sim. quality (music) | Modality | Params / file size | Runtime deps | Inference (M-series CPU, per ~30s track) | License | Bundle ease | Verdict |
|---|---|---|---|---|---|---|---|---|
| **LAION-CLAP `larger_clap_music`** | Strong; best human-aligned timbre semantics of the CLAP family | **text + audio (shared space)** | ~615M / **776 MB** fp32 `.bin`; **~190 MB int8 ONNX** | torch+transformers (fp32) OR **onnxruntime only** (exported) | ~1-3 s/track CPU; faster int8 | **Apache-2.0** ✅ | Medium (ONNX export removes torch) | **RECOMMENDED** |
| **MS-CLAP** | Comparable; trained on 4.6M pairs (vs LAION 630K) | text + audio | similar order | torch | similar | MIT-ish but check weights | Medium | Viable alt; LAION better-documented + cleaner HF path |
| **MERT-v1-95M / 330M** | **SOTA audio understanding**, 14 MIR tasks | **audio-only** | 95M (~180-200 MB) / 330M (~1.2 GB) | **torch + torchaudio + transformers** | ~1-2 s (95M) | **CC-BY-NC-4.0** ❌ | Heavy (torch) | **DISQUALIFIED — non-commercial** |
| **MuQ / MuQ-MuLan-large** | **New 2025 SOTA**, beats MERT zero-shot tagging; MuLan adds text | audio-only (MuQ) / text+audio (MuLan) | large | torch | — | **CC-BY-NC-4.0** ❌ | Heavy | **DISQUALIFIED — non-commercial** |
| **OpenL3 (music, emb512)** | Decent general audio; weaker on fine music similarity than CLAP/MERT | audio-only | small (~50-80 MB) | **TensorFlow≥2 + Kapre** | ~0.5-1 s | **MIT** ✅ | Hard (TF + Kapre bundling on Win/Mac is painful) | Fallback only; TF dep is worse than CLAP's torch |
| **CLMR** | Research-grade contrastive; dated (2021), small community | audio-only | small | torch | fast | MIT/research ✅ | Medium | Weaker + stale; skip |
| **Essentia discogs-effnet embeddings** | Very good for electronic/underground (Discogs-trained); used by cosine.club | audio-only | ~80-90 MB `.pb` | **essentia-tensorflow** (AGPL lib) | fast | **models CC-BY-NC-SA ❌ + lib AGPLv3 ❌** | Hard (TF wheels Linux-only on pip; brittle Mac, no Win) | **DOUBLE-DISQUALIFIED** |
| **Whisper-based** | N/A — Whisper is ASR, not a music-similarity embedder | — | — | — | — | MIT | — | **Wrong tool — do not use** |

Notes:
- "Quality" rankings synthesised from the 2025-2026 MIR similarity literature (MuQ paper; the MS-CLAP/LAION-CLAP/MuQ-MuLan human-rating comparison; the Jan-2026 "Interpretable and Perceptually-Aligned Music Similarity" paper). Audio-only SSL models (MERT/MuQ) top *understanding* benchmarks; CLAP trades a little raw similarity accuracy for the crossmodal text head.
- CLAP int8 ONNX: Optimum dynamic quantization gives ~4× size reduction and ~3× CPU speedup with negligible accuracy loss → the practical way to ship CLAP without torch.

---

## 3. CROSSMODALITY TRADEOFF — keep text→audio, or go audio-only?

**What Gemini-embedding-2 gave you:** text→audio ("hard techno" finds tracks) AND audio→audio in one shared space. That powered both the vibe-search box and the similar-track lookup.

**The honest framing of Kaan's actual goal:** the *next-song engine* is **pure audio→audio** (current track → nearest mixable tracks). For that single feature, text crossmodality is **not required** — any audio-only model (MERT-quality) would do.

**But** — the repo *already ships* a text vibe-search surface (`embed_query`, `library/search.py`) built on the shared space. Going audio-only **silently breaks** "type 'peak-time rolling techno' → get tracks." That's a real product regression, not a clean scope cut.

**Verdict: keep a text-capable model → LAION-CLAP.** Reasoning:
1. It's the only commercially-licensed option that preserves text→audio at all (the audio-only alternatives MERT/MuQ are NC-disqualified anyway, so "best audio-only" isn't even on the table for commercial bundling).
2. CLAP gives you BOTH the next-song audio→audio path AND keeps the existing text vibe-search alive — no feature regression, single model, single index.
3. A **hybrid (local CLAP for audio→audio + Gemini text embed only for the rare text-query)** is possible but adds a second vector space and a dimension-mismatch headache. Not worth it: CLAP's own text tower handles queries locally for free. Only revisit hybrid if CLAP text-query quality measurably underperforms on Kaan's ear test.

If, after testing, CLAP's audio→audio neighbour quality disappoints and text search turns out to be a dead feature nobody uses → drop to **OpenL3 (MIT, audio-only)** and retire text vibe-search. That's the only scenario where audio-only wins.

---

## 4. GENRE DETECTION — already covered, do NOT add a model

**You already have a working on-device genre detector** (`state/genre/genre_autodetect.py`): pure-numpy profile scoring with an anti-slop confidence gate + hysteresis, scoring BPM + band shares + crest factor against `state/genre/profiles/*.json`. It's tuned (psy-vs-techno midpoint discrimination), zero-cost, zero new deps, and already wired into `refresh.py`.

- **Do NOT add Essentia's genre_discogs400.** It's CC-BY-NC-SA (models) on top of an AGPLv3 lib — disqualified — and would duplicate a feature you already ship.
- **If you adopt CLAP anyway**, you get genre *for free as a bonus*: zero-shot tag the track embedding against genre-label text embeddings ("techno", "house", …) via CLAP's text tower, OR k-NN the neighbour set's known genres. This could *augment* the numpy detector (cross-check / fill `unknown`) but should not replace the grounded DSP path that the anti-slop tests depend on. **Recommendation: keep the numpy detector as source-of-truth; optionally use CLAP zero-shot as a secondary signal later.**

---

## 5. BPM + KEY — confirm existing, one gap

- **BPM: already on-device, keep it.** `state/genre/bpm_validator.py::validate_bpm` + `refresh.py::estimate_bpm` (autocorrelation, half/double snap). €0. No change.
- **KEY: present but tag-derived only.** `state/harmonics.py::to_camelot` maps a track's **existing key tag** (Rekordbox `Tonality`) → Camelot, with `is_clash`/`compatible`/`semitone_distance` for harmonic next-track logic. It does **NOT detect key from raw audio** — tracks without a key tag get `key=unknown`.
  - **Gap for the next-song engine:** harmonic matching needs a key for *every* track. Untagged tracks (folder-ingested, non-Rekordbox) have no key.
  - **Fix without AGPL Essentia:** a small **Krumhansl-Schmugler / template-matching key detector in numpy** (chroma from scipy FFT → correlate against 24 major/minor key profiles). ~80 lines, €0, no deps, fits the existing numpy-DSP house style. This is the one genuinely *new* DSP worth writing. Feed its output through `to_camelot` (it already accepts musical notation like `Am`/`F#m`).
  - Camelot wheel + `is_clash` already exist — only the audio→key estimator is missing.

---

## 6. INSTALL-SIZE IMPACT (the hard one-click constraint)

vibemix has a **hard one-click-install requirement** (Mac+Win, auto-install deps) and a PyInstaller bundle-cap discipline (they already fight to keep sqlcipher3 out, gate pyrekordbox `--no-deps`).

| Approach | Added install size | New runtime deps | Notes |
|---|---|---|---|
| **CLAP via torch+transformers** | **~2-2.5 GB** (torch CPU wheel ~800 MB-1.5 GB unpacked + 776 MB weights + transformers) | torch, transformers, tokenizers | ❌ Blows the bundle cap. Torch alone is a non-starter for a "polished narrow utility." |
| **CLAP via int8 ONNX (RECOMMENDED)** | **~150-250 MB** (int8 ONNX weights ~190 MB + onnxruntime ~40 MB + tokenizer files ~3 MB) | **onnxruntime only** (no torch at runtime) | ✅ Export once at build time with Optimum; ship the `.onnx`. This is the path. |
| **OpenL3** | ~300-500 MB | TensorFlow + Kapre | ❌ TF is heavier + Kapre Win/Mac bundling is brittle. Worse than CLAP-ONNX. |
| **Essentia** | ~200 MB | essentia-tensorflow | ❌ AGPL + NC + Linux-only pip TF. Disqualified. |
| **numpy key detector (the BPM/key gap)** | **~0 MB** | none (scipy already in) | ✅ |

**The torch question is the whole ballgame.** Shipping torch is incompatible with the install discipline. **CLAP must be exported to int8 ONNX at build time** so the runtime only needs `onnxruntime` (~40 MB, clean wheels for Mac arm64 + Win x64). That turns "+2.5 GB + torch" into "+~200 MB, no torch." Verify the ONNX export preserves embedding quality on a 20-track ear test before committing.

**Privacy + key-leak win (real, not theoretical):** local embedding means **audio never leaves the machine** and there is **no API key to leak** for the similarity path. This directly serves the `project_one_click_install_hard_req` + the "API key embedded in binary is the problem of the year" constraint — the proxy still fronts the *conversational* Gemini brain, but the per-track-cost firehose (the €897/mo driver) goes to €0.

---

## 7. THE RECOMMENDED LOCAL NEXT-SONG STACK

```
┌─────────────────────────────────────────────────────────────┐
│ NEXT-SONG ENGINE (100% on-device, €0/track)                  │
│                                                              │
│  audio→audio similarity   → LAION-CLAP larger_clap_music     │
│                             (int8 ONNX, onnxruntime, Apache) │
│  text→audio vibe-search   → SAME CLAP text tower (kept!)     │
│  genre                    → existing numpy genre_autodetect  │
│  BPM                      → existing numpy estimate_bpm      │
│  key (tagged)             → existing harmonics.to_camelot    │
│  key (untagged, NEW)      → numpy KS-template chroma detector│
│  harmonic next-track      → existing harmonics.is_clash/     │
│                             compatible/semitone_distance     │
│  index + ranking          → existing store.search_centered   │
│                             (mean-centered cosine, unchanged)│
└─────────────────────────────────────────────────────────────┘

Gemini stays ONLY for: the conversational co-host brain (RealtimeModel)
+ TTS. The embedding firehose is gone.
```

**Why this exact stack:**
- One model (CLAP) covers BOTH similarity *and* text search → no feature regression, one vector space, one index.
- Apache-2.0 → clean to bundle + redistribute (matches repo LICENSE).
- ONNX int8 → no torch, fits the install cap.
- Everything else (genre/BPM/key/Camelot/store) is **reused unchanged** — the move is surgical: swap the embedder, add one numpy key detector.

### Slot-in points (the code is already abstracted for this)
- `LibraryEmbedder.embed_track(track) -> np.ndarray` and `.embed_query(str) -> np.ndarray` are the **only two methods** the engine depends on. A `LocalClapEmbedder` with the same two methods + same return contract (fixed-dim, L2-normalized float32) is a drop-in.
- `EMBEDDING_DIM` (currently 1536, in `library/_cosine.py`) → set to CLAP's projection dim (512). Single-source constant; `store.recreate_table()` already exists to rebuild the vec0 table at a new dim. The cache-DB dim-guard in `embed.py::_cache_get` already treats wrong-dim rows as clean misses → migration is automatic.
- `store.search_centered` (mean-centered cosine) is model-agnostic — **no change**.
- `similar.py::similar_to` calls `embedder.embed_track` + `store.search_centered` — **no change**, just inject the local embedder.

### PHASED BUILD PLAN

**Phase A — Spike (de-risk, ~1 session).** Export `larger_clap_music` to fp32 ONNX, then int8 via Optimum. Embed Kaan's `hardtechno/` subset (~49 tracks) with both Gemini-1536 and CLAP-512. Eyeball: do CLAP's nearest-neighbour sets feel like real mixable matches on Kaan's ear? Measure per-track CPU time + final ONNX size. **Gate:** if neighbour quality fails the ear test, stop and reconsider (OpenL3 / hybrid). This is the hallucination-grounding-equivalent gate for similarity.

**Phase B — `LocalClapEmbedder` drop-in.** Implement the two-method contract behind the existing `LibraryEmbedder` interface; wire an env/config switch (`VIBEMIX_EMBED_BACKEND=local|gemini`) so the Gemini path stays as fallback during bring-up. Bump `EMBEDDING_DIM` → 512, let `recreate_table()` + cache dim-guard handle migration. Keep `search_centered` untouched.

**Phase C — numpy key detector (fills the untagged-track gap).** ~80-line KS-template chroma key estimator (scipy FFT → 24-profile correlation → musical-notation string → `to_camelot`). Wire into `folder_ingest.py` so untagged tracks get a key for harmonic matching. Gate on confidence (anti-slop: `unknown` over a wrong guess, mirroring `genre_autodetect`).

**Phase D — bundle + install.** Add int8 ONNX as a bundled asset (PyInstaller datas), add `onnxruntime` to deps (verify Mac arm64 + Win x64 wheels, no torch). Re-run the bundle-cap gate. Update CLAUDE.md tech-stack block (and fix the false "Essentia/librosa installed" prose) + the `feedback_no_clap_use_gemini_embedding` memory (now reversed, cost-driven).

**Phase E — retire / fence the Gemini embed path.** Once CLAP passes, the Gemini embedding path becomes dead/fallback-only. Remove the per-track cost from `budget.py`'s projection (the €50/mo gate becomes trivially green); keep Gemini only for the conversational brain.

---

## 8. Risks & honest caveats
- **CLAP audio→audio is good but not MERT/MuQ-tier.** The best-quality models are license-locked out, so CLAP is "best *commercially-usable* local," not "best absolute." Phase-A ear test is the real go/no-go.
- **ONNX export of CLAP** (dual-tower: SWIN-audio + RoBERTa-text) needs care — export both towers; verify embeddings match the torch reference within tolerance. Budget time for this.
- **512-dim < 1536-dim** → re-index everything once (handled by the dim-guard + `recreate_table`, but it's a one-time re-embed of every user library; that's now free/local so fine).
- **Two licenses to honor in NOTICE:** CLAP Apache-2.0 (attribution) — clean. Make sure no NC/AGPL model accidentally gets pulled in by a transitive (it won't, if you only add onnxruntime + the CLAP onnx asset).

---

## Sources
- [m-a-p/MERT-v1-95M (HF) — CC-BY-NC-4.0, audio-only, torch+torchaudio](https://huggingface.co/m-a-p/MERT-v1-95M)
- [m-a-p/MERT-v1-330M (HF)](https://huggingface.co/m-a-p/MERT-v1-330M)
- [tencent-ailab/MuQ + OpenMuQ/MuQ-MuLan-large — CC-BY-NC-4.0](https://github.com/tencent-ailab/MuQ)
- [MuQ paper (arXiv 2501.01108)](https://arxiv.org/abs/2501.01108)
- [laion/larger_clap_music (HF) — Apache-2.0, text+audio shared space](https://huggingface.co/laion/larger_clap_music)
- [laion/larger_clap_music file sizes (776 MB fp32 .bin)](https://huggingface.co/laion/larger_clap_music/tree/main)
- [LAION-AI/CLAP repo](https://github.com/LAION-AI/CLAP)
- [Essentia models — all CC-BY-NC-SA 4.0, proprietary on request](https://essentia.upf.edu/models.html)
- [Essentia core library — AGPLv3 (SIGMM Records)](https://records.sigmm.org/2014/03/20/essentia-an-open-source-library-for-audio-analysis/)
- [marl/openl3 — MIT, TF2+Kapre, emb 512/6144](https://github.com/marl/openl3)
- [CLAP int8 ONNX quantization ~4× smaller, ~3× faster (Sentence-Transformers efficiency docs)](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)
- [2026 "Interpretable and Perceptually-Aligned Music Similarity with Pretrained Embeddings"](https://arxiv.org/pdf/2601.19109)
- [MS-CLAP vs LAION-CLAP vs MuQ-MuLan human-rating comparison](https://www.researchgate.net/figure/similarity-vs-human-ratings-per-descriptor-for-MS-CLAP-LAION-CLAP-and-MuQ-MuLan_fig1_396541690)
- [cosine.club — Essentia discogs-effnet embedding similarity engine (HN)](https://news.ycombinator.com/item?id=40072062)
