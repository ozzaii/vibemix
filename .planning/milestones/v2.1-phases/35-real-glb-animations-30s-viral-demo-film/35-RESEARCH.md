# Phase 35 Research — Real GLB Animations + 30s Viral Demo Film

**Date:** 2026-05-15
**Mode:** gsd-autonomous fully — autonomous deliverables only

---

## 1. gltfpack / DRACO / KTX2 — toolchain decisions

### gltfpack (Khronos / meshoptimizer)

- `gltfpack -i in.glb -o out.glb -cc -c -tc -tq 8`
  - `-cc` enable meshopt compression (Khronos draft KHR_mesh_quantization + EXT_meshopt_compression)
  - `-c` DRACO level (cascade integer; `-cc -c` already covers; for traditional DRACO use `-c` only and tune level)
  - `-tc` KTX2 transcoding for textures
  - `-tq 8` texture quality (8 = good, 4 = small, 10 = max)
- DRACO L7+ ≈ `gltfpack -c -cl 7` (compress level 7 of 10). L7 is the sweet spot — L10 is +5% size reduction for +60% decode CPU.
- KTX2 (Basis Universal) — best for color textures; WebP is the fallback for transparency/alpha (KTX2 alpha-channel support requires UASTC mode which doubles size).
- **Decision:** ship `gltfpack` wrapped by `scripts/glb_optimize.py`. Python is the orchestration shell; gltfpack does the heavy lifting. Python validates per-clip + total budget.

### Per-clip + total budget

- Per-clip ≤ 600 KB (Phase 35 doctrine). Synthetic 700 KB → fail, 500 KB → pass.
- Total ≤ 25 MB (Phase 31 MASCOT-27 sub-budget under 350 MB hard cap). Already enforced by `tests/repo/test_mascot_glb_size_gate.py` + `scripts/check_mascot_glb_size.sh`. We EXTEND that test surface — new per-clip test joins the existing total test.

### Fallback: gltfpack absent

- The optimization script must not hard-fail CI when `gltfpack` binary is missing (CI runners may not install it). Behavior:
  - `--check` mode: scan existing GLBs for size budget violations only. No optimization. Always works.
  - `--optimize` mode: requires `gltfpack` on PATH. If missing → exit 2 with install hint.
- CI only needs `--check`. Kaan invokes `--optimize` locally before committing real GLBs.

---

## 2. ffmpeg — manual cut + concat pipeline

### Cut driver — `scripts/demo_film/cut.sh`

- Reads `cuts.json`: list of `{start, end, source}` cut points (≤ 8 cuts, P57).
- Per cut: `ffmpeg -ss <start> -to <end> -i <source> -c:v libx264 -c:a aac -y <out>/cut_NN.mp4`
- Concat: filelist `concat.txt` + `ffmpeg -f concat -safe 0 -i concat.txt -c copy -y demo.mp4`
- Stream-copy concat preserves quality + is fast. Re-encode only if codec mismatch.
- **No filter_complex auto-pacing, no smart cuts, no AI suggestions** (P57 — anti-slop).

### cuts.json schema

```json
{
  "source": "raw/dj_session_2026_05_15.mov",
  "cuts": [
    {"id": "beat_a_overlay", "start": "00:01:42.000", "end": "00:01:48.500"},
    {"id": "beat_b_lean_in", "start": "00:02:13.250", "end": "00:02:18.100"},
    {"id": "beat_c_reaction", "start": "00:02:22.000", "end": "00:02:30.000"}
  ],
  "vo_track": null,
  "max_cuts": 8
}
```

- `cuts` len > 8 → reject (P57).
- `vo_track`: null OR path. Never a Gemini/ElevenLabs/OpenAI TTS path (P58 — grep gate).
- `max_cuts` echoes the doctrine constant; presence is informational.

---

## 3. README hero hash sync gate

### Pattern

Current README hero line:

```html
<img src="docs/assets/demo-placeholder.gif" alt="vibemix demo (placeholder — real demo coming)" width="720" />
```

After Phase 35 ship, this becomes:

```html
<!-- vibemix:hero-start sha256=<HASH> -->
<video src="docs/assets/demo.mp4" alt="vibemix 30s demo" width="720" controls></video>
<!-- vibemix:hero-end -->
```

- Hash comment delimits the sync block AND carries the expected SHA256 of `docs/assets/demo.mp4`.
- `scripts/check_readme_hero_hash.py` parses the comment, hashes the asset, compares.
- CI workflow `.github/workflows/readme-hero-sync.yml` runs on PR + nightly.
- **Asset absent path:** if `docs/assets/demo.mp4` is missing (placeholder phase before Kaan-action), the script must NOT fail. It treats `sha256=PLACEHOLDER` as a sentinel meaning "asset not yet shipped — no drift to detect". This lets us land the gate now and have it activate when the real asset lands.

### Why a comment, not a `data-hash` attribute

GitHub's README rendering strips most HTML attributes but preserves comments. The comment also keeps the hash invisible to readers while being machine-parseable.

---

## 4. Existing infrastructure to integrate with

### Phase 31 GLB size gate (already shipped)

- `scripts/check_mascot_glb_size.sh` — 25 MB total cap, sums every `.glb` under `tauri/ui/assets/mascot/` + `tauri/ui/public/mascot/`.
- `tests/repo/test_mascot_glb_size_gate.py` — pytest wrapper.
- Phase 35 EXTENDS by adding per-clip 600 KB cap. New test: `test_mascot_glb_per_clip_under_600kb`. Same roots scanned.

### Existing prep_* placeholder GLBs

`tauri/ui/assets/mascot/animations/`:
- `prep_lean_in_neutral.glb`
- `prep_lean_in_hyped.glb`
- `prep_head_turn_left.glb`
- `prep_head_turn_right.glb`
- `prep_settle.glb`

These are LIVE placeholders currently loaded via `tauri/ui/assets/mascot/manifest.json`. The manifest already maps them to states. ASSETS-03 doctrine says **the placeholders stay in repo; real GLBs land via Kaan-action drop-in replacement at the same paths**.

→ `additive-layer.ts` change required: **none**. Filename pointing happens via manifest, which already points at `prep_*.glb` filenames. The "rename to `prep_*_placeholder.glb`" suggestion from CONTEXT was a red herring; the placeholders ARE the names that real GLBs will replace.

→ What we DO add: a comment in the manifest documenting placeholder status + a unit-test docstring tying the prep_* files to Phase 22-02 idle-zero contract.

### Phase 22-02 idle-zero contract

- Contract: prep_* clips must zero out the lower-body delta when sampled at t=0 (additive layer must not displace the base layer on first frame).
- Currently asserted at the layer level (`additive-layer.test.ts` makeClipAdditive call).
- Phase 35 preserves: when real GLBs replace placeholders, the test must still pass. We add a regression-style test that EXPLICITLY documents the contract in pytest form so the Python CI surface also fails loudly if Kaan ships a real GLB that breaks idle-zero.
- Since we can't actually parse GLB bone hierarchies from Python without three.js, the Python-side test is a STRUCTURAL contract test: it verifies the 5 prep_* GLB files exist + are non-empty + the TS test file references all 5. Bone-level validation stays in `additive-layer.test.ts` where it belongs.

### `.github/workflows/` patterns

Existing workflows: `release.yml`, `eval.yml`, `secret-scan.yml`, `capabilities-lint.yml`, `python-cve.yml`, `rust-cve.yml`. The new `readme-hero-sync.yml` follows the same pattern: ubuntu-latest, pytest call, run on PR + push to main.

---

## 5. Anti-slop discipline — forbidden-token grep gate

Per P58 + CONTEXT:

- `tests/scripts/test_demo_film_no_ai_vo.py`: grep `scripts/demo_film/` for known AI-VO services → fail if any appear.
- Token list: `elevenlabs`, `openai`, `gemini-tts`, `tts.googleapis`, `synth.voice`, `ai-voiceover`, `synthesize_speech`. Case-insensitive.
- The grep target is the scripts dir only, NOT the docs. The doctrine docs MUST be allowed to mention the forbidden terms in negation ("we do NOT use ElevenLabs"). To avoid false positives in our own doctrine docs, grep file extensions: `.sh`, `.py`, `.json`, `.ts`, `.js`.

---

## 6. Doctrine docs structure

### `scripts/demo_film/3beat_structure.md`

- Beat A: overlay highlight — 6-8s, mascot in neutral, overlay cue is the camera focal.
- Beat B: mascot lean-in BEFORE voice fires — 4-6s, anticipation prep_* clip, demonstrates "real DJ friend reading the room".
- Beat C: cited reaction — 6-10s, voice line + reaction clip, evidence string visible.

### `scripts/demo_film/recording_protocol.md`

- Kaan/Francesco-only. macOS Quartz screen capture via Phase 15 capability.
- 3min+ raw, single-take preferred.
- BlackHole audio routing live.
- Stash raw to `scripts/demo_film/raw/` (gitignored).

### `scripts/demo_film/vo_policy.md`

- Kaan or Francesco writes copy if any.
- Kaan or Francesco records voice if any.
- NO Gemini-TTS, NO ElevenLabs, NO OpenAI TTS, NO synthetic narration.
- Default: NO VO. Music + ambient + caption text only.
- This file is also a contract — its existence + content is grep'd to ensure no AI-VO path can land without explicit policy violation.

### `docs/asset_pipeline.md`

- Meshy v6 vs Hunyuan3D 3.0 — A/B with $50 credit.
- Mixamo auto-rig (free with Adobe account) + Rokoko fallback ($5/mo if Mixamo IK drifts per P61).
- SkeletonHelper QA — render skeleton in Three.js dev shell before commit.
- DRACO L7 + KTX2 via gltfpack.
- Drop into `tauri/ui/assets/mascot/animations/prep_*.glb` (overwrites placeholders).

---

## 7. KAAN-ACTION-LEGAL.md — additions

6 new entries. Mirror existing entry pattern (numbered, ID-coded, action steps, completion criteria, "Mark X as done when complete" line).

- `ASSETS-MESHY-A/B` — generate, A/B, pick.
- `ASSETS-MIXAMO-RIG` — Mixamo auto-rig, 8-12 motion clips, SkeletonHelper QA.
- `ASSETS-PREP-REPLACE` — drop real GLBs into `tauri/ui/assets/mascot/animations/`, ensure size budgets hold, Phase 22-02 contract holds.
- `ASSETS-SESSION-RECORD` — 3min+ raw DJ session.
- `ASSETS-DEMO-CUT` — manual ffmpeg cut, ≤8 cuts, 3-beat structure, populate `scripts/demo_film/cuts.json` + run `cut.sh`.
- `ASSETS-VO` — Kaan/Francesco-written + recorded OR no-VO.

---

## 8. Plan split (preview, ratified in 35-PLAN-INDEX.md)

1. **35-01** — `scripts/glb_optimize.py` + per-clip + total budget tests (ASSETS-04).
2. **35-02** — `scripts/demo_film/cut.sh` + `cuts.json` schema + `≤8 cuts` test (ASSETS-05).
3. **35-03** — `scripts/check_readme_hero_hash.py` + `.github/workflows/readme-hero-sync.yml` + drift test (ASSETS-07).
4. **35-04** — Doctrine docs: `3beat_structure.md`, `recording_protocol.md`, `vo_policy.md`, `docs/asset_pipeline.md` + grep gate test (ASSETS-01/02/06).
5. **35-05** — manifest.json comment + Phase 22-02 structural contract test + README hero block comment (ASSETS-03).
6. **35-06** — KAAN-ACTION-LEGAL.md entries (ASSETS-MESHY/MIXAMO/PREP/SESSION/DEMO/VO).

---

## 9. Open risks / things to watch

- gltfpack version drift — pin to a specific release in install hint.
- README hero comment may be stripped if a future tooling pass minifies HTML — add comment to `tests/repo/test_readme_shape.py` follow-up if drift seen.
- `cuts.json` schema enforcement is informational only at the JSON level — the test is the real gate.
- All tests run against synthetic fixtures since real GLBs / demo.mp4 are Kaan-action.

