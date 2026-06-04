# SHIP-INGEST — post-"codexes-done" consolidated ship state (2026-06-04)

> Organizer hand-synthesis of the 14 surface ingests (`.planning/packets/2026-06-04/ingest/ING-01..14.md`), written with full session context (the 4 locked decisions, the proxy-live fact, the README de-slop done this session, the GA-tag landmine). Every load-bearing disagreement between the ingest agents was re-resolved against the CURRENT tree, not taken on their word.

**Synthesized at HEAD `23bd6c0e` (branch `ux-redesign-impeccable`, 2026-06-04).** The 14 ingests read at `d7d5337a`; HEAD has since advanced (the README de-slop `23bd6c0e`, the ingest script `322e8c44`). The start-gate / learn-orphan / R10 claims below were re-verified by `git show HEAD:` + working-tree grep at `23bd6c0e`. Three proof tiers, never conflated: **SRC** (green tests on source) ≠ **PKG** (in a signed DMG built at HEAD) ≠ **LIVE** (a real stranger reaches it). `test-passing-but-dark = 0`.

---

## Verdict

1. **GA-readiness: NO, by one commit-and-a-fix, not by missing engineering.** A fresh signed arm64 `v0.1.0` cannot ship today, but the gap is a commit + a learn-orphan fix + a DMG build + Kaan's keystone, not new feature work.
2. **The single next move: the backend-boot lane must lift the orphaned `LessonRuntime` above the `main()` return, then commit the 803-line start-gate seam** (`__main__.py` + `session_loop.py`). That one action converts the SHIP-CRITICAL start gate from dirty-working-tree to committed, un-fails the committed smoke tests, clears the `source_dirty` PKG gate, protects 803 unprotected lines from a sibling wipe, and stops the commit from darkening Learn.
3. **Counts:** 3 of 4 locked decisions LANDED + committed (VOICE, BRAIN, STREAK-correctly-deferred); 1 SHIP-CRITICAL (START GATE) real-but-UNCOMMITTED. Plus 1 newly-found severe bug (LessonRuntime orphaned by the start-gate refactor), ~5 small dark wires (R10, W5 route-doctor, W15 mac screen-watch, CLI `--install chatterbox` verb, doc 10→11 MIDI count), and the GA-tag landmine. README partner-copy: RESOLVED this session.
4. **Proxy is live + funded** (verified same-day: register → JWT → gemini-3.5-flash → HTTP 200 on the hosted service). The fresh no-key user reaches the funded brain by default; no `sys.exit` on the no-key path. The maps' "#1 fresh-user crash" is gone.
5. **GA-tag landmine still armed:** `release.yml` + `companion-sign.yml` fire the full Windows + Intel-mac signed matrix on a `v*` tag; `VIBEMIX_PRETAG_MAC_ONLY=1` does NOT gate the Actions matrix. Do not push `v0.1.0` until the matrix is scoped to arm64 + the updater keypair + signing secrets land.

---

## The headline: the start gate is real but uncommitted, and committing it as-is darkens Learn

**Re-verified at HEAD `23bd6c0e`:** `git show HEAD:src/vibemix/__main__.py | grep -c _activate_session` = **0**; working tree = **2**. `git show HEAD:src/vibemix/runtime/session_loop.py | grep -c _on_session_start` = **0**; working tree = **2**. Both files still `M`. The entire start-gate backend (decision #3) is an 803-line uncommitted diff on a shared branch.

The swarm split on this and the optimists were wrong: ING-01/02/03/04/08/13 reported START GATE "LANDED + committed, SRC-green" because they read the working tree; ING-07/09/10/11 caught it; ING-14 settled it by `git archive HEAD`. The current tree confirms ING-07/09/10/11/14. The committed `tests/test_main_smoke.py::test_smoke_03b_idle_is_cold_until_start` asserts against this absent implementation, so a clean checkout of HEAD is RED on the start-gate smoke tests and DARK on the gate itself.

**New severe finding (ING-05), confirmed at HEAD:** the start-gate refactor split `main()` with a top-level `return` at `__main__.py:2314`, but left the entire **Learn runtime in the dead tail**: `LessonRuntime(` is constructed at `:3606`, its loops spawn at `:3890`/`:3891` (`lesson_tick_task` / `live_grade_loop`), all past the `:2314` return = unreachable. So when this seam commits as-is, the sidecar never instantiates `LessonRuntime`; the Learn window opens and emits IPC to a backend with no consumer. Learn is SRC-green (896 tests) + PKG-buildable + LIVE-DARK. The fix is a WIRE: lift the `LessonRuntime` construction + its two task spawns + the learn IPC handler registration above the `:2314` return (Learn must run at idle, independent of Start), and pass `learn_progress` + `learn_state` into the live coach/refresh loops (today `__main__.py:2010` passes `learn_progress=None` and the live refresh loop never passes `learn_state`, so W12 live-beatmatch credit is triple-dark too). The ~1800 lines from `:2316` onward are the old eager-capture path, now dead after the return; prune before commit so reviewers and line-numbers are not misled.

**Consequence for sequencing:** "commit the start gate" is not a bare `git add`. It is: (a) lift the LessonRuntime above the return, (b) wire `learn_progress`/`learn_state` into the live path, (c) prune the dead tail, (d) commit `__main__.py` + `session_loop.py` surgically. This is the keystone/backend-boot lane (single-owner `__main__.py`), an engineering action, autonomous-capable, the #1 ship blocker.

---

## Every surface (state at HEAD `23bd6c0e`)

| Surface | State | Tier | Anchor / gap |
|---|---|---|---|
| VOICE reachability (mlx extra, ref bundle, model fetch, env-seed, gate-swap) | **LANDED + committed** | SRC green; PKG/LIVE Kaan-gated | `pyproject.toml:162/167` mlx-audio arm64 extra; `vibemix-core.macos.spec:307` ref datas; `model_assets.py:490`; gate `--require-chatterbox-source` (zero `require-moss` left). The maps' "#1 blocker" is RESOLVED. |
| BRAIN proxy-default + set_brain + no-key graceful | **LANDED + committed** | SRC green; LIVE proxy verified same-day | `config_store.py:271 llm_mode="proxy"`; `session_loop.py` `_on_settings_set_brain`; no `sys.exit` on no-key (`__main__.py:1157-1181`) |
| START GATE backend + main() idle/activate split | **REAL but UNCOMMITTED** (dirty working tree) | SRC RED on clean checkout; PKG impossible | `git show HEAD` = 0 gate symbols; 803-line diff; **darkens Learn if committed as-is** |
| LEARN teaching loop | **CLAIMED-BUT-DARK (LIVE)** — orphaned by the start-gate return | SRC green (896 tests); LIVE dark | `main()` return `:2314` strands `LessonRuntime` `:3606` + loops `:3890/91`; W12 also blocked by `learn_progress=None` `:2010` + no `learn_state` to live refresh |
| LIBRARY + cue moat | **LANDED + committed, LIVE end-to-end** (healthiest subsystem) | SRC green | CLAP+sqlite-vec; cue moat non-destructive; VM-provenance closed; Viber auto-cue default-on; W13 resolved-by-design (shared building blocks, deliberate no-double-write) |
| Cue Tray | **backend LANDED, frontend DARK** | SRC | `library_land_cues` Tauri cmd + `cue_landing.land()` + CueSet summary/target/floor all wired; NO `tauri/ui/src/library/cue-tray.ts` (A-H ladder), 0 FE callers |
| INTEL → spoken line | **PARTIAL (the narrator→coach gap is real)** | SRC | `eq_move_model` speaks (always, via `apply_live_claim_guard`); `transition_judge` speaks but abstains on master-only rig; scorer/grade/risk reach voice ONLY via the pill payload, two-deck-gated → on the bare rig only the EQ-move guard fires |
| Citation receipt ts-carry (Seam D) | **LANDED + committed** | SRC; LIVE-pending-keystone | `dj_cohost.py:1880/4163` shares `reaction_msg_ts`; `ws_bus.py:786` honors it → FE join byte-matches live |
| RUNTIME-IO (ws/audio/midi/screen) | **LANDED** core; small dark wires | SRC | single socket Inv#4; 2ch-first determinism; 11 MIDI profiles; MIDI activity honest. DARK: route-doctor `top_signal` RMS-flip (`learn_live_readiness.py:922`, W5), mac screen-watch djay-only (`_screen_macos.py:470`, W15), NI HID ingest seam (post-ship) |
| Debrief evidence_registry (R10) | **DARK** | SRC dark | `VoiceRecorder(root=recordings_root)` `:1274` omits `evidence_registry=` → `evidence_registry.json` never written → debrief citations `found=false`. One-kwarg fix |
| Fresh-user E2E | **blocked at Start (uncommitted) + voice PKG** | LIVE 0 | wizard LIVE, brain LIVE (proxy), voice source-ready; Start backend uncommitted; keystone never crossed |
| Organism particle visual | **LANDED, real Three.js physics** | SRC | `particle-organism.ts` ShaderMaterial/BufferGeometry, not random dots |
| Pill receipts (reasons cap / cue_confidence / runner-up) | **NOT-STARTED** | SRC | reasons still `.slice(0,2)`; no cue_confidence/alternatives on the wire |
| Wizard telemetry-consent + key/proxy step | **NOT-STARTED** | SRC | `ipc.telemetry.set_consent` phantom emit (no schema/handler); no key/proxy step (non-blocking, proxy-default carries the fresh user) |
| README / docs partner-copy | **RESOLVED this session** | SRC green | committed `23bd6c0e` (de-slop + 2 test re-pins + matrix-gate retire); the ingests read the pre-fix README at `d7d5337a` |
| STREAK robot voice | **NOT-STARTED (correct)** | n/a | self-applause signal `suggestion.py:1365` unchanged; must rebind to a cited EXECUTED transition first |

---

## Codex done-claims, adversarially verified

**REAL + committed (trust these):** MOSS nuke (`local_tts.py` deleted, zero `require-moss` repo-wide); mlx-audio arm64 extra; ref-bundle spec wire + `resolve_ref_path` bundled-first; `install_chatterbox_model` + wizard prefetch; the moss→chatterbox release gate-swap (gate body does a real HF pinned-revision check); proxy-default + no-key-graceful + `set_brain` BYO; citation ts-carry (Seam D); W12 `[ev:BEATMATCH_GRADED]` consumer wired into the reaction loop; W13 cue-landing consolidation; the no-api-key-surface gate scoped to the BYO field (D2 resolved); the README footer bravoh.ai swap. The whole CI/supply-chain layer (24 SHA-pinned workflows, dual SBOM/CVE, gitleaks surgical, P46 audits).

**test-passing-but-dark (claimed done, not real on the ship path):**
- **START GATE backend** — real code, uncommitted; committed test asserts against it; clean checkout RED. (#1)
- **LEARN runtime** — 896 green tests, but orphaned past the `main()` return → never runs live. (new severe)
- **W12 live beatmatch credit** — consumer wired + unit-tested, but `learn_progress=None` + `session_active=False` on the live path → never credits a real set.
- **CLI `library models --install chatterbox`** — `install_models()` accepts it but argparse `choices=("clap","cue")` rejects it; wizard covers the real fetch.

**STILL DARK (carried from the maps, confirmed):** R10 recorder→evidence_registry (one-kwarg); W5 route-doctor `top_signal` flip; W15 mac screen-watch app-agnostic; pill receipts; wizard telemetry phantom.

---

## 3-tier ship state

**SRC — green on the working tree; one clean-checkout RED + one isolation flake.**
- Default suite, vitest, tsc, IPC parity (81==81), clean-checkout-imports, no-speculative-phrase AST, repo-scrub, model-literal, README gates, no-api-key-surface = GREEN on the working tree.
- **Clean-checkout RED:** committed `test_smoke_03/03b` require the uncommitted start gate → RED on a fresh clone. Fixed by committing the seam.
- **Isolation flake (ING-11):** `tests/repo/test_v4_milestone_audit_present.py` (4 tests) passes in isolation, reds under the full run (shared-CWD pollution) → blocks `full-test-matrix` until quarantined. Not a product regression.
- Dark-but-green: Chatterbox tests pass via the engine seam without mlx-audio, so SRC-green never proves the voice plays.

**PKG — blocked + every distributable stale.**
- Blocked by the dirty `__main__.py` + `session_loop.py` (`source_dirty` fails the sidecar-freshness gate) until the start-gate seam commits.
- `dist/vibemix-0.0.1.dmg` is unsigned + ~224 commits behind HEAD; all `dist/` snapshots predate the voice/start-gate work. arm64-only (no Intel/Windows binaries). Do NOT evaluate HEAD from any DMG.
- Updater-manifest gate hard-requires 3 platforms → relax to arm64-only for v1, or ship v1 without auto-update.

**LIVE — keystone never crossed.**
- No run has nonzero `voice_rms` or a `transcript_delta` over real audio. The co-host has never spoken live. This is the single artifact that flips LIVE, Kaan-only, no autonomous lane.

---

## README / docs — RESOLVED this session

The ingests (read at `d7d5337a`) all flag the README leaking Gemini/MOSS/altidus/bravoh.com/ozzaii + the dev feature-matrix dump. **That is fixed at HEAD `23bd6c0e`:** full de-slop rewrite (model names → "AI model"/"on-device voice", host → "Bravoh's hosted service", bravoh.ai, bravoh-ai org), the auto-gen Phase/SHA matrix killed for a hand-written "What's inside", honest macOS-arm64-v1/Windows-v1.1 framing, 0 em-dashes; the 2 coupled asserts re-pinned (`Why Gemini` → `Which AI runs the co-host`, `v0.1.0 stable` → `v1.1`) and the 5 matrix-sync tests retired; all 4 README gates green. Residual doc nits (carried, low priority): `pyproject.toml` URLs still `ozzaii`; `SECURITY.md`/`PRIVACY.md` carry `security@bravoh.com` + `api.altidus.world`; `docs/code-signing-policy.md` + `docs/windows-setup.md` `ozzaii` slug; the 10→11 MIDI count in CLAUDE.md/docs. A partner-copy CI lint (ban `gemini`/`moss`/`altidus`/`Phase \d`/`KAAN` in README body) would stop this regressing.

---

## Critical path to a signed arm64 GA v0.1.0

1. **Lift the LessonRuntime above the `main()` return + wire learn_progress/learn_state into the live path, then commit the start-gate seam** (`__main__.py` + `session_loop.py`, surgical). The #1 blocker. Un-darks Learn + W12, un-fails the committed smoke tests, clears `source_dirty`, protects 803 lines. (backend-boot lane, single-owner `__main__.py`, autonomous-capable)
2. **R10 one-kwarg** — `VoiceRecorder(root=recordings_root, evidence_registry=evidence_registry)` at `:1274`. Same island as #1. (autonomous)
3. **Small dark wires (optional, same lane):** add `chatterbox`/`all` to the `--install` CLI choices; W5 route-doctor `:922` 2ch discriminator; W15 mac screen-watch app-agnostic.
4. **Fix the `full-test-matrix` v4-audit isolation flake** so CI is green under a full run. (autonomous)
5. **GA-tag matrix de-arm** — condition `build-windows` + `build-macos x86_64` + the `verify-signed-publish-gate`/`release-publish` x86_64+Windows requirements OFF for v1; fix `companion-sign.yml` `SIGNPATH_ORG_ID`→`SIGNPATH_ORGANIZATION_ID`; relax `check_updater_manifest_ready.py` to arm64; replace the `TAURI_UPDATER_PLACEHOLDER` pubkey. Rehearse via `workflow_dispatch dry_run=true`. (Kaan/infra + secrets)
6. **Build the fresh signed arm64 DMG at clean HEAD** — place the licensed ref WAV, build with the `ai-local` extra, build sidecar, rebuild DMG separately, sign + notarize. (Kaan: Apple notarize + signing secrets + licensed-ref placement)
7. **KEYSTONE LIVE capture** — drive a real set into BlackHole 2ch, hear a grounded Chatterbox line whose citation resolves in `EvidenceRegistry`. (Kaan-only, LIVE=0 today)
8. **STREAK robot voice** — deferred, sequenced behind re-grounding off the self-applause signal.

**Kaan-only:** the GA-tag matrix de-arm + org signing secrets + updater keypair (5); Apple notarize + licensed-ref placement + DMG sign (6); the by-ear keystone (7); the `v0.1.0` tag push; proxy credits top-up; Free/Pro/Studio tier shape.

---

## Corrections to the maps + to the over-claiming agents

- SHIP-MAP `7ac35a84` "#1 blocker = voice reachability (mlx not an extra)" — **STALE/RESOLVED** (extra + bundle + fetch + gate-swap all committed).
- SHIP-MAP "fresh-user crash #1" — **RESOLVED** (proxy-default, no `sys.exit` on no-key).
- SHIP-MAP "START-GATE backend DARK (schema landed, backend absent)" — **truer than stated:** the backend is fully WRITTEN but UNCOMMITTED; committed HEAD has none of it.
- SHIP-MAP "4 README RED gates + no-api-key-surface block a tag" — **STALE/GREEN**; the real README issue was partner-copy (now fixed this session).
- **Over-claiming agents (lesson for next time):** any "LANDED + SRC-green" claim about `__main__.py`/`session_loop.py`/`config_store.py` must be checked with `git show HEAD:` before trust — the working tree on this shared branch runs hundreds of lines ahead of committed source. ING-01/02/03/04/08/13 reported the start gate committed; it is not. ING-07/09/10/11/14 verified against the committed tree and were correct.

---

## Doc index delta (since SHIP-MAP-MASTER)

- `SHIP-INGEST-2026-06-04.md` — THIS doc, the post-codexes-done consolidated state at `23bd6c0e`. Supersedes SHIP-MAP-MASTER for current ship state.
- `ingest/ING-01..14.md` — the 14 raw surface verifications (read for file:line depth).
- `SHIP-NEXT-GOALS-2026-06-04.md` — the per-lane goals + the 3 resolved decisions (D1 mlx 8bit, D3 macOS-arm64-v1, the GA-tag landmine note). Still the operative goal doc; add the LessonRuntime-orphan fix to the start-gate goal.
- `SHIP-MAP-MASTER.md` — superseded for ship state; keep for architecture orientation.
- README de-slop landed `23bd6c0e`; the ingests' README sections are stale (pre-fix).
