# FRONTEND WIRING EXIT-MAP — 2026-06-04

For the vibemix Frontend session (cclaude). Synthesis of 10 verified audit slices + the owned packets
(`SHIP-FINISH-PLAN.md`, `SHIP-READINESS-2026-06-04.md`, `NEXT-LANE-BLUEPRINT-{keyfield,cuetray}.md`,
`CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`, `FRONTEND-PURGE-ORGANISM-HANDOFF.md`,
`HANDOFF-SESSION2-FONTS-NEXTLANES.md`). Pin a SHA before acting — the tree is hot (HEAD `7057d154`
as this is written, walked through `7f03589c`/`4fccd3c2`/`b6217dde` across the audits; line numbers
drift as files grow, so confirm the anchor before each edit).

Tier language is load-bearing and never conflated: **SRC** (green tests on current source) != **PKG**
(in the signed DMG built at HEAD) != **LIVE** (a real user runs the app and SEES a grounded result).
`test-passing-but-dark = 0`.

---

## The exit, in one paragraph

"Fully wired frontend" means every human-facing surface either renders a real, grounded backend source
the instant that source produces a value, OR shows an honest empty/idle state when it does not (idle is
not a fault, Invariant #5; honest-null is not a dead wire). The good news from the audit: the outbound
IPC seam is healthy. There are ZERO server-to-client IPC types that are emitted-but-unread. The dark or
ungrounded problem the master arrangement named does not live in the emit-to-consume seam for the shell
window. It lives in a small, specific set of breaks: (1) two whole UI surfaces that do not exist yet (the
Cue Tray and the in-GUI key/proxy/voice settings controls), (2) one render-without-source panel that
auto-opens empty on every live transition (the shell Receipts panel), (3) one citation-receipt join that
silently mis-keys under the live runtime so the signature "the sentence underlines its own claim" gesture
never fires live, (4) computed pill receipts (`reasons[]`, cue-confidence posture, runner-up) that ride
the wire but render capped or not at all, plus the streak that must be STRIPPED not rendered, (5) two
phantom emits the wizard fires into nowhere (`ipc.telemetry.set_consent` and an absent key/proxy step),
and (6) the Learn loop, which closes on the eye (lock-meter, waveform, grade) but stays mute on the ear
(`tts_marker` never synthesized). The frontend lane closes every break under `tauri/ui/src/**` + the IPC
schema + `src/vibemix/ui_bus/*.py`, hands the Python persist/handler halves to the backend lane via named
IPC types, and proves each surface BY EYE in the running app before exit. Exit is not test-green; exit is
the user seeing it work.

---

## Wiring exit-map

Ordered by ship-leverage (top = closest to the democratization / keystone / anti-slop gates).

| # | Surface | Computed/emitted source (file:line) | Where it dies | THE EXACT WIRE | Proof (by-eye) |
|---|---|---|---|---|---|
| 1 | **In-GUI Gemini-key field + DIRECT/PROXY rocker** (democratization #1, ship-blocking) | Boot reads `GEMINI_API_KEY` env then `app_data_dir()/.env` (`__main__.py:462-466`); `ConfigStore.llm_mode` default `"direct"` (`config_store.py:194`). A non-dev can write NEITHER. | Stranger sees `crash-banner.ts:49` `api-key-missing`, only remedy = hand-edit `.env`. No key input, no proxy toggle anywhere in `tauri/ui/src/` (grep = display strings only). | NEW `tauri/ui/src/settings/components/brain-group.ts` (masked write-only `type=password` input + DIRECT/PROXY rocker reusing `session/components/rocker.ts`), mounted in `SettingsDrawer.ts` between PERSONA append and OUTPUT. NEW IPC `ipc.settings.set_brain` (request) + `ipc.settings.brain_ack` (carries NO secret). `brain-group.ts onSaveClick` -> `sendIpcRequest("ipc.settings.set_brain", {mode, gemini_api_key}, "ipc.settings.brain_ack")`. Do NOT route through `ipc.settings.set` (its enum echoes into `ipc.settings.state` + the `vmxLog` payload). Redact the key in `ipc/client.ts:64/178` logging. Full spec already written: `NEXT-LANE-BLUEPRINT-keyfield.md`. | On real sidecar with NO key: `api-key-missing` banner -> open drawer -> BRAIN group -> paste key -> Save -> "Saved. Restart to apply." -> restart -> co-host boots DIRECT and speaks. A single REDACTED `set_brain` fires on Save (eyeball `ui.log`, key absent). PROXY sends `{mode:"proxy"}` only. |
| 2 | **Cue Tray UI** (the moat surface, fully MISSING) | `library/cue_landing.py`: `CueSet`/`LandedCue`/`land(cueset,target,*,granted)->LandReceipt` + provenance; `smart_cues.py` SLOTS A-H / SLOT_ROLES / SmartCuePolicy floors. CueSet is computed but nothing renders it. | One caller (`toolset.py:2141` imports only `sections_from_anchors`); no CLI JSON emitter, no Rust bridge, no TS component. The entire frontend cue surface is dark. | NEW `tauri/ui/src/library/cue-tray.ts` (`renderCueTray` 3 states: Detecting/Review/Landed; A-H ladder rows present-or-empty; per row pad letter + `SLOT_ROLES` word + `m:ss` + ConfidenceMeter banded to policy floors + ProvenanceBadge `◇ AUTO` hollow vs `● DJ` filled + accept checkbox AUTO-only; one-consent Land button + target picker + Landed receipt). DTOs + `libraryLandCues(...)` in `library/api.ts` calling `invoke("library_land_cues", {...granted:true})`. This is a **Tauri `invoke()` command, NOT a `messages.schema.json` ipc type** -> do NOT run `codegen:ipc`; add the literal to `mock-transfer/contract.ts library.outbound`. Ship behind `getInvoke()===null -> DEV_LAND` fixture so the tray renders green before Lane B lands the Rust command. Full blueprint: `NEXT-LANE-BLUEPRINT-cuetray.md` (verified accurate to HEAD). | Render a real CueSet: `● DJ` badge byte-true vs the written Rekordbox XML (VM-named POSITION_MARKs = non-DJ; DJ marks byte-preserved; zero DB writes). Locked DJ rows show no checkbox; empty slots render dim "empty"; Land sends `granted:true` exactly once. A green tray over a fixture is NOT done. |
| 3 | **Settings voice-engine picker** (MOSS vs Chatterbox-Turbo) | `build_tts_chain` reads `os.environ.get("VIBEMIX_TTS_ENGINE","moss")` (`tts_chain.py:53`); built at boot (`__main__.py:1607/1621`), never hot-swapped. | GUI launch strips env (launchd) -> the only selector is unreachable. No `ConfigStore.tts_engine`, no settings control. Kaan's chosen live voice (Chatterbox-Turbo) can never be picked by a normal user. | Two-segment `renderRocker` MOSS/CHATTERBOX in PERSONA under the existing MOSS speaker picker (`SettingsDrawer.ts:938-950`). Route through the EXISTING `ipc.settings.set {field:"tts_engine", value}` path (optimistic-repaints + echoes, no secret). Extend the enum in 4 mirrored places: `SETTINGS_FIELDS` (`ws-bridge.ts:208`), schema `SettingsSet.field` enum (`messages.schema.json:1446`), Python `SettingsSetPayload.field` Literal (`ui_bus/messages.py:361`), `applySettingsOptimistic` switch (`SettingsDrawer.ts:831` add `case "tts_engine"`). Add `tts_engine` to `ipc.settings.state` for round-trip. Backend lane: new `ConfigStore.tts_engine="moss"` + boot reads it into `build_tts_chain(engine=...)`. | Flip to CHATTERBOX -> restart -> co-host speaks in the cloned voice (Chatterbox available on Mac; Windows degrades to MOSS honestly). Rocker flips `data-active` synchronously, re-confirmed by the `ipc.settings.state` echo. |
| 4 | **Shell "Receipts" panel** (render-without-source, ship-visible) | `SessionState.reactions[]` each with `citation_strip` (`session/state.ts:139-163`), fed by `ipc.session.cohost-reaction`, already projected into the deck (`render-loop.ts:208`). `next_suggestion` ws field already consumed by the pill (`pill/next-suggestion.ts:4-7`). | `shell/GroundingPanel.ts:38-46` hardcodes `<p>No cited move yet.</p>` / `<p>No suggestion yet.</p>` while `activation==="live"`. The panel AUTO-OPENS on every idle->live transition (`shell-store.ts:148-156`), so it pops empty forever next to a real cited reaction in the deck. | Extend `shell/activation-bridge.ts:64-72 tick()` (already polls `getSessionState().cohostStatus` at 500ms) to ALSO read `getSessionState().reactions[last]` + the `next_suggestion` ws field -> add a `receipt` slot + setter in `shell/shell-store.ts` -> `GroundingPanel.ts:38-46` renders real `citation_strip` chips (reuse `session/components/citation-strip.ts mountCitationStrip variant:"pill"`) instead of the hardcoded `<p>`. Honest-null preserved: empty `reactions`/`null` suggestion keep the placeholder. No backend change; both sources already flow in the same frontend. | On a live transition the Receipts panel shows the latest reaction text + its resolving citation chips (matching the deck hero), and "what's next" when a suggestion exists; empty when truly empty. |
| 5 | **Deck citation receipt join** (the signature gesture, silently dark live) | Per turn: `dj_cohost.py` builds `SessionCohostReaction.make(...)` stamping `ts=_now_iso()` (`messages.py:1540`) AND `_push_transcript(text)` (`:3793/:3838`) which `ws_bus.py:783` later wraps in `TranscriptLine(ts=_now_iso())` — a SEPARATE `_now_iso()`. | `SessionLayout.ts:1171` joins chips by `next.cohost.reactions.get(nowLine.ts)`. The transcript-line `ts` and the reaction-envelope `ts` are two different `_now_iso()` calls -> never byte-equal -> `.get()` returns `undefined` -> receipt stays `hidden`. Works in unit tests only because mocks hand-author matching `ts`. | Backend lane (ui_bus-adjacent, handshake): capture one `reaction_ts = _now_iso()` near `dj_cohost.py:4011`, pass it to BOTH `SessionCohostReaction.make(ts=reaction_ts, ...)` (add `ts=` kwarg to `make()` at `messages.py:1510`, default `_now_iso()`) AND `_push_transcript(text, ts=reaction_ts)`; then `ws_bus.py:781-784` drains the carried `ts` instead of minting fresh. Frontend lane: no change to the join logic, but ADD a vitest that exercises the live mismatch shape (a reaction + transcript with DIFFERENT `ts`) and asserts the receipt fails to fire, so the regression is caught. Do NOT touch `session_loop.py:237 append_transcript` (0 callers, dead). | On a captured voice-ON set, a grounded co-host line in the deck hero ignites its underline + citation chip in real time. By-bus: the `transcript_delta` line and its `cohost-reaction` envelope carry the SAME `ts`. |
| 6 | **Pill receipts: `reasons[]` cap, cue-confidence posture, runner-up** | `next_suggestion.py:813` `reasons[]` (full), `:802` `cue_confidence`, `:227` `transition_alternatives` (each with `scores`) — all ride the `next_suggestion` ws frame via `asdict` (`:69`). | `reasons[]` RENDERED but hard-capped `.slice(0,2)` in BOTH densities (`pill/next-suggestion.ts:313`, read `:387`/`:584`). `cue_confidence` NOT declared in `NextSuggestionTransitionWire` (grep = 0). `transition_alternatives` NOT declared in `NextSuggestionWire` (grep = 0; the mock reader was purged). | (a) Make the slice density-aware in `next-suggestion.ts:306-314`: thread `RenderOptions.density` so `"full"` returns all reasons, `"peek"` keeps `.slice(0,2)`. (b) Add `cue_confidence?: number|null` to the transition interface (`~:44`) and render a coarse 3-state posture from `cue_source` (Rekordbox=high/detected=medium/estimated=low) — NOT a precise %. (c) Add `transition_alternatives?: NextSuggestionTransitionWire[]` to `NextSuggestionWire` (`:84`); render alt #2 + a losing-margin string on DEEP-HOVER only (never a persistent backups section — that is what the purge killed). All three are wire-only, no schema/engine change. Owner-gate on (b) 3-bucket vocabulary + (c) deep-hover alt. | On hover the pill shows full reasons (full density) and a coarse cue-confidence posture word; deep-hover reveals the runner-up + margin. Peek density stays at 2 reasons. |
| 7 | **Pill streak / combo / level_up** (STRIP, do NOT render) | `_next_grade_progress` computes streak/total_xp/heat/level_up EVERY frame (`suggestion.py:1375-1420`), attached to the wire at `:387/520/1015/1296`. | DARK by design now: `.pill__streak` is a dead hit-test selector, all gamification writers deleted (`826fddc9`). The streak counts the engine grading its OWN un-played SUGGESTION clean/sexy/bomb (`move_grade.py`) — self-applause, NOT an executed+judged transition. | OWNED DECISION (`CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`): do NOT re-render. Backend lane STRIPS the `_attach_grade_progress` call-sites (`suggestion.py:387/520/1015/1296`) from the serialized frame so it can never be silently re-rendered as a fake counter (keep `move_grade.py` for the Viber chat surface that legitimately uses it). A real streak needs a cited `[ev:BEATMATCH_GRADED@…]`/`[judge:]` LIVE event that does not exist on the bus today (practice-loop/recorder only) -> that is debrief plumbing (L-effort), not a pill wire. Frontend: no render; confirm no shipped pill TS reads streak/level_up (the only readers are `library/` = Viber). | The pill never shows a streak/XP/level badge. By-bus: the serialized `next_suggestion` frame carries no `grade_progress` once Lane B strips it. |
| 8 | **Learn tutor VOICE** (loop closes on eye, mute on ear) | `LearnTutorSpeak` carries `tts_marker` (e.g. `"{lesson_id}.grade"`, `runtime.py:2544`) end-to-end; `ipc.learn.live_grade` (`runtime.py:2536`), `waveform_ready`, `playhead_tick`, `progress_state.skill_wall` all EMIT and are CONSUMED (lock-meter `live-meter.ts`, waveform `waveform-display.ts`, SkillWall `shell/app.ts:77`). | Zero frontend consumer plays audio for `tts_marker`: no `new Audio`, no MOSS synth under `tauri/ui/src/learn/`. Sven is a silent subtitle in Learn. | Backend-side wire (handshake, cleaner than frontend Audio): on `_emit_tutor_speak`, also drive `tts_chain` (gated by `local_tts_enabled()`) and play through the Learn headphone `sd.OutputStream` already owned by `TwoDeckPlayer`/`ExemplarPlayer` — reuse the stream, do not add one. Frontend lane: no new consumer needed for audio; verify the lock-meter actually paints (its host is `display:none` outside `#learn-root.lesson-mode`, `learn.css:728-742`) and confirm which Learn surface ships (SkillWall is mounted ONLY in `shell/app.ts:77`, NOT standalone `learn-window.ts`). | In a live beatmatch lesson the tutor SPEAKS the grade line ("close, nudge the jog") through MOSS, the lock-meter canvas paints on a real `live_grade` tick, and the SkillWall renders on the surface the user actually sees. |
| 9 | **Wizard telemetry-consent** (phantom emit) | `step-telemetry-consent.ts` renders a real radio; on Continue `router.ts:558` `emitIpc("ipc.telemetry.set_consent", {consent})`. | NOT in the schema + NO Python handler (absent from `wizard.py:111-142`, which registers the sibling `ipc.profile.set_consent`). `emitIpc` does not validate outbound, so `WizardBus.dispatch` finds no handler and silently swallows it. The user's telemetry choice never persists. | NEW IPC `ipc.telemetry.set_consent {consent:boolean}` in `messages.schema.json` -> `npm run codegen:ipc`. Backend lane: register a handler in `wizard.py:142` mirroring `_on_profile_set_consent` (`:446-468`), persisting `telemetry_consent:bool` to `state.json`. | Pick a telemetry consent in the wizard -> `state.json` / `config_store.telemetry_consent` reflects the choice (not the silent default `False`). |
| 10 | **Wizard key/proxy step** (no step exists; chains onto #1) | `STEP_ORDER` (`router.ts:168-176`) has intro->permissions->audio->controller->skill->profile-consent->telemetry->smoke-test->done. NO key/proxy step. The smoke-test plays a bundled offline WAV (`wizard.py:419` always raises), never exercising the brain. | A fresh non-dev finishes the whole wizard and the brain is still unauthenticated -> live session boots direct, no key -> `sys.exit(4)` -> `api-key-missing` banner. The wizard's happy path terminates in a crash. | OPTION A (preferred, reuses #1): after #1's `brain-group` lands, add a `"llm"` step to `WizardStep` (`router.ts:49`) + `STEP_ORDER` (after telemetry) + a render-case + `back()` arm, NEW `tauri/ui/src/wizard/step-llm.ts` emitting the SAME `ipc.settings.set_brain` (or a wizard twin `ipc.wizard.set_llm`) handled by `wizard.py` mirroring `_on_wizard_set_skill` (`:470-495`). OPTION B (keyless): the step persists `llm_mode="proxy"` (chain already live, `__main__.py:1155-1167`) — gated on Kaan's packaged-default flip + proxy credits (external). NOTE the orphans: `onboarding-flow.ts`, `step-driver-fetch.ts`, `step-forewarning.ts`, `step-48k-probe.ts` are 0-caller dead weight that make the wizard look like it has proxy/format/driver steps it does not — leave or delete intentionally, do not mistake for live coverage. | A fresh user completes the wizard, the key/proxy step persists a working brain, and the session boots speaking — no `sys.exit(4)`, no `.env` hand-edit. |

### Confirmed CLEAR (real source + honest state, or dead-before-seen) — NOT findings, do not "fix"

- **Organism** is the rare fully-wired grounded-to-render chain (MOSS voice -> breath, beat -> radial kick, teaching_focus -> dissolve/stream/glow, EQ CC -> swirl), build-fresh in SRC, Kaan-LOCKED visual ("stays as-is, wire-not-rebuild"). Its only gap is the STALE DMG (predates all organism commits) = backend/ship lane rebuild, NOT a frontend wire. The one live-MIDI->swirl leg not yet routed in `index.ts:507` is the only optional hardening; the rig by-eye is Kaan's. Lane-3 work = integrate the mask into the learn window (wire, do not redo).
- Deck scene chips / hardcoded deck-live-line in `DesktopShell.ts:54-68` are wiped by `session/router.ts:60 replaceChildren()` before mount (never seen).
- Deck cohost hero, VoiceReadinessBadge, DebriefDock, StatusFooter, GroundingPanel idle state, debrief `?mock=` path — all real source + honest empty/loading, or dev-gated.
- Outbound IPC seam: every ~45 server->client types resolves to a live consumer (S1). `ipc.learn.live_grade` IS emitted + consumed (the MEMORY "grade discarded at runtime.py:2088" note is STALE/fixed). `teaching_focus`/`control_rect` are consumed by the mascot window by design, not learn.
- `ipc.debrief.ear-test-submit` is a dev-only WS fallback (real path = Rust `write_ear_test_log`); `ipc.learn.`/`ipc.unknown.thing` are a string fragment + a test fixture (noise).
- **Debrief window** (port 8766) is wired end-to-end and renders on the 58 long real sessions; its ONE break (`evidence_registry.json` never written -> drills error + citation tooltips `found=false`) is a BACKEND wire (`__main__.py:1260` -> `recorder.py:208/549`, give the recorder the live registry), NOT a frontend surface.

---

## New IPC types to add (Frontend owns the schema; the handshake)

Run `npm run codegen:ipc` after editing `messages.schema.json` (the ajv validator is pre-compiled; stale =
new fields rejected). Run the `ipc-wiring-checker` skill on each (it will show the backend handler RED until
the backend lane lands it — note that as a known cross-lane dep, do NOT fake it).

| New type | Direction | Payload (Frontend defines) | Backend handler the backend lane must implement |
|---|---|---|---|
| `ipc.settings.set_brain` | shell -> sidecar (request) | `{mode:"direct"\|"proxy", gemini_api_key?:string\|null}` | `_on_settings_set_brain` in `runtime/session_loop.py` (mirror `_on_settings_set:387`) -> `SettingsApplier.apply_brain(mode, gemini_api_key)` in `runtime/settings.py` (mirror `apply():281`); write key -> `app_data_dir()/.env` chmod 600; `config_store.llm_mode=mode; save_config`; NEVER log the key. |
| `ipc.settings.brain_ack` | sidecar -> shell (ack) | `{ok:boolean, mode, key_set:boolean, restart_required:boolean, error:string\|null}` — NO secret | Emitted by the same handler. `key_set` is a boolean only. |
| `ipc.telemetry.set_consent` | shell -> sidecar (request) | `{consent:boolean}` | Handler in `runtime/wizard.py:142` (mirror `_on_profile_set_consent:446-468`) persisting `telemetry_consent:bool` to `state.json`. Also register on the session loop if telemetry is re-settable post-wizard. |
| `ipc.wizard.set_llm` (Option A only) | shell -> sidecar (request) | `{mode:"direct"\|"proxy", api_key?:string\|null}` — OR reuse `ipc.settings.set_brain` from the wizard step | Handler in `runtime/wizard.py:111` (mirror `_on_wizard_set_skill:470-495`) persisting `llm_mode` + key. |
| **`library_land_cues`** (NOT a schema ipc type) | Tauri `invoke()` command | `{cueset, target, acceptedSlots, name, granted:true}` -> `LandReceipt` DTO | `#[tauri::command] pub async fn library_land_cues` in `tauri/src-tauri/src/library_cmds.rs` (mirror `library_cue_folder:866`) registered in `main.rs::generate_handler!`; shells to a NEW Python CLI verb that emits the proposed CueSet as JSON + calls `cue_landing.land(cueset, target, granted=True)`. ALSO the IN seam: `library_propose_cues(path)->CueSet[]` or extend `library_cue_folder` to return `cuesets`. Add the literal to `mock-transfer/contract.ts library.outbound` (do NOT `codegen:ipc`). |

Extended (not new): add `"tts_engine"` to the `ipc.settings.set` field enum (4 mirrored places, see exit-map #3)
and to the `ipc.settings.state` payload for round-trip. Add optional `llm_mode` (+ optional `key_present:boolean`)
to the `ipc.settings.state` payload so the DIRECT/PROXY rocker `active` re-syncs (backend reads `config_store.llm_mode`).

Backend lane handshake notes for the secret: dedicated, never-echoed message; redact in `vmxLog`
(`ipc/client.ts:64/178`); the backend writes the key (never the frontend); pin a vitest that no `vmxLog` arg
stringifies to the fake key `"AIza-test-fake"` (anti-leak gate, must be GREEN before commit).

---

## Paste-ready /goal for the Frontend session

```
/goal FRONTEND WIRING EXIT — close every dead human-facing surface in tauri/ui, in ship-leverage order, from
.planning/packets/2026-06-04/FRONTEND-WIRING-EXIT-MAP.md. Pin a SHA first (tree is hot, ~7057d154). For each
surface: build TDD, prove BY EYE in the running app, commit the instant it is green + proven. Order:
(1) In-GUI Gemini-key field + DIRECT/PROXY rocker (democratization #1) — NEW settings/components/brain-group.ts;
    NEW ipc.settings.set_brain + ipc.settings.brain_ack (you OWN the schema; codegen:ipc; never route the secret
    through ipc.settings.set; redact the key in ipc/client.ts logging). Full spec: NEXT-LANE-BLUEPRINT-keyfield.md.
(2) Cue Tray UI — NEW library/cue-tray.ts (A-H ladder, ◇AUTO/●DJ ProvenanceBadge, ConfidenceMeter banded to
    policy floors, locked DJ rows, empty-as-empty, one-consent Land + target picker + Landed receipt). This is a
    Tauri invoke() command library_land_cues, NOT a schema ipc type (do NOT codegen:ipc; add to contract.ts
    library.outbound). Ship behind getInvoke()===null -> DEV_LAND fixture. Full spec: NEXT-LANE-BLUEPRINT-cuetray.md.
(3) Voice-engine picker (MOSS/CHATTERBOX) in PERSONA — route through ipc.settings.set field "tts_engine" (extend
    the enum in SETTINGS_FIELDS + schema + ui_bus + applySettingsOptimistic; add to ipc.settings.state round-trip).
(4) Shell Receipts panel — extend shell/activation-bridge.ts tick() to read reactions[last] + the next_suggestion
    ws field into a shell-store receipt slot; render real citation_strip chips in GroundingPanel.ts (reuse
    citation-strip.ts); keep honest-null placeholders. No backend change.
(5) Deck citation receipt — ADD a vitest that exercises the live ts-mismatch (reaction ts != transcript ts) and
    asserts the receipt fails to fire (the backend lane carries the matching ts; you guard the regression).
(6) Pill receipts — density-aware reasons[] slice (full vs peek), declare + render coarse cue-confidence posture
    from cue_source (3-state, owner-gate the vocabulary), declare transition_alternatives + render runner-up on
    DEEP-HOVER only (owner-gate). Wire-only, no schema/engine change.
(7) Pill streak — do NOT render. Confirm no shipped pill TS reads streak/level_up (only library/ Viber does). The
    backend lane strips the serialized grade_progress (CODEX_READY-PILL-STREAK-ROBOT-VOICE.md). Hands-off.
(8) Wizard telemetry-consent — NEW ipc.telemetry.set_consent {consent} (schema + codegen); backend lane persists.
(9) Wizard key/proxy step — after (1) lands, add an "llm" step reusing the brain-group; backend mirrors
    _on_wizard_set_skill. Leave the orphan onboarding-flow.ts/step-*.ts dead weight as-is unless deleting intentionally.

HANDSHAKE: you OWN the IPC schema; backend lane (Python) owns every handler named in the exit-map "New IPC types"
table (set_brain persist, telemetry persist, wizard llm persist, library_land_cues Rust command + Python CLI verb,
the reaction-ts carry, the Learn tts_marker -> MOSS synth, the grade_progress strip, the debrief evidence-registry
write). The ipc-wiring-checker will show those handlers RED until the backend lands them — note as a known cross-lane
dep, do NOT fake the Python side.

SHARED LAW (obey or lose work): ONE shared tree (ux-redesign-impeccable), 2+ concurrent sessions. Commits survive;
uncommitted work gets WIPED by a sibling git op. git add <exact paths> NEVER -A; review git diff --cached --name-only
in a SEPARATE step; before staging a SHARED file (contract.ts, tokens.css, messages.schema.json) re-check git diff for
foreign hunks and stage only yours. IPC schema = FRONTEND lane only; backend lanes request types from you. Sidecar
127.0.0.1:8765 = ONE socket: pkill -f "python -m vibemix" before any probe. Settings/pills repaint OPTIMISTICALLY
(flip data-active locally in the click handler, the round-trip self-corrects). Tokens-only (no hex), Geist type, one
rose sign-of-life per group, no gold. Run frontend-enforcement + ipc-wiring-checker before each commit; run
vibemix-grounding-review before shipping any co-host/learn/tutor reaction wiring. test-passing-but-dark = 0: prove each
surface by-eye/by-bus on the running Vite dev server (:1420: ?dev=session-mock, ?dev=shell, library.html, learn.html,
mascot.html?dev=organism-probe) or the real sidecar, not just vitest. commit -s, Kaan Özkan <rahipdotaci@gmail.com>,
trailer Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>. Commit each surface the instant it is
green + proven.
```

---

## NEEDS-CLARIFICATION

1. **Cue-confidence posture vocabulary (exit-map #6b).** The precise % was purged. The wire renders a coarse
   3-state posture from `cue_source` (Rekordbox=high / detected=medium / estimated=low). Confirm the exact 3
   label words and whether 3 buckets (vs 2: trusted/estimated) is the right granularity before rendering.
2. **Runner-up reveal surface (exit-map #6c).** The blueprint says deep-hover only, never a persistent backups
   section (the persistent section is what the purge killed). Confirm deep-hover is the accepted affordance, or
   whether the runner-up belongs only in debrief.
3. **Wizard key/proxy step shape (exit-map #10).** Two viable paths: Option A (user types a key in the wizard,
   needs the key-input UI inline) vs Option B (keyless proxy-default, gated on Kaan's packaged-default flip +
   proxy credits top-up, both external). The packaged-default `direct`->`proxy` flip is a Kaan owner-gate
   (`__main__.py:1108-1111`) — confirm which path the wizard step ships before building it.
4. **Learn tutor voice identity (exit-map #8).** `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md` explicitly leaves the
   Learn tutor voice UNDECIDED (the robot was floated for Learn, then reassigned to the pill). The wire (route
   `tts_marker` -> MOSS through the existing Learn `sd.OutputStream`) is clear, but the VOICE identity (MOSS
   default vs a distinct tutor voice) is an open Kaan decision before the backend lane synthesizes.
