# ING14 — CRITICAL-PATH critic + GA-readiness (completeness audit of the other 13)

**HEAD read at: `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04, last commit `test(config): isolate device defaults from rig env`).
SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree advanced ~26 commits to this HEAD. Every line number below was re-pinned at `d7d5337a` against either committed source (`git show HEAD:...`) or the working tree (flagged explicitly).

Three proof tiers, never conflated: **SRC** (green tests on source) ≠ **PKG** (present + correct in a signed DMG built at HEAD) ≠ **LIVE** (a real stranger reaches it). `test-passing-but-dark = 0`. READ-ONLY pass: no product code edited, no sidecar launched.

This is the completeness-critic pass. ING-01..ING-13 covered the per-decision verification in depth. ING14 does three things they did not: (1) **adversarially resolve the one headline disagreement between the prior agents** by hitting the committed tree directly, (2) **name the surface the swarm most over-claimed**, (3) **sequence the shortest honest GA path** with file-island + Kaan-only ownership called out.

---

## THE HEADLINE FINDING — the swarm split on this and the optimists are WRONG

**The SHIP-CRITICAL START-GATE backend (locked decision #3) is NOT committed at HEAD. It lives entirely in the dirty working tree as an unprotected 803-line diff.**

The prior agents disagree on this exact point:
- **ING-01 §"DECISION 3"** and **ING-02 §"DECISION 3"** report START GATE as **LANDED end-to-end (SRC), both IPC ends wired, idle-cold test GREEN.** They read the WORKING TREE (where the symbols exist) and conflated working-tree-green with committed-HEAD. This is the precise trap the task warns about.
- **ING-07 §"Locked decision #3"** reports it as **CLAIMED-BUT-DARK at the commit level**, LANDED in dirty working tree only. ING-07 is **CORRECT**.

I verified by archiving HEAD to a clean tree (`git archive HEAD | tar -x`) and grepping the committed source:

| symbol | committed HEAD (`git archive`) | dirty working tree |
|--------|-------------------------------|---------------------|
| `_activate_session` in `__main__.py` | **0 occurrences** | `__main__.py:1704` |
| `_start_live_session` / `_stop_live_session` | **0** | `:2172` / `:2188` |
| `_silent_prewarm_hook` / `_RunGatedMusicState` | **0** | `:2200` / `:1624` |
| `"start gate: armed (idle..."` banner | **0** | `:2275` |
| `_on_session_start` in `session_loop.py` | **0** | `session_loop.py` (working) `:331` |
| `register_handler("ipc.session.start"...)` | **0** | (working) `:278/279` |
| `test_smoke_03b_idle_is_cold_until_start` in `tests/test_main_smoke.py` | **PRESENT** (line 800) | present |

The committed `__main__.py` carries ONLY the voice env-seed: `os.environ.setdefault("VIBEMIX_TTS_ENGINE", _tts_engine_seed)` at committed `__main__.py:1428`. Nothing else of the start gate.

Confirming provenance: the last 3 commits to touch `__main__.py` are `1a66cca0 feat(voice): make chatterbox the only cohost voice`, `0300dc93`, `c0814c94`. The start-gate feature commit `23f3167d feat(session): SHIP-WIRE START-gate` is LATER in `git log` but does **not** appear in `__main__.py`'s file history — proving `23f3167d` committed only the frontend + IPC schema half (its own body says exactly this per ING-07), and the `main()` restructure was never committed.

The diff size of the uncommitted seam: `git diff --stat` = `__main__.py` **+738 lines**, `session_loop.py` **+72 lines** = **803 lines of SHIP-CRITICAL code with zero git protection** on a shared tree where (per CLAUDE.md) any sibling's `git commit` absorbs everything staged and a sibling `git checkout`/`reset` could WIPE it.

**The consequence the optimists missed (the test-passing-but-dark inversion):** committed `tests/test_main_smoke.py:800 test_smoke_03b_idle_is_cold_until_start` and `:668 ipc.session.start` REQUIRE the uncommitted implementation. So a clean checkout of HEAD `d7d5337a` would (a) lack the Start gate in `main()` entirely, and (b) **FAIL `test_smoke_03b` and `test_smoke_03`** — the committed test requires a feature the committed source does not contain. CI on the committed tree catches this; the "73 start-gate tests green" the swarm reported is green ONLY against Kaan's local working tree.

**Verdict: START GATE backend = CLAIMED-BUT-DARK (commit level) / LANDED (working tree only). SRC = RED on clean checkout. PKG = impossible (`source_dirty` fails the freshness gate). LIVE = unreachable.** This is the #1 PKG blocker — ahead of voice, ahead of README — and it is an autonomous-fixable one-action commit, not a build.

---

## VERDICT TABLE — the 4 locked decisions at COMMITTED HEAD

| # | Decision | Committed-HEAD verdict | Tier | Evidence (committed unless noted) |
|---|----------|------------------------|------|-----------------------------------|
| 1 | VOICE = Chatterbox only, MOSS nuked, mlx-audio extra, ref bundle, gate-swap | **LANDED + committed** | SRC green; PKG/LIVE Kaan-gated | `config_store.py:65 DEFAULT_TTS_ENGINE="chatterbox"`; `local_tts.py` deleted; `pyproject.toml` mlx-audio extra; `pretag_check.sh`/`release.yml` `--require-chatterbox-source` (no `require-moss` left) |
| 2 | BRAIN = proxy default, no-key graceful, set_brain BYO | **LANDED + committed** | SRC green; LIVE proxy unverifiable read-only | `config_store.py:271 llm_mode="proxy"`; `session_loop.py:279/423 _on_settings_set_brain`; no missing-key `sys.exit` |
| 3 | START GATE backend handler + main() idle/activate split | **CLAIMED-BUT-DARK (commit), LANDED (working tree only)** | SRC RED on clean checkout; PKG/LIVE impossible | committed `__main__.py` = 0 gate symbols; 803-line uncommitted diff |
| 4 | STREAK Daft-Punk robot voice, sequenced behind re-grounding | **NOT-STARTED (correct, per lock)** | n/a | no `technologic`/vocoder code; self-applause signal `suggestion.py:1365` unchanged |

The corollary: **3 of 4 locked decisions are genuinely committed and SRC-green; the SHIP-CRITICAL one (#3) is not.** The swarm's "the build is done, the gap is commit→sign→capture" headline (ING-02) is half-right — but it under-states that the most important commit has not happened and a committed test currently asserts against absent code.

---

## CROSS-DECISION DONE-CLAIMS RE-VERIFIED (committed HEAD)

| claim | prior-agent verdict | ING14 committed verdict | evidence |
|-------|---------------------|------------------------|----------|
| mlx-audio is a pyproject extra | LANDED (ING-01/02/07) | **CONFIRMED LANDED** | `pyproject.toml` `tts-local`+`ai-local`, PEP508 `darwin and arm64` |
| ref clip PyInstaller `datas` + `resolve_ref_path` prefers bundled | LANDED | **CONFIRMED LANDED** | `vibemix-core.macos.spec:307` + `chatterbox_tts.py:106` (CAVEAT: `collect_chatterbox_ref_datas` returns `[]` if ref absent at build — `--require-chatterbox-ref` gate catches it on the release path only) |
| `install_chatterbox_model()` + `library models --install chatterbox` CLI verb | ING-01 PARTIAL; ING-02 "registered in --install chatterbox\|all" | **ING-01 CORRECT, ING-02 OVER-CLAIMED.** Installer landed (`model_assets.py`); CLI argparse `choices=("clap","cue")` at committed `__main__.py:4088` **rejects `chatterbox`**. `install_models()` dispatch accepts it but argparse blocks first. Verb DARK; wizard covers the real fetch. |
| env-seed `VIBEMIX_TTS_ENGINE` at boot | LANDED | **CONFIRMED LANDED + committed** | committed `__main__.py:1428` `os.environ.setdefault(...)` |
| release gate moss→chatterbox swap | LANDED | **CONFIRMED LANDED** | zero `require-moss` in `scripts/`+`.github/`; `--require-chatterbox-source`/`-ref` present; gate body does real HF revision-SHA check |
| citation ts-carry (Seam D, `d67e6f81`) | LANDED (ING-07) | **CONFIRMED LANDED + committed** | committed `dj_cohost.py:1880 _push_transcript(*, ts=...)`, `:4063/4081/4163 reaction_msg_ts` threaded |
| W12 `[ev:BEATMATCH_GRADED]` into live credit (`8c0c0ffa`) | LANDED (ING-07) | **CONFIRMED LANDED + committed** | committed `coach.py:264 _credit_live_beatmatch_grade_receipts`, called `:643`, 2.0s freshness |
| `set_brain` BYO handler | LANDED | **CONFIRMED LANDED + committed** | committed `session_loop.py:279/423` |
| no-api-key-surface gate scoped to BYO (D2, `ae30e16e`) | ING-01 "still RED"; ING-02/07 "GREEN/scoped" | **ING-01 STALE, ING-02/07 CORRECT.** `tests/security/test_no_api_key_surface.py:7` documents D2; `ALLOWED_BYO_KEY_SURFACE="brain-group.ts"`. Gate is GREEN — NOT a tag blocker. |
| README footer re-pin bravoh.ai (`aaa330ad`) | LANDED | **CONFIRMED** (footer only — body still violates, below) |
| **R10 recorder→evidence_registry** | ING-07 STILL DARK | **CONFIRMED STILL DARK at committed AND working tree** | `VoiceRecorder(root=recordings_root)` omits `evidence_registry=` — committed `__main__.py:1268`, dirty `:1274`. Recorder CAN write `evidence_registry.json` (`recorder.py:549-561`) but is never given the registry → debrief citations `found=false` on every long session. One-kwarg fix, still unwired. |

---

## WHICH SURFACE DID THE OTHER 13 AGENTS MOST OVER-CLAIM AS DONE?

**The START-GATE backend (decision #3), by a wide margin.** Two of the three agents who looked at it (ING-01, ING-02) reported it LANDED-and-committed-SRC-green because the symbols exist in the working tree they were reading. Only ING-07 ran `git show HEAD:` and caught that the entire 803-line `main()` restructure + `session_loop` handlers are uncommitted, and that a committed test asserts against the absent implementation. This is the canonical "test-passing-but-dark" failure the ingestion pass exists to catch, and the majority of the swarm fell into it.

Second most over-claimed: **the CLI `--install chatterbox` verb** (ING-02 said registered; it is argparse-rejected). Minor, but it shows the same pattern — reading the dispatch function and assuming the user-reachable verb follows.

Pattern lesson for the organizer: any "LANDED + SRC-green" claim about `__main__.py`, `session_loop.py`, or `config_store.py` (the three single-owner files with large uncommitted diffs) must be re-checked with `git show HEAD:` before it is trusted, because the working tree on this shared branch is routinely ahead of committed source by hundreds of lines.

---

## GA-TAG LANDMINE — STILL ARMED AND HOTTER THAN A SINGLE-JOB PROBLEM

The repo is now `Bravoh-ai/vibemix` (`main` pushed). A `v*` tag push fires the full signed cross-platform matrix, and `VIBEMIX_PRETAG_MAC_ONLY=1` does NOT defuse it — that flag only gates the LOCAL `scripts/dist/pretag_check.sh:148`, never the GitHub Actions matrix. Verified:

- `release.yml:59-60` trigger `tags: ['v*']`.
- `release.yml:271 build-macos` matrix = **BOTH** `arch: arm64 / macos-14` (`:283`) **AND** `arch: x86_64 / macos-13` (`:287`). The Intel-mac job runs unconditionally on a v-tag and is voiceless (mlx-audio is `darwin and arm64` only).
- `release.yml:470 build-windows` full SignPath job, unconditional on v-tag.
- `release.yml:678 verify-signed-publish-gate` `needs: [build-macos, build-windows]` and `::error`s if the x86_64 DMG (`:705`) or windows DMG is missing.
- `release.yml:739 release-publish` hard `::error` at `:770-774` if the **x86_64 updater artifact** is missing ("Intel macOS installs require darwin-x86_64 in latest.json").
- `check_updater_manifest_ready.py:17-18,120-122` REQUIRED_PLATFORMS includes `darwin-x86_64` + `windows-x86_64` — the all-3 requirement.
- **`companion-sign.yml` ALSO fires on `tags: [v*]`** (`:17-18`) with `companion-sign-windows` (windows-latest, `:67-69`) needing `SIGNPATH_API_TOKEN`/`SIGNPATH_ORG_ID` secrets (`:94-95`), and a final job `needs: [companion-sign-macos, companion-sign-windows]` (`:118`).
- `binaries/vibemix-core-x86_64-apple-darwin/` and `-windows-msvc/` are `.placeholder` only → Intel + Windows PKG = 0.

**Net:** pushing `v0.1.0` today fires Windows + Intel-mac matrix jobs that have no binaries and no SignPath secrets → the release FAILS the publish gate, AND the now-org repo may lack the macOS signing secrets too. **This is a hard GA blocker that requires a `release.yml` + `companion-sign.yml` EDIT** (condition the `build-windows`, `build-macos x86_64`, and `companion-sign-windows` jobs OFF for the arm64-only v1, OR relax `verify-signed-publish-gate` + `check_updater_manifest_ready.py` to arm64-only) BEFORE any tag. There is a `workflow_dispatch` + `dry_run` rehearsal path (`release.yml:61, 298`) — Kaan should rehearse via `workflow_dispatch dry_run=true` before the real tag. Local tags today: `v0.1.0-rc1` exists, **no `v0.1.0` GA** (landmine not yet tripped — good). The `0.1.0` non-`v` source-snapshot pre-release fired only the benign SBOM job (correct).

---

## README / PARTNER-COPY — CLAIMED-BUT-DARK (4 CI gates GREEN, every policy VIOLATED)

The README "looks shipped" and the 4 pinning gates pass, but the body violates every public-copy rule and is now factually wrong about the voice. Verified at HEAD:

- **Leaks `api.altidus.world`** (policy: "Bravoh's hosted service"): `README.md:39, 241, 259`.
- **Names "Gemini"** (policy: "AI model"): `README.md:39, 61, 149, 241, 259, 269, 271, 283, 287`.
- **Names "MOSS" as the live voice — and it is FACTUALLY WRONG (MOSS is nuked, voice is Chatterbox)**: `README.md:229` ("Sven speaks through the local MOSS voice path"), `:241`, `:271`. Double defect: model-name leak + stale lie.
- **`security@bravoh.com`** (policy domain `bravoh.ai`): `README.md:63`.
- **Old org `ozzaii/vibemix`** (policy org `Bravoh-ai`): `README.md:330` (release-notes link); also `pyproject.toml` URLs per prior agents.
- **Internal dev slop**: Phase numbers + "SHIPPED 2026-05-28" (`:134-149`), "Kaan ear-passes daily" (`:69`), KAAN-ACTION/KAAN-ACTION-LEGAL refs (`:10, 11, 30, 86, 134`).

The 4 CI gates do NOT check body prose: `test_readme_shape.py` (footer link only), `test_readme_feature_matrix_sync.py` (AUTO-GEN markers + `sync_feature_matrix.py --check`), `check_readme_grids_a11y.py` (dj grid 6 imgs / controller grid 10 cells vs `midi/profiles`), `check_readme_hero_hash.py` (hero `sha256=PLACEHOLDER` sentinel exits 0 when not-yet-shipped, `scripts/check_readme_hero_hash.py:90`). **A partner-copy rewrite must be coordinated with these gates** (especially the feature-matrix AUTO-GEN sync and the footer-link assertion) or `full-test-matrix` CI breaks. This is a real NOT-STARTED copy task, owner-visible, NOT a product-code change. CAVEAT: the MOSS→Chatterbox factual fix is also a release-honesty item, not just a cosmetic one.

---

## DEV-MACHINE PKG/LIVE REALITY (proximity, not proof)

- `chatterbox_available()` returns **True on this rig**: ref present (`~/.cache/vibemix/cohost_voice_ref.wav`, 384k), model cache present (`~/.cache/huggingface/hub/models--mlx-community--chatterbox-turbo-8bit`), `mlx_audio` INSTALLED in `.venv`. The voice CAN synthesize locally. This is a dev-rig fact, NOT a PKG (no signed HEAD DMG carries it) or LIVE (never spoken over real audio) proof.
- DMGs are all stale: `dist/vibemix-0.0.1.dmg` (487M, 09:59, unsigned per maps), `dist/fresh-20260604-wav-signed-v2/` — all predate the working-tree start-gate work. **PKG = 0 at HEAD.**
- LIVE = 0: no run has nonzero `voice_rms`; the co-host has never spoken in the cloned voice over real audio. The keystone is Kaan's hand on the rig and has no autonomous lane by definition.

---

## THE SHORTEST HONEST PATH — HEAD → signed arm64 GA v0.1.0

Goal: a stranger downloads the DMG, passes Gatekeeper, reaches the funded brain (proxy default), hears a grounded Chatterbox line, no crash. Ordered blocker sequence with ownership:

1. **COMMIT the START-GATE seam** — `git add src/vibemix/__main__.py src/vibemix/runtime/session_loop.py` (exact paths, NEVER `-A`; verify `git diff --cached` shows only these), then commit. This is the #1 blocker now (ahead of voice, which is fully committed). It (a) clears the `source_dirty` freshness gate, (b) un-fails the committed `test_smoke_03/03b`, (c) protects 803 lines from a sibling wipe. **Owner: the single-owner-`__main__.py` lane (autonomous-OK — it is a commit of existing green-in-working-tree code, not a build).** RISK: `__main__.py`/`session_loop.py` are single-owner; confirm no concurrent session is mid-edit before staging.

2. **One-line CLI verb fix (optional, low-cost)** — add `"chatterbox"` to `__main__.py:4088 choices=("clap","cue")` so ops can pre-fetch headless. Not GA-blocking (wizard covers it); bundle into the start-gate commit or a follow-up. **Autonomous-OK.**

3. **R10 one-kwarg wire** — `VoiceRecorder(root=recordings_root, evidence_registry=evidence_registry)` at `__main__.py:1268` so `evidence_registry.json` is written and debrief citations resolve. Trivial, real LIVE-tier defect. **Autonomous-OK, same island as #1.**

4. **README partner-copy rewrite** — strip `api.altidus.world`/`Gemini`/`MOSS`/`bravoh.com`/`ozzaii`/dev-slop; fix the stale MOSS→on-device-voice lie; coordinate with the 4 CI gates (re-run `sync_feature_matrix.py`, preserve footer + hero-comment structure). **Autonomous-OK (copy + gate-coordination), but the licensed-content/branding voice is Kaan's review.**

5. **GA-tag matrix de-arm** — edit `release.yml` (condition `build-windows` + `build-macos x86_64` + `verify-signed-publish-gate` + `release-publish` x86_64/windows requirements OFF for v1) + `companion-sign.yml` (condition `companion-sign-windows` off) + relax `check_updater_manifest_ready.py` to arm64-only (or ship v1 without auto-update, manual download). **Owner: Kaan/infra — touches release infra + needs the org signing secrets decision.** Rehearse first via `workflow_dispatch dry_run=true`.

6. **Build the fresh signed arm64 DMG at clean HEAD** — after #1-#4 commit: place the licensed ref WAV, build with the `ai-local`/`tts-local` extra (mlx-audio + ref in the spec), `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`, rebuild the DMG SEPARATELY (sidecar rebuild does not refresh the DMG), `scripts/dist/sign_macos.sh`, then `VIBEMIX_PRETAG_MAC_ONLY=1 scripts/dist/pretag_check.sh`. **Owner: Kaan (Apple notarize + signing secrets + licensed-ref placement).**

7. **KEYSTONE LIVE capture** — drive a real set into BlackHole 2ch, hear a grounded Chatterbox line whose citation resolves in `EvidenceRegistry`. Validates voice + grounding + Invariant #3 at once. **Owner: Kaan-only, LIVE=0 today, no autonomous lane.**

8. **STREAK robot voice** — deferred, sequenced behind re-grounding the streak off the self-applause signal (`suggestion.py:1365`) onto a cited EXECUTED transition. NOT v1-launch-critical.

**File-island collisions:** `__main__.py` + `config_store.py` are SINGLE-OWNER (the keystone/backend-boot lane) — steps 1, 2, 3 all live in `__main__.py` and MUST be one owner, one commit-set. IPC schema (`messages.schema.json`) is FRONTEND-lane only — none of the above touch it. One socket `127.0.0.1:8765` — `pkill -f "python -m vibemix"` before any probe.

**Kaan-only (no autonomous lane):** the GA-tag matrix de-arm + org signing secrets (step 5), Apple notarize + licensed-ref placement + DMG sign (step 6), the by-ear keystone capture (step 7), the `v0.1.0` tag push itself, proxy credits top-up, Free/Pro/Studio tier shape.

---

## THE SINGLE NEXT MOVE

**Commit the 803-line START-GATE seam (`src/vibemix/__main__.py` + `src/vibemix/runtime/session_loop.py`).** It is the highest-leverage, lowest-risk action: it converts the SHIP-CRITICAL decision #3 from "dirty working tree, clean-checkout-RED, one sibling-`git checkout` from oblivion" to committed-SRC-green, it un-fails the committed smoke tests, it clears the `source_dirty` PKG gate, and it is the gating dependency for every downstream step (the DMG cannot be built dirty; the keystone capture needs the Start gate to even run idle-cold). Voice reachability — the blocker the maps and most of the swarm named #1 — is already committed; the start gate is the actual laggard, and the swarm largely missed that because it was reading the working tree.

---

## VERDICT LEGEND RECAP

- VOICE #1 = **LANDED + committed** (SRC green); PKG/LIVE Kaan-gated. CLI `--install chatterbox` verb DARK (one-line).
- BRAIN #2 = **LANDED + committed** (SRC green); proxy LIVE unverifiable read-only.
- START GATE #3 = **CLAIMED-BUT-DARK at commit level** — 803-line uncommitted diff, committed test asserts against absent code, SRC RED on clean checkout. **The single most important finding; the surface the swarm most over-claimed.**
- STREAK #4 = **NOT-STARTED** (correct).
- Seam D ts-carry, W12 beatmatch credit, set_brain, proxy default, no-key graceful, moss-nuke, gate-swap = **all LANDED + committed**.
- R10 recorder→evidence_registry = **STILL DARK** (committed + working tree); one-kwarg fix.
- GA-tag landmine = **ARMED** — `release.yml` + `companion-sign.yml` fire the full Windows + Intel matrix on a `v*` push; `VIBEMIX_PRETAG_MAC_ONLY` does NOT gate the Actions matrix. Hard GA blocker, infra-edit + secrets, Kaan-owned.
- README partner-copy = **CLAIMED-BUT-DARK** — 4 CI gates green, every policy violated, MOSS reference factually stale. NOT-STARTED copy rewrite.
- moss_tts/ dir on disk = untracked residue, zero committed importers (`git grep -i moss src/vibemix` = empty) — harmless, cleanup-only.
