## ING06 — LIBRARY + cue moat + locked-decision adversarial verification

**HEAD read at:** `d7d5337a175ac90612702c3adda4d17aa3918899` (branch `ux-redesign-impeccable`, 2026-06-04). The maps (`SHIP-MAP-MASTER.md`) were synthesized at `7ac35a84`; the tree advanced ~since with the voice/start-gate/packaging build-loops. Every line number below re-pinned at this HEAD.

**Proof tiers (never conflated):** SRC = green test on committed source · PKG = inside a signed DMG built at HEAD · LIVE = a stranger reaches it. `test-passing-but-dark = 0`.

**Working-tree caveat that drives the #1 finding:** `src/vibemix/__main__.py` (+733 lines) and `src/vibemix/runtime/session_loop.py` (+70 lines) are DIRTY (uncommitted). A large slice of the START-GATE backend and the packaged-defaults env-seed lives ONLY in the working tree, NOT at committed HEAD. Adversarial verdicts below distinguish HEAD-committed from dirty-only.

---

### HEADLINE

The 4 locked decisions are mostly real in source, with one decisive exception:

1. **VOICE (Chatterbox-only, MOSS nuked):** LANDED at SRC, including reachability on this dev machine. The map's "#1 blocker = mlx_audio not installed / not an extra" is RESOLVED.
2. **BRAIN (proxy default + set_brain + no-key graceful):** LANDED at committed HEAD, all three halves.
3. **START GATE:** frontend + IPC schema LANDED + committed; **backend handler is CLAIMED-BUT-DARK at HEAD** — `_on_session_start`/`_on_session_stop` register and the `main()` idle/activate split exist ONLY in the uncommitted working tree. On a fresh checkout the Start button fires an envelope NO backend handler receives. This is the single biggest test-passing-but-dark trap in this pass.
4. **STREAK (Technologic robot voice, sequenced):** NOT-STARTED, correct per decision.

Library + cue moat is the healthiest subsystem and is genuinely LIVE end-to-end at SRC. README still violates the partner-copy policy on body copy (Gemini/altidus/MOSS leaks) while all 4 README CI gates are GREEN — the gates do not enforce that policy.

---

### DECISION 1 — VOICE (Chatterbox the ONLY voice; MOSS nuked; mlx-audio Apple-only; voiceless+banner on no-GPU)

| sub-claim | verdict | evidence |
|---|---|---|
| MOSS nuked from source | LANDED (SRC) | `src/vibemix/agent/local_tts.py` DELETED (gone on disk + in git diff `7ac35a84..HEAD`, -546). `agent/moss_tts/` holds only an empty `__pycache__`. `config_store.py:65 DEFAULT_TTS_ENGINE="chatterbox"`, `:66 _SUPPORTED_TTS_ENGINES=frozenset({"chatterbox"})`. |
| tts_chain Chatterbox-only, no cloud/MOSS fallback | LANDED (SRC) | `agent/tts_chain.py:38` raises `ChatterboxUnavailable` if `engine_selected()` false; no MOSS branch, no cloud key path; doc states "cloud TTS keys are intentionally ignored". |
| mlx-audio as a pyproject extra (Apple-arm64-gated) | LANDED (SRC) | `pyproject.toml`: extra `tts-local` (`:160-162`) AND folded into `ai-local` (`:164-167`): `"mlx-audio>=0.3; sys_platform=='darwin' and platform_machine=='arm64'"`. The app/installer build uses `--extra ai-local` (per `vibemix-core.macos.spec:144`). |
| bundle `cohost_voice_ref.wav` via PyInstaller datas + resolve_ref prefers bundled | LANDED (SRC) | `vibemix-core.macos.spec:307 datas.extend(collect_chatterbox_ref_datas())`; helper `scripts/dist/chatterbox_bundle.py:30 collect_chatterbox_ref_datas()`, dest `models/chatterbox/cohost_voice_ref.wav`. `chatterbox_tts.py:106 resolve_ref_path()` prefers REF_ENV override → bundled (`_MEIPASS`/exe-parent, `:93 bundled_ref_candidates`) → dev cache `~/.cache/vibemix/cohost_voice_ref.wav`. |
| first-run model fetch via model_assets + wizard trigger | LANDED (SRC) | `library/model_assets.py:490 install_chatterbox_model()`; repo `mlx-community/chatterbox-turbo-8bit` (`:34`) with PINNED revision `2f2e21a0…` (`:35`). Wizard fires it: `runtime/wizard.py:436 await self._prefetch_chatterbox_model()` (on `_on_wizard_done`) → `:506 install_chatterbox_model` in a thread, fail-soft, emits `voice_status` muted/ok. |
| env-seed `VIBEMIX_TTS_ENGINE` at __main__ | PARTIAL (HEAD) / LANDED (dirty) | HEAD has ONE seed only: `__main__.py:1428 os.environ.setdefault("VIBEMIX_TTS_ENGINE", _tts_engine_seed)` inside `main()`. The launchd/Dock-surviving seed in `_apply_packaged_defaults()` is DIRTY-ONLY — committed HEAD `_apply_packaged_defaults` still `return None` (verified via `git show HEAD`). The packaged-launch (`open -a`/Dock strips VIBEMIX_*) path therefore relies on the dirty hunk. |
| release gate swap `--require-moss-source` → `--require-chatterbox-source` | LANDED (SRC) | `scripts/dist/pretag_check.sh:109/111/113` now `--require-chatterbox-ref --require-chatterbox-source`. `.github/workflows/release.yml:355/356, 399/400, 426/427, 541/542` all swapped. `grep require-moss` = 0 hits anywhere. |
| CLI `library models --install chatterbox\|all` | CLAIMED-BUT-DARK (minor) | `install_models()` accepts `{required,clap,chatterbox,cue,all}` (`model_assets.py:840`), and `--install all` would route chatterbox (`:855-859`). BUT the CLI argparse `choices=("clap","cue")` (`__main__.py:4816`) BLOCKS `chatterbox`/`all`/`required` from ever reaching it. The CLAUDE.md doc claims `--install clap\|cue\|all` — `all` isn't even a choice. NOT ship-blocking: the wizard calls `install_chatterbox_model()` directly, so the fresh-user voice fetch still works; only the CLI affordance is dark. |

**Reachability on this dev machine (the map's #1 blocker, re-tested):** `importlib.util.find_spec('mlx_audio')` = present in `.venv`; ref clip present (`~/.cache/vibemix/cohost_voice_ref.wav`, 384k); `mlx-community/chatterbox-turbo-8bit` cached in HF hub. So `chatterbox_available()` returns True HERE. The map's "voiceless on every launch" is STALE for SRC/dev — it was true before the extra/spec/wizard landed. **Remaining gap is PKG/LIVE only:** unverifiable read-only (no DMG build, no rig). A fresh DMG must bundle deps via `--extra ai-local` (spec confirms `mlx`/`mlx_audio`/`mlx_lm` hiddenimports `:152/186`) and a stranger's machine must complete the first-run HF fetch.

**Voice tests SRC verdict:** `tests/agent/test_chatterbox_tts.py` + `test_tts_chain.py` + `tests/install/test_chatterbox_bundle_data.py` + `tests/library/test_cue_landing.py` = 29 passed. Dark-but-green risk: the LiveKit plumbing is testable via the `ChatterboxEngine` seam (`chatterbox_tts.py:146`) WITHOUT mlx-audio, so SRC-green does not prove a real `mlx_audio.load_model` synth — that is the keystone LIVE capture (Kaan).

**VOICE overall: LANDED at SRC (incl. dev reachability). PKG/LIVE = unverified. One dirty-only env-seed + one minor CLI gap.**

---

### DECISION 2 — BRAIN (hosted Bravoh proxy DEFAULT; client flips direct→proxy; set_brain BYO; no-key graceful, no sys.exit)

| sub-claim | verdict | evidence |
|---|---|---|
| client default = proxy | LANDED (SRC, HEAD) | `config_store.py:271 llm_mode: str = "proxy"`. `__main__.py:1136` reads persisted `llm_mode` default "proxy", `:1138` excepts to "proxy". |
| no-key direct → proxy fallback (no crash) | LANDED (SRC, HEAD) | `__main__.py:1157-1166`: mode==direct + no `GEMINI_API_KEY` → prints "trying Bravoh proxy", `mode="proxy"`. No `sys.exit` on missing key. The `sys.exit` at `:1143` is invalid-mode-string only; `:1517/:1573` are BlackHole/audio-fatal; `:2566` is the opt-in OpenRouter path. |
| total brain failure degrades to banner | LANDED (SRC, HEAD) | `__main__.py:1169-1181`: proxy register/jwt failure → `brain_unavailable_reason` set + `_log_brain_unavailable(...)`, no crash. Proxy base `https://api.altidus.world` (`:1139`). |
| set_brain BYO handler wired (committed) | LANDED (SRC, HEAD) | `git show HEAD:session_loop.py` contains `_on_settings_set_brain` (count 2). Registered `session_loop.py:288 register_handler("ipc.settings.set_brain", self._on_settings_set_brain)`. Persists `llm_mode` + writes key to `brain_env_path()` per map. |

**BRAIN overall: LANDED at committed HEAD, all halves. Proxy credits/rate-cap are a Bravoh-ops flag (not a code wire, unverifiable read-only).**

---

### DECISION 3 — START GATE (SHIP-CRITICAL: idle=cold, Start button, silent pre-warm, Stop releases)

This is the decisive adversarial finding.

| seam | verdict | evidence |
|---|---|---|
| IPC schema `ipc.session.start`/`.stop` | LANDED (committed) | `messages.schema.json:1430-1463` (both consts). `git show HEAD:messages.schema.json` count=2. |
| FE generated types + emit | LANDED (committed) | `git show HEAD:messages.ts` count=1 (`:325 type:"ipc.session.start"`); `SessionLayout.ts` HEAD count=2 (`:974` onStop fires `ipc.session.stop`, `:1053` onStart fires `ipc.session.start`, optimistic repaint). `session/state.ts:195-266` armed/running state machine. |
| FE Start button + armed/running state | LANDED (committed) | `tauri/ui/tests/session/start-gate.spec.ts` (committed `23f3167d`): boots armed → `data-runstate="armed"`, Start click flips to running optimistically + fires onStart once. |
| **backend handler `_on_session_start`/`_on_session_stop`** | **CLAIMED-BUT-DARK (HEAD)** | `git show HEAD:session_loop.py` grep `_on_session_start` = **0**; grep `ipc.session.start` register = **0**. The handlers (`session_loop.py:331/356`), `_session_active` (`:322`), and the `register_handler("ipc.session.start"…)` (`:278-279`) exist ONLY in the DIRTY working tree (`grep` working-tree = 3). |
| **main() idle/activate split + lifecycle wiring** | **CLAIMED-BUT-DARK (HEAD)** | `git show HEAD:__main__.py` grep `_start_live_session\|_activate_session` = **0**. Working tree has `_activate_session` (`:1704`), `_start_live_session` (`:2172`), `_stop_live_session` (`:2188`), `_silent_prewarm_hook` (`:2200`, imports-only, models stay cold), and `SessionLoop(… session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active)` (`:2225-2241`), plus a `_RunGatedMusicState` gating state by active and `brain_available` gated by `_is_live_session_active`. None of this is at committed HEAD. |

**START GATE overall:** frontend half is committed and SRC-green; **backend half exists only in the uncommitted working tree.** At a fresh checkout of `d7d5337a`, pressing Start sends `ipc.session.start` to a bus with no registered handler — a silent one-ended dead wire (the exact failure class an IPC-wiring check exists to catch). The implementation is real and well-shaped in the working tree (idle=cold, prewarm=imports-only, Stop releases), but it MUST be committed before it is anything but DARK at SRC. Both dirty files parse cleanly (`ast.parse` OK on HEAD and working tree), so it is a coherent WIP, not broken — just uncommitted.

---

### DECISION 4 — STREAK (Daft-Punk Technologic robot voice, SEQUENCED behind rebinding to a cited EXECUTED transition)

NOT-STARTED, which is correct per the lock. The streak still grades its own un-played suggestion (`runtime/suggestion.py` `_attach_grade_progress`, per map W7/R7 — self-applause, Invariant #3 risk). The robot-voice recipe is designed in `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`. Do not ship the robot voice on the present self-applause signal; the rebind to a cited executed transition is the prerequisite. No regression; matches the locked sequencing.

---

### LIBRARY + CUE MOAT (the ING06 subject) — the healthiest subsystem, LIVE end-to-end at SRC

| component | verdict | evidence |
|---|---|---|
| CLAP ONNX 512-dim embedder | LANDED (SRC) | `library/clap_engine.py:2` "local on-device CLAP audio/text embedder (512-dim)", `onnx` default backend (Xenova/larger_clap_music_and_speech), deterministic. |
| sqlite-vec vec0 search | LANDED (SRC) | `library/index_sqlite_vec.py:23 import sqlite_vec`, `:57 sqlite_vec.load`, `:60-62 CREATE VIRTUAL TABLE … vec0(embedding FLOAT[512] distance_metric=cosine)`. `store.py:62 search_centered` (mean-centered anisotropy fix), `:154 open_store(prefer_sqlite_vec=True)` with NumpyStore fallback. CLI uses `open_store` at `__main__.py:2777/5734/8692`. |
| CUE-DETR ONNX producer (torch-free) | LANDED (SRC) | `library/cue_detr.py:7` "NO torch at inference time", lazy heavy deps, `:78 model_status()`, model at `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx` / `VIBEMIX_CUE_ONNX_PATH`. |
| SmartCue slot/provenance policy | LANDED (SRC) | `library/smart_cues.py:77 SmartCue` with `slot` + `provenance_ref` (`:81/:93`); A-H slot semantics. `propose_smart_cues` is the producer. |
| non-destructive carriers, NO direct-DB write | LANDED (SRC) | `cue_landing.land()` routes to `export_rekordbox.export_set` (XML), `cue_folder.write_m3u8`, `export_serato.write_serato_cues` (opt-in file tags, `allow_write=True`). No SQLCipher/collection.db write path. |
| **VM provenance leak closed** | LANDED (SRC) | `library/cue_provenance.py:16 VM_CUE_PREFIX="VM "`, `:44 provenance_stamped_cue_name` idempotently stamps machine cues (`INTRO`→`VM INTRO`), DJ cues unstamped. Tests: 7 passed (`pytest -k provenance`). |
| Viber auto-cue-on-export default-ON | LANDED (SRC) | `library/toolset.py:984 auto_cue_enabled = bool(args.get("cue", args.get("auto_cue", True)))` — defaults True. Fires `_auto_cue_marks_for_export` (`:1002`), reports per-track (`:1013-1017`), receipt carries `auto_cues` (`:1114/:1729`). |
| auto_crate.py wired end-to-end | LANDED (SRC, FE-wired) | `library/auto_crate.py:76 build_auto_crate`, `:27 AutoCrateResult`. Tauri cmd `library_cmds.rs:935 library_auto_crate`, registered `main.rs:110`, called by FE `tauri/ui/src/library/api.ts:2736 invoke("library_auto_crate", …)`. CLI subparser `__main__.py:4499`. Tests: `test_auto_crate.py` + `test_smart_cues.py` = 21 passed. |

**W13 — does live Viber auto-cue route through `cue_landing.land()`?** DELIBERATELY NO, by design (this resolves the open question). `toolset.py:2236 _auto_cue_marks_for_export` now imports and composes `cue_landing`'s shared building blocks (`cue_set_from_proposal`, `export_marks_for_cueset`, `sections_from_anchors` at `:2242/:2257`) instead of a hand-rolled spine — commit `4831b226 "route Viber auto-cues through cue landing spine"`. It does NOT call `land()` itself: the `cue_landing.py:387-389` docstring is now load-bearing — `export_marks_for_cueset` is "the write-free half of `land()`. Viber's live export_set path needs the exact same provenance checks/slot labels … but it must not call `land()` itself and write a second [copy]." So the divergence risk the map flagged (two spines that "agree today but can diverge") is now mitigated: both paths share the same projection/provenance code; only the write side differs (Viber writes via `export_set`, `land()` writes via its carrier dispatch). Verdict: W13 RESOLVED-by-design, NOT a literal `land()` consolidation. The map's "5 callers all tests" is STALE — `land()` now has a real non-test caller (`__main__.py:8476`, the `library land-cues` CLI verb `_cmd_library_land_cues`).

**Cue Tray backend (`library_land_cues` Tauri cmd + CueSet summary/target/floor fields):** BACKEND-LANDED, FRONTEND-DARK.
- `cue_landing.land()` (`:290`) — full verb, all 3 carriers (rekordbox_xml/m3u8/serato_tags), permission-gated (`:292 requires_permission and not granted` → PermissionError). LANDED.
- Python CLI verb `library land-cues` — subparser `__main__.py:4369`, handler `_cmd_library_land_cues` (`:8471`): reads a CueSet JSON packet, `cue_set_from_dict`, resolves target from `cueset.detected_target`, calls `land(… granted=…)`, returns receipt. LANDED.
- Tauri cmd `library_land_cues` — `library_cmds.rs:1041` (writes packet via `:301 write_land_cues_packet`, calls Python `library land-cues`), registered `main.rs:112`. LANDED.
- CueSet fields the ING asked about: `cue_landing.py:85 CueSet` has `summary: CueSetSummary` (`:71`, full counts incl. `export_ready_count`/`review_count`/`missing_required_count`), `detected_target: TargetKind` (the "target"), `policy_floors: CuePolicyFloors` (the "floor"). LANDED.
- **DARK seam:** NO frontend caller. `grep -rn "library_land_cues\|landCues\|CueTray" tauri/ui/src` = 0 hits; `api.ts` has no `land` invoker. The Cue Tray A-H slot ladder GUI does not exist; the backend ladder is fully wired and waiting. So Cue Tray = BACKEND LANDED end-to-end (FE can call it tomorrow), FRONTEND NOT-STARTED.

---

### CI GATES (the ING06 partner-copy + README pins)

| gate | result | finding |
|---|---|---|
| `tests/repo/test_readme_shape.py` | GREEN (with `test_readme_feature_matrix_sync.py`, 53 passed) | Asserts footer `bravoh.ai/vibemix?utm_source=github` present and `https://altidus.world/vibemix` ABSENT (`:101-102`). The map's "RED gate asserts altidus.world/vibemix in README" is STALE/RESOLVED — the bravoh.ai swap landed for the footer/link. |
| `tests/repo/test_readme_feature_matrix_sync.py` | GREEN | `:102-104` comment EXPLICITLY allows `api.altidus.world` proxy references "in privacy/FAQ copy" — so the gate does NOT forbid the body-copy altidus leaks. |
| `scripts/launch/check_readme_grids_a11y.py` | PASS (exit 0) | DJ-software grid 6 cells + controllers grid 10 cells locked to `midi/profiles`. |
| `scripts/check_readme_hero_hash.py` | PASS (exit 0) | hero sha256=PLACEHOLDER sentinel, pending Kaan ASSETS-DEMO-CUT. |
| `tests/security/test_no_api_key_surface.py` (D2) | GREEN (4 passed) | The map's "RED — conflicts with BYO key field" is STALE/RESOLVED; already reconciled. |

**README partner-copy policy = VIOLATED on body copy while all 4 gates are GREEN (test-passing-but-dark).** Concrete violations at HEAD `README.md`:
- Leaks `api.altidus.world`: lines 39, 61, 241, 259 ("Bravoh's Gemini proxy at `api.altidus.world`"). 3 raw `altidus.world` hits.
- Names "Gemini"/"Google Gemini": lines 39, 149, 241, 259, 269 ("Why Gemini and not GPT…").
- STALE "MOSS": lines 229, 241 ("local MOSS voice path", "Speech is rendered locally through the MOSS voice path") — contradicts decision 1 (MOSS nuked, Chatterbox is the voice).
- `security@bravoh.com` (line 63) — should be bravoh.ai.
- Dev feature-matrix dump: Phase numbers + SHIPPED dates + "Kaan ear-passes daily" (line 69) + KAAN-ACTION (lines 11, 30, 86) + the whole `| 104 | … |` … `| 80 |` matrix (lines 134-149).
The "README→bravoh.ai swap" the maps reported as LANDED is PARTIAL: footer/link swapped (14 bravoh.ai hits), but the policy-violating body copy persists and no gate enforces it. Owner-call: the policy needs either README edits or a new CI gate; it is NOT shippable partner copy as-is.

---

### GA-TAG LANDMINE (re-verified at HEAD)

- `release.yml` still triggers on `push` of a `v*` tag (`:57-60 tags: ['v*']`) with the FULL matrix incl. `windows-latest` (`:12`) + SignPath (`:20-21`). The `--require-moss-source` gate IS swapped to `--require-chatterbox-source` (good), but Windows + SignPath are still armed on a v-tag.
- `VIBEMIX_PRETAG_MAC_ONLY=1` suppresses only the LOCAL `pretag_check.sh` SignPath gate (`:148`) — it does NOT alter `release.yml`. A real `v*` push still spins the Windows/SignPath jobs.
- Tag state: `v0.1.0-rc1` exists and IS pushed — but to `origin` (`ozzaii/vibemix`), pointing at OLD commit `905b24b5` (2026-05-13, pre-chatterbox/Windows). The dangerous repo is `bravoh` (`Bravoh-ai/vibemix`) where `main` was pushed; a `v*` tag pushed THERE fires the matrix. v10.0 tag also present (legacy).
- Verdict: landmine ACTIVE. Do NOT push `v0.1.0` to `bravoh` until START-GATE backend commits, the dirty packaged-defaults env-seed commits, Windows is excluded from the `release.yml` matrix (or scoped + secrets present), and the keystone voice capture passes (Kaan).

---

### CORRECTIONS TO THE MAPS (`SHIP-MAP-MASTER.md` @ 7ac35a84)

1. STALE: "#1 blocker = mlx_audio not installed / not a pyproject extra → chatterbox_available()=False forever." RESOLVED — extra `tts-local`/`ai-local` landed, ref bundles via spec, model auto-fetches via wizard; True on the dev machine. Remaining gap is PKG/LIVE only.
2. STALE: map row "`cue_landing.land()` — 5 callers all tests." Now has a real non-test caller `__main__.py:8476` (the `library land-cues` CLI). W13 is RESOLVED-by-design (shared building blocks; deliberate no-double-write), not "tested-but-unused."
3. STALE: map "START-GATE backend handler still DARK" understated — it is now FULLY WRITTEN but UNCOMMITTED (working-tree only), so it is dark at SRC/HEAD, not merely "schema landed, backend absent." Same for the launchd-surviving env-seed (dirty-only).
4. STALE: the 4 README RED gates + the `test_no_api_key_surface` RED the map flagged as blocking a tag are all GREEN at HEAD. The real README problem is the OPPOSITE: gates are green but partner-copy policy is unenforced and violated.
5. NEW: CLI `library models --install` choices are `("clap","cue")` only — `chatterbox`/`all` are blocked at argparse despite `install_models()` supporting them. Minor (wizard covers the fresh-user path).

---

### SHIP-CRITICAL TODO (ordered, from this verification)

1. **COMMIT the START-GATE backend + the dirty packaged-defaults env-seed.** Until `__main__.py` + `session_loop.py` commit, decision 3 is DARK at SRC and the launchd-stripped voice seed is missing — both invisible on a fresh checkout / DMG. (Kaan/keystone-lane; single-owner `main()`.)
2. **README partner-copy pass** — strip `api.altidus.world`/Gemini/MOSS/bravoh.com/dev-matrix from body copy (or add a CI gate). Currently green-but-non-shippable.
3. **Exclude Windows from `release.yml` matrix** (or wire secrets) before any `v*` tag to `bravoh`. The mac-only flag does not protect the CI matrix.
4. **PKG/LIVE proof of voice** (Kaan-only): build a fresh signed arm64 DMG that bundles `--extra ai-local` + the ref, confirm a stranger's first-run HF fetch lands `chatterbox-turbo-8bit`, then the keystone capture (nonzero voice_rms over real BlackHole audio). SRC cannot prove this.
5. (minor) add `chatterbox`/`all` to the `library models --install` CLI choices to match the doc + give an offline pre-fetch affordance outside the wizard.

**SRC suite spot-checks run this pass:** cue_landing+chatterbox+tts_chain+bundle = 29 passed; provenance = 7 passed; auto_crate+smart_cues = 21 passed; README shape+sync = 53 passed; no-api-key-surface = 4 passed; grids/hero gates exit 0. Both dirty Python files parse clean.
