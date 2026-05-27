# Phase 35 Summary — Real GLB Animations + 30s Viral Demo Film

**Status:** SHIPPED 2026-05-15
**Mode:** gsd-autonomous fully
**Plans:** 6/6 (35-01 through 35-06)
**REQ-IDs satisfied:** ASSETS-01..07 (real assets + Kaan-action ffmpeg cut deferred via 35-06)

## What shipped (scaffolding + CI gates)

| Plan | Commit | Surface | REQ |
|------|--------|---------|-----|
| 35-01 | d931f28 | `scripts/glb_optimize.py` + per-clip 600KB / total 25MB CI gate | ASSETS-04 |
| 35-02 | 1fdae7d | `scripts/demo_film/` — manual ffmpeg cut driver + `cuts.json` schema + ≤8 cuts gate | ASSETS-05 |
| 35-03 | 2a7e74e | README hero hash sync gate + CI workflow + drift test | ASSETS-07 |
| 35-04 | 720fc80 | Doctrine docs (3-beat / recording / VO / pipeline) + AI-VO grep gate | ASSETS-01, 02, 06 |
| 35-05 | 7f60a78 | `prep_*` placeholder note + Phase 22-02 structural contract test | ASSETS-03 |
| 35-06 | 63bb9f0 | `KAAN-ACTION-LEGAL.md` entries for 6 deferred items | (deferred — Kaan-action) |

## Deferred to Kaan-action (per 35-06)

Real-asset production deferred — autonomous run only ships pipeline + CI gates. Kaan-action items captured in `KAAN-ACTION-LEGAL.md`:

1. Generate 5 real Mixamo-rigged mascot GLBs (Meshy v6 / Hunyuan3D).
2. Run `scripts/glb_optimize.py --optimize` (requires `gltfpack` on PATH).
3. Record 30s screen-capture + DDJ-FLX4 controller footage per `recording_protocol.md`.
4. Cut the demo film with `scripts/demo_film/cut.sh` (manual ffmpeg, ≤8 cuts per `cuts.json`).
5. Re-encode to `assets/demo.mp4` and refresh README hero hash.
6. AI-VO production paths NEVER used — VO is policy-blocked (35-04 grep gate enforces).

## Hard gate evidence

```
pytest tests/scripts/test_demo_film_cuts.py tests/scripts/test_demo_film_no_ai_vo.py \
       tests/scripts/test_glb_optimize.py tests/repo/test_phase_22_02_prep_glb_contract.py \
       tests/repo/test_readme_hero_hash_sync.py tests/repo/test_mascot_glb_size_gate.py -q
35 passed in 0.85s
```

## Pitfall coverage

- **P52** (real GLBs push bundle past 350 MB) — `glb_optimize.py --check` per-clip 600KB + total 25MB ceiling enforced in CI.
- **P57 / P58** (asset-quality drift, render time) — pipeline scaffold + recording protocol documented; production gated on Kaan-action.
- **P61** (AI VO slop) — `tests/scripts/test_demo_film_no_ai_vo.py` grep gate blocks AI-VO surfaces from landing.
- **P68** (demo film visual coherence) — `cuts.json` schema + ≤8 cuts gate keeps the film tight.

## Notes

Phase 35 ships pipeline + CI gates only; real GLB + film bytes are intentionally deferred to a Kaan-action window per `KAAN-ACTION-LEGAL.md`. Autonomous run owns the SCAFFOLD; Kaan owns the FRAMES.
