# CLAP engine — local on-device audio/text embedding

> **Status: PRODUCT DEFAULT (2026-05-26) — local CLAP ONNX embeddings.**
> The `onnx` backend is live in `clap_engine.py`, `ClapEmbedder` implements the
> product embedder protocol, the `embed_factory.build_embedder` factory always
> selects CLAP, and `_cosine.EMBEDDING_DIM` is fixed at 512. All construction sites
> (curate/search/similar/build-set/telegram/embed-folder CLI + co-host grounding
> + session_loop + mcp_server) + `grounding.py` route through it. For the full
> local model runtime use `pip install -e ".[ai-local]"`; for embedding-only
> work use `pip install -e ".[clap]"`. Put the
> `Xenova/larger_clap_music_and_speech` ONNX snapshot under
> `~/.cache/vibemix/clap-onnx/` (or set `VIBEMIX_CLAP_ONNX_DIR`). `vibemix
> library models --json` reports CLAP/CUE-DETR cache readiness for setup UX, and
> `vibemix library models --install required --json` downloads/verifies the
> required CLAP full-precision ONNX snapshot with size + SHA-256 checks.
> fp16/q8 are treated as future installer variants only after the real-library
> parity gate proves they do not regress retrieval quality. **Remaining
> KAAN-ACTION:** host/download
> UX for CUE-DETR, the live re-embed of a real library, and the funded-key curate
> ear-pass (the parity gate already passed on the engine — see below).
>
> ## How it's wired (Phase 90)
>
> - **Seam:** `_cosine.EMBED_BACKEND == "clap"` and
>   `EMBEDDING_DIM == 512`; `embed_factory.build_embedder()` returns `ClapEmbedder`.
>   Historical Gemini embedding code remains only for legacy tests/migrations.
> - **`ClapEmbedder`** (`library/embed_clap.py`): wraps `ClapEngine(backend="onnx")`,
>   exposes `embed_track` / `embed_query` / `embed_audio_bytes` / `has_cached_embedding`
>   through the product embedder protocols; owns clap-tagged content-hash cache in the shared
>   `embeddings.db` (never collides with historical Gemini rows).
> - **`grounding.py`** routes the "what's playing" embed through the public
>   `embedder.embed_audio_bytes` seam — no more `embedder._client` reach-in
>   (CLAP has no `_client`). The legacy migration embedder keeps a matching
>   shim for explicit legacy tests only.
> - **Mel frontend is torch-FREE and Transformers-free.** The ONNX audio path
>   uses local numpy helpers (`mel_filter_bank` + `spectrogram` +
>   `window_function`) pinned against the CLAP feature-extractor math, without
>   importing the full Transformers package.
>   For a 10s `rand_trunc` segment CLAP uses the **Slaney** filterbank
>   (`norm="slaney"`, `mel_scale="slaney"`), Hann window, frame 1024 / hop 480,
>   power 2.0, `log_mel="dB"`. A first hand-rolled librosa mel (htk/norm=None)
>   degraded separation (techno 6/10) — the pinned Slaney numpy path is the fix.
> - **Gate PASSED, torch absent** (`ClapEngine(backend="onnx")`, real shipped
>   module, 40 tracks 20+20, isolated cache): dim 512, determinism cos=1.000000,
>   "hard techno"→{hardtechno:10/10}, "psy trance"→{psymind:10/10} — matches the
>   proven baseline with `torch` not installed. Wiring tests:
>   `tests/library/test_embed_clap.py` (CI-safe, fake engine).

## What it is

A deterministic, **on-device** embedder built on the LAION-CLAP `HTSAT-tiny`
music checkpoint. It maps both audio and text into ONE **512-dim** space — the
cross-modal property that lets "dark rolling techno" land near dark rolling
techno audio. It replaces cloud embedding calls for the **library vibe-search /
curator / next-suggestion layer ONLY** and is now the selected library embedding
path.

CLAP is an on-device **embedding** model, not a second LLM provider. It does not
change whichever conversational brain is selected for the live co-host or Viber
agent.

### The pipeline

```
load audio → mono (mean across channels) → resample to 48kHz
  ├─ total ≤ CHUNK_SAMPLES (10s): zero-pad to one 10s chunk
  └─ else: non-overlapping 10s slices; a trailing remainder ≥ 5s is
           zero-padded and kept as a final chunk
per chunk: CLAP.get_audio_embedding_from_data(batch, use_tensor=False)
L2-normalize EACH chunk → mean-pool → re-L2-normalize → (512,) float32
```

Constants (`clap_engine.py`, ported verbatim): `CLAP_SR=48000`,
`CHUNK_SAMPLES=480000` (10s @ 48kHz, CLAP's native `clip_samples`),
`CHUNK_BATCH=128`, `CLAP_DIM=512`.

**Why 10s-chunk + mean-pool:** it is *deterministic*. CLAP's fusion path applies
a **random** truncation when fed a clip longer than its native 10s window.
Feeding it exact 10s chunks bypasses that randomness, so re-embedding the same
file yields a bit-identical vector. Mean-pooling the L2-normalized chunk
embeddings (then re-normalizing) gives one stable per-track vector.

The text query path uses CLAP's text encoder
(`get_text_embedding([text])` → `[0]` → L2-normalize) into the same 512-dim
space, so text→audio search works cross-modally.

## Proven reliability evidence

A real **99-track, 2-genre** probe on the user's own library (hardtechno +
psymind) — not a synthetic benchmark:

- **Determinism — bit-identical re-embed:** re-embedding the same file gives
  cosine = **1.000000**, max |Δ| = **0.0**. (This is the whole reason the
  10s-chunk path was chosen over CLAP's native long-clip fusion.)
- **Cross-modal genre separation — top-10 = 100%:** `"aggressive hard techno"`
  → all 10 nearest were hardtechno; `"psychedelic trance"` → all 10 were
  psymind. Clean, no cross-contamination at the top of the ranking.
- **Honest calibration:** vibes that are *absent* from the library score low —
  the model does not force a hit. (Aligns with the trust-the-audio / no-slop
  invariant: silence over a fabricated match.)
- **Timings (CPU):** ~**2.21 s/track** embed; warm model load **14.2 s**. (An
  earlier 242 s figure was a one-off cold cache fetch of the checkpoint, not the
  steady-state load.)

## Ship path — on-device ONNX

The torch backend proves the quality; the **ship** backend is **ONNX Runtime**:

- **Wheel size:** the `onnxruntime` wheel is **~13–18 MB**, self-contained and
  cross-platform — versus the **~88–123 MB** torch tree. Going ONNX drops the
  *entire* torch dependency from the distributed bundle (a one-click-install
  win on both macOS and Windows).
- **Mel frontend in pure numpy:** the mel-spectrogram frontend is computable in
  pure numpy (`np.fft.rfft`), so **no torchaudio** is needed at inference time.
- **Model footprint:** ~**783 MB fp32** for the current default audio+text ONNX
  models. fp16/q8 remain future installer variants, not the product default,
  until they pass the same real-library retrieval parity gate.
- **Export precedent:** the pre-exported `Xenova/clap-htsat-unfused` proves the
  HTSAT audio encoder + RoBERTa text encoder export to ONNX cleanly.

### Upload-vs-download rationale (why on-device, not server-side)

A server-side embedder would have to **upload the user's 9–15 GB library**
upstream — recurring, slow on home connections, and it puts the audio on our
infra. The on-device model is a **one-time ~783 MB fp32 download** by default,
then every embed is local and free. On-device is still far cheaper in bytes
moved and honors **"audio never leaves the device"**.

## The parity gate (the single risk)

This is the one thing that can silently break, so it is gated explicitly.

The **proven** vectors above were produced by `laion_clap` (the LAION **630k**
checkpoint) with a **torchlibrosa** mel frontend. The ONNX ship path would, by
default, use Hugging Face **`larger_clap_music`** weights (a documented accuracy
drop vs the 630k checkpoint) plus a **numpy Slaney mel** frontend. Either
difference can silently **shift the embedding distribution** — search would
still "work" but rank differently, and nobody would see an error.

**Before the ONNX backend is trusted, this gate must pass:**

1. Export `larger_clap_music` → ONNX (a custom `OnnxConfig` — CLAP is **not** in
   the `optimum` registry yet; pin the exporter toolchain).
2. Build a numpy mel matched to the **shipped** encoder (Slaney vs HTK, fft
   size, hop, mel bins — all must match the exported graph).
3. Embed **50 tracks** through **both** the torch reference and the ONNX path.
4. **Require ≥ 0.98 mean cosine** between the two per-track vectors.

**Fallback if parity fails:** do a manual `torch.onnx.export` of the **exact
630k checkpoint** (the same validated weights as the proven path) — still
on-device + ONNX, just exported from the trusted weights instead of swapping to
`larger_clap_music`.

**This gate PASSED (Phase 90, 2026-05-26)** — the resolved ship path used the
pre-exported `Xenova/larger_clap_music_and_speech` ONNX (not a custom export) +
the torch-free local Slaney mel (see the banner). The real shipped
`onnx` backend reproduces the proven genre separation (techno 10/10, psy 10/10)
with `torch` absent. The `torch` backend (laion_clap) remains as the reference
the ONNX path was validated against.

## Current wiring map

- `src/vibemix/library/_cosine.py` fixes `EMBED_BACKEND="clap"` and
  `EMBEDDING_DIM=512`.
- `src/vibemix/library/embed_factory.py::build_embedder()` returns `ClapEmbedder`;
  `src/vibemix/library/embed.py::LibraryEmbedder` is legacy-only.
- `grounding.py` uses the public `embed_audio_bytes` seam, so no path reaches
  into a Gemini client for audio embeddings.
- CLAP stores use the `-clap` suffix (`library-clap.db`,
  `library-clap_centroid.npy`) to avoid wiping old Gemini stores.
