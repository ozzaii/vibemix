# Handoff: v0.1.0-rc1 Integration Audit — Find What We Missed

**Date:** 2026-05-27 ~15:30 TRT (Wednesday, release day)
**Author:** previous session
**Branch state at handoff:** `live-tuning-or-brain` == `main` == origin (f0b3e453), 0/0 divergent.
**Mission:** **continue the audit.** This session believed everything was wired in. Verify that claim. Find what's broken, half-done, or invisibly degraded. Report what's actually shipping vs what we're claiming.

---

## Your mandate

You inherit a repo where the previous session executed a high-velocity rescue: 132 untracked files committed in 13 atomic commits, sync-debt resolved, 7 Apple secrets wired, pretag goes from 4 fail → 1 fail (ear-pass only), live runtime is up.

**Trust nothing in this doc by default.** Verify each verdict against the live codebase before reporting it up to Kaan.

**You may spawn additional `general-purpose` agents** to investigate any surface. Default agent budget is generous; if you find a real risk, spawn 2-3 more agents to triangulate. Each agent prompt should be sharp, time-bounded, and ask for **evidence with file:line citations**.

**Goal output:** a follow-up handoff doc (`.planning/handoffs/2026-05-27-rc1-integration-followup.md`) that:
- confirms or refutes each of the 6 prior audit verdicts below,
- surfaces any NEW issues we missed (broken surfaces, dead buttons, dangling features, marketing copy that overclaims),
- ranks each by **ship-impact**: BLOCKER / MARKETING-ACCURACY / FUTURE-CUT,
- proposes the minimal commit(s) to close each BLOCKER before tag.

Show your work. Cite file:line. Don't repeat what's already proven here — go where the gaps point.

---

## What we tried to do (release intent)

**v0.1.0-rc1, macOS-only, today (2026-05-27).** This is vibemix's first public release candidate:

- An AI DJ co-host (live cohost): listens to master output via BlackHole 2ch, watches the DJ app, ingests MIDI, talks back through headphones/speakers as hype-man or coach.
- A library mode: CLAP-onnx embeddings, vibe search, Codex-powered curator + set-builder + Rekordbox export.
- A post-session debrief: tactile analyzer console with TLDR/chapters/drills, opens automatically after a session closes.
- Mac-only for rc1 (Windows + SignPath approval in flight, ships v0.1.0 stable next week).

The promise: "real DJ friend in your ear, no AI slop". The anti-slop release gate is Phase 16 hallucination ear-pass.

## What landed this session (proven by tests + commits)

13 atomic commits on `live-tuning-or-brain`, fast-forwarded to `main`:

```
f0b3e453 feat(release): pretag rc-mode + mac-only flags, Discord pinned to Release notes
bbaada71 fix(hero-lock): swap genre-robust → genre-agnostic (AI-slop blocklist)
3c24cebe fix(repo-sync): regen feature matrix + AUDIT + orphans, archive-aware changelog
37527098 chore(planning): archive v2.1 phase detail + v8.2 milestone sweep (351 files)
e1a645a9 chore(lockfile): uv.lock + PyInstaller specs
16634880 docs: AGENTS.md + pill-hover mocks + v8.2 doc sweep (33 files)
3cb3b407 chore(infra): pyproject + workflows + scripts surface fixes (25 files)
dcdab364 feat(tauri): IPC + Rust shell + UI wiring for pill/library/intel surface (63 files)
a7ec691c feat(core): wire intel/section/cue into live runtime + suggestion path (118 files)
f953583c feat(debrief): analyzer-console UI rebuild + ?mock=1 sidecar-free preview (12 files)
7c001fdf feat(install/dist): macOS + Windows packaging chain — bundle-ready gates (44 files)
4664ae9c feat(library): Rekordbox ANLZ ingest + auto-cue engine + section builder (94 files)
585707ae feat(intel): grounded decision runtime + claim validation + replay eval (50 files)
f961e823 fix(eval/router-scan): teach Plan 41-01 audit to count resolve_model()
```

**Verification at handoff time:**
- pytest (excluding e2e/macbook): **5123 passed, 0 failed**, 20 skipped, 12 deselected, 1 xfailed, 4 xpassed
- vitest (tauri/ui): **929/929 passed**
- cargo check (tauri/src-tauri): green
- pretag (`VIBEMIX_PRETAG_MAC_ONLY=1 VIBEMIX_PRETAG_RC=1`): **5 pass / 1 fail / 2 warn** — only fail is Phase 16 ear-pass

**GitHub secrets wired this turn (all 11):**
- Apple: `APPLE_DEVELOPER_ID`, `APPLE_DEVELOPER_ID_P12_BASE64`, `APPLE_DEVELOPER_ID_PASSWORD`, `APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD`, `APPLE_API_KEY_ID` (`URMDRP5M3P`), `APPLE_API_KEY_ISSUER` (`3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b`), `APPLE_API_KEY_P8`
- Tauri: `TAURI_UPDATER_PRIVATE_KEY` (base64), `TAURI_UPDATER_KEY_PASSWORD` (empty — generated with no password May 13)
- Bravoh: `BRAVOH_MANIFEST_UPLOAD_TOKEN` = placeholder (workflow does NOT fail on 404; replace when Bravoh ops endpoint deploys)
- Pre-existing kept: `APPLE_TEAM_ID`

**Skipped this turn (mac-only):** 5 SignPath secrets — Windows path waits on SignPath OSS-program approval (multi-day).

**Live runtime currently running** (PID via `/tmp/vibemix-live.log`): `uv run python -m vibemix` — BlackHole 2ch listening, 1547 tracks indexed, pill next-suggestion armed, mascot bus on `ws://127.0.0.1:8765`.

---

## 6 integration audits — verdict summary

Six parallel `general-purpose` agents audited the post-Codex codebase end-to-end. Each returned <250 words with file:line evidence. Summarized below; full transcripts in `/private/tmp/claude-501/.../tasks/` (ephemeral, may not survive session boundary — re-run agents if you need raw text).

### 1. intel/ → runtime path
**Verdict:** PARTIALLY WIRED, closer to DARK.

`src/vibemix/intel/transition_scorer.py::score_transition_slate` IS called on the live pill ranking path (via `library/next_suggestion.py:209,245`). Everything else in `src/vibemix/intel/` — `decision_runtime`, `claim_validator`, `context_compiler`, `decision_validator`, `MusicClaimLedger`, `AgentContextEnvelope`, `decision_trace` — is **dark on the live path**. They are imported only from `library/toolset.py` (the Viber/curate MCP tool path) and from `tests/intel/`.

Grep `import vibemix.intel` in `src/vibemix/runtime/`, `agent/`, `state/`, `__main__.py` → **zero hits**.

**Implication for ship:** the pill renders deterministic section/cue/bars data from `transition_scorer`, which is real. But the "grounded decision with validated musical claims and traceable trace" framing that the intel/ package was built for is **not on the live path**. README/PROJECT.md copy that promises this is overstated.

**Gaps for next session to investigate or close:**
- Confirm: does `runtime/suggestion.py` need an `AgentContextEnvelope` for each pill payload + a `validate_agent_decision` call before broadcasting? If so, that's a real future-cut PR.
- Confirm: does `agent/dj_cohost.py` (Gemini live reactions) consult intel at all, or do reactions bypass claim grounding entirely?
- Confirm: should `MusicClaimLedger` be instantiated per session in `__main__.py` and threaded through `SuggestionService.__init__`?

### 2. section_builder + transition_scorer → next_suggestion
**Verdict:** WIRED end-to-end (with cold-case caveats).

`library/next_suggestion.py::transition_payload_for_candidate` (lines 209-281) calls `section_builder.{sections_for_entry, best_source_section, section_at_position, destination_sections, bars_until_section_end}` AND `intel/transition_scorer.score_transition_slate`. Builds real `{from_section_id, to_section_id, cue_slot, start_in_bars, timing_basis, score, risk_flags, reasons}` payload.

`__main__.py:1262` instantiates `SuggestionService(_library_store, deck_library)`; `:1394` passes it to `ws_broadcast(suggestion_holder=...)`. `runtime/ws_bus.py:503-508` merges `suggestion_holder.current_for_state(state)` onto every 30 Hz mascot frame.

UI: `tauri/ui/src/pill/next-suggestion.ts:168-183` renders "load B · cue A · in N bars". Vitest spec covers rendering at `next-suggestion.test.ts:122-146`.

**Caveats — real-world degradations the next session should test in a live run:**

1. **Folder-only library (no Rekordbox XML import)** → `deck_library.lookup_by_id(seed_track_id)` returns None for any track not xml-imported → `transition` collapses to None → pill shows track name but loses cue/bars tail.
2. **Low playhead confidence** — `SECTION_POSITION_CONFIDENCE_FLOOR = 0.50` (`state/refresh.py:610`). Below that, falls back to `best_source_section` and `bars_until_section_end` returns None — pill loses "in N bars".
3. **Weak beat lock** — `runtime/suggestion.py:138-151`, `bpm_confidence < 0.80` → `remaining_bars=None` → "in N bars" dropped.

**For next session:** a 30-second WS probe at `127.0.0.1:8765` during a real DJ session would confirm whether the pill actually emits transition data in production conditions, or whether confidence stays so low that the "load B · cue A · in N bars" experience is rare in practice.

### 3. ANLZ ingest → library DB
**Verdict:** WRITE-MISSING (parse + embed-influence only).

`vibemix library ingest --anlz ...` runs, auto-builds an `anlz_index`, threads it into `ingest_source(..., anlz_index=anlz_index)`. ANLZ is used by `_match_anlz_for_cache` (cache-key only) and `_embed_track_cue_anchored` (window selection for embedding). `store.add_batch([(track_id, vec)])` writes ONLY `(id, vector)`. **Phrases / cues / beatgrid / cue-labels are NEVER persisted.**

`library/section_builder.py:25-60` reads `entry.cues` (DJ hot cues from Rekordbox XML), with synthetic intro/outro fallback. **ANLZ is never imported.** The `source="anlz"` branch in `intel/transition_scorer.py:248` is unreachable.

`tests/library/test_ingest_cli_anlz.py:62-91` stubs `ingest_source` entirely — only asserts that `anlz_index` is passed as a kwarg, never that phrases land in any store.

**Implication for ship:** the "Rekordbox phrase-aware mixing" framing in PROJECT.md / docs is **false** at rc1. ANLZ improves audio embedding anchoring (cache-key precision). It does NOT make phrases queryable downstream.

**Gaps for next session:**
- Decide: does v0.1.0-rc1 need ANLZ-phrase materialization in the store, or is "ANLZ improves embedding precision" honest copy enough?
- If materialization is required: add a `phrases` table to `LibraryStore`, extend `add_batch` to accept phrase payload, extend `TrackEntry` and `RekordboxLibrary` to expose phrases, teach `section_builder.sections_for_entry` to prefer ANLZ phrases when present.

### 4. CLAP embedding backend
**Verdict:** PURE CLAP, ship clean.

`library/embed_factory.py:32-34` unconditionally returns `ClapEmbedder`; `library/_cosine.py:36-37` hard-codes `EMBED_BACKEND = "clap"`, `EMBEDDING_DIM = 512`. `library/grounding.py:120` routes through backend-agnostic `embedder.embed_audio_bytes()`. `library/store.py:29`, `index_numpy.py:25/53`, `index_sqlite_vec.py` all derive dim from `_cosine.EMBEDDING_DIM`.

Live probe with no `GEMINI_API_KEY`: `build_embedder()` → `ClapEmbedder`; `embed_query("driving acid techno")` returns `shape=(512,), norm=1.0`. **Works.**

Grep `LibraryEmbedder(` outside `library/embed.py` itself → zero hits in `src/`. The legacy `library/embed.py` LibraryEmbedder class is dead-but-importable for migration tests; nothing constructs it.

**Implication for ship:** "no API key needed for library" holds. Live co-host still needs `GEMINI_API_KEY` for the brain/TTS — that's expected.

**Cleanup (non-blocking) for a future PR:** retire `library/embed.py::LibraryEmbedder` when the last migration test is dropped.

### 5. Tauri UI wiring
**Verdict:** WIRED end-to-end across every surface (pill, library build-set, debrief). No silent schema drift. No dead-button stubs. No unregistered Rust commands.

- **Pill (`next_suggestion` + deck chips):** reads off the FLAT 30Hz mascot frame on `ws://127.0.0.1:8765` (`pill/index.ts:176-185, 568-595`). Backend `SuggestionService` instantiated + passed via `suggestion_holder` in `__main__.py`. Falls back to honest-null silence if `deck_library` or store is missing.
- **Library `build-set`:** UI button → `libraryBuildSet()` → Tauri command (`library_cmds.rs:577-608`) → CLI subprocess `library build-set ... --json` → Python `_cmd_library_build_set_codex` → `library/codex_curate.build_set_with_codex`. **Real Codex CLI subprocess, not stub.** Requires `VIBEMIX_CODEX_ALLOW_SHELL=1` + `codex login` + ChatGPT subscription. Fails actionably (honest), not silently.
- **Debrief (non-mock):** Rust `open_debrief_window` spawns sidecar `--debrief <session_dir>` → `debrief/main.py` validates dir, loads events.jsonl, runs Gemini drills/TLDR (with cache hit fast path), `DebriefWsServer` on `:8766` emits progressive frames the renderer consumes.
- **`?mock=1`:** mock-only by design (`debrief-window.ts:42-49`). Production users never see this URL.

**Documentation gap:** the dual-channel split (validated `ipc.session.snapshot` vs flat mascot frame for `next_suggestion`/`deck_state`) isn't called out in `messages.schema.json`. A Python contributor adding `next_suggestion` to `SessionSnapshot.make` would trip the validator with no breadcrumb.

**For next session:** confirm the pill end-to-end by probing `ws://127.0.0.1:8765` during the live run already in progress, and visually confirm "load B · cue A · in N bars" actually appears in the rendered pill DOM when a real track is playing through BlackHole.

### 6. Bundle / dist artifact (the ship-day audit)
**Verdict:** SHIPS WITH FIRST-RUN GOTCHAS — build itself will succeed cleanly on CI, but two silent-failure paths persist on the user's first launch.

**Build is fine:** `.github/workflows/release.yml:322-326` runs `scripts/build_sidecar.py --target-arch ${{ matrix.arch }}` fresh per tag on both `macos-14` (arm64) and `macos-13` (x86_64). CI ignores the local `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` (211 MB, built 13:39 today — PREDATES today's intel + library commits at 14:43+). CI rebuilds from source tree; `.gitignore` only allows `.placeholder` for git tracking. AST walking from `__main__.py` chains in 223 vibemix modules including the new `intel/`, `library/section_builder`, `library/smart_cues`, `library/cue_engine`, `audio/resample`, `agent/_livekit_google_slim`.

**Gotcha 1 — no first-run CLAP fetch.** `runtime/wizard.py` has zero `install_models` calls. CLAP ONNX weights (~785 MB across 6 files defined in `library/model_assets.py:_CLAP_FILES`) are downloaded only by the CLI subcommand `vibemix models install` (`__main__.py:2903`). On a fresh signed-app install:
- ✅ Live co-host works (Gemini Flash brain + TTS — small, network-bound)
- ❌ Library / Viber tabs silently degrade — CLAP files absent → `clap_engine.py:137` raises `RuntimeError` when the user clicks Library mode

**Gotcha 2 — CUE-DETR unhosted by default.** `model_assets.py:451-456` reads `VIBEMIX_CUE_ONNX_URL` env var. Not baked at packaging → smart-cue features error with `"set VIBEMIX_CUE_ONNX_URL..."` when invoked.

**Gotcha 3 — silent degradation in `next_suggestion`.** `library/next_suggestion.py:209-262` wraps the section/transition path in `try/except Exception: return None`. Any future module-missing regression here will be silent — pill just shows nothing.

**Gotcha 4 — no regression test for bundled-module completeness.** `tests/dist/` covers AIza leak + 60s gate. A `tests/dist/test_pyz_module_coverage.py` that extracts the PYZ and asserts every `vibemix.*` .py is present would catch stale-spec / bundle-coverage drift.

**Gotcha 5 — local `cargo tauri build` (NOT CI) will ship broken .app.** The stale 211 MB sidecar in `binaries/vibemix-core-aarch64-apple-darwin/` was built 13:39 today, PREDATES `4664ae9c` (library expansion, 14:43) and `585707ae` (intel, 15:00+). Any local dev who runs `cargo tauri build` without first re-running `scripts/build_sidecar.py` produces a .app that hits `ModuleNotFoundError: vibemix.library.section_builder` on Library/Viber.

**For next session — three real PRs worth considering before tag:**
1. Wire `models install` into wizard first-run (or surface a "Library not ready — install models" CTA in the Library tab UI).
2. Add `tests/dist/test_pyz_module_coverage.py` to lock the bundle module set against `src/vibemix/`.
3. Add a `cargo tauri build` pre-hook (or CONTRIBUTING.md prominent warning) that runs `scripts/build_sidecar.py` first.

---

## Ranked summary — what's actually shipping vs what's claimed

| Claim in PROJECT.md / README / docs | Reality | Severity |
|---|---|---|
| Live co-host listens, watches, talks back | TRUE (verified live runtime up) | ✅ |
| Section-aware "load B · cue A · in N bars" pill | TRUE in healthy state; degrades to track-only on folder-libs or low confidence | ⚠ test in real run |
| Rekordbox phrase-aware mixing | FALSE — ANLZ phrases parse but never persist; consumers read XML hot cues only | 🟠 marketing-accuracy fix |
| Grounded decisions with validated musical claims | FALSE on live path — only `transition_scorer` reaches the pill; intel/ rest is dark | 🟠 marketing-accuracy fix |
| Library mode (CLAP search, Viber curator, build-set) | TRUE in code; first-run UX broken (no CLAP weights downloaded) | 🟠 first-run UX |
| Debrief analyzer auto-opens after session | TRUE | ✅ |
| One-click install macOS | TRUE post-CI build; local `cargo tauri build` shortcut produces broken .app | 🟠 dev-loop hygiene |
| No GEMINI_API_KEY needed for library | TRUE | ✅ |
| Bravoh proxy is closed-source by design | TRUE (carveout sentinel restored in CONTRIBUTING.md) | ✅ |

**BLOCKER count:** 0 (Phase 16 ear-pass excluded — that's a runtime gate, not a wiring gate).
**MARKETING-ACCURACY items:** 2 (phrase-aware, validated-claims overstatements).
**FIRST-RUN UX item:** 1 (CLAP auto-fetch).
**DEV-LOOP HYGIENE items:** 2 (stale local sidecar warning, bundle coverage test).

---

## Open questions for next session

1. **Is the pill actually emitting transition payload in the running live runtime right now?** Probe `ws://127.0.0.1:8765` for 30 seconds during DJ playback. If `next_suggestion.transition` field is consistently None even with a healthy session → folder-only or confidence-floor cold case is biting; promote one of the three caveats in audit #2 to BLOCKER.
2. **Does the Tauri shell start at all right now?** Vite dev server is on `:1420`, live Python runtime is on `:8765`. Confirm Kaan can open `http://127.0.0.1:1420/` in a browser and see live deck data (deck chip, BPM, pill payload) flowing. If not, find the wiring gap.
3. **Are there any UI surfaces we forgot to audit?** mascot.html (root-level Canvas 2D overlay, wired to ws_bus), wizard window (calibration flow), library window (sub-windows for build/curate/chat). Agents 5+6 covered pill/library/debrief; mascot + wizard windows + the recordings browser were NOT explicitly audited. Spawn an agent.
4. **Is `agent/_livekit_google_slim.py` actually loaded on the live path, or only a stub?** The slim wrapper replaces eager grpc loading. Confirm by checking what `agent/dj_cohost.py` imports at runtime.
5. **Phase 16 ear-pass:** Kaan does the run himself. If he flags any hallucinations or "scripted feel", that's a BLOCKER. If he signs off `.planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md` with `status: passed`, we tag.

---

## Tools you have

- **You may spawn `general-purpose` agents** for any of the open questions. Default budget: generous. Pattern: sharp question → ≤250-word reply with file:line evidence + verdict + gaps.
- **Live runtime is running** at handoff time. Use it. WS probe at `ws://127.0.0.1:8765` is cheap.
- **Tests are green.** Re-run after any change: `uv run pytest -q --no-header --ignore=tests/e2e/macbook`.
- **Pretag command:** `VIBEMIX_PRETAG_MAC_ONLY=1 VIBEMIX_PRETAG_RC=1 scripts/dist/pretag_check.sh`.
- **Tag command (when ready):** `git tag v0.1.0-rc1 && git push origin v0.1.0-rc1` — this triggers `.github/workflows/release.yml`. Workflow does fresh PyInstaller sidecar build + sign + notarize + create GitHub Release.
- **Commit hygiene:** Kaan's memory warns against `git add -A`; stage by named paths. He runs concurrent sessions on this tree.

---

## What success looks like for this next session

You deliver `.planning/handoffs/2026-05-27-rc1-integration-followup.md` containing:
1. **Confirmed or refuted** verdicts for each of the 6 audits above (with new evidence if you changed any).
2. **Newly discovered issues** the previous session missed (mascot, wizard, recordings, anything else).
3. **A ranked punch list** of BLOCKER vs MARKETING-ACCURACY vs FUTURE-CUT items.
4. **A concrete recommendation:** does Kaan tag `v0.1.0-rc1` right after Phase 16 signoff, or are there real BLOCKERs we should close first?

Cite file:line. Show your work. Don't repeat what's proven here — go where the gaps point.

Kaan is preparing his gin and doing the ear-pass. He'll come back to whatever you've found.

---

**End of handoff.** Branch `live-tuning-or-brain` is your starting point. Go.
