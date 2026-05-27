# CLAP Phase-A Spike — Results

**Date:** 2026-05-25 · **Scope:** /tmp-only viability experiment · **Goal:** go/no-go on replacing
Gemini audio embedding with LAION-CLAP `larger_clap_music` (Apache-2.0) for audio→audio similarity.

---

## VERDICT: INCONCLUSIVE — deps installed cleanly, but the 777 MB model download stalled on slow internet. NOT a no-go; resume when bandwidth is healthy.

The experiment was **set up successfully end-to-end** (env + all deps + spike script ready), and the model
download **started** (xet backend, reached 97 MB / 777 MB) but then **flatlined at 97 MB for ~2.5 min
straight with zero throughput** — the owner's slow/flaky connection throttled the transfer to a halt.
Per the brief's hard rule (can't finish in ~15 min → stop + write the recipe), I stopped rather than
block forever. **No neighbor lists were produced** because the model never finished loading.

This is a *connectivity* result, not a *quality* result. CLAP is fully viable to test — everything is
staged. The moment internet is good, one command finishes it (the download even resumes from the 97 MB
partial via xet's content-addressed cache).

---

## What completed (the feasibility facts that matter)

### Install: SMALL, not multi-GB. Clean.
- Created isolated venv at `/tmp/clap_spike/.venv` (Python 3.12.12 via `uv`).
- `uv pip install torch transformers librosa soundfile numpy scikit-learn` **succeeded** —
  torch **2.12.0**, transformers **5.9.0**, librosa **0.11.0**. All imports verified.
- **Wheel download total ≈ 165 MB** (measured from PyPI): torch arm64 macOS wheel **88 MB**
  (NO CUDA — Mac arm64 wheels are CPU-only and small), llvmlite 37 MB, scipy 21 MB, sklearn 8 MB,
  + small stuff. Installed venv on disk = **856 MB** (unpacked).
- **Correction to the research doc's §6 install-size claim:** it estimated "torch+transformers ≈
  2-2.5 GB". On **macOS arm64** the actual torch wheel is **88 MB download** / ~300 MB unpacked — the
  multi-GB figure is the Linux+CUDA case. The torch path is far lighter on Mac than the doc assumed.
  (ONNX-int8 is still the right *ship* path for the Windows bundle + one-click cap, but torch-on-Mac for
  the spike/dev path is cheap.)

### Model download: the blocker.
- `laion/larger_clap_music` repo = 10 files; the weight `pytorch_model.bin` = **777 MB** (HEAD-verified).
- Config + tokenizer files (small) downloaded fine. The 777 MB weight downloads via HF **xet** chunked
  backend into `~/.cache/huggingface/xet` (NOT the `.incomplete` blob — that stays 0 until assembly).
- Progress: 0 → 97 MB in the first ~1 min, then **stalled at 97 MB** (held flat across three checks:
  20s, 45s, 90s — `nettop` showed the python proc alive but ~0 bytes moving). Slow internet, confirmed.
- Total fresh download to run the spike ≈ **165 MB wheels + 777 MB model ≈ ~940 MB**.

### Per-track embed speed: NOT MEASURED (model never loaded). Research doc estimates ~1-3 s/track CPU on
M-series; plausible but unverified here.

### Neighbor lists / clustering quality: NOT MEASURED. This is the actual go/no-go signal and it remains
open. The Gemini baseline (hard-techno query → IMEON/CREAM/HardtraX/PVR pulled cleanly) has nothing to
compare against yet.

---

## EXACT RESUME RECIPE (everything is already staged in /tmp — do this on good internet)

The venv and the spike script already exist. **One command** finishes it:

```bash
# 1. (already done — venv + deps live at /tmp/clap_spike/.venv, ~856 MB on disk)
#    If /tmp was cleared, recreate:
uv venv --python 3.12 /tmp/clap_spike/.venv
uv pip install --python /tmp/clap_spike/.venv/bin/python torch transformers librosa soundfile numpy scikit-learn

# 2. Run the spike (downloads the 777 MB model on first call; resumes from the 97 MB xet partial):
cd /tmp/clap_spike && /tmp/clap_spike/.venv/bin/python spike.py
```

`spike.py` (already written at `/tmp/clap_spike/spike.py`) does the full Phase-A test:
- Resolves ~14 cross-genre files from `/Users/ozai/Music/runnin over my body` (hard/aggressive:
  Brutalismus 3000, CRRDR TRI-TEK, 2HOT2PLAY, "64 Extended"; vocal/pop/rap: Azealia Banks, Charli XCX,
  365 ft shygirl, BDE ft slowthai, Club classics).
- Loads `ClapModel`/`ClapProcessor` from `laion/larger_clap_music`.
- Embeds a 30s mono excerpt (offset 20s) of each at 48 kHz via `get_audio_features`.
- Prints **raw cosine** AND **mean-centered cosine** off-diagonal stats + top-5 neighbors for 4 seeds.
- Runs **text→audio**: queries "hard aggressive techno", "soft female vocal pop song",
  "funky house groove", "distorted hardcore gabber" → top-5 tracks each (`get_text_features`).
- Dumps raw numbers to `/tmp/clap_spike/raw_results.json`.

**Download sizes to budget:** wheels ~165 MB (cached if venv kept) + model 777 MB. On a healthy
connection (~10 MB/s) the model is ~80 s; the stall here was pure bandwidth, not a code/setup problem.

**Faster alternative if the full 777 MB is still painful:** test the smaller general
`laion/clap-htsat-unfused` (~600 MB) first as a sanity check, or pre-stage the model via
`huggingface-cli download laion/larger_clap_music` overnight so the embed run is instant. Note the
research doc's recommendation stands: for *shipping*, export to **int8 ONNX (~190 MB, onnxruntime, no
torch)** — but that export step itself needs the 777 MB fp32 weights downloaded once first, so this same
download gates Phase B regardless.

---

## What we DID learn (actionable)

1. **Dependency feasibility = GREEN.** torch + transformers + librosa install on Mac arm64 / py3.12 with
   zero friction, and far smaller than the research doc feared (~165 MB, not 2.5 GB). The torch path is
   not a blocker for dev/spike work.
2. **The only feasibility risk is the one-time 777 MB weight pull on slow internet** — and it's a
   one-time cost (cached forever after, and ships as a ~190 MB ONNX asset, never re-downloaded by users).
3. **The quality go/no-go is still unanswered** and must be — re-run the staged script on good bandwidth.
   Do not commit to Phase B until the neighbor lists pass Kaan's ear test vs the Gemini baseline.

## Hygiene
- Nothing under `/Users/ozai/projects/dj-set-ai` was touched. Nothing under `~/.cache/vibemix` was touched.
- Artifacts left in /tmp: `/tmp/clap_spike/{.venv,spike.py,install.log,run.log}`.
- Side effect outside /tmp: partial model in `~/.cache/huggingface/{hub,xet}` (~97 MB) — *helps* the
  resume (don't delete it). Delete with `rm -rf ~/.cache/huggingface/hub/models--laion--larger_clap_music
  ~/.cache/huggingface/xet` if you want it gone.
