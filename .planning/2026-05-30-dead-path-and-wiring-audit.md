# vibemix — Dead-Path & Frontend/Backend Wiring Audit (2026-05-30)

> Companion to `2026-05-30-state-of-the-tree-inventory.md`. Where the inventory asked
> "is the recent work in the app?", this asks "what is **dead** vs merely **unwired**?"
> after 3 days of parallel sessions wired the frontend (`tauri/ui`) and backend
> (`src/vibemix`) **separately**.
>
> Method: a 94-agent workflow — 8 subsystem map lanes + 9 dead-path finder dimensions
> (Python/TS/Rust/schema/seam), each finder piped into **adversarial per-candidate
> verification** (a skeptic whose job was to find ANY live reference — the exact check
> that the stale 16-agent inventory failed when it called `skill_recognizer` orphaned
> one commit before it was wired). 73 candidates verified.

## Headline

**Most of what looks dead is `unwired`, not `dead`** — exactly as predicted. The
classic shape: one session built a producer, the other built the consumer, neither
wired the seam. The verdict split:

| Bucket | Count | Meaning | Action |
|---|---|---|---|
| **DELETE** | 14 | Truly vestigial — re-export shims, superseded code, setters replaced by re-render | Remove |
| **WIRE_UP** | 6 | Dead at runtime but a fully-built consumer/producer waits on the other side | Connect |
| **KEEP (intentional)** | 36 | By-design orphans: deferred One Mind infra, eval-only scripts, Protocols, serialized fields | Leave |
| **TEST_ONLY** | 14 | Referenced only by tests — fine | Leave |
| **Seam GAP/PARTIAL** | 14 | Frontend↔backend wiring gaps (overlaps WIRE_UP/DELETE) | Per-row below |
| Proven-live false alarms | 2 | Finder was wrong; verifier caught it | — |
| Uncertain | 1 | Needs a second look | Investigate |

**The single highest-confidence unwired connection** (appears in this hunt **and** the
strategic brief **and** the Judge workflow thesis): the **v11 skill-tree live→UI seam**.
`ipc.learn.progress_state` already transmits a validated `skills` block, but the
frontend `LearnProgressProjection.progress` type (`learn-window.ts:184-196`) declares
**no `skills` field** and nothing renders `mastered/competent/live_proof_count`. The
backend credit is computed, citation-gated, persisted — and **invisible**. Wire this one
seam and v11 "Earned" lights up.

---

## Bucket 1 — DELETE (14, true dead)

Safe to remove; verifiers confirmed zero live + zero dynamic/registration/serde reach.

**Python (1)**
- `src/vibemix/learn/prepared_pool.py` — pure re-export shim; canonical module is
  `library/prepared_pool.py` and every live importer already uses it. Parallel sessions
  moved the home and left the alias. Zero importers anywhere. *(Re-run
  `tests/repo/test_clean_checkout_imports.py` after — it pins the `library` module, not
  this shim.)*

**TypeScript (11)** — all under `tauri/ui/src/`, tree-shake out, build stays green:
- `mascot/layers/phase47-emotion.ts` (`Phase47EmotionLayer`) + `mascot/layers/phase47-reaction.ts` (`Phase47ReactionLayer`) — the unwired **Phase-47 mascot cluster**; no importer, no entrypoint.
- `session/components/titlebar.ts:365` `setTitlebarSettingsActive` — superseded by `SettingsDrawer.ts::setGearArmed`.
- `session/components/event-ribbon.ts:140` `setEventRibbon` — zero callers *(or WIRE_UP if a live event-ribbon is wanted)*.
- `wizard/components/button.ts:231,236` `setButtonState` / `setButtonLabel` — no callers.
- `wizard/components/status-bar.ts:154` `setStatusBarState` — duplicated by the inline re-render in `router.ts:977`.
- `wizard/components/step-indicator.ts:239` `setStepState` — wizard advances by full re-render.
- `debrief/components/citation-tooltip.ts:62` `hideCitationTooltip` — redundant; show-handler already dismisses.
- `shell/surfaces.ts:105` `surfaceById` — no imports.
- `session/icons/speakers.svg.ts` + `screw.svg.ts` (`SPEAKERS_SVG`, `SCREW_SVG`) — dead icon exports *(or WIRE_UP `SPEAKERS_SVG` into the output-device row like `GEAR_SVG`)*.
- `pill/index.ts:1193` `nextPillGradeStreak` — dead alias of the live `nextPillGradeProgress`.

**Rust (2)** — under `tauri/src-tauri/src/`:
- `config.rs:316` `write_mascot_window_state` — registered in `main.rs:87` but zero callers; geometry already persists via the internal `save_mascot_state` debounce (`mascot_window.rs:210`). Drop the fn + its `generate_handler!` line + doc-comment.
- `tray.rs:647` `set_tray_state` (+ its `#[allow(dead_code)]`) — superseded by the typed `apply_tray_state` path.

## Bucket 2 — WIRE_UP (6, built-but-not-connected — the real "separately wired" gaps)

Dead at runtime, but the **other half is fully built**. These are the connections, not deletions.

- **`agent/emote_parser.py` (`parse_emote_tags`/`strip_emote_tags`) → mascot ReactionLayer.**
  The end-to-end frontend consumer exists (`mascot/layers/reaction.ts` fires clips on
  `[emote:NAME]`; `types.ts` whitelist; `ws_bus.py:947` broadcasts `reaction_intent`),
  but the backend **never calls the parser** and **never writes `state.last_reaction_intent`**
  (`music_state.py:171` default `None`, only read, never assigned). Also no persona/prompt
  teaches the LLM to emit `[emote:*]`. **Fix:** call `strip_emote_tags(reply)` in the
  reaction path → clean text to TTS, intent onto `last_reaction_intent`; add the emote
  vocab to the persona. *(If the mascot is being abandoned, delete parser+test+field as one
  unit — but the live consumer says wire it.)*
- **`wizard/step-driver-fetch.ts` `createStepDriverFetch` → `run_companion_fetch`.** Backend
  (`wizard_cmds.rs`, installer scripts, `emitInstallReadyEvent`) is alive; the Phase-49
  install step is just **not in `STEP_ORDER`** (`router.ts:168-176`). Deferred-wiring orphan.
- **`overlay/overlay-highlight.ts` `startOverlayHighlightListener` → `show_overlay_highlight`.**
  Rust command (`main.rs:98`) + the Python emit (`dj_cohost.py` `ipc.session.overlay-highlight`)
  + the overlay ring renderer are all live; the session-side **listener is never started**, so
  the IPC frame arrives nowhere. Deleting it would orphan a live command + a published envelope.
- **`wizard/uninstall-dialog.ts` `createUninstallDialog`** → needs a `run_uninstall` Rust
  command shelling to `installer/companion/uninstall.{sh,ps1}` (intended INSTALL-07 surface).
- **`wizard/components/window-picker.ts` `NonDjConfirm`** → wire into `step2-output-device.ts`
  the warn-then-allow path for non-DJ windows (UI-SPEC §9 / IPC D-Area-3.2).
- **`wizard/router.ts:558` `ipc.telemetry.set_consent`** → add the schema branch +
  `npm run codegen:ipc` + backend handler so wizard telemetry consent actually persists.

## Bucket 3 — KEEP (36 intentional + the PARTIAL seams)

By-design orphans — do **not** churn:
- **intel/ deferred One Mind S2–S6** — the validated decision spine
  (`decision_runtime.decide` ← `decision_for_state`/`decision_payload_for_state`,
  `suggestion.py:755/800`) is fully built + test-covered but has **no live caller**; the
  taste/gold/claim infra is consumed by `scripts/eval/*` (real dev/eval consumers, not the
  app). This is the deferred opinion-poll routing — a Kaan-gated design decision, not a bug.
- **Protocols & serialized fields** — `GeminiClientProtocol`, dataclass fields used via
  serialization (orphan-flagged but load-bearing).
- **Offline/eval tooling** — `course_pack` (authoring CLI), `demo_mode` (test harness),
  `doctor` `DEEP_CHECKS`/`check_search_live` (only under `run_doctor(deep=True)` — the
  `library doctor` subparser has no `--deep` flag; a 1-line flag would expose it),
  `record_learn_e2e_result` (e2e-mode only), the `embedding` model-router route
  (legacy/migration only — product embeddings are local CLAP).
- **Parallel mascot multi-layer arch** — `priority-stack.ts` / `additive-layer.ts` /
  `crossfade-policy.ts` / `layers/*` (~1186 LOC) is reached only by `mascot/__`, not the
  live `event-dispatcher.ts → state-machine.ts` path. Superseded-but-retained.

## The 14 frontend↔backend seam gaps (the "separately wired" map)

| Seam | Status | Disposition |
|---|---|---|
| `ipc.learn.progress_state.skills` → Learn UI mastery render | GAP | **WIRE** (the headline — v11 spine is dark) |
| `emote_parser` → mascot `reaction_intent` | GAP | **WIRE** (Bucket 2) |
| `ipc.session.overlay-highlight` → `startOverlayHighlightListener` | GAP | **WIRE** (Bucket 2) |
| wizard install steps (`run_companion_fetch`/`run_audio_config`/`open_audio_settings`) ← frontend | GAP | **WIRE** (steps not in `STEP_ORDER`) |
| `write_mascot_window_state` command ← frontend | GAP | **DELETE** (geometry persists internally) |
| intel decision-validation spine → live runtime | GAP | KEEP (deferred S2–S6, Kaan-gated) |
| `demo_mode.DEMO_SEQUENCE` → live loop | GAP | KEEP (test harness; or add `VIBEMIX_DEMO` gate) |
| `deck_vision.DeckVisionReader` → `DeckPoller` (gated vision leg) | GAP | KEEP (documented-gated; vision leg never constructed) |
| `doctor DEEP_CHECKS` → `run_doctor(deep=True)` | GAP | KEEP (add `--deep` flag to expose) |
| `embedding` router route → product path | PARTIAL | KEEP (legacy/migration only) |
| `course_pack` validation → runtime | PARTIAL | KEEP (offline authoring/CI) |
| mascot `priority-stack` multi-layer → dispatcher | PARTIAL | KEEP (superseded arch) |
| `record_learn_e2e_result` command ← frontend | PARTIAL | KEEP (e2e-mode injected JS) |
| `intel gold_*`/`decision_validator` → eval scripts | PARTIAL | KEEP (eval-only infra) |

## Codebase map (8 lanes, one line each)

1. **state + `__main__`** — single-writer `MusicState` (10Hz `state_refresh_loop`), `EventDetector` typed events, `coach.py` evidence-grounded prompts, deck-context two-lane brain. *(deck_vision leg gated/unwired.)*
2. **agent / llm / livekit** — `DJCoHostAgent.llm_node` hijacks LiveKit's text cascade → direct `google.genai` (+ OpenRouter TTS fallback); deck-audio Gemini Parts; `live_claim_guard`. *(embedding route legacy-only.)*
3. **library / viber / curate** — on-device CLAP vibe-search + CUE-DETR auto-cue + Codex set-prep; `anlz_ingest` (Rekordbox), `section_vectors`, `smart_cues`.
4. **learn / v11 skill-tree** — `LessonRuntime` FSM + 36-lesson curriculum; the skill-tree engine + recognizer are wired backend-side but the **mastery UI seam is dark**.
5. **runtime / ws / pill** — asyncio loops (`coach_loop` 10Hz), pill `next_suggestion` 30Hz, `SuggestionService` off-loop compute. *(demo_mode unwired.)*
6. **intel / memory** — pure deterministic scorers/contracts; live scoring stratum wired, the **validated-decision stratum (S2–S6) deferred**; memory recall opt-in.
7. **tauri/ui frontend** — 8 HTML window entries (index/shell/pill/mascot/debrief/library/learn/overlay); main window runs the first-run gate → DesktopShell fold.
8. **rust shell + IPC/ws seam** — 38 `#[tauri::command]`s; thin parent spawns Python sidecar + ws-bus client. *(write_mascot_window_state dead; record_learn_e2e_result e2e-only.)*

## Disposition (leader call)

- **DELETE the 14** in one surgical commit per island (Python / TS / Rust separately, per
  the concurrent-sessions rule). Pure removals; build + suite stay green.
- **WIRE the 6** — these are real product capability already half-built. Priority order:
  (1) `progress_state.skills` → Learn UI mastery render (lights up v11), (2) `emote_parser`
  → mascot reaction, (3) `overlay-highlight` listener, (4) wizard install steps into
  `STEP_ORDER`, (5) `NonDjConfirm`, (6) telemetry consent.
- **KEEP the 36** — intentional deferred infra; document, don't delete.

The deterministic-over-guessing principle Kaan set is **system-wide**, not Gemini-only: the
WIRE_UP items are precisely where the system already computes grounded/deterministic signal
(skill credit, reaction intent, overlay targeting) that no surface consumes yet. Wiring them
is the autonomy gain — surfacing decided facts instead of leaving them dark.
