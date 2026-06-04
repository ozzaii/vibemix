# ING09 — FRESH-USER E2E ladder + done-claim adversarial verification

**HEAD pinned: `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04).
SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree advanced ~20 commits since (the voice/start-gate/citation/learn work landed AFTER the map). I re-pinned every line number against this HEAD before judging. Read-only pass: code + git + tests + committed packets. No product edits, no sidecar launch (one socket 8765).

Three proof tiers, never conflated: **SRC** (green tests on the source you can read) ≠ **PKG** (in a signed DMG built from a committed HEAD) ≠ **LIVE** (a stranger reaches it). `test-passing-but-dark = 0`.

---

## TL;DR — the one finding that reframes everything

**The START-GATE backend + voice env-seed are NOT COMMITTED. They live ONLY in the uncommitted working tree.** `git log -S "_activate_session" -- src/vibemix/__main__.py` returns EMPTY — that symbol was never in any commit. Committed `HEAD:src/vibemix/__main__.py` has **0** occurrences of `_activate_session` / `_RunGatedMusicState` / `start gate: armed`; the working tree has 6. `git show HEAD:src/vibemix/runtime/session_loop.py` has **0** `session_start`/`session_stop`; the working tree has 7. The dirty diff is **738 insertions in `__main__.py` + 72 in `session_loop.py`** (`git diff --stat`). HEAD `__main__.py` = 8724 lines, working tree = 9452.

Worse: the **tests for the start-gate ARE committed**. `HEAD:tests/test_main_smoke.py` has 13 references to `test_smoke_03b_idle_is_cold` / `session.start` / `_start_live_session`, but the source they exercise is uncommitted. So on a CLEAN CHECKOUT of HEAD, the start-gate tests reference source that does not exist → the committed test suite goes RED on a fresh clone (the green I observed is purely the local dirty tree). This is the exact clean-checkout landmine from project memory. Commit `18dc95cb`'s message ("the backend was already implemented and green") is true only of the never-committed working tree.

Everything else in the 4 locked decisions DID land and IS committed (VOICE, BRAIN, CITATION ts-carry, the 4 CI red gates, W12, W13). The single act that flips the build from "claimed" to "real" is **committing `__main__.py` + `session_loop.py`** (surgically, de-conflicting the 2 concurrent loops per `5dbd7290`).

---

## Locked decision verdicts

### (1) VOICE — Chatterbox-only, MOSS nuked, mlx-audio extra, ref bundle, gate-swap

**Verdict: LANDED + COMMITTED. SRC=green, PKG=reachable-once-built, LIVE=0 (keystone never crossed).** All five sub-pieces real:

- **mlx-audio extra** — `pyproject.toml:161-167`: `tts-local` and `ai-local` both carry `"mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"` (Apple-arm64 gated, never a base dep). **LANDED.** (`pyproject.toml` clean/committed.)
- **MOSS nuked** — `src/vibemix/agent/local_tts.py` is DELETED. `grep -rn moss src/vibemix/*.py` = 0 source hits. (`src/vibemix/agent/moss_tts/` survives but is a stale empty `__pycache__` dir, untracked, no source — harmless.) **LANDED.**
- **Chatterbox-only path** — `agent/chatterbox_tts.py` (clean/committed): `chatterbox_available()` (`:124`) honestly gates on mlx_audio present + ref present + model cached; `chatterbox_unavailable_reason()` (`:133`) gives an actionable reason; `_MlxChatterboxEngine.load` (`:169`) lazy-imports `mlx_audio.tts.utils.load_model` + pins revision; `prewarm()` (`:258`) for the Start gate; `build_chatterbox_adapter` (`:327`) raises `ChatterboxUnavailable` rather than falling back to any other voice. No cloud, no MOSS branch. **LANDED.**
- **Ref-clip bundle** — `vibemix-core.macos.spec:36` imports `collect_chatterbox_ref_datas`, `:307` `datas.extend(collect_chatterbox_ref_datas())`. `scripts/dist/chatterbox_bundle.py` exists. `resolve_ref_path()` (`chatterbox_tts.py:106`) prefers the bundled `models/chatterbox/cohost_voice_ref.wav` via `bundled_ref_candidates()` (`:93`, handles frozen `sys._MEIPASS`), falls back to the dev cache. **LANDED.**
- **First-run model fetch** — `library/model_assets.py:490 install_chatterbox_model()`, pinned `CHATTERBOX_MODEL_REVISION="2f2e21a0..."` (`:35`), required-files validation (`:48`), progress callbacks. Triggered from the wizard: `runtime/wizard.py:436 _on_wizard_done → _prefetch_chatterbox_model()` (`:499`) → `install_chatterbox_model` offloaded via `asyncio.to_thread` (`:514`), fail-soft to `_emit_voice_status("muted")` honest banner. **LANDED.**
- **env-seed `VIBEMIX_TTS_ENGINE`** — `__main__.py:1063` (inside `_apply_packaged_defaults`, called `:1109`) + `:1434`: `os.environ.setdefault("VIBEMIX_TTS_ENGINE", tts_engine)` from config (launchd/Dock strip `VIBEMIX_*` — this is the "always silent" root-cause fix). **LANDED IN SOURCE — but in the UNCOMMITTED `__main__.py` (see TL;DR). CLAIMED-BUT-DARK at the committed tier.**
- **release gate swap `--require-moss-source` → `--require-chatterbox-source`** — `scripts/dist/pretag_check.sh:109/111/113` now `--require-chatterbox-ref --require-chatterbox-source`; `release.yml:356/400/427/542` `--require-chatterbox-source`. `check_sidecar_bundle_ready.py:335/336` accepts `require_chatterbox_ref`/`require_chatterbox_source` flags, `:452/460` CLI args. Zero `require-moss` left. **LANDED + COMMITTED.**

**Minor gap (cosmetic, not ship-blocking):** the `library models --install` CLI choices are `("clap", "cue")` at `__main__.py:4816` — `chatterbox` is NOT a direct CLI choice and there's no `all`. The internal `install_models` DOES call `install_chatterbox_model` (`model_assets.py:857/859`), and the wizard is the real first-run trigger, so the voice still fetches. But an operator typing `library models --install chatterbox` gets an argparse rejection. SHIP-NEXT goal step (3) said "register in the `library models --install chatterbox|all` CLI" — the CLI surface is incomplete; the ship path (wizard) is complete.

### (2) BRAIN — hosted Bravoh proxy DEFAULT + set_brain BYO + no-key graceful

**Verdict: LANDED + COMMITTED. SRC=green, LIVE proxy verified same-day (per map, not re-runnable read-only).**

- **Client default = proxy** — `config_store.py:271 llm_mode: str = "proxy"`. **LANDED.**
- **No-key graceful (no crash)** — `__main__.py:1157-1166`: direct without `GEMINI_API_KEY` prints "trying Bravoh proxy" and flips `mode="proxy"`; `:1169-1181` proxy setup failure sets `brain_unavailable_reason` + logs honestly, never exits. The `sys.exit` calls in `main()` are: `:1143` (invalid `VIBEMIX_LLM_MODE` env literal — operator error), `:1517` (no BlackHole — hardware fatal), `:1573` (no audio output at all — hardware fatal). **None is the fresh-user no-key crash. The crash the maps named #1 is GONE.** **LANDED.**
- **set_brain handler** — `session_loop.py:288 register_handler("ipc.settings.set_brain", self._on_settings_set_brain)`; `:486 _on_settings_set_brain` rejects bad mode (`:494`), persists via `persist_brain_settings(env_path=brain_env_path(), ...)` (`:515-519`), redacted logging. FE emits from `brain-group.ts:348`; raw key redacted in `ipc/client.ts:47`. **LANDED + COMMITTED.** (`session_loop.py` set_brain block is committed — distinct from the uncommitted start-gate block in the same file.)

### (3) START GATE — idle=cold, Start activates, Stop releases, silent pre-warm

**Verdict: SOURCE-COMPLETE + SRC-green AGAINST THE WORKING TREE, but UNCOMMITTED → CLAIMED-BUT-DARK at PKG/committed tier. This is the headline gap.**

What exists in the working-tree source (all CORRECT):
- **Backend handlers** — `session_loop.py:278-279` registers `ipc.session.start`/`ipc.session.stop`; `:331 _on_session_start`, `:356 _on_session_stop`; callbacks injected as `session_start`/`session_stop` ctor params (`:189-190`). **(uncommitted, 72-line diff)**
- **main() idle/activate split** — `__main__.py:1592` "SHIP-WIRE START gate" comment; light idle boot (`:1596-1607`); `_RunGatedMusicState` returns cold values until active (`:1624`, `_COLD` dict at `:1627` incl `session_active=False`); `_activate_session` (`:1704`) builds the heavy graph (TTS at `:1759`, AgentSession `:1845`, voice/passthrough/input streams `:1864/1875/2056`) ONLY on Start; `_start_live_session` (`:2172`) + `_stop_live_session` (`:2188`, tears down streams + clears playback + "session parked; live graph released" `:2170`); `_silent_prewarm_hook` (`:2200`) warms imports keeps models cold. `:2275` prints "start gate: armed (idle; capture/reactions/model load wait for Start)". Then `await stop_event.wait()` (`:2278`) + `return` (`:2314`). **(uncommitted, 738-line diff)**
- **Frontend (COMMITTED via `23f3167d`)** — schema `messages.schema.json:1430/1453` (`ipc.session.start`/`.stop`); TS types `ipc/messages.ts:325/330`; Start button `SessionLayout.ts:1053-1057` flips `data-runstate="running"` optimistically then `onStart()`; Stop `:981-982`; emit `render-loop.ts:76` (start) / `:89` (stop); `runState` state `session/state.ts:192`; CSS armed/running gating `SessionLayout.ts:428-433`. **LANDED + COMMITTED.**

So the IPC schema + UI button half is committed and real; the Python backend half + the env-seed are real but stuck dirty. A DMG built from committed HEAD boots WITHOUT the start gate (eager old path) and WITHOUT the voice env-seed → the packaged app would be the pre-start-gate behavior. **CLAIMED-BUT-DARK (PKG): the start gate cannot ship until `__main__.py` + `session_loop.py` are committed.**

**Cleanliness note (working tree):** `__main__.py:2314 return` makes everything from `:2316` onward (the old eager non-gated capture path: `open_passthrough_output` `:2318`, `AgentSession` `:2821`, input stream `:4041`, etc.) UNREACHABLE dead code. Functionally harmless (the live path is the gated one) but a large dead block that should be pruned before commit — a reviewer will trip on it.

### (4) STREAK — Daft-Punk Technologic robot voice, sequenced behind cited-executed-transition rebind

**Verdict: NOT-STARTED, correctly deferred. SRC clean.** No `Technologic`/robot-voice code anywhere in `src/`. The self-applause source the decision warns about is still present and unchanged: `runtime/suggestion.py:1365 _attach_grade_progress` increments `streak` (`:1391`) on the co-host's OWN un-played suggestion. It is NOT wired to any voice, so no Invariant #3 violation ships. Correct posture: rebind off self-applause onto a cited EXECUTED transition BEFORE the robot voice fires (W7/R7).

---

## CI red-gate verdicts (block a tag)

All 4 stale RED gates the maps screamed about are **GREEN at HEAD + COMMITTED:**

- `tests/repo/test_readme_shape.py` + `tests/repo/test_readme_feature_matrix_sync.py` + `tests/security/test_no_api_key_surface.py`: **57 passed** (ran at HEAD). Re-pinned to the bravoh.ai README via `aaa330ad`; key-surface scoped via `ae30e16e`.
- `scripts/launch/check_readme_grids_a11y.py`: **PASS** (DJ-software grid 6 cells, controllers grid 10 cells, alt-text/balance/no-slop).
- `scripts/check_readme_hero_hash.py`: **OK** (hero sha256=PLACEHOLDER sentinel intact, "pending Kaan-action").
- IPC schema parity (`scripts/check_ipc_schema.py`): **OK — 81 dataclasses validate, 81 oneOf == 81 wrappers** (includes the start-gate session.start/stop types).

The key-surface gate was scoped HONESTLY, not gutted: `test_no_api_key_surface.py:59` allows exactly ONE file (`tauri/ui/src/settings/components/brain-group.ts` — the locked-decision-#2 BYO field), still forbids the key surface in the wizard + all other UI (`:108/:122`), and ADDS a positive assertion (`:134`) that the BYO field is scoped + write-only + redacted (`:145-147`). This is a correct D2 policy resolution.

---

## Fresh-user step ladder @ HEAD (the "can a stranger get value" verdict)

Walked install → wizard → first session → Start → grounded line in Chatterbox voice → deck underlines its citation. Verdict per step (against committed HEAD unless noted):

0. **DMG download / Gatekeeper** — **DARK (PKG stale).** `dist/vibemix-0.0.1.dmg` is 487M from 09:59, ~200 commits behind HEAD and UNSIGNED. The freshest signed set `dist/fresh-20260604-wav-signed-v2/` predates the voice/start-gate work. No DMG at HEAD exists. Platform `binaries/` dir is empty (no x86_64/windows binaries) — arm64-only is the only possible PKG.
1. **Wizard launch** — **LIVE.** Steps wired: intro → permissions → audio → controller → skill-level → forewarning/driver-fetch/format-check → profile-consent → telemetry-consent → smoke-test → done (`wizard/router.ts:49-65`). Skill persists to `config.extra["skill"]` (`wizard.py:472`).
2. **Key / proxy step** — **DARK but non-blocking.** There is NO key/proxy wizard step in the state machine. Proxy is the default + funded, so the fresh user reaches the brain without one. The in-GUI BYO key field lives in Settings (`brain-group.ts`), not the wizard. Acceptable for v1.
3. **Audio routing** — **PARTIAL/LIVE.** `step2-output-device` + calibration probe + window picker are wired. Detect + deep-link, no in-app BlackHole installer (deferred). A `[FATAL]` exit (`__main__.py:1517`) fires only if BlackHole is wholly absent — a precondition, not a crash-on-happy-path.
4. **Reach the brain** — **LIVE.** Proxy default + graceful no-key fallback (verdict #2). Register→JWT→gemini-3.5-flash→HTTP 200 verified same-day per map (not re-runnable read-only; credits are a Kaan/ops flag).
5. **Voice reachable** — **DARK on a real packaged launch until BOTH: (a) `__main__.py` env-seed commits, and (b) the user completes the wizard voice prefetch + has mlx-audio installed.** Source is complete and correct; on a built DMG with the extra installed and the wizard fetch done, `chatterbox_available()` returns True. But the env-seed that selects the engine on a launchd-stripped launch is in the UNCOMMITTED `__main__.py` → a HEAD-committed DMG would not seed it. **CLAIMED-BUT-DARK (PKG).**
6. **Start the session** — **DARK at committed tier (backend handler uncommitted).** Frontend button + IPC committed; backend `_on_session_start` + `_activate_session` uncommitted. A HEAD-committed build has the button but no backend handler → pressing Start emits an envelope nothing handles (the `_on_session_start` is absent in committed `session_loop.py`). **CLAIMED-BUT-DARK (PKG).**
7. **Hear a grounded line in the Chatterbox voice** — **DARK / LIVE=0.** Depends on 5+6 both committing AND Kaan's hand on the rig. No captured run has nonzero `voice_rms` or a `transcript_delta` over real audio. The co-host has never spoken live. This is the keystone — Kaan-only, unreachable by any read-only lane.
8. **Deck underlines its citation** — **LANDED + COMMITTED (SRC), LIVE-pending-keystone.** The Seam-D ts-carry is fixed and committed (`d67e6f81`): `dj_cohost.py:4075` builds `SessionCohostReaction.make()` once, captures its ts into `reaction_msg_ts` (`:4081`), threads the SAME ts into `_push_transcript(..., ts=reaction_msg_ts)` (`:4163`). `ws_bus.py:786` HONORS a transcript item's own ts (`ts = str(item.get("ts") or ts)`) instead of re-stamping `_now_iso()` — the exact line that closed the bug. FE join: `SessionLayout.ts:1294 reactions.get(nowLine.ts)`, reactions map keyed by the reaction envelope ts (`ws-bridge.ts:646-651 applyCohostReaction(ts,...)`). The two ts now byte-match → the underline gesture fires live. **LANDED.**

**Ground-truth: a stranger CANNOT get value from a HEAD-committed build today** — not because of an engineering hole, but because the start-gate backend + voice env-seed are sitting uncommitted in the working tree, and there is no fresh signed DMG. The fix is a commit + a build, not new code.

---

## Other committed done-claims verified (build-on-maps, no re-derivation)

- **W12 — `[ev:BEATMATCH_GRADED]` live credit** — **LANDED + COMMITTED** (`8c0c0ffa`). `runtime/coach.py:264 _credit_live_beatmatch_grade_receipts` consumes `[ev:BEATMATCH_GRADED@t]` with a 2.0s freshness window (`:113/:309`), routes through `_credit_live_skill_demo` (`:324`), honors Invariant #3. The map's "0 references in coach.py" is now resolved. Both files clean.
- **W13 — cue-landing consolidation** — **LANDED + COMMITTED** (`4831b226`). Live Viber path imports `cue_landing` (`toolset.py:1178/:2242/:2257`) instead of a fully-parallel inline spine. Files clean.
- **MOSS legacy runtime retired** — `fddddfc9` + `de9233f9` + `cf18d85d`: source + comments scrubbed. Verified 0 moss source hits.
- **Chatterbox packaged prefetch** — `0e5590c5` + `eec239ac` + `7082fb8d`: wizard prefetch + preflight + bundle-required gate. Committed.

---

## SRC test state @ HEAD (against the working tree — the caveat matters)

- `tests/agent tests/runtime tests/state`: **2134 passed, 1 skipped** (79s).
- `tests/test_main_smoke.py`: **38 passed** (incl. `test_smoke_03b_idle_is_cold_until_start`).
- The 4 named CI gates: **GREEN** (above).
- `tsc --noEmit`: **exit 0.** `vitest run src/session`: **49 passed**.
- `tests/repo/test_clean_checkout_imports.py`: **2 passed** — BUT this gate only checks IMPORTABILITY, not start-gate test behavior. It does NOT catch the committed-test-vs-uncommitted-source split.

**SRC-green is conditional on the dirty tree.** A clean checkout of `d7d5337a` would: (a) lose the start-gate backend entirely, and (b) run committed `tests/test_main_smoke.py` against absent source → the start-gate smoke tests would ERROR/FAIL. The "green" is local-working-tree-only. This is a real CI/clean-checkout RED waiting to surface the moment the dirty files are NOT present (e.g. another machine, CI, or if a concurrent loop reverts them).

---

## PKG tier @ HEAD

- **Every distributable is stale.** `dist/vibemix-0.0.1.dmg` (487M, 09:59) is unsigned + ~200 commits behind. `dist/fresh-20260604-wav-signed-v2/` is the freshest signed set but predates the voice/start-gate/citation work. `dist/vibemix-core` sidecar (26M, 09:56) is stale. Do NOT evaluate HEAD from any DMG.
- **Platform coverage = arm64-only.** `binaries/` is empty (no x86_64 or windows binaries). The updater-manifest gate (`check_updater_manifest_ready.py:17-18`) still hard-requires `darwin-x86_64` + `windows-x86_64` → no signed `latest.json` for an arm64-only v1 without relaxing that gate or shipping v1 without auto-update.
- **Gate to a fresh signed HEAD arm64 DMG (ordered):** (1) **commit the dirty seam files** `__main__.py` + `session_loop.py` (de-conflict the 2 concurrent loops first; prune the dead-code block below `:2314`); (2) the gate-swap is already done; (3) `build_sidecar.py --spec vibemix-core.macos.spec`; (4) rebuild DMG separately; (5) `sign_macos.sh`; (6) `VIBEMIX_PRETAG_MAC_ONLY=1 pretag_check.sh` then tag.

---

## GA-TAG LANDMINE — CONFIRMED ACTIVE at HEAD

- `release.yml:57-60` fires on `push: tags: 'v*'`. `companion-sign.yml:16-18` fires on `push: tags: [v*]`.
- `release.yml` still has a `windows-latest` build job (`:472`) + SignPath references (`:20`); `companion-sign.yml:69 runs-on: windows-latest`. The `build-macos` matrix is arm64-only (`:282-284 runner: macos-14`), but **Windows is NOT excluded** — a `v0.1.0` push fires the full matrix incl. Windows + SignPath.
- The MOSS→chatterbox gate-swap IS done (so the gate itself won't false-fail), but Windows-in-matrix remains. **Do NOT push `v0.1.0` until Windows is excluded from the v1 matrix and the `Bravoh-ai/vibemix` org repo has the signing secrets.** The `0.1.0` non-`v` source-snapshot pre-release is the interim marker (fired only the benign SBOM job).

---

## README / partner-copy violations @ HEAD (public-facing, not code wires)

The CI README gates pass (shape/sync/grids/hero), but the partner-copy POLICY is still violated in the prose those gates don't check:

- **`README.md:39` LEAKS `api.altidus.world`** ("Live co-host calls go to Bravoh's Gemini proxy at `api.altidus.world`"). Policy: say "Bravoh's hosted service", never the endpoint. Also names **"Gemini"** twice (`:39`) — policy: "AI model".
- **`pyproject.toml:182-184` URLs = `github.com/ozzaii/vibemix`** — policy: org is `Bravoh-ai`. (README badges correctly use `bravoh-ai/vibemix` at `:42-52`, so the repo moved but pyproject didn't follow.)
- README `:39` says "Windows build targeting v0.1.0 stable" — fine as roadmap, but reconcile with the macOS-arm64-only v1 / Windows-v1.1 decision.

These are docs fixes, not ship-blockers for a macOS-only RC, but they violate the stated public-copy policy and should land before any public tag.

---

## Dead / do-not-touch confirmations

- `agent/local_tts.py`: DELETED (correct).
- `__main__.py:2316+` (post-`return`): dead eager-capture path in the working tree — prune before commit.
- `runtime/suggestion.py:1365 _attach_grade_progress`: self-applause source — leave unwired until W7 re-grounding; do NOT attach the streak robot voice to it.

---

## The single next move (organizer)

**COMMIT `__main__.py` + `session_loop.py`** (surgically, `git add <exact paths>`, verify `git diff --cached`, de-conflict the 2 concurrent `__main__.py` loops per `5dbd7290`, prune the dead block below `:2314`). That one act:
1. makes the START-GATE backend real at the committed/PKG tier (decision #3 → committed),
2. lands the voice env-seed so a launchd-stripped packaged launch selects Chatterbox (closes the last voice-reachability gap at PKG),
3. turns the committed `test_main_smoke.py` start-gate tests from "references absent source" to "green on a clean checkout".

After that: exclude Windows from the v* matrix, fix the README endpoint/model-name leak + pyproject org URL, then build → sign → arm64 RC → Kaan's keystone capture. No new engineering is required to ship — the gap is a commit + a build + Windows-matrix exclusion + Kaan's by-ear keystone, exactly as the map predicted, plus this one un-flagged commit hole.
