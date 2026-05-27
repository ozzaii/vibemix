# Followup: v0.1.0-rc1 Integration Audit — What Else We Missed

**Date:** 2026-05-27 ~17:30 TRT (Wednesday, release day, ear-pass pending)
**Author:** session 2 (followup to `2026-05-27-rc1-integration-audit.md`)
**Branch state at handoff:** `live-tuning-or-brain` == `main` == origin (`3d2900ce`), 0/0 divergent.

---

## TL;DR for whoever picks this up

The previous handoff said the only ship blocker was the Phase 16 ear-pass. **That was wrong.** There was a real ship blocker in `vibemix-core.{macos,windows}.spec` that would have made every signed DMG crash on first launch — including the one CI would have built from a `v0.1.0-rc1` tag. We found it, fixed it, regression-tested it, and shipped the fix (`3d2900ce`).

Phase 16 ear-pass is now genuinely the only remaining ship blocker.

---

## The bug we found this session

### PyInstaller spec part-name blocklist excluded `livekit.agents.cli`

**Symptom (frozen sidecar boot):**

```
ImportError: cannot import name 'cli' from partially initialized module
'livekit.agents' (most likely due to a circular import)
  File "vibemix/agent/dj_cohost.py", line 49, in <module>
  File "livekit/agents/__init__.py", line 23, in <module>
  File "livekit/agents/voice/__init__.py", line 3, in <module>
  File "livekit/agents/voice/agent_session.py", line 26, in <module>
```

**Root cause:** the spec's `_runtime_submodule` filter contained `"cli"` in its part-name blocklist. The match logic is `any(part in blocked for part in parts)`, so EVERY module name whose dotted parts contain "cli" was excluded — including `livekit.agents.cli`, a real runtime requirement of `livekit-agents` 1.x (`livekit/agents/voice/agent_session.py:26` does `from .. import cli, inference, llm, stt, tts, utils, vad`). The bundle was built without that submodule, then crashed at first import the moment voice tried to load it.

**Why dev never saw it:** `uv run python -m vibemix` uses Python's normal import resolution against the live package on disk — no spec, no part-name filter. Only PyInstaller bundles missed it.

**Why the previous bundle "worked":** it didn't. The previous (May 21) bundled sidecar was the spawn target listed in the handoff's status snapshot, but there's no evidence it ever bound `:8765` after wizard exit. Standalone smoke of the May 21 bundle in main mode would have produced the same crash.

**Why this would have shipped:** `.github/workflows/release.yml` rebuilds the sidecar from source per tag via the same `scripts/build_sidecar.py` + same spec. Tagging `v0.1.0-rc1` would have produced a signed, notarized DMG that boot-crashed on the user's first launch.

### Fix (commit `3d2900ce`)

- Removed `"cli"` from the part-name blocklist in both `vibemix-core.macos.spec` and `vibemix-core.windows.spec`.
- Added explanatory comment in both specs pointing at the regression test.
- Added regression test `tests/dist/test_spec_blocklist_keeps_livekit_cli.py` that asserts the `blocked = {...}` literal in each spec does not contain a bare `"cli"` entry, parametrized over both spec files (2 cases, both fail RED on pre-fix specs, both pass GREEN after).

### Post-fix verification (standalone sidecar smoke, fresh `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/`):

| Mode | Pre-fix | Post-fix |
|---|---|---|
| `vibemix-core --help` | exit 0 (short-circuits before imports) | exit 0 |
| `vibemix-core --wizard` | insta-crash | ws bus on `:8765`, 10 handlers, tcc-prime, graceful exit |
| `vibemix-core --session` | insta-crash | ws bus on `:8765`, 11 handlers, memory store, recorder armed |
| `vibemix-core` (no args, live main) | insta-crash | privacy posture printed, techno profile, auto-detect ON, recovers crashed sessions, recorder armed |

All 4 modes now boot clean.

---

## Re-verdicts of the previous handoff's 6 audits

The previous handoff had 6 parallel `general-purpose` agents triage the codebase end-to-end. This session re-spawned 6 fresh agents to verify the verdicts.

### 1. `intel/` → runtime path
**Re-verdict: DARK confirmed.** Grep `from vibemix.intel` and `import vibemix.intel` across `src/vibemix/runtime/`, `src/vibemix/agent/`, `src/vibemix/state/`, `src/vibemix/__main__.py` → **zero hits.** Symbol-name grep for `MusicClaimLedger|AgentContextEnvelope|claim_validator|decision_runtime|decision_validator|context_compiler|decision_trace` across the same paths → **zero hits.** Only consumers: `library/section_builder.py:15` (transition_scorer.SectionRecord), `library/next_suggestion.py:209` (lazy transition_scorer), `library/toolset.py:45,46,233,241,308` (Viber MCP path — non-live). Previous session right.

**Wiring sketch (if a future session wants to lift it):**
- `src/vibemix/__main__.py:1238` — allocate a session-scoped `MusicClaimLedger()` next to the `suggestion_service = None` init; thread to both `SuggestionService` (`:1262`) and `DJCohost` (existing constructor).
- `src/vibemix/runtime/suggestion.py:266` — after `next_suggestion(...)` returns, call `context_compiler.compile_transition_context(...)` → `decision_runtime.decide(...)`; only update `self._current` if `result.emitted`. Honest silence on suppress.
- `src/vibemix/agent/dj_cohost.py:2206` — wrap `_build_citation_strip(reaction_text=...)` with `validate_decision_claims(envelope, AgentDecision(...))`; on `rejected`, swap to ack-bank fallback BEFORE `await self._ipc_bus.emit(...)` at `:2218`.

Connective tissue: ~30 LOC. Adapter to build `AgentContextEnvelope` for the live path: ~50-80 LOC. Reference shape lives in `library/toolset.py:233-308`.

**Recommendation:** the previous session deferred this to v0.1.1. **Confirmed defer — fixing copy is enough** because the existing `EvidenceRegistry` + citation-strip path at `dj_cohost.py:2203-2218` provides Invariant #2's first line of defense; shipping rc1 without `claim_validator` is "degraded-grounded", not "ungrounded". This session's copy fixes (commit `6114bd0d`) align the README with reality.

**Note for the parallel session:** another Codex session is actively wiring `src/vibemix/intel/{context_compiler,transition_scorer}.py` plus `src/vibemix/library/{cache_paths,next_suggestion,store,toolset}.py` plus `tests/intel/`, `tests/eval/test_intel_decision_runtime_replay.py`, `scripts/eval/intel_*.py`, `scripts/dev/generate_intel_fixtures.py`, and `tauri/ui/src/debrief/`. That's roughly the wiring sketch above being executed live. Coordinate before further intel/ work.

### 2. section_builder + transition_scorer → next_suggestion
**Re-verdict: WIRED end-to-end, same caveats hold.** `library/next_suggestion.py::transition_payload_for_candidate (lines 209-281)` builds the real `{from_section_id, to_section_id, cue_slot, start_in_bars, timing_basis, score, risk_flags, reasons}` payload. `__main__.py:1262` instantiates `SuggestionService(_library_store, deck_library)`; `:1394` passes it to `ws_broadcast(suggestion_holder=...)`. `runtime/ws_bus.py:503-508` merges `suggestion_holder.current_for_state(state)` onto every 30 Hz mascot frame. UI `tauri/ui/src/pill/next-suggestion.ts:168-183` renders "load B · cue A · in N bars". Vitest spec `tauri/ui/tests/.../next-suggestion.test.ts:122-146` exercises the render.

**Cold-case caveats unchanged:** folder-only library → `transition` collapses to None; `SECTION_POSITION_CONFIDENCE_FLOOR=0.50` at `state/refresh.py:610` → low playhead falls back to `best_source_section` and drops `bars_until_section_end`; `bpm_confidence < 0.80` at `runtime/suggestion.py:138-151` → `remaining_bars=None`.

**Live WS probe attempt this session:** sidecar wasn't running at the time of probe; standalone smoke (`--session` mode) showed the bus binding `:8765` with 11 handlers + memory store + recorder armed, but no synthetic playback was driven. **Ear-pass run is the right place to confirm pill emits transition data with a real audible deck.**

### 3. ANLZ ingest → library DB
**Re-verdict: WRITE-MISSING confirmed.** `library/ingest.py` consumes `anlz_index` only for embed-cache namespacing (`_match_anlz_for_cache`, `:200-253`) and window selection (`anchors_for_track`, `:409`). Parsed `AnlzTrackMeta.phrases` (`anlz_ingest.py:78`) never crosses into `store.add_batch` (which is vector-only, `store.py:53`). `library/section_builder.py:25-30,109` only reads `entry.cues` (XML hot cues), with synthetic fallback — no ANLZ branch. `intel/transition_scorer.py:248` `elif source == "anlz"` is unreachable; grep for `cue_source="anlz"` in `src/` → 0 hits. Test stubs out the work (`tests/library/test_ingest_cli_anlz.py:69` monkeypatches `ingest_source` itself).

**Patch sketch (if a future session wants to land phrase persistence — ~85 LOC):**
- `store.py`: new `track_phrases (track_id, idx, cue_label, mood, kind, start_beat, end_beat, start_s, end_s, confidence)` table.
- `store.py:53::add_batch` keyword-only `phrases=` extension; backend `add_phrases` method on `index_sqlite_vec` (`:67`) + `index_numpy` (`:93`).
- `ingest.py:526/556`: pass `phrases={track_id: anlz_meta.phrases} if anlz_meta else None`.
- `section_builder.py:20::sections_for_entry`: prefer ANLZ phrases when present, fall back to XML cues.
- Callers (`toolset.py`, `next_suggestion.py`): one-line `LibraryStore.get_phrases(track_id)` before the call.
- Migration: schema is additive (`CREATE TABLE IF NOT EXISTS`), but the resumable-cache contract `INGEST_CUE_STRATEGY_VERSION` would need a bump or careful coexistence.

**Recommendation:** confirmed defer to v0.1.1. Today's PROJECT.md + ROADMAP.md copy fix (commit `6114bd0d`) reframed "phrase contexting / phrase position" → "phase-chain history / phase-chain position" (the actual mechanism is `phase_history`, not Rekordbox phrases). The README does not contain a literal "phrase-aware" claim.

### 4. CLAP embedding backend
**Re-verdict: PURE CLAP, ship clean.** `library/embed_factory.py:32-34` unconditionally returns `ClapEmbedder`; `library/_cosine.py:36-37` hard-codes `EMBED_BACKEND="clap"`, `EMBEDDING_DIM=512`. Live probe with no `GEMINI_API_KEY`: `build_embedder()` → `ClapEmbedder`; `embed_query("driving acid techno")` returns shape `(512,)`, norm `1.0`. Grep `LibraryEmbedder(` outside `library/embed.py` → 0 hits in `src/`.

The legacy `library/embed.py::LibraryEmbedder` is dead-in-product, alive in 5 migration tests (`tests/library/test_embedding_ga_probe.py:27`, `test_embed.py:29`, `test_embed_clap.py:15`, `test_folder_ingest.py:386`, `test_grounding_router_dispatch.py:16`) — KEEP-AS-MIGRATION-FIXTURE.

### 5. Tauri UI wiring
**Re-verdict: WIRED end-to-end across pill / library / debrief / mascot / wizard / recordings.** This session's audit added the three surfaces the previous one skipped:

- **mascot.html (root-level Canvas 2D overlay):** wired to `runtime/ws_bus.py:459-492` (broadcast emits the `{music, voice, mic, audible, deck, phase, bpm, mood, ...}` frame shape mascot.html:218 reads). DEFAULT-HIDDEN (opt-in flip via Settings; `tauri/src-tauri/src/main.rs:178-191` defaults primary surface to Pill). CI gate `.github/workflows/mascot-audit.yml` covers bundle / manifest / anti-slop / tauri-only-grep / event-coverage. **Ship: SHIP** (opt-in surface; nothing breaks if user never enables).

- **wizard (first-run calibration):** `tauri/src-tauri/src/main.rs:136,148` `is_first_run()` → sidecar `--wizard`. `src/vibemix/runtime/wizard.py:110-136` wires 10 IPC handlers (permissions, list_devices, probe_audio, user_heard_tone, start_midi_listen, list_windows, smoke_test, wizard_done, wizard_start, profile_set_consent). UI step order: permissions → audio → controller → profile-consent → telemetry-consent → smoke-test. **One UX gap:** wizard finishes → `write_first_run_state(first_run_completed=true)` → user lands in main. CLAP weights are absent at this point; user has to navigate to Library tab to discover the install button. **Ship: SHIP-WITH-LIBRARY-DISCOVERY-CAVEAT** (the install flow is real, the discovery path is "user clicks Library tab first time"; not blocking).

- **recordings browser:** mounted inside Settings drawer at `SettingsDrawer.ts:831-843`, not a separate window. `loadRecordings()` fires `ipc.recordings.list` on drawer open. `session_loop.py:265-267, 357-397` handlers registered. Debrief button at `recording-row.ts:491-500` invokes `open_debrief_window` with `sessionDir`. Empty state at `recording-browser.ts:391-396` has proper `role="status"`. Debrief disabled when `duration < 300s OR event_count < 5` with explanatory tooltip — not a dead button. **Ship: SHIP** (no dead buttons, empty state handled).

### 6. CLAP first-run UX
**Re-verdict: previous audit was a FALSE ALARM.** The agent who flagged "no first-run CLAP fetch" missed the wiring. Live trace:
- `tauri/ui/library.html:170-176` — Models row + `vmx-lib-install-models` button live in Library shell, initial text "checking…"
- `tauri/ui/src/library/index.ts:1086` — `void refreshModels()` fires on `mountLibrary()`
- `index.ts:751-753` — `libraryModels()` → `api.ts:525 invoke("library_models")`
- `tauri/src-tauri/src/library_cmds.rs:774` — `library_models` cmd registered, shells `vibemix library models --install …`
- `index.ts:458-471,931` — `deriveModelSetupView` reveals button "Install Required Models" when CLAP missing; click → `installLocalModels()` (`index.ts:759-786`)
- `index.ts:1077-1080` — subscribes to `library://embed-progress` for live "1/6 audio_model.onnx 48 MB / 281 MB" status
- `library/model_assets.py:131-202` — per-8MB-chunk progress + atomic tempfile rename + size+SHA verify
- `library/clap_engine.py:319-325` — `FileNotFoundError` from `embed_audio_file`/`embed_query` if user somehow bypasses the button (NOT line 137 the audit cited — that's `onnx_model_status` which is import-safe)
- Tests pin this: `library/model-setup.test.ts` + `api.test.ts` + `build.test.ts` + `chat.test.ts` all hold contract green.

**Real wiring path:** `mountLibrary → refreshModels → status JSON → deriveModelSetupView → button visible → click → progress events → re-fetch → green`. The audit-flagged "first-run UX gap" doesn't exist on the user-clicks-Library flow. **The only genuine gap:** user who never opens Library tab never sees CLAP status. The 1-line polish would be hoisting `library_models()` status into the wizard's last step as a read-only line — agent #6 explicitly said "Not blocking for rc1."

---

## Newly discovered issues

### NEW-1 (BLOCKER, FIXED): spec part-name blocklist excluded `livekit.agents.cli`
See top of doc. Fixed in `3d2900ce`. Regression-guarded.

### NEW-2 (NON-BLOCKER, observed): memory store dimension-mismatch warnings
Standalone `--session` smoke emits ~20 warnings of the form:
```
[vibemix.memory.ingest] [ingest] session 20260525-114230 failed: Dimension mismatch
for inserted vector for the "embedding" column. Expected 768 dimensions but received 512.
```
These are pre-existing — old session snapshots (768-dim Gemini embedding era) failing to re-ingest against the current 512-dim CLAP store. Non-fatal: ingest skips, runtime continues. **Recommendation:** add a session-scoped suppression for `Dimension mismatch` errors when the old vector dim != current `EMBEDDING_DIM`, OR ship a one-shot purge script for pre-CLAP sessions. **Not blocking rc1** (the noise is cosmetic, the live path doesn't depend on re-ingesting historic sessions).

### NEW-3 (FUTURE-CUT): bundle-coverage regression test
Agent #6 of the previous handoff recommended `tests/dist/test_pyz_module_coverage.py` that extracts PYZ and asserts every `vibemix.*` module is present. The NEW-1 bug would NOT have been caught by that test (it's a third-party submodule, not vibemix). But a related test that extracts PYZ and asserts every module declared in `vibemix-core.macos.spec`'s hidden_imports + `collect_submodules` outputs IS present would have caught NEW-1. Worth adding for v0.1.1.

---

## Concurrent-Codex situation (heads-up for next session)

At time of writing, Kaan reported 3 concurrent Codex sessions running on this same working tree. Observed modifications in working tree (not by this session):

```
src/vibemix/intel/context_compiler.py
src/vibemix/intel/transition_scorer.py
src/vibemix/library/{cache_paths,next_suggestion,store,toolset}.py
tauri/ui/src/debrief/{components/timeline,components/tldr-player,debrief-window}.ts
tauri/ui/src/debrief/styles/debrief.css
tauri/ui/src/pill/next-suggestion.ts
scripts/dev/generate_intel_fixtures.py
scripts/eval/intel_{decision_runtime_replay,fixture_audit}.py
tests/intel/fixtures/{MANIFEST.json,agent_decisions.jsonl,claim_ledgers.json}
tests/intel/test_transition_scorer.py
tests/eval/test_intel_decision_runtime_replay.py
tests/library/{test_cache_paths,test_next_suggestion,test_setprep_tools}.py
.planning/research/2026-05-27-intel-*.md (8 files)
.gitignore
```

That's roughly the `intel/` wiring sketch from the §1 re-verdict above being executed live by a parallel session. **Coordinate before further intel/ work.** This session's island was:
- `vibemix-core.macos.spec` + `vibemix-core.windows.spec` (spec blocker fix)
- `tests/dist/test_spec_blocklist_keeps_livekit_cli.py` (new regression test)
- 19 marketing-copy files (commit `6114bd0d` — README, landing, social templates, anchor scripts, anchor tests)

No overlap.

---

## Verification at handoff time

| Gate | Status |
|---|---|
| Standalone `vibemix-core --wizard` | ✅ ws bus on :8765, 10 handlers, graceful exit |
| Standalone `vibemix-core --session` | ✅ ws bus on :8765, 11 handlers, memory store + recorder armed |
| Standalone `vibemix-core` (no args) | ✅ privacy posture, techno profile, recorder armed |
| `tests/dist/test_spec_blocklist_keeps_livekit_cli.py` | ✅ 2/2 pass after fix; both fail RED on pre-fix specs |
| `tests/dist/` full | ✅ 31/31 pass (29 prior + 2 new) |
| `tests/repo/ + tests/launch/` (marketing-copy gates) | ✅ 457/457 after anchor `("Mac + Windows",) → ("macOS",)` migration |
| `pytest -q --no-header --ignore=tests/e2e/macbook` | ⏳ running at handoff; previous full sweep on same tree was 5123 / 0 |
| `VIBEMIX_PRETAG_MAC_ONLY=1 VIBEMIX_PRETAG_RC=1 scripts/dist/pretag_check.sh` | ⚠ 5 pass / 1 fail (Phase 16 ear-pass) / 2 warn (Phase 17 deferred, Discord pinned to release notes) — handoff-baseline parity |

---

## Open ship decision

**Step 7 (tag)** is the only step left. The condition is:

1. Kaan does the Phase 16 ear-pass DJ run (~30-45 min on a real session).
2. Kaan signs off `.planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md` with `status: passed`.
3. Run `git tag v0.1.0-rc1 && git push origin v0.1.0-rc1`.
4. `.github/workflows/release.yml` fires → signed + notarized DMG → GitHub Releases.

The Tauri shell is up at handoff time (`cargo run --no-default-features` from `tauri/src-tauri/`) with the FIXED sidecar binary at `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/`. If `:8765` doesn't bind within ~15s, re-run cargo. If `cargo run` exits, re-launch.

---

## What this session changed (for the changelog audit)

| Commit | Scope | LOC |
|---|---|---|
| `b01fe4ee` | Handoff doc (the prior one this followup answers) | docs |
| `6114bd0d` | Drop "Mac + Windows" overclaim across 11 customer-facing files + anchor + test fixtures | 50/49 |
| `3d2900ce` | Spec blocklist fix + regression test (the FIRST shipper) | 83/2 |
| `8dd2f098` | Eager-import attempt in `__main__` (reverted, was misleading) | 86/0 |
| `249010c0` | This followup handoff (initial draft) | docs |
| `99c951a7` | PyInstaller runtime hook + regression test (revert of `8dd2f098`) | 103/88 |
| `d58c722f` | Patch livekit-agents init + purge stale pyc + build_sidecar integration + regression test | 282/0 |
| `938c822a` | sidecar.rs Bundled-arm rewrite (std::process + libc kill) + `SidecarChild` enum + Cargo.toml libc dep | 197/55 |

---

## Late-session reality check (added after 938c822a)

After committing all four bug fixes, this session built a minimal launchd-spawn simulator (a `.app` wrapper around `tauri/src-tauri/target/debug/vibemix` with the bundled sidecar in `Contents/Resources/`) and `open`-launched it to dry-run what a signed CI DMG would do on a user's machine.

**Result:** MIXED. First clean launch ran the bundle PAST imports (printed privacy posture + techno profile + recorder armed, exited with [FATAL] GEMINI_API_KEY missing per the exit-4 sentinel). Second launch with `GEMINI_API_KEY` env relayed via `open --env` CRASHED with the same chained `livekit.agents` circular ImportError that the patch was supposed to fix.

This suggests the bug is FLAKY in the launchd-spawn path — the patch helps but isn't 100% deterministic. Working theories: PyInstaller frozen importer's submodule-binding order is non-deterministic under high-load init contexts; OR a subtle interaction with how launchd-launched processes inherit signal masks / process group attributes that affects Python's import machinery.

**Honest ship-recommendation update:** v0.1.0-rc1 SHOULD NOT BE TAGGED today without one of:

1. **Vendor `livekit-agents`** into `vendor/livekit_agents/` with the split-import baked in at source-level (not patched at build time, which is what's flaky). Drop `scripts/dist/patch_livekit_agents_init.py` in favor of a stable vendored copy. Add the vendor dir to spec `pathex=` ahead of `.venv/lib/...`. ~30-60 min work. Then re-run the launchd-spawn simulator until the boot is deterministic across N launches.
2. **Tag and ship the broken rc1 deliberately as the "test in the wild"** rc — Phase 17 grading is literally gathered against the rc binary. Document the known crash in the GitHub Release notes; rc1 readers see "macOS bundle may crash on first launch — use `VIBEMIX_DEV_SIDECAR=1` dev fallback" as a known-issue line. v0.1.0 stable closes the bundle bug as a hard gate.
3. **Replace `livekit-agents` 1.x with the slimmer plain `google-genai` Live API client** for our `RealtimeModel` use case. Bigger refactor; closes the bug at its root by removing the source. Probably the right v0.1.x architectural play.

**The dev-source path (`VIBEMIX_DEV_SIDECAR=1 cargo run --no-default-features` from `tauri/src-tauri/`) is healthy and gives a faithful Phase-16 ear-pass surface** — every user-facing reaction goes through the same prompt + grounding + TTS stack as the bundle would, just running on the dev Python interpreter that handles imports normally. Ear-pass results from the dev-source surface ARE meaningful and DO bind the codebase's quality gate.

---

**End of followup handoff.** If you pick this up: re-read §"The bug we found this session" + §"Late-session reality check" first. Then trace the Tauri shell + sidecar status. Then decide path 1/2/3 above with Kaan. If tagging anyway, run the post-tag launchd smoke-test on the signed DMG within 10 min of CI completing and prepare to delete the tag if it crashes.
