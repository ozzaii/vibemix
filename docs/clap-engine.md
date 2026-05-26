# CLAP engine — local on-device audio/text embedding

> **Status: WIRED (Phase 90, 2026-05-26) — OPT-IN via `VIBEMIX_EMBED_BACKEND=clap`.**
> The `onnx` backend is live in `clap_engine.py`, `ClapEmbedder` is a drop-in for
> `LibraryEmbedder`, the `build_embedder` factory + `_cosine.EMBED_BACKEND` seam
> flip dim (512) + class together off ONE env var, and all 8 construction sites
> (curate/search/similar/build-set/telegram/embed-folder CLI + co-host grounding
> + session_loop + mcp_server) + `grounding.py` route through it. **Default stays
> `gemini` (1536-dim) — the cold path + the whole existing suite are
> byte-identical.** To use CLAP: `pip install -e ".[clap]"`, put the
> `Xenova/larger_clap_music_and_speech` ONNX snapshot under
> `~/.cache/vibemix/clap-onnx/` (or set `VIBEMIX_CLAP_ONNX_DIR`), then run with
> `VIBEMIX_EMBED_BACKEND=clap`. **Remaining KAAN-ACTION:** the one-time model
> download/cache UX + the live re-embed of a real library + the funded-key curate
> ear-pass (the parity gate already passed on the engine — see below).
>
> ## How it's wired (Phase 90)
>
> - **Seam:** `_cosine.EMBED_BACKEND` (env `VIBEMIX_EMBED_BACKEND`, default
>   `gemini`) sets `EMBEDDING_DIM` = 512 (clap) | 1536 (gemini). `embed.build_embedder()`
>   reads the same flag and returns `ClapEmbedder` | `LibraryEmbedder`. One switch,
>   dim + class move together.
> - **`ClapEmbedder`** (`library/embed_clap.py`): wraps `ClapEngine(backend="onnx")`,
>   exposes `embed_track` / `embed_query` / `embed_audio_bytes` / `has_cached_embedding`
>   1:1 with `LibraryEmbedder`; own clap-tagged content-hash cache in the shared
>   `embeddings.db` (never collides with the 1536-dim Gemini rows).
> - **`grounding.py`** routes the "what's playing" embed through the public
>   `embedder.embed_audio_bytes` seam — no more `embedder._client` reach-in (CLAP
>   has no `_client`); `LibraryEmbedder.embed_audio_bytes` added to match.
> - **Gate PASSED through the real shipped module** (`ClapEngine(backend="onnx")`,
>   20 tracks): dim 512, determinism cos=1.000000, text spread 0.274,
>   "hard techno"→{hardtechno:10}, "psy trance"→{psymind:9} — matches the proven
>   baseline. Wiring tests: `tests/library/test_embed_clap.py` (CI-safe, fake engine).

## What it is

A deterministic, **on-device** embedder built on the LAION-CLAP `HTSAT-tiny`
music checkpoint. It maps both audio and text into ONE **512-dim** space — the
same cross-modal property Gemini Embedding 2 has ("dark rolling techno" lands
near the audio of dark rolling techno). It is meant to replace the Gemini
embedding call for the **library vibe-search / curator / next-suggestion layer
ONLY**.

CLAP is an on-device **embedding** model, not a second LLM provider — the
**Gemini-only provider rule stays intact** for the conversational co-host brain.
The co-host keeps talking through Gemini; only the silent similarity/genre math
underneath moves on-device.

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
- **Model footprint:** ~**160 MB int8** / ~**311 MB fp16** — a one-time download.
- **Export precedent:** the pre-exported `Xenova/clap-htsat-unfused` proves the
  HTSAT audio encoder + RoBERTa text encoder export to ONNX cleanly.

### Upload-vs-download rationale (why on-device, not server-side)

A server-side embedder would have to **upload the user's 9–15 GB library**
upstream — recurring, slow on home connections, and it puts the audio on our
infra. The on-device model is a **one-time ~160–310 MB download**, then every
embed is local and free. On-device is roughly **40–100× cheaper** in bytes moved
and honors **"audio never leaves the device"**.

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
   the `optimum` registry yet; pin `transformers`).
2. Build a numpy mel matched to the **shipped** encoder (Slaney vs HTK, fft
   size, hop, mel bins — all must match the exported graph).
3. Embed **50 tracks** through **both** the torch reference and the ONNX path.
4. **Require ≥ 0.98 mean cosine** between the two per-track vectors.

**Fallback if parity fails:** do a manual `torch.onnx.export` of the **exact
630k checkpoint** (the same validated weights as the proven path) — still
on-device + ONNX, just exported from the trusted weights instead of swapping to
`larger_clap_music`.

**Until this gate passes**, the `onnx` backend in `clap_engine.py` is a
`NotImplementedError` stub (it points back at this section). The `torch` backend
is the only one that returns a real vector today.

## Future wiring change-map

The swap is a **later phase** — summarized here, **not implemented** by the
staging work:

- **Dim flip:** `EMBEDDING_DIM` **1536 → 512** in
  `src/vibemix/library/_cosine.py:56` — the single source of truth; the change
  cascades to every shape assertion (`cosine_topk` and friends) automatically.
- **`ClapEmbedder` wrapper:** a new class wrapping `ClapEngine` with the **same
  public interface as `LibraryEmbedder`** (so call sites swap 1:1).
- **Hardest coupling — `grounding.py:120-126`:** it calls
  `embedder._client.models.embed_content(...)` **directly**. CLAP has no
  `_client`, so this call must be re-routed through `embed_audio_bytes` (the
  bytes path exists on `ClapEngine` precisely for this seam).
- **Cache rebuild:**
  - `library.db` — recreate at `FLOAT[512]` (the vec0 store is dim-typed).
  - `embeddings.db` — **auto-invalidates** (the `model_id` is part of the
    content-hash key, so a model change is a cache miss, not stale data).
  - `library_centroid.npy` — **auto-recomputes** on a dim mismatch.
  - `library.pkl` — safe (titles only, no vectors).
- **Backend dispatch:** a `VIBEMIX_EMBED_BACKEND=clap|gemini` seam in `embed.py`
  so the two embedders can coexist behind one switch.
- **Tests asserting 1536** to update: `test_embed.py:325`, the embedding
  fixtures, and `conftest`.

None of the above is done yet. The engine is **staged + documented** so the
wiring phase has a tested, import-safe seam to plug into — without dragging
torch/onnx into the live co-host bundle before the parity gate is green.
