# CODEX GOAL — UX (utmost priority)

Worktree: /Users/ozai/projects/qa-ux (branch qa/ux). Touch `tauri/**` + `tauri/src-tauri/src/library_cmds.rs` ONLY. Use the impeccable + frontend-enforcement + stop-slop skills.

MISSION: UX is the utmost-priority layer — the engine and the soul are strong, UX is the dark layer that gates the whole product. Make every surface legible (you instantly know the next action), alive, and slop-free — impeccable craft. Clear the floor first: voice is invisible today (the readiness badge is keyed to the dead model id `moss-tts`, the backend now emits `chatterbox-voice` → the badge hides; the install path is dead). Then elevate the hero surfaces.

DONE = your self-check (run it to decide BOTH "what next" and "am I there yet"):
`cd tauri/ui && npm run build && npm test` (~886 vitest) + `grounding-failure.spec.ts` stay green, the voice-readiness badge resolves and shows status, the install path is real, and the MOSS test-pins are re-keyed to chatterbox — AND each hero surface (session, Learn, Viber, wizard) is self-reviewed against `mocks/` + the impeccable laws and FLAGGED for Kaan's eye-pass (there is no vision judge tonight, so you do NOT self-certify "UX done"). Voice must be visible; nothing reads as AI slop.

HOW TO WORK — do NOT restart, do NOT tunnel:
- Plan your own steps toward DONE. Pick the next step from the GAP (the weakest surface / the failing test), never from a fixed list.
- Build → `npm run build && npm test` green (fix your own change, never advance on red) → REGRESSION GUARD: never reduce the green count.
- Commit each gain surgically (`git add <exact paths>`, never `-A`; verify `git diff --cached --name-only`; if you touch `messages.schema.json`, run `npm run codegen:ipc` in the SAME commit) ending the message with:
  `QA-LANE: ux` / `QA-ITEM: <slug>` / `QA-VERIFY: cd tauri/ui && npm run build && npm test` / `QA-PASS: <true|false>`.
- Loop. Halt only on a hard blocker (write it down, switch angle). Never idle waiting on anyone.

ORIENTATION (pointers to save you time — re-derive, this is NOT a script to execute top-down): badge `shell/VoiceReadinessBadge.ts:42` resolve `chatterbox-voice` + neutral "Voice" copy (`:3,54,62,68-101`); `settings/SettingsDrawer.ts:945` drop `sub:"MOSS"`; `wizard/step0-intro.ts:522` → `["Voice","on-device"]`; `library/api.ts:124,162,2524-2531` retype id; install remap `library_cmds.rs:331,190` `moss→chatterbox` (Python already supports `--install chatterbox`); re-key `model-setup.test.ts` / `api.test.ts` / `build.test.ts`; voice chip in Learn `learn/components/status-bar.ts`; then elevate session/Learn/Viber/wizard against `mocks/`.

LAW: `tauri/**` + `library_cmds.rs` only — do NOT touch `src/vibemix/` (the backend lane owns it; it already emits `chatterbox-voice`). stop-slop on user copy, no model filenames in user copy, positive framing. Commit `-s Kaan Özkan <rahipdotaci@gmail.com>`. Not yours: Sven/engine (backend lane), the vision-judge build.
