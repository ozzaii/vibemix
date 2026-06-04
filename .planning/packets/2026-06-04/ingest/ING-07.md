# ING-07 — INTEL → the SPOKEN line + ship done-claim verification

HEAD read at: **`d7d5337a`** (`test(config): isolate device defaults from rig env`), branch `ux-redesign-impeccable`, 2026-06-04.
Maps were synthesized at `7ac35a84`; the tree advanced 26 commits since (the voice + start-gate + learn + README loops landed in that window). Every line number below was re-pinned at `d7d5337a`.

Three proof tiers, never conflated: **SRC** (green tests on source) ≠ **PKG** (in a signed DMG built at HEAD) ≠ **LIVE** (a stranger reaches it). `test-passing-but-dark = 0`.

---

## TL;DR — the one finding that matters

**The START-GATE backend (locked decision #3) is implemented in the DIRTY WORKING TREE, NOT committed at HEAD.** Commit `23f3167d` landed only the frontend + IPC half and says so in its own body ("the backend lifecycle ... is the BACKEND-BOOT lane's ... NOT implemented (their island)"). The committed `__main__.py` at `d7d5337a` has ZERO start-gate symbols; the committed `tests/test_main_smoke.py` HAS the tests that require it (`test_smoke_03`, `test_smoke_03b_idle_is_cold_until_start`). So a fresh clone / a DMG built at committed HEAD would (a) lack the Start gate in `main()` and (b) FAIL those two committed smoke tests. The green state exists only in Kaan's local working tree. This is a clean-checkout / source-uncommitted gap — CI on the committed tree would catch it. **CLAIMED-BUT-DARK at the commit level, LANDED in the working tree.**

Everything else in the four locked decisions verifies as genuinely landed (committed) with the exceptions called out below.

---

## Locked decision #1 — VOICE (Chatterbox only, MOSS nuked) → LANDED (committed), SRC-green

| sub-claim | verdict | evidence |
|---|---|---|
| MOSS nuked | LANDED | `src/vibemix/agent/local_tts.py` DELETED; commit `fddddfc9 refactor(voice): retire legacy moss runtime` |
| `tts_chain` Chatterbox-only, no cloud/MOSS fallback | LANDED | `agent/tts_chain.py:38` raises `ChatterboxUnavailable` if `engine_selected()` false; no MOSS branch; commit `1a66cca0` |
| `mlx-audio` as a pyproject extra (Apple-only) | LANDED | `pyproject.toml:162` (`tts-local`) + `:167` (`ai-local`), both gated `sys_platform=='darwin' and platform_machine=='arm64'` |
| ref clip bundled via PyInstaller `datas` | LANDED | `vibemix-core.macos.spec:36` imports `collect_chatterbox_ref_datas`, `:307` `datas.extend(...)`; bundler `scripts/dist/chatterbox_bundle.py` exists; `agent/chatterbox_tts.py:93 bundled_ref_candidates()` reads `sys._MEIPASS` + exe-parent/`_internal` |
| `resolve_ref_path()` prefers bundled, falls back to dev-cache | LANDED | `agent/chatterbox_tts.py:106-116` (override → bundled → `_DEV_REF`) |
| first-run model fetch via `model_assets.py` + CLI | LANDED | `library/model_assets.py:490 install_chatterbox_model`, registered in the `--install chatterbox|all` CLI at `:857/:859`; repo `mlx-community/chatterbox-turbo-8bit` pinned rev `2f2e21a0` (`:34/:35`) |
| wizard prefetch trigger (download before first set, offline → voiceless) | LANDED | `runtime/wizard.py:436 await self._prefetch_chatterbox_model()`, impl `:499-535`, offline → "co-host starts voiceless" (`:528`); commit `0e5590c5`/`eec239ac` |
| env-seed `VIBEMIX_TTS_ENGINE` (launchd strips env) | LANDED | `__main__.py:1063` (packaged-defaults helper) AND `:1434` (boot), both `os.environ.setdefault(...)` from `cfg.tts_engine` |
| `DEFAULT_TTS_ENGINE="chatterbox"` config field | LANDED | `runtime/config_store.py:65` + `tts_engine` field `:248` + `normalize_tts_engine` `:69` |
| release gate swap `--require-moss-source` → `--require-chatterbox-source` | LANDED | `scripts/dist/pretag_check.sh:109/111/113` + `.github/workflows/release.yml:355/356/399/400/426/427/541/542`; flags implemented in `scripts/dist/check_sidecar_bundle_ready.py:335/336/428/432/453/461`; **ZERO lingering `require-moss` anywhere in `scripts/` or `.github/`** |

`chatterbox_available()` (`agent/chatterbox_tts.py:124`) honestly checks `mlx_audio` present + ref resolvable + model cached; `chatterbox_unavailable_reason()` (`:133`) returns an actionable string. Voiceless-but-honest path is real.

**Tier verdict:** SRC LANDED + committed. PKG = unverifiable read-only (mlx-audio must actually install on the build host; the model is first-run-fetched, not in the DMG — by design). LIVE = the keystone "stranger hears the cloned voice" has never been crossed (Kaan-only, by definition no autonomous lane).

**Note (factual drift, not a code bug):** the README still describes the voice as "MOSS" (see decision-policy section below) — the product is now Chatterbox; the README is stale + wrong.

---

## Locked decision #2 — BRAIN (hosted Bravoh proxy DEFAULT) → LANDED (committed), SRC-green

| sub-claim | verdict | evidence |
|---|---|---|
| client default flips direct→proxy | LANDED | `runtime/config_store.py:271 llm_mode: str = "proxy"`; commit `c0814c94 fix(boot): default fresh users to proxy brain` |
| no-key direct → proxy fallback (no crash) | LANDED | `__main__.py:1160-1166` (direct + no `GEMINI_API_KEY` → `mode = "proxy"`) |
| total brain failure degrades gracefully (no `sys.exit`) | LANDED | `__main__.py:1174-1179` sets `brain_unavailable_reason` on proxy setup/network failure, `_log_brain_unavailable(...)`, **no `sys.exit`**. The `sys.exit(3)` at `:1517/:1573` are MISSING-AUDIO-DEVICE (BlackHole / no output), not a brain crash; `sys.exit(...)` at `:1143` is an invalid `VIBEMIX_LLM_MODE` *value*, not a missing key |
| `set_brain` BYO handler wired (persist mode + write GEMINI key) | LANDED + committed | `runtime/session_loop.py:288 register_handler("ipc.settings.set_brain", ...)`, impl `:486 _on_settings_set_brain`; persists `llm_mode` + writes to `brain_env_path()`; committed HEAD has 5 `set_brain` markers (verified via `git show HEAD:...`) |

**Tier verdict:** SRC LANDED + committed. PKG n/a. LIVE = the "register→JWT→gemini-3.5-flash→HTTP 200 on api.altidus.world" claim is NOT verifiable read-only (no network probe; credits are a Kaan/Bravoh-ops flag). Accept as a same-day external claim, flag as unverified-here.

---

## Locked decision #3 — START GATE → CLAIMED-BUT-DARK (uncommitted), LANDED in working tree only

**The headline gap.** Decomposed:

| sub-claim | verdict | evidence |
|---|---|---|
| frontend Start/Stop button + optimistic repaint | LANDED + committed | `tauri/ui/src/session/render-loop.ts:76 emitIpc("ipc.session.start", {})`, `:89` stop; `data-runstate` armed/running CSS gate `SessionLayout.ts:428-477`, `:981/:1056`; click→optimistic flip→fire-wire (`render-loop.ts:74-89`); commit `23f3167d` (frontend half only, by its own body) |
| IPC schema `ipc.session.start` / `.stop` both ends | LANDED + committed | `tauri/ui/src/ipc/messages.schema.json:1440/:1463`; `messages.ts:324-330`; Python `ui_bus` mirror `SessionStart`/`SessionStop`; oneOf parity 81==81 (commit `23f3167d`) |
| backend `_on_session_start` handler in `session_loop.py` | **CLAIMED-BUT-DARK (uncommitted)** | working tree `session_loop.py:278/279` registers `ipc.session.start`/`.stop` → `_on_session_start`/`_on_session_stop` (`:331/:356`) calling injected `session_start`/`session_stop` callbacks (`:189/190`). **`git show HEAD:session_loop.py` = 0 `_on_session_start` markers; the diff adds them.** |
| `main()` idle boot + `_activate_session()` split | **CLAIMED-BUT-DARK (uncommitted)** | working tree `__main__.py:1704 _activate_session`, `:2172 _start_live_session`, `:2188 _stop_live_session`, `:2200 _silent_prewarm_hook` ("models still cold"), `:2248 _RunGatedMusicState` cold view, `:2275` banner "start gate: armed (idle...)". **`git show HEAD:__main__.py` = 0 start-gate symbols; the diff adds 6+.** |
| idle = cold (no heavy model resident until Start) | DESIGN-CORRECT (uncommitted) | TTS instance (`ChatterboxLocalTTS()`), LLM (`build_llm`), `AgentSession`, `DJCoHostAgent`, capture stream all constructed INSIDE `_activate_session` (`:1751`, `:1737/1742`, `:1811`); idle `main()` blocks at `:2277 await stop_event.wait()` running only ws-broadcast + parent-watch + import-only prewarm. Correct architecture — but in the working tree. |
| Stop releases | DESIGN-CORRECT (uncommitted) | `_activate_session` `finally:` `:2098-2148` (midi stop, agent tasks cancel, `session.aclose()`, `_close_tts_chain`, stream close) |
| committed tests REQUIRE the uncommitted impl | RED on clean checkout | `git show HEAD:tests/test_main_smoke.py` HAS `test_smoke_03` (`:668` sends `ipc.session.start`, `:673/:795` expects `session_started`) AND `test_smoke_03b_idle_is_cold_until_start` (`:800`). Both committed (commits `02ffb7c0`, `18dc95cb`). On the working tree: 6 start-gate tests PASS. Against committed source: they would FAIL (no handler, no `_activate_session`). |

**Tier verdict:** SRC = green ONLY on the dirty working tree; the COMMITTED HEAD is internally consistent-but-gateless (committed `session_loop.py` and committed `__main__.py` BOTH lack the gate, so a clean checkout imports fine — `tests/repo/test_clean_checkout_imports.py` would pass — but the committed `test_smoke_03/03b` would FAIL). PKG = blocked: `check_sidecar_bundle_ready.py:298 source_dirty_paths` will reject the build because `__main__.py` + `session_loop.py` are dirty. LIVE = unreachable.

**Action for the organizer:** commit the dirty `__main__.py` + `session_loop.py` start-gate seam BEFORE any sidecar/DMG build or any "tests green" claim. This is the #1 PKG blocker, ahead of even voice reachability now (voice fully committed; start-gate is not).

---

## Locked decision #4 — STREAK (Daft-Punk robot voice, sequenced) → NOT-STARTED (correct)

No robot-voice live wiring found in the spoken path; the self-applause streak (`runtime/suggestion.py` grade-progress) is still the only signal and must be re-grounded onto a cited EXECUTED transition first (per the lock). Correctly deferred; not a v1-launch blocker. NOT-STARTED, as intended.

---

## INTEL → the SPOKEN line (the narrator→coach gap) — the core ING07 question

The live spoken path is: `event_detector` event → `coach_loop` (`runtime/coach.py:525`) decorates `ev.extra` with voice-line receipts → `dj_cohost.py llm_node` builds the prompt + the post-generation scrubber `apply_live_claim_guard` (`state/deck_context.py:2999`, called `dj_cohost.py:3629`). For each engine, "reaches-spoken-line?":

| engine | reaches spoken line? | how / why-dark | file:line | verdict |
|---|---|---|---|---|
| **`eq_move_model`** (keystone narrator→coach unlock) | **YES** | `apply_live_claim_guard` uses `canonical_eq_move` + `_eq_move_current_state_supports` to KEEP a grounded EQ-move claim and STRIP an ungrounded one (post-generation guard) | `state/deck_context.py:19` import, `:2083/:2177/:3304/:3364`; guard call `agent/dj_cohost.py:3629` | LANDED + committed |
| **`transition_judge`** (Vibe Judge) via `judge_evidence_line` | **YES but rig-dark** | `coach.py:1040` runs the Judge ONLY when `deck_audio_capture is not None AND tag=="TRACK_CHANGE"`; verdict → `verdict_evidence_line` → `judge_voice_lines[0]` → `ev.extra["judge_evidence_line"]` (`:1059`) → prompt (`prompt_builder.py:809/832`) + guard (`dj_cohost.py:3313/3636`). On the DEFAULT master-only rig `deck_audio_capture` is `None` (`__main__.py:1543` only builds `DeckAudioCapture` when `routing.enabled or opened_channels != 2`) → the Judge **never fires live** | `coach.py:458 (run fn)`, `:1040 (call-site)`; `__main__.py:1543` | LANDED-but-DARK on default rig (W8 = abstains/never-fires) |
| **`transition_scorer` reasons / `score_transition_slate`** | **CONDITIONAL** | NOT directly in the spoken path. BUT the pill's scored payload reaches the spoken line via `build_transition_verdict_voice_line` (`runtime/transition_verdict_voice.py:27`), called `coach.py:880`, stuffed into `ev.extra["transition_verdict_voice_line"]` (`:886`) → prompt (`prompt_builder.py:808`). It surfaces `transition.reasons` + score + role/key clauses — but ONLY on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY`, two-deck, confidence ≥ `LIVE_SELECT_CONFIDENCE_FLOOR`, citable. Single-deck/master-only → no verdict voice. | `transition_verdict_voice.py:27`; `coach.py:880`; consumers of `score_transition_slate` = `next_suggestion.py`/`toolset.py`/`context_compiler.py` (PILL/set-prep, not the live line) | PARTIAL — pill payload reaches voice when two-deck + grounded; bare-rig dark (W9) |
| **`move_grade` / `grade_transition` verdict** | **NO** | ZERO references in `prompt_builder.py`, `coach.py`, `dj_cohost.py`. Consumers = `intel/context_compiler.py`, `intel/move_grade.py`, `library/next_suggestion.py`, `library/toolset.py` — all pill/set-prep | (none in spoken path) | DARK — pill-only (W9) |
| **`judge.risk_flags`** (harmonic_clash / bass_collision) | **INDIRECT-ONLY** | Raw `risk_flags` never reach the spoken line directly. They surface as a citation tail via `transition_verdict_voice.py::_register_first_risk_citation` (from the PILL suggestion payload, not the live Judge). The live `transition_judge` computes risk_flags but the coach loop only carries `judge_evidence_line` (a verdict line), not raw flags. Consumers = `runtime/suggestion.py`, `suggestion_voice.py`, `transition_verdict_voice.py`, `next_suggestion.py`, `auto_crate.py` | `transition_judge.py:71`; verdict-voice citation `transition_verdict_voice.py` | DARK as a direct "you clashed the keys" line (W11); reaches voice only as a citation tail when the pill payload carries it |

**Net narrator→coach verdict:** the asymmetry the maps named is real and accurate. Two engines speak directly: `eq_move_model` (always, via the post-gen guard) and `transition_judge` (only with per-deck routing + TRACK_CHANGE). The rich scorer/grade/risk intel reaches the spoken line ONLY through the pill's `next_suggestion` payload via the two `*_voice_line` builders (`transition_verdict_voice` + `suggestion_voice`), and ONLY when two-deck + confident + grounded. On Kaan's documented default master-only single-mix rig, NONE of the transition intel speaks (Judge `None`, verdict-voice fails two-deck check) — so live, the EQ-move guard is effectively the only intel→voice path that fires. That is the gap to close for "coach, not narrator" on the bare rig.

---

## Adjacent done-claims verified

| claim | verdict | evidence |
|---|---|---|
| **Citation ts-carry / Seam D** (commit `d67e6f81`) | LANDED + committed | `dj_cohost.py:1880 _push_transcript(*, ts=None)`; `:4081 reaction_msg_ts` taken from `SessionCohostReaction.make(...)`'s own `ts` (the same message that carries `citation_strip`); `:4163 _push_transcript(..., ts=reaction_msg_ts)`. `ws_bus.py:786` preserves `item.get("ts")`. The transcript_delta and the cohost-reaction now share one ts → the FE join (`SessionLayout.ts:1171`) can byte-match live. |
| **W12 — `[ev:BEATMATCH_GRADED]` into live credit** (commit `8c0c0ffa`) | LANDED + committed | `runtime/coach.py:264 _credit_live_beatmatch_grade_receipts`, called in the live loop `:643`, 2.0s freshness (`:113/:309`), routes through `_credit_live_skill_demo` (`:324`) honoring Inv #2/#3. The map's "0 references in coach.py" is now STALE — wired. |
| **W13 — Viber auto-cue through `cue_landing.land()`** (commit `4831b226`) | LANDED (claimed) | commit `4831b226 fix(library): route Viber auto-cues through cue landing spine` exists; not deep-verified here (out of ING07 scope), flag for the library lane. |
| **CI RED gate: `test_no_api_key_surface` scoped to BYO** (commit `ae30e16e`) | LANDED | `tests/security/test_no_api_key_surface.py:59 ALLOWED_BYO_KEY_SURFACE = "tauri/ui/src/settings/components/brain-group.ts"`, D2 scope `:7/:134`. |
| **CI RED gate: README footer re-pin to bravoh.ai** (commit `aaa330ad`) | LANDED | `tests/repo/test_readme_shape.py:101` asserts `bravoh.ai/vibemix?utm_source=github`, `:102` asserts `altidus.world/vibemix` ABSENT; `test_readme_feature_matrix_sync.py:104`. |
| **R10 — recorder → evidence_registry** (`evidence_registry.json` for debrief) | **STILL DARK** | `audio/recorder.py:198` accepts `evidence_registry=`, writes `evidence_registry.json` on finalize (`:549-561`), BUT `__main__.py:1274 VoiceRecorder(root=recordings_root)` omits the kwarg and nothing attaches it post-construction. The `evidence_registry=` at `__main__.py:2236` is the SessionLoop, NOT the recorder. So `evidence_registry.json` is never written → debrief drill citations `found=false` on long sessions. The map's R10 is unresolved. |

---

## PKG / README — partner-copy policy = CLAIMED-BUT-DARK (CI green, policy violated)

The footer link IS `bravoh.ai` (the CI gate only checks the footer), so the gate PASSES — but the README BODY violates the public-facing policy throughout. This is a clean "test-passing-but-dark" inversion for the README:

- **Leaks `api.altidus.world`** (policy: never expose; say "Bravoh's hosted service"): `README.md:39, 61, 241, 259`.
- **Names "Gemini"** (policy: "AI model"): `README.md:39, 149, 241, 259, 269, 271, 283, 287`.
- **Names "MOSS" as the voice** (policy: "on-device voice" — AND factually WRONG, MOSS is nuked, voice is Chatterbox): `README.md:229, 241, 271`.
- **`security@bravoh.com`** (policy: domain is `bravoh.ai`): `README.md:63`.
- **`github.com/ozzaii/vibemix`** (policy: org is `Bravoh-ai`): `README.md:330` (also `pyproject.toml:182-184` URLs still `ozzaii`).
- **Dev feature-matrix dump / internal slop**: Phase numbers + "SHIPPED" + "Kaan ear-passes daily" (`:69`) + "KAAN-ACTION" (`:10, 30, 86, 135, 198`) across the feature-matrix table (`:134-149`).

The 4 README CI gates (`test_readme_shape.py`, `test_readme_feature_matrix_sync.py`, `scripts/launch/check_readme_grids_a11y.py`, `scripts/check_readme_hero_hash.py`) do NOT enforce these policy items, so they pass green while the README is partner-unsafe. **README rewrite is a real pre-public-launch task; CI-green is not proof of policy compliance here.**

---

## PKG / tag landmine status

- Local tags: `v0.1.0-rc1` exists (an old rc). **No `v0.1.0` GA tag** — the GA landmine (`release.yml` + `companion-sign.yml` fire on a `v*` push → full signed matrix incl. Windows + SignPath) has NOT been triggered. Good. The `0.1.0` non-`v` source-snapshot pre-release noted in the maps is a GitHub release tag (not in local `git tag`), benign (SBOM job only).
- **Dirty seam files at HEAD**: `__main__.py`, `runtime/session_loop.py`, `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts` (+ untracked `docs/launch/.build_talking.py`). The first two carry the entire uncommitted start-gate; `check_sidecar_bundle_ready.py:298 source_dirty_paths` will fail the freshness gate until they commit. **No fresh HEAD signed arm64 DMG is buildable until the start-gate seam commits.**
- v1 scope = macOS arm64 only (D3 resolved); Windows/Intel binaries are `.placeholder` (PKG=0) — off the v1 critical path with `VIBEMIX_PRETAG_MAC_ONLY=1`.

---

## Verified next-move ordering (what the organizer should sequence)

1. **COMMIT the start-gate seam** (`__main__.py` + `session_loop.py`) — it is the #1 PKG blocker now; it un-fails the committed `test_smoke_03/03b` and clears the sidecar-freshness gate. Voice is already fully committed; the start-gate is the laggard. (keystone/backend-boot lane, single-owner `__main__.py`.)
2. **R10 one-kwarg wire** — `VoiceRecorder(root=recordings_root, evidence_registry=evidence_registry)` at `__main__.py:1274` so `evidence_registry.json` is written and debrief citations resolve. Still dark; trivial.
3. **Narrator→coach on the bare rig** — the EQ-move guard is the only intel→voice path that fires on master-only. Closing W8 (Judge on master-only) or W9 (scorer/grade voice without a two-deck requirement) is the substantive "coach not narrator" work; both currently gate on per-deck routing the default rig lacks.
4. **README partner-copy rewrite** — CI-green ≠ policy-safe; MOSS reference is also factually stale.
5. Keystone LIVE capture + DMG sign/notarize remain Kaan-only (no autonomous lane).

## Verdict legend recap

- VOICE #1 = **LANDED + committed** (SRC); PKG/LIVE = Kaan-gated.
- BRAIN #2 = **LANDED + committed** (SRC); proxy-live = unverified-here.
- START GATE #3 = **CLAIMED-BUT-DARK at commit level** (impl in dirty working tree only); the single most important verification finding.
- STREAK #4 = **NOT-STARTED** (correct).
- eq_move_model → spoken = **LANDED**; transition_judge → spoken = **LANDED-but-rig-dark**; scorer/grade/risk → spoken = **PARTIAL/DARK** (pill-mediated, two-deck-gated).
- citation ts-carry, W12 = **LANDED + committed**; R10 = **still DARK**; README policy = **CLAIMED-BUT-DARK** (CI green, policy violated).
