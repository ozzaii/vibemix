# QUEUE — UX lane (THE priority lane). Pull top, loop, no regression.

> Goal contract: `.planning/packets/2026-06-04/CODEX-GOAL-UX.md`. Gate: `cd tauri/ui && npm run build && npm test` (~886 vitest) + `grounding-failure.spec.ts`; never reduce the green count. Visual = impeccable self-review vs `mocks/`, flagged for Kaan's eye-pass (no vision judge tonight).

## Correctness floor (clear first)
- [ ] 1. MOSS→Chatterbox rename+reroute — badge resolves on `chatterbox-voice`, neutral "Voice" copy. (`shell/VoiceReadinessBadge.ts:42`, `settings/SettingsDrawer.ts:945`, `wizard/step0-intro.ts:522`, `library/api.ts:124,162,2524-2531`, `shell/dj-vocab.ts`, `DesktopShell.ts:90`)
- [ ] 2. Install/repair button real end-to-end. (`library_cmds.rs:331,190` remap `moss→chatterbox`; backend supports `--install chatterbox`)
- [ ] 3. Re-key the test pins to `chatterbox-voice` (they LOCK the dead contract). (`library/model-setup.test.ts`, `api.test.ts:106-148`, `build.test.ts:155-268`)
- [ ] 4. Voice-status chip inside Learn (`ipc.status.tick.voice`). (`learn/components/status-bar.ts`)

## Elevation pass (the real mission — impeccable, after the floor)
- [ ] 5. Session deck hero — grounded-vs-idle unmistakable, kill telemetry/defensive-copy slop. (`session/*`, `shell/*`; mock `vibemix-rebuild-session.html`)
- [ ] 6. Learn legibility — single next action obvious on open; booth/recommended/"your move" legible. (`learn/*`)
- [ ] 7. Viber/Crate — real tool_trace legibility, BUILD/CUE/INGEST affordances obvious.
- [ ] 8. Wizard/first-run — every screen names the next action; honest on-device framing.
- [ ] 9. (stretch) silent-lesson honesty — "no audio for this drill" instead of "listen" over silence.

When queue dry AND build+test green → `DONE-ALL-ux.md` (flag screens needing Kaan's eye-pass). Hard blocker → `BLOCKED-ux.md` + continue an unblocked item.
