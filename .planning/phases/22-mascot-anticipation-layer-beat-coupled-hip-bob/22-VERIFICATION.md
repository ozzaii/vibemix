---
status: human_needed
phase: 22
phase_name: Mascot Anticipation Layer + Beat-Coupled Hip-Bob
verified_at: 2026-05-14
mode: gsd-autonomous fully
plans_verified_auto: 2
plans_deferred_human: 2
must_haves_total: 4
must_haves_verified: 2
must_haves_human_pending: 2
---

# Phase 22 — Verification

**Mode:** Autonomous (fully). Plan 22-01 shipped spike script (real measurement = Kaan during Phase 16). Plan 22-02 shipped AdditiveLayer + manifest + sidecar 30Hz fields + 5 GLB stubs (real prep_* animations = artist task).

## ROADMAP Success Criteria

| # | Criterion | Auto-test | Human-test | Notes |
|---|-----------|-----------|------------|-------|
| 1 | Wave 0 Gemini text-channel ordering verdict | ✓ spike script + synthetic-mode tests | ⏸ Kaan-action | KAAN-ACTION.md: run during Phase 16 DJ session, ≥10 turns. |
| 2 | 5 prep_* clips additive-blended on existing AnimationMixer | ✓ AdditiveLayer.test.ts (8 vitest) | ⏸ artist-action | GLB stubs byte-copied from Mixamo; real prep_* animations = Blender export per ASSETS.md. |
| 3 | Sidecar 30Hz mascot snapshot extended with `beat_phase` + `active_genre` | ✓ test_ws_bus_phase22_fields.py (4 pytest) | — | Live + tested. |
| 4 | Anticipation fires 400-1200ms BEFORE Gemini voice arrives | ✗ blocked on real GLBs + Wave-0 verdict | ⏸ Kaan ear-test + artist | Closure path documented in 22-02-SUMMARY. |

## Auto-test Verification

- `pytest -q` baseline: 1843 → 1847 (+4 new), 10 pre-existing failures unchanged.
- `vitest tauri/ui`: 421 → 429 (+8 new).
- AdditiveLayer uses caller's AnimationMixer (Pitfall 19 single-mixer mandate honored).

## Deferred to Kaan / Artist Action

- **Spike measurement** — Kaan runs `scripts/spike_gemini_text_ordering.py` during Phase 16 DJ session; records verdict in WAVE-0-SPIKE.md.
- **Real prep_* GLB animations** — Blender export per ASSETS.md authoring brief; replaces stubs before P26 viral demo / v2.0 RC.

## Status

✓ Code-side contract live, additively-tested, sidecar wired.
⏸ Real animations + spike measurement = Kaan-action / artist task; documented in KAAN-ACTION.md.
