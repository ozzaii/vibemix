# Mascot — Phase 47 docs

This directory carries the Phase 47 mascot deliverables:

- `persona_smoke.webm` — 30-second persona smoke screencast (see below).
- `BUNDLE-DECISION.md` — 25 MB cap vs 30 MB bump audit trail.

## Persona smoke

A 30-second headless capture that cycles through every Phase 47 emotion
and reaction at least once, proving the 23-clip + 4-layer additive
state machine renders end-to-end.

### What's in the smoke

| Range | Clip | Layer |
|-------|------|-------|
| t=1-3.5s | emotion_joy | Emotion (priority 60) |
| t=3.5-6s | emotion_trust | Emotion |
| t=6-8.5s | emotion_surprise | Emotion |
| t=8.5-11s | emotion_anticipation | Emotion |
| t=11-13.5s | emotion_focus | Emotion |
| t=13.5-15s | react_kick_swap | Reaction (priority 80) |
| t=15-16.5s | react_sub_layer | Reaction |
| t=16.5-18s | react_breakdown | Reaction |
| t=18-19.5s | react_reentry | Reaction |
| t=19.5-21s | react_phrase_boundary | Reaction |
| t=21-22.5s | react_distortion_climb | Reaction |
| t=22.5-24s | react_acid_line | Reaction |
| t=24-25.5s | react_mix_in | Reaction |
| t=25.5-27s | react_mix_out | Reaction |
| t=27-30s | react_hype_peak | Reaction (README hero anchor) |

Schedule: `tauri/ui/src/mascot/persona-smoke-harness.ts` exports
`PERSONA_SMOKE_SCHEDULE` as the single source of truth.

### Running the smoke

From repo root:

```bash
bash scripts/mascot/persona_smoke.sh
```

Outputs `docs/mascot/persona_smoke.webm` (480p VP9, ~800 kbps, < 5 MB).

Platform paths:

- **Mac:** ffmpeg captures via avfoundation; operator runs
  `cd tauri && cargo tauri dev -- --persona-smoke` in a separate
  terminal first.
- **Linux:** xvfb-run + ffmpeg x11grab on virtual display :99.

### When the smoke runs

- **Weekly CI cron** + manual `workflow_dispatch` (per
  `.planning/phases/47-*/47-CONTEXT.md` § Persona Smoke Script — not
  a per-PR gate; per-PR coverage is via the vitest
  event-coverage-matrix at `tauri/ui/src/mascot/__tests__/`).
- **Locally on Mac** before §VIS-04 discharge (placeholders) and
  after (real retargets) to compare visual output.

### Placeholder smoke vs real smoke

Before Kaan §VIS-04 discharge: every clip aliases `prep_settle.glb`
via `seed_phase_47_placeholders.py`, so the WebM shows the same
breathing-idle animation for all 15 states. The 15 captions still
advance, proving event dispatch routes correctly.

After §VIS-04 discharge: each clip plays its Mixamo-retargeted
Neon Rebel animation. The WebM becomes the persona showcase.
