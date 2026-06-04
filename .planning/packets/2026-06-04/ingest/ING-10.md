# ING-10 — SRC proof tier (adversarial done-claim verification, ship-ingestion pass)

## HEAD read at

- **Committed HEAD = `d7d5337a175ac90612702c3adda4d17aa3918899`** (`test(config): isolate device defaults from rig env`), branch `ux-redesign-impeccable`, 2026-06-04.
- The whole-system map (`SHIP-MAP-MASTER.md`) was synthesized at `7ac35a84`. Since then the voice + start-gate + citation-ts loops landed (commits `0e5590c5`, `eec239ac`, `18dc95cb`, `7082fb8d`, `fddddfc9`, `d67e6f81`, `ae30e16e`, `aaa330ad`, `8c0c0ffa`). Several map "DARK" claims are now superseded — corrected inline below.
- **Working tree is DIRTY on two ship-critical files** (`src/vibemix/__main__.py` +738 lines, `src/vibemix/runtime/session_loop.py` +72 lines, both uncommitted). This is the single biggest adversarial finding and it changes the SRC verdict on the START GATE (see §3). Proof tiers never conflated: **SRC** (green tests on source) ≠ **PKG** (in a signed DMG built at HEAD) ≠ **LIVE** (a stranger reaches it). `test-passing-but-dark = 0`.

Remotes: `bravoh` = `github.com/Bravoh-ai/vibemix.git` (GA target), `origin` = `github.com/ozzaii/vibemix.git` (legacy). Tags: `v0.1.0-rc1` present; **no GA `v0.1.0` tag yet** — the landmine has not fired.

---

## ⚠ HEADLINE FINDING — the START GATE backend is uncommitted, not at HEAD

The START GATE backend handler (locked decision #3) and the voice env-seed are **SRC-green but live ONLY in the dirty working tree of a concurrent session — they are NOT at committed HEAD `d7d5337a`.**

Evidence:
- `git show HEAD:src/vibemix/__main__.py | grep -c "_start_live_session|_activate_session|session_start="` → **0**. None of the start-gate symbols are at committed HEAD.
- `git show HEAD:src/vibemix/runtime/session_loop.py | grep "_on_session_start|ipc.session.start"` → **none at HEAD** (only `_on_settings_set_brain`/`set_brain` is committed at `:279`/`:423`).
- `git diff src/vibemix/runtime/session_loop.py` shows every start-gate line as a `+` add (uncommitted): `register_handler("ipc.session.start", self._on_session_start)`, `_on_session_start`, `_on_session_stop`, `session_start`/`session_stop` ctor params.
- `git diff src/vibemix/__main__.py` (+738) carries the entire `_activate_session`, `_RunGatedMusicState` cold-shell, `_is_live_session_active`, `_start_live_session`/`_stop_live_session`, `session_start=`/`session_stop=` wiring, AND the `_apply_packaged_defaults` env-seed body (was `return None` at HEAD, now seeds `VIBEMIX_TTS_ENGINE`).
- The committed test `18dc95cb` (`test(start-gate): lock idle-cold`) and its commit message assert "the START-gate backend ... was already implemented and green" — **but the implementation it tests is NOT committed.** `tests/test_main_smoke.py::test_smoke_03b_idle_is_cold_until_start` + `test_smoke_03_full_wiring` **PASS on the dirty working tree** (2 passed) but would FAIL against committed-HEAD source (the code they exercise does not exist at HEAD).

**Consequence:** committed HEAD is internally inconsistent — it carries a test (`18dc95cb`) whose subject code is only in another session's uncommitted buffer. If that buffer is lost (stash drop, checkout, machine reset), committed HEAD has a RED test and a DARK start gate. **The start gate must be COMMITTED before any DMG/tag, and the `__main__.py`/`session_loop.py` dirty state is a `source_dirty` PKG-freshness blocker right now.** Verdicts below carry both a working-tree (WT) and a committed-HEAD (HEAD) state where they differ.

---

## Locked decision #1 — VOICE (Chatterbox-only, MOSS nuked) — LANDED (source), reachability-wired

Map said "source-side DONE; reachability + bundle + gate-swap REMAIN". **All five remaining wires the SHIP-NEXT goal listed have now LANDED.** Per-piece verdicts:

| Wire | Status | Evidence | Tier |
|------|--------|----------|------|
| MOSS nuked | LANDED | `src/vibemix/agent/local_tts.py` deleted; `grep -rni "require-moss|install_moss" scripts/ .github/ src/` = **NO lingering moss gate**; `fddddfc9 refactor(voice): retire legacy moss runtime` | SRC |
| (1) `mlx-audio` as a `pyproject.toml` extra | LANDED | `pyproject.toml:162` + `:167` `"mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"` (Apple-arm64 marker, no hard dep elsewhere) | SRC |
| (2) bundle `cohost_voice_ref.wav` | LANDED | `vibemix-core.macos.spec:36` imports `collect_chatterbox_ref_datas`, `:307` `datas.extend(collect_chatterbox_ref_datas())`; `scripts/dist/chatterbox_bundle.py:30 collect_chatterbox_ref_datas()`; `chatterbox_tts.py:106 resolve_ref_path()` prefers bundled (`bundled_ref_candidates()`) then dev-cache `_DEV_REF` | SRC |
| (3) `install_chatterbox_model()` + CLI + progress | LANDED | `library/model_assets.py:490 install_chatterbox_model(...)` with pinned `CHATTERBOX_MODEL_REPO="mlx-community/chatterbox-turbo-8bit"` (`:34`), revision pin (`:361 chatterbox_model_revision`), `ModelProgress` callback (`:550`), CLI target whitelist `{"required","clap","chatterbox","cue","all"}` (`:840`), wired into `install` dispatch (`:855-859`); `eec239ac feat(voice): preflight pinned chatterbox model` | SRC |
| (4) env-seed `VIBEMIX_TTS_ENGINE` at `__main__` | LANDED (WT) / DARK (HEAD) | `__main__.py:1063` (in `_apply_packaged_defaults`, uncommitted body) + `:1434` (boot path). **Both edits are in the +738 uncommitted diff** — at committed HEAD `_apply_packaged_defaults` is still `return None`. | SRC(WT) only |
| (5) release gate `--require-moss-source` → `--require-chatterbox-source` | LANDED | swapped at every site: `pretag_check.sh:109/111/113` (`--require-chatterbox-ref --require-chatterbox-source`), `check_sidecar_bundle_ready.py`, `check_macos_app_bundle_ready.py`, `check_macos_dmg_artifact_ready.py`, `check_windows_app_payload_ready.py`, `check_macos_updater_artifact_ready.py`, `release.yml:356/400/427/542`; `7082fb8d build(voice): require packaged chatterbox reference` | SRC |

Reachability logic is honest and complete: `chatterbox_available()` (`chatterbox_tts.py:124`) returns True only when `mlx_audio` spec found + ref resolves + `chatterbox_model_cached(...)`; otherwise `chatterbox_unavailable_reason()` (`:133`) gives an actionable string ("mlx-audio not installed", "no reference clip", "model not downloaded ... complete first-run download"). `engine_selected()` (`:119`) defaults to `chatterbox`. `tts_chain.py` is Chatterbox-only, no MOSS/cloud fallback.

- **VERDICT: VOICE = LANDED at SRC.** All five wires present (env-seed only in WT). **DARK at PKG/LIVE** by definition: no signed HEAD DMG exists, the 675MB model is first-run-fetched (not in any DMG), and no run has had nonzero `voice_rms` (LIVE = Kaan's hand on the rig). The #1 blocker the map named ("`mlx_audio` not an extra → voiceless forever") is **NO LONGER a code gap.** What remains for voice is PKG (build the arm64 DMG, bundle deps+ref) + LIVE (model fetch + ear) — owner/external, not a wire.
- **Note (W17 governance, still open):** the CI model-literal grep only matches `gemini-*`; voice/audio IDs (`chatterbox_tts.py:40`, `model_assets.py:34`, `cue_detr.py`) drift silently green. Not a regression, a coverage gap.

---

## Locked decision #2 — BRAIN (hosted proxy default, funded) — LANDED

| Claim | Status | Evidence | Tier |
|-------|--------|----------|------|
| Client default flips direct→proxy | LANDED | `runtime/config_store.py:271 llm_mode: str = "proxy"`; boot resolves `mode = (load_config().llm_mode or "proxy")` with `except: mode = "proxy"` (`__main__.py:1135-1138`) | SRC |
| `set_brain` BYO handler | LANDED (committed) | `session_loop.py:288 register_handler("ipc.settings.set_brain", self._on_settings_set_brain)`, `:486 _on_settings_set_brain` validates mode, persists `llm_mode`, writes key to `brain_env_path()`; **this one IS at committed HEAD** (`git show HEAD` confirms `:279`/`:423`) | SRC |
| No-key graceful (no `sys.exit`) | LANDED | `__main__.py:1147-1165`: mode `direct` with no `GEMINI_API_KEY` → prints "trying Bravoh proxy" + `mode = "proxy"`; proxy setup failure sets `brain_unavailable_reason` + `_log_brain_unavailable(...)` (`:1173-1180`), **never exits**. The only `sys.exit` near brain (`:1143`) fires solely on an *invalid* `VIBEMIX_LLM_MODE` value (not a fresh-user path). The two other `sys.exit(3)` (`:1517`, `:1573`) are missing-audio-device faults with an actionable BlackHole hint, not brain crashes. | SRC |
| Proxy live + funded | NOT-RE-VERIFIABLE here | `proxy_client.py`, `jwt_cache.py:79` register POST `{base}/api/vibemix/v1/register`, base `https://api.altidus.world`. End-to-end register→JWT→200 was verified same-day by the ingestion brief; read-only I cannot re-hit it (and would not, network-gated). Credits are a Bravoh-ops flag. | LIVE (external) |

- **VERDICT: BRAIN = LANDED at SRC. The fresh-user crash the older maps called #1 is FIXED** — confirmed no `sys.exit` on the no-key path. LIVE depends on proxy credits (Kaan/ops).

---

## Locked decision #3 — START GATE (idle=cold, Start activates, Stop releases) — LANDED at WT, DARK at committed HEAD

This is the headline finding (§ above). Per-piece:

| Piece | WT status | HEAD status | Evidence |
|-------|-----------|-------------|----------|
| `register_handler("ipc.session.start"/.stop", ...)` in session_loop | LANDED | **DARK** | `session_loop.py:278-279` (uncommitted `+` lines) |
| `_on_session_start`/`_on_session_stop` handlers (null-safe, error-enveloped) | LANDED | **DARK** | `session_loop.py:331-371` (uncommitted) |
| `main()` split: light idle boot + `_activate_session` | LANDED | **DARK** | `__main__.py:1592 "SHIP-WIRE START gate"`, `:1704 _activate_session`, `:1697 _is_live_session_active` (all uncommitted) |
| idle = cold (no resident model/state) | LANDED | **DARK** | `__main__.py:1624 _RunGatedMusicState` returns `_COLD` dict (`session_active=False`, all bands 0, `phase="silent"`) until `_is_live_session_active()`; `chatterbox` "armed (loads on Start)" not constructed at boot (`__main__.py:1437` diff: removed eager `ChatterboxLocalTTS()`) |
| lifecycle callbacks wired into bus | LANDED | **DARK** | `__main__.py:2238-2239 session_start=_start_live_session, session_stop=_stop_live_session`; `:2179 _activate_session(...)`, `:2184` timeout guard (uncommitted) |
| frontend Start/Stop button + emit | LANDED (committed) | LANDED | `session/render-loop.ts:74-91` `emitIpc("ipc.session.start"/.stop", {})` with optimistic `setSessionState({runState})`; `session/state.ts:201 runState?: "armed"|"running"`; schema `messages.schema.json:1430/1453` (`ipc.session.start`/`.stop` consts). `tests/session/start-gate.spec.ts` **6/6 pass** (vitest). |
| idle-cold lock test | committed, PASSES on WT | committed, would FAIL on HEAD | `tests/test_main_smoke.py::test_smoke_03b_idle_is_cold_until_start` + `test_smoke_03_full_wiring` — 2 passed on dirty WT |

- **VERDICT: START GATE = LANDED-BUT-UNCOMMITTED.** SRC-green only against the dirty working tree. **At committed HEAD it is CLAIMED-BUT-DARK** (test committed, impl not). PKG = impossible until committed (`source_dirty` fails the sidecar-freshness gate). **Action: commit `__main__.py` + `session_loop.py` surgically (CLAUDE.md shared-commit hazard applies — `git add` exact paths, verify `git diff --cached --name-only`, the third dirty file `CLAUDE.md` belongs to another session).**

---

## Locked decision #4 — STREAK (Daft-Punk Technologic robot voice, sequenced) — NOT-STARTED (correct)

- No robot-voice engine wired. The sequencing prerequisite is intact and correct: the streak signal today is `runtime/suggestion.py:1365/1391/1450 _attach_grade_progress` which grades its OWN un-played suggestion (self-applause, an Invariant #3 risk). Per locked decision #4 this MUST be rebound onto a cited EXECUTED transition before any robot voice fires.
- **VERDICT: NOT-STARTED, correctly deferred.** Not v1-launch-critical. The self-applause strip (W7/R7) is the gating prerequisite and is still present (do not ship robot voice on it).

---

## Other map-flagged DARK items — re-checked at HEAD

| # | Item | Map state | HEAD re-verdict | Evidence |
|---|------|-----------|-----------------|----------|
| Seam D / #6 | citation-receipt ts-carry | DARK | **LANDED (committed)** | `d67e6f81 fix(session): share cohost reaction timestamp with transcript`; `dj_cohost.py:1880 _push_transcript(self, text, *, ts=None)`, `:4163 self._push_transcript(pending_transcript_text, ts=reaction_msg_ts)`; `ws_bus.py` reuses the shared ts. The "sentence underlines its own citation" gesture now shares a ts source instead of two `_now_iso()` calls. SRC only (LIVE = real run). |
| #3 / W12 | `[ev:BEATMATCH_GRADED]` live credit | DARK | **PARTIAL — improved** | `8c0c0ffa fix(learn): credit live beatmatch grade receipts` landed; verify on real-set path remains (LIVE). |
| — | Viber auto-cue provenance / cue spine | DARK risk W13 | **routed** | `4831b226 fix(library): route Viber auto-cues through cue landing spine` — narrows the two-spine divergence (W13). |
| — | packaged chatterbox prefetch | n/a | **LANDED** | `0e5590c5 fix(voice): prefetch chatterbox for packaged launch` |
| #10 / R10 | evidence_registry → recorder kwarg | DARK | NOT-RE-CHECKED in this pass (out of the 4-decision scope; flag carried) | `__main__.py:1262` recorder ctor — recommend a follow-up single-kwarg check |

---

## Gate inventory at HEAD (RED set + fix + product-regression-vs-stale-repin)

All gates I could safely run read-only. Result: **every gate the maps flagged RED is now GREEN.** The README CI gates pass, but a separate **partner-copy policy violation persists that NO gate catches** (see below).

| Gate | Result | Notes |
|------|--------|-------|
| `tests/repo/test_readme_shape.py` | **GREEN** (53 passed, combined w/ matrix) | map said RED (altidus assert) → **re-pinned to bravoh.ai** (`aaa330ad test(repo): re-pin README funnel to bravoh.ai`). STALE-policy fix landed. |
| `tests/repo/test_readme_feature_matrix_sync.py` | **GREEN** | AUTO-GEN markers + `sync_feature_matrix.py --check` pass. |
| `scripts/launch/check_readme_grids_a11y.py` | **GREEN** (exit 0) | "DJ-software grid (6) + controllers grid (10) — alt-text + balance + no slop". |
| `scripts/check_readme_hero_hash.py` | **GREEN** (exit 0) | hero sha256=PLACEHOLDER sentinel intact ("pending Kaan-action"). |
| `tests/security/test_no_api_key_surface.py` | **GREEN** (4 passed) | map's D2 head-on conflict RESOLVED — `ae30e16e test(security): scope BYO key surface gate` scope-narrowed the Phase-33 gate so the locked-decision-#2 in-GUI BYO key field coexists. STALE-policy re-pin landed. |
| `tests/repo/test_model_literal_gate.py` + `tests/bench/test_no_model_literal.py` | **GREEN** (12 passed) | no hardcoded `gemini-*` literals. (Coverage gap W17: voice/audio IDs not matched.) |
| `tests/repo/test_clean_checkout_imports.py` | **GREEN** (2 passed) | committed untracked-module imports resolve. |
| `tests/repo/test_repo_scrub.py` | **GREEN** (11 passed) | retired POC files stay gone. |
| `tests/learn/test_no_speculative_phrase.py` (Inv#3 AST gate) | **GREEN** (4 passed) | |
| IPC schema parity (`tests/ipc/` + `tests/ui_bus/test_messages_schema.py`) | **GREEN** (160 passed) | |
| `tauri/ui` codegen:ipc | **IN SYNC** | re-ran `codegen-ipc.mjs`, `git diff` on `validator.generated.mjs`/`messages.ts` = empty (validator current). |
| `tsc --noEmit` | **GREEN** (exit 0) | |
| `tests/session/start-gate.spec.ts` (vitest) | **GREEN** (6 passed) | |
| `tests/library/test_auto_crate.py` (stop-reason) | **GREEN** (8 passed) | |

**RED set: empty at the test layer.** The only test-vs-source mismatches the map screamed about (2 README asserts + key-surface conflict) are all re-pinned GREEN. No product regression found in the gate suite.

**The real RED is hidden — not a CI gate, but the partner-copy policy:**
- `README.md` GREEN on all 4 structural gates yet VIOLATES the public-facing policy on **content** the gates do not inspect:
  - **Model names leaked:** "Sven uses Bravoh's Gemini path" (`README.md:271`), "Why Gemini and not GPT/Claude/Llama?" (`:269`), "Gemini is Google's" (`:283`), "MOSS voice path" (`:229`, `:241`, `:271`) — 11 gemini/moss mentions. Policy = "AI model"/"on-device voice", never the engine name.
  - **`api.altidus.world` leaked 3×** (`:39`, `:241`, `:259`) — policy = "Bravoh's hosted service", never the endpoint.
  - **Internal dev slop:** Phase numbers (`:130-149` full feature matrix with "Phase 96/104/91…"), commit SHAs (`:139` `c740fd90 → 617b663b → …`), "Kaan ear-passes daily" (`:69`), "KAAN-ACTION" (`:11/:30/:86/:198`), "v0.1.0-rc1 rater grading" (`:279`) — 14 internal-slop tells.
  - **MOSS is stale-in-copy:** README still says speech renders through "the local MOSS voice path" (`:229/:241/:271`) — MOSS is NUKED; the copy is now factually wrong as well as policy-violating.
- **Fix:** rewrite README partner copy (strip model names → "AI model"/"on-device cloned voice"; replace `api.altidus.world` → "Bravoh's hosted service"; delete the Phase/SHA/KAAN-ACTION feature-matrix dump; correct MOSS→Chatterbox/on-device). This is a **product/launch regression** (public GitHub README ships internal-slop + leaks the prod endpoint), NOT a stale test re-pin. It does not block the test matrix (gates are structural) but it MUST land before the repo goes public on `Bravoh-ai/vibemix`. Recommend adding a partner-copy lint gate (no `gemini`/`moss`/`altidus.world`/`Phase \d`/`KAAN` in README body) so this stops being uncaught.

---

## GA-TAG LANDMINE — confirmed ARMED at HEAD

- `release.yml:57-60` triggers on `push: tags: ['v*']`. Its build matrix is **hardcoded arm64 + x86_64** (`:283-290`) AND stages **Windows MSVC** (`:540 --triple x86_64-pc-windows-msvc`). `companion-sign.yml:18 tags: [v*]` fires a **`windows-latest` SignPath** job (`:69`).
- **`VIBEMIX_PRETAG_MAC_ONLY` does NOT defuse the workflow.** It is only read by the LOCAL `scripts/dist/pretag_check.sh:148` (skips the SignPath gates locally). The GitHub `release.yml`/`companion-sign.yml` matrices are NOT gated by it. **Pushing `v0.1.0` to `Bravoh-ai/vibemix` would fire the full Windows + x86_64 + SignPath matrix in CI**, regardless of the mac-only intent.
- The `--require-moss-source`→`--require-chatterbox-source` swap that the older landmine called out IS done (release.yml `:356/400/427/542`), so that half is defused. The remaining live landmine is the **Windows/x86_64/SignPath matrix on `v*`** + secrets readiness on the new org.
- **Status:** no GA `v0.1.0` tag exists yet (`v0.1.0-rc1` is the latest `v*`). Landmine has NOT detonated. **Fix is a workflow edit (gate the Windows/x86_64 legs behind a dispatch input or `matrix.exclude` for v1) OR an ops discipline (do not push `v*` until the org has secrets + Windows is intentionally scoped).** This is an ops/Kaan gate, not a product wire — but it is the single thing that turns "ship macOS-arm64 v1" into "accidental full-matrix release with a Windows build that has no GPU Chatterbox backend".

---

## 3-tier roll-up

- **SRC:** GREEN. Every gate the maps flagged RED is re-pinned GREEN. The 4 locked decisions are wired in source — VOICE fully, BRAIN fully + committed, START GATE fully **but only in the uncommitted working tree**, STREAK correctly not-started. Citation ts-carry (Seam D) committed. **One internal inconsistency at committed HEAD:** the idle-cold test (`18dc95cb`) is committed while its start-gate implementation is not — commit the two dirty files to make HEAD self-consistent.
- **PKG:** BLOCKED. `__main__.py` + `session_loop.py` dirty → `source_dirty` fails the sidecar-freshness gate; no fresh signed arm64 HEAD DMG; the 675MB chatterbox model is first-run-fetched (not bundled). Every existing DMG is ~190–250 commits stale and the canonical one is unsigned. PKG path is otherwise unblocked (extra + ref-bundle + gate-swap all landed).
- **LIVE:** keystone never crossed. No run has nonzero `voice_rms`/`transcript_delta` over real audio; the co-host has never spoken live. Proxy credits + Apple notarize + (if `v*` pushed) the Windows matrix are external/ops gates. This tier flips only by Kaan's hand on the rig.

## The ordered ship-blocker list (post-Codex-DONE reality)

1. **COMMIT the start-gate + voice-env-seed** (`__main__.py`, `session_loop.py`) — turns START GATE from CLAIMED-BUT-DARK-at-HEAD into LANDED, makes the committed `18dc95cb` test honest, and clears `source_dirty`. (Code wire, surgical commit, CLAUDE.md shared-commit hazard.)
2. **README partner-copy rewrite** — strip Gemini/MOSS/`api.altidus.world`/Phase-SHA-KAAN slop; correct MOSS→on-device voice. (Launch regression, uncaught by any gate; add a lint.)
3. **Defuse the GA-tag landmine** — gate Windows/x86_64/SignPath legs in `release.yml`/`companion-sign.yml` for the arm64 v1, OR ops-hold the `v*` push until org secrets + intentional Windows scope. (Ops/workflow.)
4. **PKG:** build + sign the arm64 HEAD DMG (after #1), bundle deps+ref, first-run model fetch. (Kaan/external.)
5. **LIVE keystone capture** — Kaan's hand on the rig; the one artifact no read-only lane can produce. (Kaan.)
