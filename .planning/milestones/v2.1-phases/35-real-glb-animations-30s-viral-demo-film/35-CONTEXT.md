# Phase 35: Real GLB Animations + 30s Viral Demo Film - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

Replace v2.0 placeholder GLBs with real Mixamo-rigged animations + ship a 30s viral demo film embedded in the GitHub release + README hero.

**Mapped REQ-IDs (7):** ASSETS-01 (Meshy v6 vs Hunyuan3D A/B), ASSETS-02 (Mixamo auto-rig + 8-12 motion clips), ASSETS-03 (replace 5 v2.0 prep_* placeholders — closes MASCOT-11), ASSETS-04 (DRACO L7+ + KTX2/WebP optimization, ≤25MB total), ASSETS-05 (`scripts/demo_film/` + ffmpeg manual edit ≤8 cuts), ASSETS-06 (real DJ session screen capture source), ASSETS-07 (`demo.mp4` in Release + README hero + sync test).

**In scope (autonomous):**
- Asset pipeline infrastructure: `scripts/glb_optimize.py` (DRACO + KTX2 batch), `scripts/demo_film/` orchestration scripts, `scripts/check_readme_hero_hash.py` CI sync gate.
- GLB loader paths in `additive-layer.ts` updated to consume real GLBs (file paths only; placeholders remain in repo until real GLBs land).
- CI gates: `≤25MB total mascot GLB budget` (already from Phase 31 MASCOT-27 — extend coverage), `≤600KB per clip`, README hero hash sync.
- Documentation: `docs/asset_pipeline.md` covering Meshy → Mixamo → DRACO → KTX2 flow; Rokoko fallback documented.

**Out of scope (autonomous; deferred to KAAN-ACTION-LEGAL):**
- ACTUAL Meshy v6 / Hunyuan3D 3.0 generation credit purchase + model creation (Kaan-action, ~$50).
- ACTUAL Mixamo signup + auto-rigging + motion clip selection (Kaan-action, free Adobe account).
- ACTUAL real DJ session 3min+ recording (Kaan-action — live session needed).
- ACTUAL ffmpeg manual editing of demo.mp4 (Kaan/Francesco-action, anti-AI-slop bar).
- ACTUAL voiceover (Kaan/Francesco-written or no-VO — anti-slop).

**Pure-out-of-scope (not in v2.1):**
- AI-auto-cut video editing (Pitfall P57 — anti-feature).
- AI-generated voiceover (Pitfall P58 — anti-slop).
- Audio music in demo (rights complications).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

This is a heavily external-dependent phase. Autonomous mode delivers pipeline + CI infrastructure; real asset generation is Kaan-action.

Grounded in:
- ROADMAP Phase 35 verbatim success criteria
- REQUIREMENTS.md ASSETS-01..07
- Pitfalls P52 (350MB cap + sub-budget), P57 (manual edit ≤8 cuts), P58 (human VO or no VO), P61 (Mixamo IK drift → SkeletonHelper QA), P68 (README hero stale)
- Phase 31 4-layer mascot (shipped) — additive-layer consumes GLB filenames
- v2.0 Phase 22 prep_* placeholders (shipped — to be replaced)
- v2.0 Phase 24 overlay + Phase 26 day-zero scaffold (shipped)
- Memory `project_mascot_as_vtuber_personality_surface` — single mascot character
- Memory `project_visual_direction_cdj_whisper` — visual restraint

### Asset pipeline scripts (ASSETS-04 pipeline)
- `scripts/glb_optimize.py`: batch DRACO L7+ + KTX2/WebP. Input dir → output dir. Per-file size assertion ≤ 600 KB. Total assertion ≤ 25 MB.
- Library: `gltfpack` (Khronos) for DRACO + KTX2.
- CI invocation: `python scripts/glb_optimize.py --check tauri/ui/public/mascot/` → exit 1 if any clip > 600 KB or total > 25 MB.
- Test: synthetic 700KB GLB → script fails. 500KB GLB → script passes.

### Demo film orchestration (ASSETS-05, ASSETS-06)
- `scripts/demo_film/cut.sh`: ffmpeg manual cut driver with named cut points (Beat A, Beat B, Beat C). Reads `scripts/demo_film/cuts.json` (cut count ≤ 8 — Pitfall P57).
- `scripts/demo_film/3beat_structure.md`: documents the 3-beat doctrine (Beat A overlay highlight, Beat B mascot lean-in BEFORE voice, Beat C cited reaction).
- `scripts/demo_film/recording_protocol.md`: how Kaan/Francesco records the 3min+ raw DJ session.
- NO auto-cut, NO AI-suggested cuts (P57 — anti-slop).

### Voiceover policy (ASSETS-05 / P58)
- `scripts/demo_film/vo_policy.md`: Kaan/Francesco-written OR no-VO. AI-generated VO explicitly rejected.

### GLB loader path update
- `tauri/ui/src/mascot/additive-layer.ts` (or layer-specific files) — update GLB file names from `prep_*_placeholder.glb` → `prep_*.glb`. Placeholders remain in repo with `.placeholder` suffix until real GLBs land.

### Idle-zero lower-body delta preservation (ASSETS-03 / Phase 22-02 contract)
- All 5 prep_* clips must preserve `idle-zero lower-body delta` invariant — Phase 22-02 test contract. Inherited by Phase 31. Test still passes after Kaan drops in real GLBs.

### README hero sync (ASSETS-07 / P68)
- `scripts/check_readme_hero_hash.py`: parses README hero block, extracts video src hash, compares to current `demo.mp4` SHA256.
- CI: `.github/workflows/readme-hero-sync.yml` runs on PR + nightly. Fails if README hero hash drifts.
- README hero block: `<video src="demo.mp4" data-hash="<sha256>">` HTML embed with explicit hash attribute.

### KAAN-ACTION-LEGAL.md entries
- `ASSETS-MESHY-A/B`: Meshy v6 vs Hunyuan3D 3.0 generation, $50 credit budget, pick winner, hash-cache output → drop into `tauri/ui/public/mascot/raw/`.
- `ASSETS-MIXAMO-RIG`: Mixamo auto-rig 8-12 motion clips. SkeletonHelper QA before drop.
- `ASSETS-PREP-REPLACE`: replace 5 prep_* placeholders with real GLBs, preserve Phase 22-02 idle-zero delta.
- `ASSETS-SESSION-RECORD`: record real DJ session 3min+, Quartz screen capture, vibemix running live.
- `ASSETS-DEMO-CUT`: manual ffmpeg cut 30s demo.mp4, ≤8 cuts, 3-beat structure.
- `ASSETS-VO`: Kaan/Francesco voiceover OR no-VO.

### Test discipline
- `test_glb_size_per_clip_under_600kb` (synthetic GLB).
- `test_glb_total_under_25mb` (synthetic + Phase 31 gate extension).
- `test_idle_zero_lower_body_delta_preserved` (Phase 22-02 contract — runs against placeholder + against real GLB when present).
- `test_readme_hero_hash_sync_drift_detected`.
- `test_demo_cuts_under_8` (parse cuts.json).
- `test_no_ai_vo_in_pipeline` (grep `scripts/demo_film/` for "elevenlabs", "openai", "gemini-tts" → must not appear).

</decisions>

<code_context>
## Existing Code Insights

- **Phase 31 (just shipped)** — `additive-layer.ts` 4-channel, `scripts/check_mascot_glb_size.sh` for 25MB CI gate.
- **v2.0 Phase 22 (shipped)** — 5 `prep_*` placeholder GLBs at `tauri/ui/public/mascot/`. Phase 22-02 test = `test_idle_zero_lower_body_delta`.
- **v2.0 Phase 24 (shipped)** — overlay rendering. Mascot path is consumer.
- **v2.0 Phase 26 (shipped)** — day-zero scaffold. README hero block stub exists.
- **v2.0 Phase 15 (shipped)** — recording capability (Quartz screen capture).
- **Memory mascot direction** — single VTuber-style character, mood variation. Picked pipeline: Meshy/Hunyuan3D + Mixamo + Three.js.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **No AI-auto-cut** (P57) — humans cut the 30s demo. ≤8 cuts.
- **No AI voiceover** (P58) — Kaan/Francesco-written or no VO.
- **Meshy v6 vs Hunyuan3D 3.0** — A/B with ~$50 credits.
- **Mixamo auto-rig** — free with Adobe account, Rokoko fallback documented.
- **DRACO L7+ + KTX2/WebP** — standard GLB optimization.
- **Per-clip ≤600KB, total ≤25MB** — sub-budget under 350MB cap.
- **README hero hash sync** — prevents stale demo.mp4 drift after ship.

</specifics>

<deferred>
## Deferred Ideas

- **AI-auto-cut video editor (Pitfall P57)** — REJECTED.
- **AI voiceover (Pitfall P58)** — REJECTED.
- **Music in demo (rights)** — out of scope.
- **Multiple mascot characters** — out of scope (single character locked).
- **Real-time motion capture from webcam → mascot** — v2.2 stretch.
- **Demo film variant for Twitter / IG short** — v2.2.
- **Localized demo film versions (TR / IT)** — v2.2.

</deferred>

<kaan_action_required>
## Critical: Kaan-Action Required (Deferred via KAAN-ACTION-LEGAL.md)

Phase 35 cannot fully ship without Kaan-action items:
1. Meshy v6 / Hunyuan3D 3.0 model generation ($50 credits).
2. Mixamo auto-rigging + 8-12 motion clips selection.
3. Real DJ session 3min+ raw recording.
4. Manual ffmpeg cut → 30s demo.mp4 (≤8 cuts, 3-beat).
5. Voiceover (Kaan/Francesco-written) OR no-VO decision.

Autonomous deliverables: pipeline scripts, CI gates, documentation, placeholder loader paths, all tests passing against synthetic fixtures. Real GLBs + demo.mp4 land when Kaan completes Kaan-action.
</kaan_action_required>
