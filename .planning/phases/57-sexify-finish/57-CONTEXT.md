# Phase 57: Sexify Finish - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded + live Kaan coordination (autonomous `fully`). Depends on Phase 51 (running app to inspect); benefits from Phases 52–56 live observations.

<domain>
## Phase Boundary

Polish the surfaces a real user touches to peak: (1) a final **CDJ-Whisper visual pass** on Tier-1 live views (session view + mascot overlay) — zero HIGH findings, 20/80 accent rule, textured material feel, no AI-slop typography; (2) close the **three v0.1.0-rc1 carryover bugs** verified on the real app — Tauri drag capability works, the mascot chrome strip is gone, the TCC permissions list populates; (3) tighten **fresh-account first-run → first-session** (no dead-ends, no confusing steps before audio is live). Covers **POLISH-01/02/03**.

**Out of this phase:** new features, the v2.x full-3D mascot art pass (Meshy/Mixamo — still v2.x), and the signed-publish gates (Phase 58). This is polish + carryover-bug close + first-run friction, nothing net-new.
</domain>

<decisions>
## Implementation Decisions (autonomous `fully` + live Kaan coordination 2026-05-21)

### Live coordination with Kaan's parallel WIP (LOCKED this session)
- **Kaan is actively editing `tauri/src-tauri/src/mascot_window.rs` + `tauri/src-tauri/tauri.conf.json5`** this session (uncommitted): a `beforeDevCommand` dev-launch fix (`npm --prefix ui run dev` → `npm run dev`) and a mascot-window off-screen guard (physical→logical Retina unit fix + persisted-origin on-screen clamp). These are coherent, complete, Phase-57-adjacent fixes (mascot window quality + first-run launch).
- **Kaan said "hallet" (I handle the Tauri carryover bugs).** Decision: the two Tauri-file carryover bugs (drag capability → `tauri.conf.json5`/capabilities; mascot chrome strip → `mascot_window.rs` window decorations) are executed **INLINE on the main checkout, layered on top of Kaan's uncommitted WIP — NOT in worktrees** (a worktree forks from HEAD without his WIP and would conflict on merge / clobber his work). His Tauri WIP is preserved and committed together with the bug fixes, attributed to him.
- **Kaan's persona/prompt WIP is OFF-LIMITS to this phase** (uncommitted, mid-tuning): `src/vibemix/__main__.py`, `agent/dj_cohost.py`, `audio/constants.py` (INVOKE_AUDIO_SECONDS 18→30), `prompts/matrix.py` (react-don't-go-silent), `tests/agent/test_persona.py` / `test_dj_cohost.py` / `test_dj_cohost_prompt_diet.py`. Phase 57 does NOT touch these — leave them untouched/uncommitted.
- **Visual pass: run `impeccable` autonomously, Kaan reviews** (his answer). I run the `impeccable` skill + paired ui-checker/ui-auditor on the Tier-1 surfaces to zero-HIGH; the "is it genuinely beautiful" call is Kaan's eye (the felt sign-off). Non-colliding visual work (UI CSS/TS, mascot.html overlay styling) may use worktrees normally — it does not collide with Kaan's python/rust WIP.

### Visual polish (POLISH-01) — `impeccable` skill, Kaan directive
- **Use the `impeccable` skill for the visual polish pass** (Kaan directive 2026-05-21), not just default ui-phase/ui-review. Target Tier-1 live surfaces: the session/live view + the mascot overlay. Hold the locked **CDJ-Whisper** direction ([[project_visual_direction_cdj_whisper]]): 5 warm blacks, single amber accent (4 intensities), tactility via faint glow not faux-3D bevels, Geist + Fraunces type, 20/80 rule, textured material feel, readability + restraint. Enforce via the project-local `frontend-enforcement` skill.
- **Gate:** paired ui-checker + ui-auditor pass with **zero HIGH findings**. The felt "looks peak / sexy" is Kaan's review.
- **Mascot overlay = the Three.js GLB rig** (`tauri/ui/mascot.html`) per the Phase 56 correction — the surface the shipped app loads. Visual polish targets that rig's presentation, not the dead root sprite overlay. Richer per-mode art remains v2.x; this is a presentation/consistency pass.

### Carryover bugs (POLISH-02) — close + real-app verify
- The three v0.1.0-rc1 carryover bugs ([[project_v0_1_0_rc1_open_bugs]]): **(a) Tauri drag capability missing** (window drag doesn't work — likely a missing capability/permission in `tauri.conf.json5` or a capabilities file); **(b) mascot chrome strip** (an unwanted window-chrome strip on the mascot overlay — `mascot_window.rs` decorations/transparency); **(c) TCC permissions list does not populate** (the macOS privacy/permissions list the first-run/setup surface shows is empty). Close the code for each.
- **Real-app verification of all three is KAAN-ACTION** (needs the real Mac: drag the window, see the chrome strip gone, watch the TCC list populate). Engineering ships the code fix + automated assertions where a headless test is meaningful (e.g., capability JSON present, decoration flags set, TCC list source wired); the visual/interaction confirmation rides the live-drive surface.

### Fresh-account first-run (POLISH-03)
- Walk a fresh macOS account first-run → first-session and tighten the friction points: no dead-ends, no confusing steps before audio is live. Engineering closes any code-fixable friction (copy, step order, dead links, missing guidance) + an automated first-run smoke where possible. The **real fresh-account walk on Kaan's Mac is KAAN-ACTION** (the felt "no friction" sign-off).
</decisions>

<code_context>
## Existing Code Insights

- **Tier-1 UI surfaces:** the live session view + mascot overlay under `tauri/ui/` (React 19 + Vite + TS, Tailwind). Visual reference contracts: `mocks/vibemix-app-ui.html` (live session UI), `mocks/vibemix-direction-final.html` (CDJ-Whisper baseline). The `frontend-enforcement` skill governs.
- **Mascot window:** `tauri/src-tauri/src/mascot_window.rs` (Tauri window builder — decorations/transparency/placement; Kaan's WIP is here) loads the Three.js rig `tauri/ui/mascot.html`.
- **Tauri capabilities/config:** `tauri/src-tauri/tauri.conf.json5` + any `tauri/src-tauri/capabilities/*.json` — the drag capability lives here.
- **TCC / permissions surface:** the first-run/setup wizard permission step (`tauri/ui/src/wizard/*`) + its IPC/rust source for the macOS privacy list.
- **First-run wizard:** `tauri/ui/src/wizard/*` (step components — blackhole-step, smartscreen-step, intro, etc., per existing vitest specs).
</code_context>

<specifics>
## Specific Ideas
- **impeccable visual pass:** run the `impeccable` skill on the session view + mascot overlay; converge to zero-HIGH ui-checker/ui-auditor; hold CDJ-Whisper + 20/80; present before/after to Kaan for the felt sign-off.
- **Tauri drag bug:** confirm/add the window-drag capability (data-tauri-drag-region wiring + capability permission); assert the capability JSON is present.
- **Mascot chrome strip:** set the mascot window decorations/transparency so no chrome strip renders; assert the decoration flags in `mascot_window.rs`.
- **TCC list:** wire the permissions list source so it populates; assert the list data path exists.
- **First-run smoke:** extend the wizard vitest specs for step continuity (no dead-end before audio live).

<deferred>
## Deferred Ideas (KAAN-ACTION — real hardware / felt-quality, autonomous carveout)
- **Felt "looks peak / sexy" visual sign-off** on Tier-1 surfaces (Kaan's eye) — engineering ships zero-HIGH ui-checker/ui-auditor + impeccable pass; the beauty call is his.
- **Real-app verification of the 3 carryover bugs** (drag works, chrome strip gone, TCC list populates) on Kaan's Mac.
- **Fresh-account first-run walk** on a real fresh macOS account (the felt "no friction" sign-off).
- **v2.x full-3D mascot art pass** (Meshy/Mixamo) — NOT this phase.
</deferred>
