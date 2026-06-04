# CODEX GOAL — UX lane (THE priority lane: make the app legible, alive, slop-free)

> Paste this whole block as the Codex goal. File island: `tauri/` + `tauri/src-tauri/src/library_cmds.rs` only. Verified against `ux-redesign-impeccable` HEAD `364c55ba` (2026-06-04). Use the **impeccable** skill for ALL visual/layout work; honor `frontend-enforcement` + `stop-slop`.

## Priority (Kaan, explicit): UX is of UTMOST importance

The engine and the soul (Sven, intel, library) are strong. **UX is the dark layer that gates the whole product** — "nobody focused on UX and it shows; when we get it there, it gets crazy." Your mission is NOT a bugfix list. It is to make every surface **legible (you instantly know what to do), alive, and free of AI slop — impeccable-grade craft.** The voice-visibility fixes below are the correctness FLOOR you clear first (you cannot have great UX with dead voice status); on top of that floor you ELEVATE the hero surfaces. This is the most important lane of the night.

## The correctness floor (keystone — clear this first)

The backend voice engine pivoted to **Chatterbox-only** (MOSS deleted), but the **entire frontend voice surface still says/seeks MOSS** — so on a real machine the user gets **ZERO voice status** and the install button is dead. This is Kaan's "TTS is not there": TTS *is* in the engine, but the UI cannot see it, name it, or install it.

Root mismatch (verified): the readiness badge keys on `model.id === "moss-tts"` (`tauri/ui/src/shell/VoiceReadinessBadge.ts:42`), but the live backend emits `{"id":"chatterbox-voice"}` (`src/vibemix/__main__.py:7686-7697`). They never match → badge silently hidden (`element.hidden=true`). And the install path sends `--install moss` (`library_cmds.rs:331`) which Python argparse rejects (`__main__.py:3255` choices = `clap,chatterbox,required,cue,all`) → dead button end-to-end.

## Bounded queue (ordered by legibility-per-effort)

1. **MOSS→Chatterbox rename + reroute (biggest win, mostly mechanical).**
   - `tauri/ui/src/shell/VoiceReadinessBadge.ts:42` — resolve `model.id === "chatterbox-voice"`; replace all "MOSS" copy (`:3,54,62,68-101`) with neutral "Voice" (use `DJ_VOCAB.voiceModel` from `shell/dj-vocab.ts` — CLAUDE.md partner-copy rule: NO model filenames in user copy).
   - `tauri/ui/src/settings/SettingsDrawer.ts:945` — drop `sub:"MOSS"`; `:496-498` fix the comment + verify `VOICE_OPTIONS` against the real Chatterbox voice set (`src/vibemix/voice_presets.py`) — do not offer voices the engine can't honor.
   - `tauri/ui/src/wizard/step0-intro.ts:522` — `["Voice","on-device"]` (no model name) — this is the first screen a new user sees.
   - `tauri/ui/src/library/api.ts:124,162,2524-2531,2806-2808` — retype id to `"chatterbox-voice"`, fix DEV_MODELS row + doc comment + `DesktopShell.ts:90` alias.
2. **Fix the install/repair button end-to-end.** `library_cmds.rs:331,190` — accept/remap target to `chatterbox` (Python already supports `--install chatterbox`). Decide with the backend row (`__main__.py:7693` `installable:False`): either flip to installable so the UI fetches (`install_chatterbox_model()` exists), or make the UI say "voice downloads in setup" instead of a dead repair button. Pick one, wire it, prove the button does something real.
3. **Re-key the test pins (they currently LOCK the dead contract — CI blocks a correct fix otherwise):** `tauri/ui/src/library/model-setup.test.ts`, `api.test.ts:106-148`, `build.test.ts:155-268` → `chatterbox-voice`. Then `npm run codegen:ipc` if you touch `messages.schema.json`.
4. **Voice status visible INSIDE Learn.** The signal already arrives (`ipc.status.tick.voice`, `ws_bus.py:1444`). Add a small voice chip in `tauri/ui/src/learn/components/status-bar.ts` (or the tutor-dock header): on / muted / installing. Today Learn shows zero voice status, so a learner can't tell if the tutor is meant to be heard.
5. **(stretch) Silent-lesson honesty.** ~26/38 lessons run "listen for the cymbals" tutor copy over silence (`learn/runtime.py:196` wires audio for only ~12). Where a lesson's copy says "listen" but no audio is wired for that `lesson_id`, the tutor-dock should show a "no audio for this drill" affordance instead of instructing the user to listen to nothing. (Frontend wire `ipc.learn.exemplar_play` exists; this is honesty, not new audio.)

## Elevation pass (the utmost-important work — after the floor, this is the real mission)

Once voice is visible and the install button is real, do a continuous **impeccable elevation** of the hero surfaces, in this priority order. For each: load the matching `mocks/` contract, apply the impeccable laws + `frontend-enforcement`, and raise it to "a real DJ would say this feels alive, and I instantly know what to do." No UI-from-scratch (the `mocks/` are the visual contract); elevate what exists.

1. **Session deck (the live hero)** — `tauri/ui/src/session/*` + `shell/*`. The "Deck Speaks": the hero line, the grounded receipt igniting on a real cite, the pill. Make grounded vs idle unmistakable; kill any telemetry-cockpit / defensive-copy slop. Mock: `mocks/vibemix-rebuild-session.html`.
2. **Learn** — `tauri/ui/src/learn/*`. The #1 "I can't tell what to do" surface. Make the single next action obvious on open; the booth panel + recommended lesson + "your move" line legible; voice/tutor state visible (item 4 of the floor).
3. **Viber / Crate** — the agentic surface. Real "Live agent log" / tool_trace legibility (not faked), the BUILD/CUE/INGEST affordances obvious.
4. **Wizard + first-run** — `tauri/ui/src/wizard/*`. The first impression. Every screen names the next action; no model filenames; on-device/private framing honest.

Quality bar for elevation = impeccable laws + `stop-slop` + the `mocks/` contract + NO test regression. Because there is no vision judge tonight, each elevated surface is **flagged for Kaan's morning eye-pass** in your commit body — you self-review against the mocks, you do not self-certify "UX done".

## Self-QA gate (you run this, no human)

- **Authoritative + fast:** `cd tauri/ui && npm run build && npm test` (~886 vitest) MUST pass — including the re-keyed voice tests. `npm run build` = `tsc --noEmit && vite build`.
- **Invariant guard:** `tauri/ui/tests/session/grounding-failure.spec.ts` must stay green (no fake idle fault).
- **By-eye (deferred to a human/morning pass):** there is NO vision judge tonight. For visual changes, render `?dev=session-mock` at `localhost:1420` (`npm run dev`) and self-review against the `mocks/` contracts + the impeccable laws; flag screens for Kaan's morning pass in your commit body. Do NOT claim "UX verified" — claim "tests green + self-reviewed; needs eye-pass".

## Done-signal (commit trailer)
```
QA-LANE: ux
QA-ITEM: <moss-to-chatterbox | install-button | voice-status-learn | silent-lesson-honesty>
QA-GATE: frontend_build_test
QA-VERIFY: cd tauri/ui && npm run build && npm test
QA-PASS: <true|false>
```

## Island + law
ISLAND: `tauri/ui/**` + `tauri/src-tauri/src/library_cmds.rs` ONLY. Do NOT touch `src/vibemix/` (backend lane) — the backend already emits `chatterbox-voice`; you consume it, you don't change it. `messages.schema.json` is yours IF needed → run `npm run codegen:ipc` (pre-compiled validator) in the SAME commit; the `ipc-wiring-checker` skill is your pre-commit gate.
LAW: work in your worktree branch `qa/ux`; `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.
COPY: stop-slop on all user-facing strings; no model filenames in user copy; positive framing.

## LOOP PROTOCOL (do NOT stop after one item — ship continuously, self-critique, NO regression)

You run a continuous overnight loop. You do not halt to wait for anyone.
1. **Pull** the top item from your on-disk queue `.planning/packets/2026-06-04/qa-loop-map/QUEUE-ux.md`.
2. **Build** it (use impeccable for visual work).
3. **Self-QA:** `cd tauri/ui && npm run build && npm test`. If red, **criticize your own change and fix it** until green — never advance on a red build.
4. **REGRESSION GUARD (the no-regression rule):** the FULL `npm test` (~886 vitest) + `grounding-failure.spec.ts` must stay green every commit. Never reduce the passing-test count. If a change breaks a prior test, fix it or revert — **never commit a regression.** Keep the green count in `BASELINE.json`.
5. **Commit** with the trailer (only when build+test green AND no test regressed). Append the item to `DONE.log`.
6. **Self-critique → next:** after each item, re-render `?dev=session-mock` and self-review against `mocks/` + the impeccable laws; the weakest surface becomes your next item. If the queue is dry, pull the next legibility win (voice-status, silent-lesson honesty, onboarding agreement).
7. **Repeat.** HALT only when (a) the queue is dry AND build+test green → write a `DONE-ALL` marker (flag the screens that still need Kaan's morning eye-pass), or (b) a hard blocker (single-owner-file collision, schema/codegen failure you can't resolve) → write `BLOCKED.md` and continue with any other unblocked item. Never sit idle waiting on Claude/Kaan.

## Out of scope
- The vision/UX judge build (no headless screenshot source tonight — deferred).
- Sven prose / speak-gate / engine (backend lane).
- `__main__.py` Python `--install` choices (already correct: supports `chatterbox`).
