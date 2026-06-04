# ING-11 — PKG proof tier (packaging readiness for an arm64 GA)

> Ship-ingestion pass run RIGHT AFTER the autonomous Codex build-loops reported "DONE".
> Job: ingest the REAL landed state at the CURRENT HEAD and ADVERSARIALLY VERIFY every done-claim.
> READ-ONLY. Three proof tiers, never conflated: **SRC** (green tests on source) != **PKG** (in a signed DMG built at HEAD) != **LIVE** (a real user reaches it). `test-passing-but-dark = 0`.

## HEAD read at

**`d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, `d7d5337a test(config): isolate device defaults from rig env`, 2026-06-04 20:06 +03).
The SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree advanced to `d7d5337a` since. Several map claims are now STALE in BOTH directions (some things landed further than the map says; one big thing the map called "DONE" is actually uncommitted). Every staleness flagged inline.

**Working tree is DIRTY at two single-owner seam files** (this is the single most important finding for PKG):
- `src/vibemix/__main__.py` — `M`, +738 lines uncommitted
- `src/vibemix/runtime/session_loop.py` — `M`, +72 lines uncommitted

These two uncommitted hunks ARE the entire START-GATE backend (decision #3). See §Decision 3.

---

## TL;DR verdicts

| Locked decision | committed-HEAD state | flag | tier |
|---|---|---|---|
| (1) VOICE = Chatterbox only, MOSS nuked, mlx extra, bundle ref, gate-swap | source-side LANDED + gate-swap LANDED + ref-bundle LANDED + model install LANDED + wizard prefetch LANDED | **LANDED** (source) | SRC green; PKG needs DMG; LIVE never crossed |
| (2) BRAIN = proxy default, set_brain BYO, no-key graceful | LANDED end-to-end at committed HEAD | **LANDED** | SRC green; LIVE proxy verified same-day per maps |
| (3) START GATE = idle-cold, Start button, prewarm, Stop releases | frontend + IPC schema + test LANDED; **BACKEND IMPLEMENTATION IS UNCOMMITTED WORKING-COPY ONLY** | **CLAIMED-BUT-DARK** at committed HEAD | SRC green ONLY with dirty tree; PKG impossible until committed |
| (4) STREAK = Technologic robot voice, sequenced behind rebind | not started, self-applause streak still present | **NOT-STARTED (correct)** | n/a |

**The #1 PKG blocker is no longer the mlx-audio gap (the map's #1) — that LANDED.** The #1 PKG blocker now is: **the START-GATE backend (decision #3) lives only in the dirty working copy of `__main__.py` + `session_loop.py`; it is NOT in commit `d7d5337a`. A DMG built from committed HEAD would have NO start gate, AND the sidecar-freshness gate hard-fails on those two dirty files.** Commit them first, or the start gate ships dark and the build gate red.

---

## Decision 1 — VOICE (Chatterbox only, MOSS nuked) — **LANDED in source**

Verified far past the map's claim. Every sub-item the GOAL listed is in committed HEAD:

- **MOSS nuked.** `grep -ri moss src/vibemix/**/*.py` = **0 hits**. `src/vibemix/agent/local_tts.py` = **deleted** (os error 2). SRC/LANDED.
- **mlx-audio is a `pyproject.toml` extra (Apple-arm64-gated).** `pyproject.toml:161-168` — both `tts-local` and `ai-local` carry `"mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"`. Apple-only environment marker is correct (Intel Macs + Windows resolve to no mlx). SRC/LANDED. (Map called this "the #1 blocker, not landed" — STALE; it landed.)
- **Ref bundle in the spec.** `vibemix-core.macos.spec:36` imports `collect_chatterbox_ref_datas`, `:307` `datas.extend(collect_chatterbox_ref_datas())`. Helper `scripts/dist/chatterbox_bundle.py:30 collect_chatterbox_ref_datas()` returns `[(str(ref_path), "models/chatterbox/cohost_voice_ref.wav")]` (`:43`), empty list if the dev-cache ref is absent (`:38`). `mlx`/`mlx_audio`/`mlx_lm` are in the spec hiddenimports + collect lists (`:151-153`, `:185-187`). SRC/LANDED.
- **resolve_ref_path() prefers bundled.** `agent/chatterbox_tts.py:106 resolve_ref_path()` order: `VIBEMIX_CHATTERBOX_REF` override → `bundled_ref_candidates()` (`:93`, scans `sys._MEIPASS` + exe-parent + `_internal`) → `_DEV_REF` cache fallback (`:53`). Correct bundled-first logic. SRC/LANDED.
- **install_chatterbox_model + pinned revision.** `library/model_assets.py:490 install_chatterbox_model()`; repo `mlx-community/chatterbox-turbo-8bit` (`:34`), revision pinned `2f2e21a03863f86a1274d1060dcc188e7cde77e1` (`:35`), `CHATTERBOX_REQUIRED_FILES` size map (`:48`), `chatterbox_model_cached()` on-disk check (`:406`), actionable offline hint (`:59`). SRC/LANDED.
- **Wizard prefetch (download before first set, NOT mid-generate).** `runtime/wizard.py:436 await self._prefetch_chatterbox_model()` → `:499` body imports `install_chatterbox_model` (`:506`), runs it (`:515`), offline → "co-host starts voiceless" warning (`:528`), no fatal. SRC/LANDED.
- **Env-seed `VIBEMIX_TTS_ENGINE` at boot.** `__main__.py:1427-1428` `_tts_engine_seed = ... ; os.environ.setdefault("VIBEMIX_TTS_ENGINE", _tts_engine_seed)` — COMMITTED. The SECOND seed inside `_apply_packaged_defaults()` is **uncommitted** (committed HEAD has the stub `return None` at `:1057` area; the dirty working copy fills it in). Net: boot-path seed committed; packaged-defaults seed dirty. SRC/LANDED (boot path) / dirty (packaged-defaults path).
- **Release gate swap `--require-moss-source` → `--require-chatterbox-source`.** `scripts/dist/pretag_check.sh:109/111/113` all pass `--require-chatterbox-ref --require-chatterbox-source`. `.github/workflows/release.yml:355/356, 399/400, 426/427, 541/542` (mac + windows) all swapped. Gate impl `scripts/dist/check_sidecar_bundle_ready.py:180 chatterbox_release_source_ready()` actually hits the HF API to confirm the pinned repo@revision still resolves (`:184-218`) and `:168 chatterbox_release_ref_ready()` checks the bundled `_internal/models/chatterbox/cohost_voice_ref.wav`. **No `--require-moss` flag remains anywhere.** SRC/LANDED. (Map flagged the gate-swap as the remaining packaging blocker — STALE; it landed.)
- **TTS armed-not-loaded at boot.** `__main__.py:1445-1449` prints `"chatterbox armed (loads on Start)"` (dirty working copy; committed HEAD still constructs `ChatterboxLocalTTS()` eagerly — the dirty diff is what defers the load to Start). This is part of the start-gate dirty hunk.

### VOICE gap found (narrow, NOT ship-blocking)
- **CLI `library models --install chatterbox|all` is REJECTED at argparse.** The GOAL said register chatterbox in the install CLI. `library/model_assets.py:install_models()` DOES accept `"chatterbox"` and `"all"` targets (it raises ValueError only for anything outside `{"required","clap","chatterbox","cue","all"}`). BUT the argparse `choices` at `__main__.py:4816` is `("clap", "cue")` only — so `--install chatterbox` and `--install all` error at the CLI before reaching `install_models`. The wizard path (calls `install_chatterbox_model` directly) works, so the model still pre-fetches on first run; only the documented MANUAL CLI fetch is dark. **CLAIMED-BUT-DARK** (CLI choices). Fix = add `"chatterbox","required","all"` to the `choices` tuple at `__main__.py:4816`. Also the `models` status display: chatterbox status IS reported (`__main__.py:9213-9232` builds a chatterbox-missing list), so `library models` status is honest; only the install verb is the gap.

**VOICE verdict:** decision #1 is **LANDED** in source. SRC green. PKG = pending the DMG build (which needs the dirty start-gate files committed first, see §Decision 3). LIVE = never crossed (no run with nonzero voice_rms; keystone is Kaan's hand). One narrow CLI-choices gap on the manual install verb.

---

## Decision 2 — BRAIN (proxy default, BYO set_brain, no-key graceful) — **LANDED**

- **Client default = proxy.** `runtime/config_store.py:271 llm_mode: str = "proxy"`; dataclass docstring (`:267-270`) "VIBEMIX_LLM_MODE env overrides ... so missing local keys never hard-crash first boot." LANDED.
- **set_brain handler wired (committed HEAD).** `session_loop.py:279 register_handler("ipc.settings.set_brain", self._on_settings_set_brain)` — present in committed HEAD (verified `git show HEAD:`). Body `_on_settings_set_brain` (`:486` in working copy / `:486`-ish committed) validates mode in {direct,proxy} (`:494`), persists `llm_mode`, writes `GEMINI_API_KEY` to `brain_env_path()`, acks `key_set=brain_key_persisted(...)`. LANDED.
- **No-key path is graceful, no crash.** `__main__.py:1157-1166` direct-without-key prints "trying Bravoh proxy" and flips `mode="proxy"`. `:1169-1181` proxy setup failure sets `brain_unavailable_reason` and logs an honest banner (`_log_brain_unavailable`) — no `sys.exit`. The only nearby `sys.exit` is `:1143` for an INVALID env-var VALUE (operator typo `VIBEMIX_LLM_MODE=foo`), not a no-key user. `:265` prints `"-> brain: unavailable (...); add your Gemini key in Settings or retry proxy"`. LANDED. (Map's "crash FIXED" claim CONFIRMED.)
- **Proxy register shape.** `agent/jwt_cache.py:79 url = f"{base}/api/vibemix/v1/register"`, non-200 raises sanitized RuntimeError (`:87`, body NOT echoed). `__main__.py:1139 proxy_base_url default "https://api.altidus.world"`. LANDED.
- **Security gate vs BYO key field (map's D2 "RED" claim) — now GREEN.** `tests/security/test_no_api_key_surface.py` is SCOPED: it allows ONE BYO surface `tauri/ui/src/settings/components/brain-group.ts` (`:59 ALLOWED_BYO_KEY_SURFACE`) and asserts it stays masked/write-only/redacted (`:133 test_byo_key_surface_is_single_masked_write_only_and_redacted`, asserts `{ mode: "direct", gemini_api_key: key }` + the IPC redact-list `"ipc.settings.set_brain": ["gemini_api_key"]`). Ran: **4 passed**. The map + SHIP-NEXT D2 call this gate RED/unresolved — STALE; it is resolved + green. Note the file moved to `settings/components/brain-group.ts` (the map's `settings/brain-group.ts` path is stale).

**BRAIN verdict:** decision #2 **LANDED** end-to-end at committed HEAD. SRC green. LIVE proxy (register→JWT→gemini-3.5-flash→200) verified same-day per maps; credits are a Kaan/Bravoh-ops flag, unverifiable read-only.

---

## Decision 3 — START GATE — **CLAIMED-BUT-DARK at committed HEAD (uncommitted working copy)**

This is the headline adversarial finding. The map says "[backend handler still DARK]" then "[IPC schema DONE frontend-side; backend handler DARK]". The recent commits `18dc95cb test(start-gate): lock idle-cold` + `02ffb7c0 test(boot): align smoke with start-gated defaults` made it LOOK landed. **It is not in the commit.**

### What IS committed at HEAD `d7d5337a`
- Frontend Start button + run-state: `tauri/ui/src/session/SessionLayout.ts` (`data-runstate="armed"|"running"`, `.vmx-armed__start` "THE primary ship action" `:445-474`, onStart/onStop optimistic repaint), `render-loop.ts:73 sessionStartHandler()` → `emitIpc("ipc.session.start", {})`, `:82 sessionStopHandler()`, real-boot default `runState:"armed"` (`render-loop.ts:434-436`, `makeDefault()`). LANDED (frontend).
- IPC schema: `messages.schema.json:1430 ipc.session.start` + `:1453 ipc.session.stop` (with `$comment` explicitly assigning the backend handler to the BACKEND-BOOT lane). `messages.ts:325/330` TS types. LANDED (schema).
- The TEST: `tests/test_main_smoke.py::test_smoke_03b_idle_is_cold_until_start` (commit `18dc95cb`). LANDED (test).

### What is NOT committed at HEAD (working-copy only)
`git show HEAD:src/vibemix/runtime/session_loop.py | grep _on_session_start` = **EMPTY.** `git show HEAD:src/vibemix/__main__.py | grep _start_live_session` = **EMPTY.**
- Committed `session_loop.py` `register_handlers()` (`HEAD:` `:263`) jumps from `ipc.session.set_mode` (`:277`) straight to `ipc.settings.set` (`:278`) — **NO `ipc.session.start`/`ipc.session.stop` registration.** It also has no `_on_session_start`/`_on_session_stop` methods and no `session_start`/`session_stop`/`session_is_active` constructor params at committed HEAD.
- Committed `__main__.py` `SessionLoop(...)` construction (`HEAD:` `:2238`) does NOT pass `session_start=`/`session_stop=`/`session_is_active=`. No `_activate_session`, no `_start_live_session`, no `_stop_live_session`, no `_silent_prewarm_hook`, no `active_task` lifecycle at committed HEAD.

### What the DIRTY working copy adds (verified via `git diff`)
The +738/+72 uncommitted diff IS the start gate: `session_loop.py` gains `_on_session_start` (`:331`), `_on_session_stop` (`:356`), `_session_active` (`:322`), constructor params (`:189-191`), and registrations (`:278-279`). `__main__.py` gains the `# --- SHIP-WIRE START gate ---` block (`:1589` onward) with `evidence_registry`, `_activate_session` (`:1704`), `_start_live_session` (`:2172`), `_stop_live_session` (`:2188`, the cleanup at `:2130-2170` closes session/tts/streams/mic + prints "live graph released"), `_silent_prewarm_hook` (`:2200`, "models still cold"), and `SessionLoop(session_start=_start_live_session, session_stop=_stop_live_session, session_is_active=_is_live_session_active)` (`:2238-2240`). The dirty diff also flips `_apply_packaged_defaults()` from stub to a real env-seed, and defers the chatterbox load to Start (`:1445-1449` "armed (loads on Start)").

### Consequence for PKG
1. The start-gate code is functionally complete and SRC-green — BUT ONLY because pytest runs against the dirty working tree. The committed HEAD does NOT have it.
2. The sidecar-freshness gate (`scripts/dist/check_sidecar_bundle_ready.py:298 current_dirty = source_dirty_paths(...)`, `:307-311`) HARD-FAILS on any dirty runtime-package source. With `__main__.py` + `session_loop.py` dirty, a release build is blocked until they commit.
3. A DMG built from committed HEAD (if the dirty files were stashed) would have NO start gate → heavy models resident at idle → decision #3 dark on a real launch.

**START-GATE verdict: CLAIMED-BUT-DARK** at committed HEAD. The implementation is correct and tested, but it is uncommitted. **Step 1 of any PKG path is: commit `__main__.py` + `session_loop.py` surgically** (these are single-owner keystone files; the CLAUDE.md shared-commit hazard applies — `git diff --cached --name-only` must show exactly these two before commit).

---

## Decision 4 — STREAK (Technologic robot voice) — **NOT-STARTED (correct)**

- No `technologic`/`robot_voice`/`daft.punk` voice anywhere in `src/vibemix/**/*.py` (the only "Daft Punk" hits are the audio tuning-constant docstrings `audio/constants.py:2/68`, the genre profile — unrelated).
- The self-applause streak the map flags as the Invariant-#3 risk (#11) still exists: `runtime/suggestion.py:1365 _attach_grade_progress`, `:1391-1413` increments + grades the co-host's OWN un-played suggestion (`streak`, `streak*18`). This is exactly the "must be STRIPPED + re-grounded before any robot voice" signal. It has NOT been wired to any voice.

**STREAK verdict: NOT-STARTED**, which matches the lock ("sequenced behind rebinding to a cited EXECUTED transition FIRST"). Correct. Do NOT ship robot voice on the present self-applause signal.

---

## 3-tier ship state at `d7d5337a`

### SRC — green except a 4-test isolation-flake set
- Full default suite: **8100 passed, 24 skipped, 12 deselected, 4 xpassed, 4 FAILED** in 843s.
- The 4 failures are ALL `tests/repo/test_v4_milestone_audit_present.py` (`exists`, `reads_wired_on_gate4_regex`, `is_generator_produced`, `labelled_v4`). **Run in isolation that file is 5 passed.** The file `.planning/v4.0-MILESTONE-AUDIT.md` EXISTS with the correct markers (`Generated:` ×1, `milestone: v4.0`, `seams_wired: 5`, `overall_verdict: WIRED`). This is **test-pollution / shared-CWD-state** (a sibling test mutates that file or CWD during the full run), NOT a content gate failure and NOT a product regression. It WILL still red the `full-test-matrix` CI job under a full run and therefore block a tag until the isolation bug is fixed (or the gate is hardened against pollution). Flag: **SRC-flaky, tag-blocking-under-full-run.**
- README CI gates: `test_readme_shape.py` + `test_readme_feature_matrix_sync.py` = **53 passed**; `check_readme_grids_a11y.py` = PASS (6 dj-software + 10 controller cells); `check_readme_hero_hash.py` = OK (PLACEHOLDER sentinel). All 4 README gates GREEN — but they enforce the OLD policy (see §README below), so green ≠ partner-copy-clean.
- Security gate `test_no_api_key_surface.py` = 4 passed (D2 resolved). Model-literal gate present (see §Governance).
- **Dark-but-green risk:** start-gate SRC-green only on the dirty tree (see §Decision 3); mlx-audio not installed in the dev venv (Chatterbox unit tests pass by mocking the engine seam — voice never actually plays in CI); the keystone (LIVE) has zero test coverage by definition.

### PKG — every distributable stale; canonical DMG unsigned; arm64-only
- `dist/vibemix-0.0.1.dmg` (487M, built 09:59) — `spctl -a -t install` = **"rejected, source=no usable signature"** = UNSIGNED, and **224 commits behind HEAD** (`git log --since="2026-06-04 09:59" --oneline | wc -l` = 224). Do NOT evaluate HEAD from this DMG.
- Other `dist/` dirs (`current-head-*`, `fresh-*`) are earlier snapshots, all behind HEAD.
- **Platform coverage = arm64-only.** No `binaries/` dir exists at all (the map's `.placeholder` x86_64/windows stubs are gone). macOS-Intel + Windows PKG = 0.
- **Updater manifest gate hard-requires all 3 platforms.** `scripts/dist/check_updater_manifest_ready.py:15-18 REQUIRED_PLATFORMS = {darwin-aarch64, darwin-x86_64, windows-x86_64}`. For a v1 arm64-only ship this must be relaxed to arm64-only, OR v1 ships without auto-update (manual download). Implementation choice, not a Kaan gate (per SHIP-NEXT D3).
- **GA-TAG LANDMINE — CONFIRMED REAL.** `.github/workflows/release.yml:57-60` triggers on `push` of any `v*` tag. The macOS build matrix (`:281-289`) includes BOTH `arm64` (macos-14) AND `x86_64` (macos-13). The header documents a Windows job + SignPath (`:12, :20, :36`). `VIBEMIX_PRETAG_MAC_ONLY=1` only suppresses the SignPath LOCAL pretag gate (`scripts/dist/pretag_check.sh:148`); it does NOT change what `release.yml` builds on a tag push. **A `v0.1.0` tag push fires the full matrix incl. x86_64 Mac + Windows + SignPath.** Do NOT push `v0.1.0` until: start-gate files committed, the 4 README gates' policy reconciled with partner-copy (or accepted as-is), Windows excluded from the v1 matrix (edit the matrix, not just the local flag), the v4-audit isolation flake fixed, and org secrets present. The `0.1.0` non-`v` snapshot pre-release fired only the benign SBOM job — interim marker, NOT signed GA.

### LIVE — keystone never crossed
- Fresh-user ladder: (0) DMG/Gatekeeper DARK (stale+unsigned). (1) wizard launch LIVE. (2) telemetry-consent DARK (phantom emit, non-fatal per maps). (3) audio routing PARTIAL. (4) reach brain LIVE (proxy default + graceful no-key). (5) voice reachable = source-LANDED, PKG-pending (needs DMG with mlx + ref + first-run model fetch). (6) Start the session = backend code exists but UNCOMMITTED → DARK at commit. (7) hear a grounded cloned-voice line = depends on 5+6, never captured. (8) deck underlines its citation = ts-join still mis-keyed per maps (not re-verified this pass; map #6 Seam D, not claimed landed).
- No captured run has nonzero `voice_rms` or a `transcript_delta` over real audio. The co-host has NEVER spoken live. Kaan's hand on the rig is the only thing that flips LIVE.

---

## Governance / drift gaps found

- **Voice/audio model literals are UNGATED (map #15, W17 — CONFIRMED).** `tests/repo/test_model_literal_gate.py:36-37` matches only `gemini-3-flash|gemini-3-pro|gemini-embedding-|gemini-3.1-flash|gemini-2.5-flash|gemini-3.1-flash-live`. The Chatterbox literals — `mlx-community/chatterbox-turbo-8bit` (`chatterbox_tts.py:48`, `model_assets.py:34`), the pinned revision SHA (`model_assets.py:35`), `_DEFAULT_TEMP = 0.4` (`chatterbox_tts.py:49`) — are NOT covered and can drift silently green forever. Note these are arguably config-source-of-truth (centralized in `model_assets.py`), so this is governance hygiene, not a live bug. Flag: **governance gap, post-ship.**

---

## README — partner-copy policy VIOLATED at HEAD (4 CI gates GREEN but enforce the OLD policy)

The bravoh.ai swap commits (`5a1e3533 docs(readme): swap legacy altidus.world marketing links to bravoh.ai`, `aaa330ad test(repo): re-pin README funnel to bravoh.ai`) DID land — README contains `bravoh.ai` 14×. BUT the swap touched only the marketing/FUNNEL links; the PRODUCT COPY still violates the partner policy. The 4 README CI gates pass against these violations because they enforce shape/grid/hero/sync, not the partner-copy ban.

Violations at `README.md` (HEAD):
- **Model names exposed** ("Gemini" ~9×): `:39, :61, :241, :259, :269, :271, :283, :287` ("AI model" required).
- **`api.altidus.world` leaked** (4×): `:39, :61, :241, :259` ("Bravoh's hosted service" required; never the raw endpoint).
- **`security@bravoh.com`** (`:63`) — domain is bravoh.ai, not bravoh.com.
- **`github.com/ozzaii/vibemix`** (`:330`) — org is Bravoh-ai, not ozzaii.
- **MOSS voice copy is now FACTUALLY FALSE** (`:229, :241, :271`): "Sven speaks through the local MOSS voice path" — MOSS is NUKED in source; the voice is Chatterbox. This is both a partner-copy and an accuracy violation ("on-device voice" required).
- **Internal dev feature-matrix dump** (Phase numbers, commit SHAs, "Kaan ear-passes daily" `:69`, "KAAN-ACTION" `:11/30/86/198`, "ear-pass" `:134/141/142/148/157/279`, SHIPPED dates `:135-157`) — internal slop in a public README. The AUTO-GEN matrix (`scripts/launch/sync_feature_matrix.py`) is the source; the violation is that the matrix CONTENT is internal-flavored, not a sync break.

**README verdict: CLAIMED-BUT-DARK on partner-copy.** The map's "README→bravoh.ai swap landed" is HALF-TRUE (funnel links only). A partner-copy scrub pass is required before public GA, and it must move in lockstep with the 4 pinning gates (re-run `sync_feature_matrix.py`, keep grid cells = 6/10, hero PLACEHOLDER sentinel) or the gates go red. This is content, not a code wire — but it IS GA-blocking for a public repo.

---

## Exact ordered steps to a fresh signed arm64 HEAD DMG

Owner tags: **[auto]** = a lane/script can do it; **[Kaan]** = human/external clock only.

1. **[auto, BLOCKER] Commit the dirty start-gate seam files.** `git add src/vibemix/__main__.py src/vibemix/runtime/session_loop.py` (verify `git diff --cached --name-only` shows ONLY these two — CLAUDE.md shared-commit race), commit. This is the prerequisite for BOTH the sidecar-freshness gate AND for the start gate to exist in the build. (Also picks up the `_apply_packaged_defaults` env-seed + "armed (loads on Start)" deferral that ride in the same hunk.)
2. **[auto] Fix or quarantine the v4-milestone-audit isolation flake** so `full-test-matrix` is green under a FULL run (passes in isolation today; pollution reds it in the suite). Either find the polluting sibling test and isolate the `.planning/v4.0-MILESTONE-AUDIT.md` write, or mark the gate resilient to CWD/file mutation.
3. **[Kaan, policy] Decide README partner-copy scrub timing.** Either scrub now (re-run `sync_feature_matrix.py --check`, keep the 4 gates green) or accept that public GA is blocked until scrubbed. Not a code wire; does not block the DMG binary, blocks public release.
4. **[auto] Add `mlx-audio` to the dev/build environment** (it is an extra now, `pyproject.toml:161-168`) so the build venv actually bundles it: build with the `ai-local` (or `tts-local`) extra. Confirm `chatterbox_available()` logic via `bundled_ref_candidates()` will find the ref in `_internal/models/chatterbox/`.
5. **[auto] Ensure the dev-cache ref clip exists** at `~/.cache/vibemix/cohost_voice_ref.wav` (720KB) so `collect_chatterbox_ref_datas()` (`chatterbox_bundle.py:38`) does NOT return an empty list — otherwise the ref silently does not bundle and `chatterbox_available()` returns False in the DMG.
6. **[auto] Build the sidecar:** `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec` (records `source_dirty=[]` only if step 1 is done).
7. **[auto] Rebuild the DMG SEPARATELY** — a sidecar rebuild does NOT refresh `dist/*.dmg` (CLAUDE.md gotcha).
8. **[auto] Pretag check (mac-only):** `VIBEMIX_PRETAG_MAC_ONLY=1 scripts/dist/pretag_check.sh` — passes `--require-chatterbox-ref --require-chatterbox-source` (the source-ready check hits the HF API for the pinned repo@revision, so the build host needs network), suppresses the SignPath gate.
9. **[Kaan] Apple sign + notarize:** `scripts/dist/sign_macos.sh` then notarytool submit/staple. Automated-but-credentialed = Kaan's Apple account.
10. **[Kaan, before tagging] Exclude Windows from the v1 matrix** — edit `release.yml` so a `v*` tag does NOT fire the Windows job + SignPath + x86_64 Mac (the matrix at `:281-289` builds x86_64 too). `VIBEMIX_PRETAG_MAC_ONLY=1` alone is insufficient — it only gates the local pretag script, not the CI matrix. Relax `check_updater_manifest_ready.py:15` to arm64-only OR ship v1 manual-download (no auto-update).
11. **[Kaan] KEYSTONE LIVE capture** — drive a real set into BlackHole 2ch, hear a grounded Chatterbox line whose citation resolves in `EvidenceRegistry`. The single artifact that flips LIVE. No autonomous lane can produce it.

**Kaan-only:** Apple sign/notarize (step 9); the Windows-matrix exclusion + GA-tag push decision (step 10); the keystone ear-capture (step 11); the README partner-copy timing (step 3); proxy credits top-up.

---

## Corrections to the maps (staleness, both directions)

| Map claim | Reality at `d7d5337a` |
|---|---|
| "#1 blocker = VOICE REACHABILITY (mlx_audio not an extra, ref unbundled)" | **STALE — LANDED.** mlx-audio is an extra, ref bundles via the spec, model installs + prefetches, gate swapped. |
| "START GATE backend handler DARK" | **STILL DARK but for a DIFFERENT reason:** the backend is fully WRITTEN but UNCOMMITTED (dirty `__main__.py` + `session_loop.py`); committed HEAD has none of it. |
| "release-gate `--require-moss-source` swap REMAINS" | **STALE — swapped** to `--require-chatterbox-source` across pretag + release.yml (all sites). |
| "security gate `test_no_api_key_surface.py` RED on the BYO key field (D2 open)" | **STALE — GREEN.** Gate scoped to allow one masked surface; 4 passed. D2 resolved. brain-group moved to `settings/components/`. |
| "3 SHIP-READINESS RED gates" | The named ones (5 persona tests, auto_crate, tsc) are green; the live RED is the 4-test v4-audit ISOLATION FLAKE (passes alone) + the README partner-copy policy gap. |
| "binaries/*.placeholder for Intel/Windows" | No `binaries/` dir at all now; arm64-only, cleaner than the map says. |
| "README swapped to bravoh.ai" | **HALF-TRUE.** Funnel links swapped; product copy still leaks Gemini/altidus.world/MOSS/bravoh.com/ozzaii + dev matrix. |

---

## Bottom line for the organizer

- **Decisions 1 (VOICE) and 2 (BRAIN) are LANDED in source and SRC-green.** Voice went FURTHER than the map claimed (the map's #1 blocker is resolved).
- **Decision 3 (START GATE) is the real PKG blocker: it is correct + tested but UNCOMMITTED.** Commit `__main__.py` + `session_loop.py` first — this single act unblocks the sidecar-freshness gate AND puts the start gate into the build. Without it, a HEAD DMG ships dark on the gate's core promise.
- **Decision 4 (STREAK) is correctly NOT-STARTED.**
- **Tag-blockers before any `v0.1.0`:** (a) commit the seam files, (b) fix the v4-audit isolation flake so full CI is green, (c) exclude Windows from the `release.yml` v* matrix (not just the local flag), (d) reconcile README partner-copy (GA-public, not binary-blocking), (e) org signing secrets.
- **LIVE is Kaan's:** the co-host has never spoken live; the keystone capture is the only thing that flips the LIVE tier and no read-only/autonomous lane can produce it.
