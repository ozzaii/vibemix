# CODEX GOAL — UX (THE priority lane: legible, alive, slop-free)

Worktree: /Users/ozai/projects/qa-ux (branch qa/ux). Island: `tauri/**` + `tauri/src-tauri/src/library_cmds.rs` ONLY. HEAD 364c55ba. Use the impeccable + frontend-enforcement + stop-slop skills. Full ref in-tree: `.planning/packets/2026-06-04/CODEX-GOAL-UX.md`.

PRIORITY (Kaan, explicit): UX is of UTMOST importance. The engine/soul are strong; UX is the dark layer that gates the whole product. Mission = make every surface legible (you instantly know what to do), alive, and slop-free — impeccable craft. The voice fixes are the FLOOR you clear first; then you ELEVATE.

FLOOR (first):
1. MOSS→Chatterbox rename + reroute. Badge keys on dead `model.id === "moss-tts"`; backend emits `"chatterbox-voice"` → badge silently hidden = ZERO voice status (Kaan's "TTS is not there"). Fix: `shell/VoiceReadinessBadge.ts:42` resolve `"chatterbox-voice"` + neutral "Voice" copy (`:3,54,62,68-101`); `settings/SettingsDrawer.ts:945` drop `sub:"MOSS"`; `wizard/step0-intro.ts:522` → `["Voice","on-device"]`; `library/api.ts:124,162,2524-2531` retype id; `shell/dj-vocab.ts` + `DesktopShell.ts:90`.
2. Install/repair button real end-to-end: `library_cmds.rs:331,190` remap `moss→chatterbox` (Python already supports `--install chatterbox`).
3. Re-key the test pins to `chatterbox-voice` (they LOCK the dead contract → CI blocks a correct fix): `library/model-setup.test.ts`, `api.test.ts:106-148`, `build.test.ts:155-268`.
4. Voice-status chip inside Learn (signal exists: `ipc.status.tick.voice`): `learn/components/status-bar.ts`.

ELEVATION (the real mission — after the floor, impeccable vs `mocks/`):
5. Session deck hero — grounded-vs-idle unmistakable, kill telemetry/defensive-copy slop (`session/*`, `shell/*`; mock `vibemix-rebuild-session.html`).
6. Learn — single next action obvious on open (booth/recommended/"your move" legible).
7. Viber/Crate — real tool_trace legibility, BUILD/CUE/INGEST affordances obvious.
8. Wizard/first-run — every screen names the next action; honest on-device framing.

GATE (self-QA): `cd tauri/ui && npm run build && npm test` (~886 vitest) + `grounding-failure.spec.ts`. Never reduce the green count. Visual = impeccable self-review vs `mocks/` + render `?dev=session-mock` @ localhost:1420; FLAG screens for Kaan's morning eye-pass (no vision judge tonight) — never self-certify "UX done".

LOOP (do NOT stop): pull `QUEUE-ux.md` top → build (impeccable) → build+test green (criticize + fix your own change, never advance red) → REGRESSION GUARD: full `npm test` green every commit, never drop the count → commit with the trailer → self-critique (weakest surface = next) → repeat. Halt only when queue dry AND green (`DONE-ALL-ux.md`, flag eye-pass screens) or a hard blocker (`BLOCKED-ux.md` + continue an unblocked item). Never idle waiting on Claude/Kaan.

COMMIT TRAILER:
QA-LANE: ux
QA-ITEM: <moss-to-chatterbox | install-button | voice-status-learn | elevate-session | ...>
QA-GATE: frontend_build_test
QA-VERIFY: cd tauri/ui && npm run build && npm test
QA-PASS: <true|false>

LAW: `tauri/**` + `library_cmds.rs` ONLY. Do NOT touch `src/vibemix/` (backend lane — it already emits `chatterbox-voice`). `messages.schema.json` is yours IF needed → `npm run codegen:ipc` in the SAME commit. `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; stop-slop on user copy, no model filenames in user copy, positive framing; commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.
OUT OF SCOPE: the vision-judge build, Sven/engine (backend lane), `__main__.py --install` choices (already correct).
