# SHIP-MAP-MASTER — the fresh-eye whole-system ship map

> The single orientation document. Read this once and you know the whole vibemix system, exactly where to look, and how to organize the ship. Synthesized from 14 subsystem maps (brain/intel/library-cue/learn/runtime-io/frontend + dark-census + 3 tiers + voice + democratization + critical-path + corpus). **Do NOT commit this file — the organizer commits.**

**Synthesized at HEAD `7ac35a84` (branch `ux-redesign-impeccable`, 2026-06-04).** The 14 maps were read across `69a5355e` → `b8122a8b`; the tree has since advanced to `7ac35a84` and several map claims are now STALE — every staleness is corrected inline and flagged `[MOVED SINCE MAPS]`. The tree moves every few minutes under 2+ concurrent sessions; re-pin a fresh SHA before acting on any line number. Three proof tiers, never conflated: **SRC** (green tests on source) ≠ **PKG** (in the signed DMG built at HEAD) ≠ **LIVE** (a stranger reaches it). `test-passing-but-dark = 0`.

---

## Read-me-first

1. **What vibemix is:** a commercial AI DJ co-host. It listens to your master output (BlackHole), watches your DJ app, ingests MIDI controller moves, and talks a grounded line back into your ear as a hype-man or coach. The bar is "real DJ friend in your ear, no AI slop" — every spoken line must cite a real detected event or it is stripped.
2. **The built-but-dark thesis:** the engine is real (~70-80%): perception, evidence registry, intel scorers, library/cue moat, learn loop all WIRED and SRC-green. The dark is concentrated at two seams: the engine→live-spoken-line seam (rich intel lights the pill but never speaks) and the boot/packaging→fresh-user seam (the locked voice + Start gate are unreachable on a real launch).
3. **The 4 locked decisions (Kaan-final):** (1) VOICE = Chatterbox zero-shot pranker is the ONLY voice, MOSS NUKED — `[MOVED: DONE in source — local_tts.py deleted, tts_chain.py Chatterbox-only, DEFAULT_TTS_ENGINE="chatterbox"]`. (2) BRAIN = hosted Bravoh proxy default, LIVE + funded — `[MOVED: DONE — llm_mode="proxy", set_brain handler wired]`. (3) START GATE + model lifecycle = SHIP-CRITICAL, idle=cold, Start button activates — `[backend handler still DARK]`. (4) STREAK = Daft-Punk Technologic robot voice, but SEQUENCED behind rebinding to a cited EXECUTED transition first — `[not started, correct]`.
4. **Proxy is now live + funded:** register → JWT → `gemini-3.5-flash` → HTTP 200 on `api.altidus.world/api/vibemix/v1/register` (verified end-to-end same-day; credits are a Kaan/Bravoh-ops flag, unverifiable read-only). The fresh client default is proxy.
5. **The #1 blocker is no longer the fresh-user crash** — `[MOVED: the crash is FIXED; there is no `sys.exit(4)` in `__main__.py`; no-key direct falls back to proxy, total brain failure degrades gracefully]`. The real #1 blocker is now **VOICE REACHABILITY: `mlx_audio` is not installed and not a `pyproject.toml` extra → `chatterbox_available()=False` → the locked voice is voiceless on every launch.**
6. **The single next move:** make the locked Chatterbox voice reachable on a packaged launch — add `mlx-audio` as a `pyproject.toml` extra (Apple-only) + bundle `cohost_voice_ref.wav` as a PyInstaller `datas` asset. Until `chatterbox_available()` returns True on a real launch, no human can hear the voice and the keystone capture (the one release gate) cannot happen.

---

## Architecture map

**brain (`state/` + `agent/`) — WIRED.** The perception heartbeat. `MusicState` (`state/music_state.py:23`) is the single source of truth, written ONLY by `refresh.py::_tick_once` (`state/refresh.py:927`, lock at `:1090`) at ~10Hz — Invariant #1 holds. `event_detector.py::detect()` (`state/event_detector.py:244`) emits one typed event/cycle with per-type cooldowns and writes `[ev:TYPE@t]` to the registry. `AICoach.build_prompt` (`state/prompt_builder.py:1106`) composes the grounded prompt (NOTE: CLAUDE.md's "coach.py builds prompts" is STALE — prompt IP is `prompt_builder.py`, the live loop is `runtime/coach.py::coach_loop:442`). `EvidenceRegistry` (`state/evidence_registry.py:234`, 11 sources) backs Invariant #2. `agent/dj_cohost.py::llm_node` (`:2464`) is the live Gemini reaction path + the citation strip/linter scrubber. In-flight single-generation gate at `runtime/coach.py:542`; speak gate (rare+earned voice) at `:822`. **DARK-by-design:** KEY_CLASH (`event_detector.py:417`), TRANSITION_OPPORTUNITY (`:466`), DROP-call (`:294`) — flags off at `__main__.py:1464` (`EventDetector(audio_buf=audio_buf)` defaults), gated behind a Kaan-ear veto, intentional anti-slop.

**intel (`intel/`, 16 modules) — WIRED to the PILL, DARK to the spoken line.** The deterministic spine: `claims.py` → `decision_runtime.py::decide` → `claim_validator` → `decision_trace` → `transition_scorer.py::score_transition_slate` (`:154`) + `move_grade.py::grade_transition`. This whole chain reaches the PILL end-to-end (`runtime/suggestion.py` → `ws_bus.py:1321` → `tauri/ui/src/pill/index.ts`), but the **live spoken line** only gets two engines through the post-generation guard `apply_live_claim_guard` (`state/deck_context.py:2999` → `dj_cohost.py:3625`): `eq_move_model.py` (the keystone narrator→coach unlock) and `transition_judge.py` (which abstains on a master-only rig → ~never fires). The transition-scorer reasons + move grade + ontology risks NEVER speak. That asymmetry IS the narrator→coach gap (BACKEND-WIRING W8/W9/W11). `feedback_hooks.py` = 0 importers (orphaned IP); the `gold_*` triplet is eval-only by design.

**library-cue (`library/`) — the HEALTHIEST subsystem, LIVE end-to-end.** CLAP ONNX 512-dim embeddings (`clap_engine.py:244`) + sqlite-vec mean-centered search (`search.py:134 store.search_centered`). The cue moat: CUE-DETR ONNX (`cue_detr.py`) → SmartCue slot/provenance policy (`smart_cues.py:78`) → non-destructive carriers (`export_rekordbox.py`, `cue_export.py`, `export_serato.py`, NO direct-DB write) → provenance stamp `VM ` leak CLOSED (`cue_provenance.py`). Viber auto-cue-on-export is LIVE default-on (`toolset.py:951`). All 9 Tauri library commands LIVE (`library_cmds.rs` + `api.ts`). **DARK:** the reusable `cue_landing.py::land()` (`:290`) has 5 callers, all tests — the live spine uses a parallel hand-rolled path (`toolset.py:2231 _auto_cue_marks_for_export`); two spines agree today but can diverge (W13, owner-gate). The Cue Tray GUI (A-H slot ladder) is designed but DARK (needs `library_land_cues` Tauri cmd). Moat ships behind the keystone, not on the fresh-user path.

**learn (`learn/`, ~35 modules) — the most-closed island, LIVE loop ~90%.** All 5 stages close in the real boot: OBSERVE (`BeatmatchPracticeDriver` + `TwoDeckPlayer`, real audible practice loops, `__main__.py:2829/3022`) → GRADE (`runtime.py:2505`) → CARRY-TO-IPC (`_emit_live_beatmatch_grade:2570` emits `LearnLiveGrade`, consumed by `live-meter.ts`/`learn-window.ts`) → CREDIT (`runtime/coach.py:151 _credit_live_skill_demo`) → UNLOCK Mastered (`coach.py:219`). Invariant-3 audio-over-live-set guard SOLID (`two_deck_player.py:44 can_play`). `[CORRECTS the 2026-06-03 "built-but-mute, grade discarded" diagnosis — STALE]`. **DARK:** `[ev:BEATMATCH_GRADED]` is not wired into `runtime/coach.py` so the highest-value skill can only be credited from practice, not a live set (W12); one frontend a11y bug on `.learn-waveforms` (aria-prohibited-attr); Course-3 routed-audio proof is an operator-config blocker, not code.

**runtime-io (`runtime/ audio/ platform/ events/ midi/`) — solid + grounding-honest.** Single socket `127.0.0.1:8765` (`ws_bus.py:1124`, Invariant #4 held — wizard + session never bind concurrently). 10 IPC handlers registered (`session_loop.py:255`), `[MOVED: now 12+ including set_brain at :279]`. Deterministic master capture (`device_select.py:133` 2ch-first), native-rate audio (`_audio_macos.py:562`), single mido daemon listener, 11 MIDI profiles (docs undercount as 10), honest MIDI activity probe (`midi/activity.py:7`, idle≠active). **DARK:** Start-gate backend handler (schema exists, no `_on_session_start`); macOS screen-watch hardcoded djay-only (`_screen_macos.py:470` vs Windows' 5-app hint list `_screen_windows.py:191`); NI S2-MK3 HID bridge built but 0 callers, no `ControllerState.apply_event` ingest seam (`_hid_macos.py:319`); route-doctor `top_signal` RMS-flips at `scripts/learn_live_readiness.py:922` (W5 2ch fix landed at 4 other sites, not this one).

**frontend (`tauri/`) — SRC-green, PKG-stale.** `tsc --noEmit` exit 0, 1510 vitest pass. WIRED: brain-group (in-GUI key + DIRECT/PROXY rocker), deck cohost hero + transcript, pill next_suggestion (3-outcome honest-null), mascot/organism (the rare fully-grounded→render chain, Kaan-LOCKED visual soul), learn EYE loop, debrief. **DARK:** Start/Stop control (no `sessionActive` state, schema exists but no UI button); Shell "Receipts" panel hardcoded empty (`shell/GroundingPanel.ts:38`); deck citation receipt ts-join silently fails live (`SessionLayout.ts:1171` joins on a ts that never byte-matches the reaction ts); learn tutor voice mute on the ear (`tts_marker` rides the wire, no audio consumer); wizard has no key/proxy step + telemetry-consent phantom-emits a type absent from schema.

---

## Wired vs DARK (ranked, shippable-value first)

| # | symbol | file:line | dies-where |
|---|--------|-----------|------------|
| 1 | `chatterbox_available()` → False (no `mlx_audio`) | `agent/chatterbox_tts.py:90`; `pyproject.toml` (no `mlx`) | the LOCKED voice is voiceless on every launch — `mlx_audio` not installed/not an extra, ref clip unbundled (`~/.cache/vibemix/cohost_voice_ref.wav` dev-only) |
| 2 | `_on_session_start` / `ipc.session.start` backend handler (absent) | schema exists `messages.schema.json:1440`; no handler in `session_loop.py`/`__main__.py` | the SHIP-CRITICAL Start gate — frontend half + schema landed, backend dark; heavy models sit resident at idle |
| 3 | `_emit_live_beatmatch_grade` → `[ev:BEATMATCH_GRADED]` | `learn/runtime.py:2570`; `grep BEATMATCH_GRADED runtime/coach.py` = 0 | on a real live set the highest-value DJ skill can NEVER be credited (only practice/recorder) — W12 |
| 4 | `score_transition_slate` reasons + `grade_transition` verdict | `intel/transition_scorer.py:154`, `move_grade.py:135` | spoken line's only transition intel is the bare Camelot join (`prompt_builder.py:493`); rich coaching lights the pill only — W9 |
| 5 | `_supports_grounded_transition_verdict` master-only abstain | `state/deck_context.py:2880` (live via `coach.py:364`) | the Vibe Judge always abstains on a default master-only rig → the one voice-wired intel engine ~never fires — W8 (FINISH) |
| 6 | citation-receipt ts-join | `dj_cohost.py:1880 _push_transcript` (no ts) vs `ws_bus.py:783` (separate `_now_iso()`) | the "sentence underlines its own citation" gesture fires only in unit tests; silently dark live — Seam D |
| 7 | `cue_landing.land()` (reusable verb) | `library/cue_landing.py:290`; 5 callers all tests | live Viber auto-cue uses a parallel inline spine; two cue spines can silently diverge — W13 (owner-gate) |
| 8 | `judge_transition.risk_flags` (harmonic_clash/bass_collision) | `intel/transition_judge.py:71` | "you clashed the keys" computed + logged, never spoken — W11 |
| 9 | `transition_alternatives` + `cue_confidence` on pill | `library/next_suggestion.py:227/:802`; not in `NextSuggestionWire` | runner-up + cue-confidence computed, never declared on the wire; `reasons[]` hard-capped `.slice(0,2)` — FE#6 |
| 10 | `evidence_registry` → recorder | `audio/recorder.py:198`; `__main__.py:1262` omits `evidence_registry=` | `evidence_registry.json` never written → debrief drills error, citations `found=false` on all long sessions — R10 (single-kwarg wire) |
| 11 | `_attach_grade_progress` streak | `runtime/suggestion.py:1365/1391/1450` | self-applause (grades its OWN un-played suggestion); must be STRIPPED + re-grounded before any robot voice — W7/R7, Invariant #3 risk |
| 12 | `find_dj_window` on macOS (absent) | `_screen_macos.py:470` hardcodes "djay" | vision DARK for Rekordbox/Serato/Traktor on Mac while README claims app-agnostic — W15 |
| 13 | `start_s2_mk3_listener` (NI HID) | `platform/_hid_macos.py:319`; 0 callers | decoded S2-MK3 events go nowhere; no `ControllerState.apply_event` ingest seam — W16 (post-ship) |
| 14 | `recommend_auto_master_input` device pick | `scripts/learn_live_readiness.py:922` | RMS-only sort, no 2ch discriminator → operator can copy a coin-flip device into the keystone capture — W5 |
| 15 | voice/audio model literals ungated | `chatterbox_tts.py:40`, `library/model_assets.py:27`, `cue_detr.py` | CI grep gate only matches `gemini-*`; voice/audio IDs drift silently green forever — W17 (governance) |

**Dead, do NOT wire:** `feedback_hooks.py` (0 importers), bare `export_serato`/`automix_demo` entrypoints (0 callers; Serato IS reachable via `cue_folder`), wizard orphans `onboarding-flow.ts`/`step-driver-fetch.ts`/`step-48k-probe.ts`, `session_loop.py:237 append_transcript`.

---

## 3-tier ship state

**SRC — green except a stale-guard RED set.**
- pytest default suite + 1510 vitest + `tsc --noEmit` (exit 0) + IPC schema parity + clean-checkout + Inv#3 AST gate + citation grounding: GREEN.
- `[MOVED: the 3 SHIP-READINESS RED gates the maps screamed about are now GREEN — the 5 agent persona/grounding tests, the auto_crate stop-reason whitelist, and tsc all pass at HEAD.]`
- **RED list (stale test-vs-source policy mismatches, NOT product regressions):** (1+2) `tests/repo/test_readme_shape.py` + `test_readme_feature_matrix_sync.py` — assert `altidus.world/vibemix` in README; commit `5a1e3533` deliberately swapped to `bravoh.ai` → re-pin gate. (3+4) `tests/security/test_no_api_key_surface.py` — fails on the in-GUI Gemini key field in `brain-group.ts`; head-on conflict between the Phase-33 "never ship a key surface" gate and locked decision #2's BYO key field → retire/scope-narrow the gate (owner/policy call). Each is a 1-test re-pin; none block the product but all block `full-test-matrix` CI and therefore a tag.
- **Dark-but-green risk:** `mlx_audio` not installed → Chatterbox tests pass by mocking but the voice never plays (PKG/LIVE gap masquerading SRC-green); 25 advisory-only orphans vs baseline; the keystone (LIVE) has zero test coverage by definition.

**PKG — every distributable is stale; the canonical one is not even signed.**
- `dist/vibemix-0.0.1.dmg` (487M, built 09:59) is UNSIGNED (`spctl`: no usable signature) and ~190+ commits behind HEAD. The freshest SIGNED DMG (`dist/fresh-20260604-wav-signed-v2/`) is ~250 commits behind. `notarytool-submission.log` "Accepted" + `verify-report.json` "clean" belong to an EARLIER run, not the canonical DMG. Do NOT evaluate HEAD from any DMG or `/Applications/vibemix.app` — all predate it.
- **Platform coverage: arm64-only.** `binaries/vibemix-core-x86_64-apple-darwin/` and `-windows-msvc/` are `.placeholder` only → macOS-Intel + Windows PKG=0. The updater manifest gate (`check_updater_manifest_ready.py:15`) hard-requires all 3 → no signed `latest.json` until Intel + Windows binaries exist.
- **Gate steps to a fresh signed HEAD arm64 DMG:** (1) commit the dirty seam files (`__main__.py`, `config_store.py`, `ws_bus.py`, agent/voice files — `source_dirty` fails the sidecar-freshness gate until clean); (2) clear the 4 stale RED gates above; (3) `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`; (4) rebuild DMG SEPARATELY (sidecar rebuild does NOT refresh the DMG); (5) `scripts/dist/sign_macos.sh`; (6) `VIBEMIX_PRETAG_MAC_ONLY=1 scripts/dist/pretag_check.sh` then tag (skips SignPath).
- **`[MOVED: a release-gate conflict the maps flagged]`:** `pretag_check.sh` + `release.yml` still pass `--require-moss-source` (MOSS bundle gate) at ~5 sites, but MOSS is NUKED in source. A HEAD DMG ships either no MOSS (gate FAILS) or stale MOSS. **The packaging layer needs a `--require-chatterbox-source` gate-swap + the mlx-audio/ref-clip bundle before a HEAD DMG can honor the voice lock.**
- **Externals (Kaan-only):** Apple notarization (automated, proven), SignPath OSS approval (Windows, in flight — `VIBEMIX_PRETAG_MAC_ONLY=1` lets an arm64 rc tag without it), proxy credits.

**LIVE — the keystone has never been crossed.**
- Fresh-user step ladder: (0) DMG download/Gatekeeper = DARK (PKG stale). (1) wizard launch = LIVE. (2) telemetry-consent = DARK (phantom emit, non-fatal). (3) audio routing = PARTIAL (detect + deep-link, no in-app installer). (4) reach the brain = LIVE `[MOVED: proxy default + graceful no-key, crash gone]`. (5) voice reachable = DARK (`mlx_audio` gap, #1 blocker). (6) Start the session = DARK (no backend handler). (7) hear a grounded line in cloned voice = DARK (depends on 5+6). (8) deck line underlines its citation = DARK (ts-join mis-keyed).
- **The 5 cross-engine seams:** A brain-handler `[MOVED: DONE — set_brain wired + writes brain_env_path]`; B voice-reachability `[DARK — the real #1]`; C Start gate `[backend DARK]`; D citation ts-carry `[DARK]`; E proxy-default `[DONE]`.
- No captured run has nonzero `voice_rms` or a `transcript_delta` over real audio. The co-host has NEVER spoken live. This is the single artifact that flips the LIVE tier, and no read-only/autonomous lane can produce it — it is Kaan's hand on the rig.

---

## The voice path + the proxy path

**VOICE — current vs required.**
- `[MOVED since maps: MOSS is NUKED.]` `local_tts.py` is DELETED. `tts_chain.py::build_tts_chain` (`:17`) is Chatterbox-only — raises `ChatterboxUnavailable` if `engine_selected()` is false, no MOSS branch, no cloud fallback, voiceless on no-GPU. `config_store.DEFAULT_TTS_ENGINE="chatterbox"` (`:65`) + `tts_engine` field (`:248`) + `normalize_tts_engine` (`:69`). Engine select reads `VIBEMIX_TTS_ENGINE` (default `chatterbox`) via `chatterbox_tts.engine_selected()` (`:85`). Locked decision #1 has LANDED in source.
- **Remaining wires:** (1) **add `mlx-audio` as a `pyproject.toml` extra** (Apple-only, pulls transformers 5.x — owner-call) — without it `chatterbox_available()` (`:90`) is False forever and the voice never plays; THIS is the #1 blocker. (2) **bundle `cohost_voice_ref.wav`** as a PyInstaller `datas` asset + point `resolve_ref_path()` at the bundled path (present in dev-cache only, 720k). (3) **env-seed** `os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine)` at `__main__.py:~1420` + in `_apply_packaged_defaults` (launchd/Dock strip `VIBEMIX_*`). (4) **swap the release gate** `--require-moss-source` → `--require-chatterbox-source` across `pretag_check.sh`/`release.yml`. (5) **Windows GPU backend** = separate BUILD lane (ONNX-DirectML or torch+CUDA, same voice or voiceless banner). (6) streak Technologic voice = SEQUENCED behind re-grounding (decision #4).

**PROXY / democratization — current vs required.**
- `[MOVED since maps: both halves DONE.]` Client default = `config_store.llm_mode="proxy"` (`:271`). No-key direct → proxy fallback (`__main__.py:1145-1158`); total brain failure degrades to an honest banner, no `sys.exit`. Register `POST {base}/api/vibemix/v1/register` (`jwt_cache.py:79`), proxy client `proxy_client.py:33`, base `api.altidus.world`. The `set_brain` BYO-key handler IS now wired (`session_loop.py:279 _on_settings_set_brain` → persists `llm_mode` + writes `GEMINI_API_KEY` to `brain_env_path()`, `:423-470`).
- **Remaining wires:** external proxy credits top-up + per-client rate cap on `ssh altidus` (429 surfaces an honest banner, never crashes — not a code wire). Optional: a wizard key/proxy step (no longer ship-blocking since proxy carries the fresh user).

---

## Locked decisions (canonical)

1. **VOICE** = the zero-shot pranker Chatterbox is the ONLY voice; MOSS nuked (engine/default/floor gone, no CPU floor, no cloud). Mac = mlx-audio Metal (`chatterbox-turbo-8bit`, temp 0.4). Windows = a GPU-backend BUILD. No compatible GPU → voiceless + honest banner (transcript still shows). Ref = `~/.cache/vibemix/cohost_voice_ref.wav`. NOT finetuned. **Ordering hazard: bundle ref + mlx-audio + reachability BEFORE relying on it.** `[source-side DONE; reachability + bundle + gate-swap REMAIN]`
2. **BRAIN** = hosted Bravoh proxy DEFAULT, live + funded. Client flips direct→proxy. In-GUI key field = advanced BYO. `[DONE]`
3. **START GATE + model lifecycle** = SHIP-CRITICAL: no heavy model resident at idle, silent background pre-warm, a Start/Başlat button activates capture + reactions, Stop/idle releases. v1 scope = Start + Stop-releases + silent pre-warm, NOT a full eager→lazy refactor. `[IPC schema DONE frontend-side; backend handler DARK]`
4. **STREAK** = full Daft-Punk "Technologic" robot voice in v1, but SEQUENCED — rebind off the self-applauding suggestion-grade onto a cited EXECUTED transition FIRST, then the robot voice fires, on debrief/progress NEVER the live eyes-off pill. `[not started, correct]`

**The #1 ship-blocker = VOICE REACHABILITY** (`mlx_audio` gap). `[The fresh-user CRASH the maps named #1 is FIXED at HEAD.]`

**Organizer smaller defaults (Kaan may override):** cue-confidence = 3 buckets; runner-up reveal = debrief; cue-landing consolidated via `cue_landing.land()`; learn tutor voice = the co-host Chatterbox engine.

---

## Open questions (Kaan)

1. **mlx-audio as a `pyproject.toml` extra** — required by decision #1; until added, the voice is permanently dark for a stranger. Owner-call (reintroduces transformers 5.x, Apple-only).
2. **Keystone capture sign-off** — no run has had nonzero `voice_rms`; the co-host has never spoken live. Kaan's hand on the rig; the single artifact that flips LIVE.
3. **Windows v1 scope** — Windows is SRC+CI real but PKG=0/LIVE=0 (needs an NVIDIA box + GPU Chatterbox backend + SignPath). macOS-Intel is ALSO PKG=0. Ship macOS-arm64-only, +Intel, or hold for Windows?
4. **Free-vs-Pro tier shape** — confirm Free / €4.99 Pro / €9.99 Studio so packaging + proxy rate-cap tiers match.
5. **Cue-landing consolidation (W13)** — route the live Viber auto-cue through reusable `cue_landing.land()`, or leave it tested-but-unused?
6. **Streak robot-voice v1 timing** — ship behind the full 3-step rebind in v1, or defer to a deck-routed-judge milestone? (Never ship on the present self-applause signal.)
7. **DMG rebuild + SignPath/Apple** — every distributable is stale; external clock, not a code wire. Also the `--require-moss-source`→`--require-chatterbox-source` gate-swap.

---

## Lanes + ownership + collisions

**Single-owner files (NEVER two sessions, `git add <exact paths>` not `-A`, verify `git diff --cached`):**
- **`__main__.py main()` = ONE owner (keystone/backend-boot lane).** Voice env-seed, Start-gate restructure, the landed proxy flip all live here. Start-gate is the most load-bearing edit and risks the keystone capture — sequence everything behind it.
- **`config_store.py` = ONE owner (keystone).** `tts_engine` + `llm_mode` (both landed), the dataclass + `_PHASE12_FIELDS`.
- **IPC schema (`messages.schema.json`) = FRONTEND-lane only.** `ipc.settings.set_brain` and `ipc.session.start/stop` types already exist — do NOT re-author (clobbers shared schema). Backend lanes implement the named Python handler only.
- **One socket `127.0.0.1:8765`** — `pkill -f "python -m vibemix"` before any live probe.

**Lanes (per the GOAL-*.md split):** engine (intel→live-brain wires W8/W9/W11), sven (`dj_cohost.py` ts-carry + spoken-line wires), learn (`learn/runtime.py`, `[ev:BEATMATCH_GRADED]` W12), library (cue-landing W13, Cue Tray), frontend (`tauri/ui`, Start button + receipts panel + pill receipts), organism (visual soul, Kaan-LOCKED). Backend-boot = the keystone/packaging lane owning `main()` + `config_store` + voice reachability.

**Landed (`[MOVED since maps]`):** MOSS nuke (source), Chatterbox-only `tts_chain`, `DEFAULT_TTS_ENGINE`, `set_brain` handler + `.env` persist, `tts_engine` config field, proxy default + crash removal, `session.start/stop` IPC schema (frontend), learn live grade loop, cue provenance leak close, auto-crate GUI, README→bravoh.ai swap.
**In-flight (dirty at HEAD):** agent/voice files (`chatterbox_tts.py`, `tts_chain.py`, `proxy_client.py`, `line_voice.py`, `config.py`), `config_store.py`, `ui_bus/messages.py`, the IPC schema/codegen triplet, `voice_presets.py`.

---

## Critical path to v1

Ordered blocker sequence (shortest honest path to a stranger hearing a grounded Chatterbox line):

1. **VOICE reachability** — add `mlx-audio` extra + bundle `cohost_voice_ref.wav` + env-seed `VIBEMIX_TTS_ENGINE`. Without this `chatterbox_available()=False` and every other proof collapses into a capture that cannot happen. **(keystone/backend-boot lane)**
2. **START GATE backend** — `register_handler("ipc.session.start", _on_session_start)` + the `main()` light-idle-boot/`_activate_session()` split + Stop-releases (schema + `prewarm()` hooks ready). **(keystone lane, touches `main()` — sequence behind/with #1)**
3. **CITATION ts-carry** — thread one `reaction_ts` through `_push_transcript` so the deck "underlines its own citation" gesture fires live (the core anti-slop visual). **(sven lane, `dj_cohost.py`)**
4. **PACKAGING** — commit dirty seam files, clear the 4 stale RED gates, swap `--require-moss-source`→`--require-chatterbox-source`, rebuild sidecar THEN DMG, sign. **(backend-boot + Kaan for sign/SignPath)**
5. **KEYSTONE capture** — drive a real set into BlackHole 2ch, hear a grounded Chatterbox line whose citation resolves in `EvidenceRegistry`. Validates voice + grounding + Invariant #3 at once. **(Kaan-only, LIVE=0 today)**
6. **STREAK robot voice** — deferred, sequenced behind re-grounding the streak to a cited executed transition. **(not v1-launch-critical)**

**THE SINGLE NEXT MOVE:** make the locked Chatterbox voice reachable on a packaged launch — add `mlx-audio` as a `pyproject.toml` extra and bundle the ref clip as a PyInstaller `datas` asset. This is the gating dependency for the keystone capture and the true #1 blocker now that the crash and the RED gates are resolved.

**Kaan-only (no autonomous lane):** the mlx-audio extra owner-call; the by-ear keystone capture; DMG sign/notarize + SignPath/Apple clock; proxy credits top-up; Free/Pro/Studio tier shape; Windows-vs-mac-only v1 scope.

---

## Doc index (live `.planning/packets/2026-06-04/`)

- `SHIP-MAP-MASTER.md` — THIS file, the fresh-eye whole-system map (synthesized at `7ac35a84`; supersedes all per-map orientation).
- `SHIP-WIRE-GOALS-RERAIL.md` — the operative driver: STOP protocol, the 4 locked decisions, observed lane state, one bounded /goal per session.
- `HANDOFF-POST-COMPACT.md` — post-compact re-entry: the 4 decisions, proxy-now-live, ownership map, doc index.
- `SHIP-READINESS-2026-06-04.md` — the 5-tier ship DoD (SRC/PKG/LIVE × 5); ordered critical path; owner-gates. (Proxy-429 + 3 RED-gate lines now STALE.)
- `SHIP-DRIVE.md` / `SHIP-FINISH-PLAN.md` — the self-driving ship loop + endgame 2-lane shape. (Pre-rerail.)
- `WIRE-DRIVE.md` — the 3-workflow wire-everything spine + voice root-cause + gate resolution.
- `FRONTEND-WIRING-EXIT-MAP.md` (W1) — 10 dead `tauri/ui` surfaces + new IPC types FE owns. (#3 voice-rocker SUPERSEDED — MOSS nuked, rocker deleted-not-built.)
- `BACKEND-WIRING-EXIT-MAP.md` (W2) — voice root-cause + 17 backend wires + per-lane /goal blocks. (MOSS-floor assumption SUPERSEDED.)
- `USER-READY-WIRING-EXIT-MAP.md` (W3) — the 5 cross-engine seams (A-E), fresh-user step-ladder, R1-R10 single-owner resolutions. (Seam A + E now DONE.)
- `CODEX_READY-CHATTERBOX-VOICE-WIRED.md` — the Chatterbox-Turbo MLX wiring (gated, green); the voice the lock builds on.
- `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md` — the Technologic robot-voice recipe + de-gap; ear-validated; streak-voice source.
- `PILL-FAFO-AND-LEVELUP.md` — streak-reality probe (proves the self-applause) + level-up opportunities.
- `CUE-LAND-ENGINE.md` — cue-landing engine design (provenance stamp, Viber auto-cue-on-export, `land()`); seeds W13.
- `NEXT-LANE-BLUEPRINT-cuetray.md` / `-keyfield.md` / `-masklearn.md` — designed-but-dark frontend lanes.
- `VIBEMIX-ORGANISM-DIRECTION.md` — the Kaan-LOCKED visual soul: one living particle organism, real curl-noise physics, animates only on real signals (visual grounding). Wire-not-rebuild.
- `UX-CRITIQUE-IMPECCABLE.md` — brutal-lens static UX/UI critique; a frontend build-it task.
- `MASTER-ARRANGEMENT-ULTRATHINK.md` — the 5-teardown rebuild thesis: engine ~70-80% real, human-facing layer dark = one grounding bug; 4 worktree lanes.
- `STATE-OF-ALL-LANES-EOD.md` — chief-organizer synthesis of 6 per-area reports, overclaims corrected.
- `NEXT-MOVES-VERIFIED.md` / `GOALS-NEXT-2026-06-04.md` — survivor opportunities re-verified vs HEAD + paste-ready /goal prompts.
- `MISSED-OPPORTUNITIES-SCAN-1.md` — HEAD-verified dark-gold/dead-wire/quick-win scan, ship-blocking vs post-ship filtered.
- `GOAL-engine.md` / `GOAL-sven.md` / `GOAL-learn.md` / `GOAL-frontend.md` / `GOAL-organism.md` — per-lane copy-paste /goals.
- `HANDOFF-SESSION2-FONTS-NEXTLANES.md` / `HANDOFF-SESSION3-KEYFIELD-DONE.md` / `FRONTEND-PURGE-ORGANISM-HANDOFF.md` — per-session frontend handoffs (KEYFIELD shipped, typeset closed, organism phase-2).
- `TODAY-GIT-DIGEST.md` — plain-language summary of the day's 110 commits.
- `CODEX-OPEN-QUESTIONS-HARDENED.md` / `RETASK-AND-RESEARCH.md` / `ARRANGEMENT-PROMPTS-LIVE.md` — open-question and re-task scaffolding.
- Cross-ref: `.planning/packets/2026-06-03/WIRE-THE-GOLD-MASTER-BACKLOG.md` — the prior work-queue; SUPERSEDED as live driver, but the KEEP-vs-FIX moat boundary + build-vs-wire census remain load-bearing reference.
