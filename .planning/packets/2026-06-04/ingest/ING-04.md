## ING04 — FRONTEND, every surface (tauri/ui/src) — adversarial done-claim verification

HEAD read at: **`d7d5337a175ac90612702c3adda4d17aa3918899`** (`d7d5337a test(config): isolate device defaults from rig env`), branch `ux-redesign-impeccable`. The FRONTEND-WIRING-EXIT-MAP was written at `7057d154`; 74 commits landed since, including the loops this ingest verifies. Line numbers re-pinned to HEAD.

Proof tiers, never conflated: **SRC** (green tests / wired on current source) != **PKG** (in a signed DMG built at HEAD) != **LIVE** (a real user reaches it). `test-passing-but-dark = 0`. No DMG was built or run, no sidecar launched (one socket). Everything below is SRC + by-bus/by-codegraph reasoning unless stated; PKG/LIVE are explicitly UNVERIFIED here (no artifact, no run).

### One-paragraph verdict

The autonomous loops landed 3 high-leverage surfaces real and both-ended (the in-GUI brain/key field, the START gate, the citation-receipt ts-join), and the two non-frontend locked decisions (VOICE=Chatterbox-only, BRAIN=proxy-default) landed deep at SRC. But the exit-map's "Cue Tray UI" did NOT land as a surface — what landed is the build-set tag-receipt + a permissioned cue-LANDING pipeline (Rust cmd + CLI verb), not the A-H ladder / ProvenanceBadge / ConfidenceMeter visual. Four exit-map breaks are still DARK at HEAD: the shell Receipts panel (still hardcoded placeholders, bridge never reads reactions), the pill receipts (reasons still hard-capped, cue_confidence + alternatives absent), the wizard telemetry-consent (still a phantom emit, no schema type, no handler), and the wizard key/proxy step (does not exist). One CLAIMED-capability is wired-but-dark: the debrief `evidence_registry.json` write capability exists in the recorder but the recorder is never handed the live registry, so it is never written. The voice-engine PICKER (exit-map #3) is now OBSOLETE not dark — Chatterbox is the only engine, there is nothing to pick — but the SettingsDrawer + README still carry stale "MOSS" copy that violates the partner-copy policy and the locked voice decision.

---

## LOCKED DECISIONS — verified against HEAD

### (1) VOICE = Chatterbox-only, MOSS NUKED, Apple-Silicon mlx-audio, voiceless+banner otherwise — **LANDED (SRC)**

- `src/vibemix/agent/tts_chain.py:6,25,31-42` — rewritten: "Chatterbox-Turbo is the only supported live engine"; `build_tts_chain` imports `chatterbox_tts` (`ChatterboxLocalTTS`, `build_chatterbox_adapter`, `engine_selected`); raises `ChatterboxUnavailable` if not selected. MOSS is gone from the chain. LANDED.
- `src/vibemix/agent/chatterbox_tts.py` — exists (13k, landed today via `eec239ac`). LANDED.
- `pyproject.toml:162,167` — `mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'` as an extra (Apple-Silicon-gated, matches v1 ship shape: arm64-only, Intel Macs voiceless). LANDED.
- First-run model fetch: `src/vibemix/library/model_assets.py` (NOT `install/model_assets.py` as the exit-map guessed) — the chatterbox preflight/prefetch landed here (`eec239ac` +297 lines). LANDED. The bundled ref clip script `scripts/dist/chatterbox_bundle.py` exists (1.4k). LANDED.
- Env-seed `VIBEMIX_TTS_ENGINE`: `src/vibemix/__main__.py:1062-1063` and `:1433-1434` seed it from `cfg.tts_engine`/`DEFAULT_TTS_ENGINE`. LANDED.
- No-GPU honest banner: `__main__.py:244-254` builds Chatterbox or "`-> tts:   unavailable (Chatterbox local only; voice muted, no fallback)`". Matches the locked "voiceless + honest banner, no cloud fallback". LANDED.
- Release-gate swap `--require-moss-source` -> `--require-chatterbox-source`: `.github/workflows/release.yml:356,400,427,542` + `scripts/dist/pretag_check.sh:109,111,113` (`--require-chatterbox-ref --require-chatterbox-source`) + `scripts/dist/check_windows_app_payload_ready.py:145,180`. The gate is swapped everywhere. LANDED.
- **STALE COPY (violation):** `tauri/ui/src/settings/SettingsDrawer.ts:496,945` still calls the voice picker presets "MOSS" (`sub: "MOSS"`). README (below) still says MOSS. This is dead/wrong copy under the Chatterbox-only decision — surface verdict in #3.

### (2) BRAIN = hosted proxy DEFAULT, set_brain BYO, no-key graceful — **LANDED (SRC)**

- Client default flipped direct->proxy: `src/vibemix/runtime/config_store.py:271` `llm_mode: str = "proxy"`; comment `:108-111` "Fresh installs default to 'proxy' so a no-key user reaches the hosted Bravoh brain". LANDED.
- Boot resolution: `__main__.py:1131-1136` env > persisted; `:1135` defaults `"proxy"`. LANDED.
- No-key graceful (no sys.exit on missing key): `__main__.py:1162-1170` — DIRECT with no `GEMINI_API_KEY` falls THROUGH to proxy ("trying Bravoh proxy"), does not exit. The only `sys.exit` at `:1143` is for a malformed mode string, not a missing key. Proxy failure -> `brain_unavailable_reason` banner (`:1175-1179`), no crash. LANDED.
- `set_brain` BYO handler: `runtime/session_loop.py:288` registers `ipc.settings.set_brain` -> `_on_settings_set_brain:486`. LANDED (see surface #1).
- NOT verified here: that `api.altidus.world/api/vibemix/v1/register` returns 200 LIVE (the prompt asserts it was verified today; I did not re-hit it — LIVE tier, out of read-only scope).

### (3) START GATE = no heavy model resident at idle, Start button, silent pre-warm, Stop releases — **LANDED (SRC, both ends)**

- Frontend (`23f3167d`): `SessionLayout.ts:151-162` `runState?: "armed"|"running"` + `onStart`/`onStop`; `:430-477` `.vmx-armed` Start gate CSS (reactions hidden while armed, Stop running-only); `:911-913` seeds runstate at mount. Render-loop `render-loop.ts:73-80` `sessionStartHandler` optimistic `setSessionState({runState:"running"})` then `emitIpc("ipc.session.start",{})`; `:86-92` `sessionStopHandler` mirror. LANDED.
- IPC: schema `ipc.session.start`/`ipc.session.stop` present (81 oneOf consts == 81 wrappers, parity green); `ui_bus/messages.py:361,368,1017,1041` `SessionStart`/`SessionStop` mirrors. LANDED.
- Backend handler (the exit-map said the backend "names but does NOT implement" — it is now IMPLEMENTED): `__main__.py:2238-2240` `session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active`; `_session_ipc.register_handlers()` wires them. LANDED.
- Idle-cold (no heavy model resident at idle): `__main__.py:2200-2209` `_silent_prewarm_hook` warms only live IMPORTS (`_ensure_live_llm_tts_deps`/`_ensure_live_session_deps`) — "live imports ready (models still cold)"; the live graph/capture only starts on `ipc.session.start` (`:1595` comment, `:2188-2198` `_stop_live_session` parks it). `_RunGatedMusicState(state, _is_live_session_active)` (`:2248`) gates the ws snapshot at idle, and `brain_available=_DynamicBool(_is_live_session_active)` (`:2265`). The start-gate lock test landed (`18dc95cb test(start-gate): lock idle-cold`). LANDED.
- `__main__.py:2275` "`-> start gate: armed (idle; capture/reactions/model load wait for Start)`". LANDED.

### (4) STREAK = robot voice, sequenced behind a cited EXECUTED transition — **CORRECTLY NOT RENDERED (still dark by design)**

- The pill streak remains DARK by design: `tauri/ui/src/pill/index.ts:997` `.pill__streak` is only a hit-test selector (no reader). No shipped pill TS reads streak/level_up/grade_progress (grep across `tauri/ui/src/pill/` returns only the hit-test). LANDED-as-intended (do NOT render).
- BUT the backend still ATTACHES the self-applause grade_progress: `runtime/suggestion.py:386-387,519-522,692-693` `_attach_grade_progress(...)` still rides the serialized `next_suggestion` frame. The exit-map decision was to STRIP these call-sites so a fake counter can never be silently re-rendered. **NOT-STARTED** — the strip did not land. The robot-voice-behind-a-cited-executed-transition sequencing is not built (no `[ev:BEATMATCH_GRADED]`/`[judge:]` LIVE event on the bus, as the exit-map noted). The pill is safe today only because no TS reads the field.

---

## Per-surface verdicts (exit-map order)

| # | Surface | Verdict | Tier | file:line evidence |
|---|---|---|---|---|
| 1 | In-GUI Gemini-key field + DIRECT/PROXY rocker | **LANDED** | SRC both ends | UI + schema + Python handler all present |
| 2 | Cue Tray UI (A-H ladder visual) | **CLAIMED-BUT-DARK** (different thing landed) | SRC partial | landing pipeline landed; the tray VISUAL did not |
| 3 | Settings voice-engine picker (MOSS vs Chatterbox) | **OBSOLETE** (Chatterbox-only) + stale copy | SRC | nothing to pick; "MOSS" copy is wrong |
| 4 | Shell "Receipts" panel | **NOT-STARTED** (still dark) | SRC | hardcoded placeholders, bridge never reads reactions |
| 5 | Deck citation receipt ts-join (signature gesture) | **LANDED** | SRC both ends | backend shares ts, frontend join intact |
| 6 | Pill receipts (reasons cap / cue_confidence / runner-up) | **NOT-STARTED** | SRC | reasons still `.slice(0,2)`, no cue_confidence, no alternatives |
| 7 | Pill streak (STRIP) | **PARTIAL** (frontend safe, backend not stripped) | SRC | no TS reader; backend still attaches grade_progress |
| 8 | Learn tutor VOICE (mute on ear) | **LANDED** | SRC | tutor_speak_audio synth wired end-to-end |
| 9 | Wizard telemetry-consent (phantom emit) | **NOT-STARTED** (still phantom) | SRC | no schema type, no handler |
| 10 | Wizard key/proxy step | **NOT-STARTED** | SRC | no step exists |
| — | Organism particle visual | **LANDED** (real Three.js physics) | SRC | imports three, ShaderMaterial/BufferGeometry |
| — | Debrief evidence_registry write | **CLAIMED-BUT-DARK** | SRC | capability in recorder, live registry never handed to it |

### #1 — In-GUI Gemini-key field + DIRECT/PROXY rocker — **LANDED (SRC, both ends)** — LIVE-data

Commit `8c6a7b6e feat(settings): in-GUI Gemini-key field + proxy/direct brain toggle (DEMOCRATIZATION-1)`.
- UI: `tauri/ui/src/settings/components/brain-group.ts` (385 lines, full). DIRECT/PROXY `renderRocker` (`:201-211`, optimistic), write-only masked `type=password` key input (`:272-279`, never seeded from inbound, cleared on good ack `:366`), Save (`:281-318`), one-line state readout (`:224-228`), "Restart now" button (`:240-254` -> `invokeTauri("restart_sidecar")`). `persist()` (`:341-373`) routes through the dedicated `sendIpcRequest("ipc.settings.set_brain", payload, "ipc.settings.brain_ack")` — NOT through `ipc.settings.set` (so the secret never echoes into SessionState/logs). Mounted: `SettingsDrawer.ts:83` import, `:1043` `body.append(BrainGroup())`. LANDED.
- Schema: `messages.schema.json:1551` `ipc.settings.set_brain`, `:1593` `ipc.settings.brain_ack` (ack carries `key_set` boolean only, no secret — `$comment:1583`). LANDED.
- Python: `ui_bus/messages.py:1083,1106` wrappers; handler `runtime/session_loop.py:288` register + `:486 _on_settings_set_brain` (validates mode, persists, `:522` never logs the key). LANDED.
- Redaction: commit notes `client.ts redactForLog()` pinned by `tests/ipc/client-redaction.spec.ts`. (SRC claim, not separately re-run here.)
- UNVERIFIED: PKG (in a DMG) + LIVE (a stranger pastes a key, restarts, hears the co-host). That is the real exit gate and needs a built DMG + ear-pass.

### #2 — Cue Tray UI — **CLAIMED-BUT-DARK: a DIFFERENT artifact landed** — STATIC (build-set receipt) / pipeline-only

Commit `a3e7dc0b feat(library): wire permissioned DJ app cue landing` is the relevant loop. What it actually landed:
- A build-set TAG-RECEIPT render in `tauri/ui/src/library/index.ts:617-660` (`buildTagReceiptLine`, `buildExportLines`, `buildExportHint`, `buildAutoCueMeta`) — Rekordbox/M3U8/markers2 export receipt lines under the existing build flow. Real source, honest-when-empty.
- A per-run consent flag `setBuildTagWriteGranted` (`index.ts:79,2462`) gating DJ-app tag writes.
- The permissioned LANDING pipeline: Rust `library_land_cues` registered (`tauri/src-tauri/src/main.rs:112`, impl `library_cmds.rs:1034`, `granted:bool` arg `:275`, packet writer `:301`); Python CLI verb `land-cues` (`__main__.py:4369-4395`, `--granted` flag `:4390`, `_cmd_library_land_cues`).
- **What did NOT land (the exit-map's surface #2):** no `tauri/ui/src/library/cue-tray.ts`, no `renderCueTray`, no A-H SLOT ladder, no `ProvenanceBadge` (◇ AUTO vs ● DJ), no `ConfidenceMeter` banded to policy floors, no Detecting/Review/Landed three-state tray, no `libraryLandCues(...)` DTO render in `api.ts` driving a tray view. The visual moat surface is still DARK; the backend that would feed it is wired. Verdict: CLAIMED-BUT-DARK (the "permissioned cue landing" commit is real and useful, but it is the pipeline + the build receipt, not the Cue Tray UI).

### #3 — Settings voice-engine picker (MOSS vs Chatterbox) — **OBSOLETE + STALE COPY violation** — STATIC-DARK

The exit-map premise (let a user pick MOSS vs Chatterbox-Turbo) is dead: the product is now Chatterbox-only (locked #1, `tts_chain.py:6`). There is correctly NO `tts_engine` selector (`grep tts_engine` across `messages.schema.json`, `ws-bridge.ts`, `ui_bus/messages.py` = 0). So "no picker" is now CORRECT, not a gap.
- BUT the existing voice picker copy is STALE and violates both the locked decision and the partner-copy policy: `SettingsDrawer.ts:496` "real MOSS-TTS-Nano", `:945` `sub: "MOSS"`. These present a retired engine to the user. NEEDS-CLEANUP (a non-blocking copy fix), not a new picker.

### #4 — Shell "Receipts" panel — **NOT-STARTED, still render-without-source** — STATIC-DARK

- `tauri/ui/src/shell/GroundingPanel.ts:41` still hardcodes `'<p class="panel-placeholder">No cited move yet.</p>'`, `:45` `'No suggestion yet.'`. The file comment `:5` even admits "until wired here, the live state must remain empty-state copy, not a fake receipt".
- `tauri/ui/src/shell/activation-bridge.ts:70` `tick()` still reads ONLY `getSessionState().cohostStatus` — it does NOT read `reactions[last]` or the `next_suggestion` ws field into a shell-store receipt slot. The proposed wire (extend the bridge, add a receipt slot, render real `citation_strip` chips) did not land.
- The panel auto-opens on idle->live (per the exit-map's `shell-store.ts` note). So it will still pop empty next to a real cited reaction in the deck. NOT-STARTED. (No backend change needed; both sources already flow — this is a pure frontend wire that was not done.)

### #5 — Deck citation receipt ts-join (the signature gesture) — **LANDED (SRC, both ends)** — LIVE-data once voice-on

Commit `d67e6f81 fix(session): share cohost reaction timestamp with transcript` closes the silent-dark join.
- Backend: `agent/dj_cohost.py` now captures ONE `reaction_msg_ts` from the reaction envelope (`:4062-4081` region) and passes it to BOTH the `SessionCohostReaction.make(...)` envelope AND, after the emit, `self._push_transcript(pending_transcript_text, ts=reaction_msg_ts)` (the `pending_transcript_text` deferral replaces the 4 inline `_push_transcript(audience_stripped[:140])` calls). `_push_transcript(self, text, *, ts=None)` appends `{"text":text,"ts":ts}` when ts is given.
- ws_bus drain: `runtime/ws_bus.py:781-787` now reads the carried ts (`if isinstance(item, dict): ts = str(item.get("ts") or ts)`) instead of minting a fresh `_now_iso()`. So the transcript-line ts == the reaction-envelope ts.
- Frontend join unchanged and correct: `ws-bridge.ts:294-297` builds `ReactionsByTs` keyed by `msg.ts` (envelope ts); `state.ts:294 appendTranscript` preserves the wire ts verbatim; `SessionLayout.ts:1294` `next.cohost.reactions.get(nowLine.ts)`. Because the two ts now byte-match, `.get()` resolves LIVE and the receipt underline/chip fires (the "sentence underlines its own claim" gesture).
- Tests: `tests/agent/test_overlay_publish.py` (+65) and `tests/runtime/test_ws_bus_snapshot.py` (+13) added with the fix. LANDED.
- UNVERIFIED: LIVE (a captured voice-ON set where the underline ignites in real time) — needs a running sidecar + ear/eye pass.

### #6 — Pill receipts: reasons[] cap, cue_confidence posture, runner-up — **NOT-STARTED** — STATIC (capped)

- `tauri/ui/src/pill/next-suggestion.ts:309-313` reasons are STILL hard-capped `.slice(0, 2)` (not density-aware; no `RenderOptions.density` thread to return all reasons at full density). `:454` the deep-reason path still spreads `t?.reasons ?? []` raw but the rendered slice is capped.
- `cue_confidence`: NOT declared in the transition wire interface (grep `cue_confidence`/`cueConfidence` in `next-suggestion.ts` = 0). The coarse 3-state posture from `cue_source` was not added.
- `transition_alternatives` / runner-up: NOT declared in `NextSuggestionWire` (grep `alternatives`/`runner` = 0). The deep-hover runner-up + margin was not added.
- All three are pure wire-only renders (engine already emits the fields per the exit-map's `next_suggestion.py` cites). None landed. NOT-STARTED. (NEEDS-CLARIFICATION items 1+2 from the exit-map — cue-confidence vocabulary, runner-up surface — remain open, so this may be intentionally parked on owner-gates.)

### #7 — Pill streak / combo / level_up (STRIP) — **PARTIAL: frontend safe, backend NOT stripped** — DARK

- Frontend: confirmed safe — no shipped pill TS reads streak/level_up/grade_progress (only `.pill__streak` hit-test selector at `index.ts:997`). LANDED-as-intended (no render).
- Backend strip NOT done: `runtime/suggestion.py:386-387,519-522` still call `_attach_grade_progress(...)`; `:692-693` still serializes `grade_progress` into the frame. The exit-map's CODEX_READY decision was to STRIP these call-sites so a future render can never silently resurrect a fake counter. NOT-STARTED on the backend. Risk today is latent (no reader), but the self-applause field still rides the wire.

### #8 — Learn tutor VOICE (loop closes on eye, was mute on ear) — **LANDED (SRC, end-to-end)** — LIVE-data when voice available

- The mute-on-ear gap is closed. `__main__.py:282-322 _build_learn_tutor_speak_audio(voice_tts, playback, muted)` returns a `speak(text, tts_marker)` that, off a daemon thread, calls `voice_tts.synthesize_pcm(text, _on_pcm)`, resamples PCM to OUTPUT_SR, and `playback.push(...)` — mute-aware (`:291,299`). Wired at boot: `:3596-3603` builds it with `voice_tts=live_voice_tts` (the SAME Chatterbox chain the co-host uses), gated `if live_voice_tts is not None`; `:3647 tutor_speak_audio=learn_tutor_speak_audio` into `LessonRuntime`.
- Consumed: `learn/runtime.py:2416-2432 _emit_tutor_speak` emits the IPC line AND, when `_tutor_speak_audio` is wired, synthesizes `payload.text` with `payload.tts_marker`. Docstring `:601-602` "every emitted LearnTutorSpeak line is also synthesized by the co-host voice". The eye surfaces (lock-meter `live_grade`, waveform, SkillWall) were already wired (exit-map "Confirmed CLEAR"). LANDED.
- Honest caveat: when voice is unavailable/muted (no Chatterbox, or push-to-mute), the tutor is silent too — which is correct (no cloud fallback). NEEDS-CLARIFICATION #4 (tutor voice IDENTITY: same Chatterbox vs a distinct tutor voice) is an open Kaan gate; the wire ships using the product co-host voice.
- UNVERIFIED: LIVE (a beatmatch lesson where the tutor actually speaks the grade line).

### #9 — Wizard telemetry-consent (phantom emit) — **NOT-STARTED, still phantom** — DARK

- `tauri/ui/src/wizard/router.ts:558` STILL emits `ipc.telemetry.set_consent` fire-and-forget. The schema has `ipc.profile.set_consent` (`messages.schema.json:2796`) but NO `ipc.telemetry.set_consent`. Python registers `ipc.profile.set_consent` (`runtime/wizard.py:137 -> :448`, `session_loop.py:308 -> :835`) but NO `ipc.telemetry.set_consent` handler anywhere. So the user's telemetry choice still falls into the void (no schema type, no handler). NOT-STARTED. The new IPC type + the `runtime/wizard.py` handler the exit-map specified did not land.

### #10 — Wizard key/proxy step — **NOT-STARTED** — DARK

- No `step-llm.ts` / `step-key.ts` / `step-brain.ts` in `tauri/ui/src/wizard/` (dir holds intro/permissions/output/controller/skill/profile-consent/telemetry/smoke + the known orphans `onboarding-flow.ts`, `step-48k-probe.ts`, `step-driver-fetch.ts`, `step-forewarning.ts`). No `ipc.wizard.set_llm` handler. A fresh non-dev still finishes the wizard with the brain on the proxy DEFAULT (locked #2 makes this survivable — proxy is keyless), but there is no in-wizard key/proxy step. NOT-STARTED. (Lower severity now that proxy-default + the Settings brain-group #1 both exist: a stranger boots on proxy and can switch to DIRECT in Settings. The wizard step is convenience, not the crash-path it was before #1+#2.)

### Organism particle visual — **LANDED (SRC), real physics** — LIVE-data (build-fresh)

- `tauri/ui/src/mascot/particle-organism.ts` (12k) imports `three` (`:12`): `BufferGeometry` (`:6,208,225,235`), `ShaderMaterial` (`:10,236,250`). NOT random dots — a real GPGPU/shader particle system, matching the Kaan-locked "ONE living organism, real physics" direction. Companions landed/touched today: `morph-controller.ts`, `focus-layer.ts` (teaching-focus glow), `renderer.ts`, `index.ts`. The exit-map's "Confirmed CLEAR" stands: organism is the rare fully-wired grounded-to-render chain; its only ship gap is the STALE DMG (PKG lane), not a frontend wire. LANDED at SRC.
- UNVERIFIED: PKG (organism commits predate the last DMG per the exit-map) + LIVE rig ear/eye is Kaan's.

### Debrief evidence_registry write — **CLAIMED-BUT-DARK (capability landed, wire missing)** — STATIC-DARK in the live path

- Capability exists: `audio/recorder.py:198 evidence_registry: object|None=None` param, `:208 self._evidence_registry = evidence_registry`, `:549-567` on close it snapshots and atomically writes `<session_dir>/evidence_registry.json` (tmp->os.replace). The debrief reader expects it: `debrief/session_loader.py:145-154` loads `evidence_registry.json` (optional; "using empty snapshot" when absent -> drills error + citation tooltips found=false, the exit-map break).
- THE GAP: the live recorder is built WITHOUT the registry. `__main__.py:1274 recorder = VoiceRecorder(root=recordings_root)` — no `evidence_registry=`. The live `EvidenceRegistry()` is created LATER at `:1596`, and there is no later `recorder._evidence_registry = ...` assignment (grep confirms only `:1274` construct + `:2235`/`:2976` `active_recorder=recorder` pass-through). So `_evidence_registry` stays `None` and `evidence_registry.json` is NEVER written for a real session. The debrief drill/citation-tooltip break the exit-map flagged is STILL DARK at HEAD. One-line fix (hand the `:1596` registry to the `:1274` recorder, or move the recorder construction after the registry), but it did not land. CLAIMED-BUT-DARK.

---

## IPC seam — emit/consume sanity at HEAD

- Schema count parity: 81 `"const": "ipc.*"` oneOf entries; commits assert 81 wrappers (`23f3167d` bumped 79->81). codegen FRESH: `validator.generated.mjs` + `messages.ts` share mtime `1780592895`, both NEWER than `messages.schema.json` (`1780586971`). So a stale-validator field-rejection is NOT a risk right now.
- New types this ingest confirmed both-ended: `ipc.settings.set_brain`/`ipc.settings.brain_ack` (UI + schema + Python handler), `ipc.session.start`/`ipc.session.stop` (UI emit + schema + Python handler).
- Dead one-ended type at HEAD: `ipc.telemetry.set_consent` — EMITTED by `wizard/router.ts:558`, NO schema type, NO consumer. This is the surface #9 phantom; it is the one shell-window emit with no consumer.
- The exit-map's "ZERO server->client emitted-but-unread" claim was not re-derived in full here (it covered ~45 types); the new outbound types added since (`brain_ack`) resolve to the `brain-group.ts` reader, so no new server->client orphan was introduced.

---

## README / partner-copy — **VIOLATES policy, NOT cleaned** (4 CI gates pin it; cleanup will need a coordinated edit)

`README.md` at HEAD violates every public-facing rule the prompt named:
- Names the model: "Google Gemini" / "Gemini proxy" (`:39,61,241,259,269,271`). Policy: say "AI model".
- Names the voice: "MOSS voice path" (`:229,241,271`). Policy: "on-device voice" (and MOSS is now retired — doubly wrong).
- Leaks the backend URL: `api.altidus.world` (`:39,61,241,259`). Policy: "Bravoh's hosted service".
- Wrong domain: `security@bravoh.com` (`:63`). Policy: bravoh.ai.
- Internal dev slop in the feature matrix: Phase numbers (`:134,135,140,142,148,149,80`...), "Kaan ear-passes daily" (`:69`), "KAAN-ACTION" (`:11,30,86,134,142,198`), SHIPPED dates + commit-grade detail. Policy: no internal slop.
NOT-STARTED on cleanup. Note: the matrix is AUTO-GEN (`sync_feature_matrix.py --check` via `test_readme_feature_matrix_sync.py`) so the Phase-number dump is generated from source, not hand-typed — fixing the policy text means fixing the generator + the 3 other gates (`test_readme_shape.py`, `check_readme_grids_a11y.py`, `check_readme_hero_hash.py`) in lockstep. This is a real, gated cleanup task, not a one-line edit.

---

## Bottom line for the ship lane

- **Real, both-ended, SRC-proven this loop:** brain/key field (#1), START gate (#3 locked), citation ts-join (#5), learn tutor voice (#8), Chatterbox-only voice (#1 locked), proxy-default brain (#2 locked), organism (real physics). These are the high-leverage wins.
- **Still DARK at HEAD (frontend wires that did not land):** shell Receipts panel (#4), pill receipts (#6), wizard telemetry phantom (#9), wizard key step (#10). None are crash-path now (proxy-default + Settings brain-group absorb the old crash), but #4 ships an empty panel popping next to a real reaction = visible slop.
- **CLAIMED-BUT-DARK (capability without wire):** Cue Tray VISUAL (#2 — pipeline landed, tray did not), debrief `evidence_registry.json` (recorder can write it, never gets the registry).
- **Latent/copy:** pill streak backend not stripped (#7, safe today), SettingsDrawer "MOSS" copy stale (#3), README policy violations (4 CI gates).
- **Tier reminder:** everything above is SRC. The exit gate is PKG (a signed arm64 DMG at HEAD) + LIVE (a stranger pastes a key OR boots on proxy, presses Start, hears Chatterbox, sees the citation underline ignite). No DMG was built and no sidecar run in this ingest — PKG/LIVE are UNVERIFIED.
- **GA-tag landmine intact:** release gate swapped to `--require-chatterbox-source`; `VIBEMIX_PRETAG_MAC_ONLY=1` skips SignPath/Windows (`pretag_check.sh:129,148`); `build-windows` job still in `release.yml:470` and fires on a `v*` tag — do NOT push `v0.1.0` until Windows is excluded from the tagged matrix + secrets are set. Confirmed unchanged from the maps.
