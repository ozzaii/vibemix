# Phase 47 Discussion Log — Mascot Real GLB Land + Full Emotion Coverage

**Date:** 2026-05-18
**Mode:** `gsd-autonomous fully` / `gsd-discuss-phase --auto` — all grey areas auto-resolved silently.

This is a human-reference record. Downstream agents (researcher, planner, executor) read `47-CONTEXT.md` instead.

---

## Auto-Resolved Grey Areas

All discussion questions auto-answered with first/recommended option. No AskUserQuestion calls.

### Areas selected: all (per `--auto` cap)

1. Clip Taxonomy + Slot Naming
2. Retarget CLI Extension
3. Bundle-Gate Strategy
4. State-Machine Wiring
5. Pools.ts Update Strategy
6. Persona Smoke Script
7. README Hero GLB Render
8. POC Immutability + mascot.html
9. Anti-slop Blocklist Extension
10. Worktree Step-0 Invariant

### Resolution summary

See `47-CONTEXT.md` § Decisions for full per-area record.

### Notable defaults locked

- Slot file-name convention: `<family>_<name>.glb` (base/emotion/prep/react prefixes).
- Old `prep_*` Phase-22-02 placeholders RETAINED (additional 5 new `prep_kick/breakdown/drop/layer/mix` join them, NOT alias).
- Bundle gate: draco retune under 25 MB Tier-1 cap (preferred); 30 MB bump documented as fallback only.
- Per-family size bands: Base 200-600 KB / Emotion 300-900 KB / Anticipation+Reaction 400-1200 KB.
- 4-layer × 7-event coverage matrix lives at `tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts`.
- Hero render: `react_hype_peak` 3s WebM loop + still PNG, sized < 100 KB each (no LFS).
- POC immutability grep gate wires into existing `.github/workflows/poc-immutability-check.yml`.
- Worktree Step-0 invariant MANDATED for every subagent prompt skeleton.

---

## Deferred Ideas (captured for future roadmap)

- `/hatch` user-generated mascot pipeline (v2.x stretch).
- Multiple character rigs (v2.x stretch — single VTuber Neon Rebel lock per memory).
- TTS waveform-driven lipsync (separate phase).
- MIDI-move-driven mascot reactions (separate phase).
- Procedural animation blending engine replacement (no scope).

---

## Kaan-Action Surface (surfaced to STATE.md)

**KAAN-ACTION-LEGAL §VIS-04** — Mixamo Adobe-account walk. Engineering ships all scaffolds + placeholders + CLI + manifest + test harness + state-machine wiring + bundle-gate logic NOW. Kaan downloads + selects 23 retargets at convenience. Bundle gate flips green automatically on drop-in.

Per memory `feedback_autonomous_no_grey_area_pause`: continue unblocked engineering work; surface this to STATE.md "Phase 47 Kaan-Action Surface" block; do NOT pause.
