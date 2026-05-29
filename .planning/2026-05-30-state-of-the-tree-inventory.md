# vibemix — State of the Tree (2026-05-30)

> Forensic inventory of the `live-tuning-or-brain` branch: 417 commits ahead of
> `origin/main` + 75 uncommitted working-tree changes from 3 days of parallel
> Claude sessions. Produced by a 16-agent investigation workflow (inventory →
> adversarial wiring-verify → synthesis) + a full-suite pytest baseline.
> Every "wired" verdict was independently re-checked against the real entrypoints
> (`python -m vibemix`, Tauri `invoke_handler`, IPC `:8765`, mounted shell).

## Executive Summary

- **Branch position:** `live-tuning-or-brain` is **417 commits ahead** of `origin/main` (merge-base `dd9deb7e`) with **75 uncommitted working-tree changes** (69 modified, 6 untracked). Everything lives locally — `origin` push is blocked by a **GitHub account billing lock** (Kaan-only, not a code problem), so this branch IS the product right now.
- **The 3-day sprint:** 86 commits 2026-05-27, 235 on 05-28, 96 on 05-29 across multiple parallel Claude sessions on one shared tree. Big landings: v11.0 Skill-Tree engine (P102-103), the deck-context/live-tuning brain expansion (the branch namesake), the Viber live-deck-context grounding pass, the tozpembe DesktopShell fold, 36-lesson Learn curriculum, and the pill polish pass.
- **Milestone state (per `.planning/STATE.md`):** v11.0 "Earned" — **Phase 102 COMPLETE, Phase 103 COMPLETE** (both plans shipped), status `verifying`. **Phase 104 (Skill-Tree Surface + Earned Celebration — the UI phase) NOT started.** Engine logic for mastery exists and tests green, but its live UI surface and live call-site are P104 + parked KAAN-ACTION.
- **Is the recent work actually in the app?** Mostly yes — the deck-context brain, Agent/LiveKit deck-audio Parts, Viber live-context chain, Memory signatures, Pill core, and Learn harmonic-pair are all **reachable from `python -m vibemix`**. The loud exception: the **v11.0 Skill-Tree mastery engine (`skill_tree.py` + `skill_recognizer.py`) is ORPHANED** — committed and fully unit-tested but with **zero live call sites** (deliberately deferred to P104 / `§EARNED-LIVE-MASTERED-VERIFY`).
- **Dirty work risk:** the entire deck-context/live-tuning subsystem (the branch's headline feature, ~12.4k insertions) sits **uncommitted in the working tree** — 6 untracked new files including the new `deck_capture.py` and `harmonic_practice.py` modules. None of it is committed.
- **Test health:** full-suite baseline = **14 failed, 6716 passed** (435s). The failures are NOT random — they are ship-readiness gates (orphan inventory, capability snapshot, pyinstaller spec, README/github-meta drift) plus two real logic regressions from the deck-context work. See § Test Baseline Health.

## Subsystem Inventory

### Learn / Skill-Tree (v11.0 Earned)

The harmonic-practice pair picker (Course 2 L2.11) is fully wired into the boot path and runtime; the 36-lesson curriculum and IPC schema v2 (skills block) are committed and green. **The mastery half of v11.0 — the skill-tree engine and recognizer — is committed but orphaned (no live caller).**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| LearnProgress v1→v2 schema + migration | `learn/progress.py` `_migrate_v1_to_v2`, skills live-portion block | committed | **WIRED** — `__main__.py:1961` `_load_progress()` | 20/20 `test_progress_persistence.py` |
| Harmonic practice pair picker | `learn/harmonic_practice.py` `pick_harmonic_practice_pair` | **untracked-NEW** | **WIRED** — `__main__.py:1964-1981` loader → LessonRuntime | `test_harmonic_practice.py` (5) + runtime (2) — both untracked |
| LessonRuntime harmonic wiring | `runtime.py:401/454/1463/1531-1566` emits L211 tutor line | **dirty** | **WIRED** — `_emit_harmonic_pair_prompt_if_needed()` in `begin()` | covered by runtime tests |
| Curriculum metadata L2.11 | `library_melody_pair:true` + `library_suggestions` lens | **dirty** | **WIRED** — `lesson_flow.py:461`, `curriculum-meta.ts:23` | curriculum_meta spec |
| IPC schema + TS codegen (skills v2) | `messages.schema.json:3421/3459-3468` | committed | **WIRED** | `test_learn_envelope_parity_p92.py` |
| WS learn client | `ws-client.ts:70` generic `tutor_speak` handles L211 marker | **dirty** | **WIRED** (was claimed partial; verified wired — no new handler needed) | `test_ws_client_uses_8765` |
| UI operator-action | `operator-action.ts` normalizer | **dirty** | **WIRED** (harmonic pair rides standard tutor_speak, not operator_action) | `test_operator_action.spec.ts` |

### Deck Context / Brain / Live-Tuning (the branch namesake)

The headline subsystem: a shared live deck-context layer + optional multichannel deck-pair capture + Gemini Deck A/B audio Parts + anti-slop claim policy that refuses "great transition" praise without real two-deck proof. **Fully wired from entrypoint, but the entire subsystem is uncommitted (dirty + untracked).**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| `state/deck_context.py` (+1348) | Render funcs: lanes/reference/source/audio/separation/features/delta/window context + claim guard | **dirty** | **WIRED** — imported by `dj_cohost.py`, `runtime/coach.py`, `ws_bus.py` | 83/83 `test_deck_context.py` (dirty +935) |
| `audio/deck_capture.py` (+620) | `DeckAudioCapture`, deck-pair routing, per-lane RMS/features | **untracked-NEW** | **WIRED** — `__main__.py:90,1056`, audio callback `:471` | 8/8 `test_deck_capture.py` (untracked) |
| `state/refresh.py` (+6) | `audio_capture_context` threaded to evidence writer | **dirty** | **WIRED** — `_tick_once`/`_write_live_grounding_evidence` | `test_tick_writes_audio_features` |
| `state/coach.py` (+44) | `task_for_event` reads `ev.extra['audio_capture_context']` | **dirty** | **WIRED** | `test_task_mix_move_live_evidence_uses_event_audio_capture_context` |
| `audio/features.py` | legacy `snapshot_features` | dirty (minor) | **PARTIAL** — legacy only; `deck_capture` defines `_deck_frame_features` locally, does not consume it | `test_features.py` (no new tests — PARTIAL) |
| `state/deck_poller.py` / `deck_state.py` | now-playing source guard, `DeckTrack` | **dirty** | **WIRED** — poller spawned `__main__.py:2179` | `test_deck_poller.py` (+86) |
| `__main__.py` orchestration | routing-from-env → capture → context dict → all loops | **dirty** | **WIRED** — threaded to ws_broadcast/refresh/coach/build_prompt | `test_main_smoke.py` (+112) |

**Flag:** This is the branch's biggest single body of work and it is **100% uncommitted.** Live-socket transport has been physically sampled (`frames_seen=62`, schema v2), but **full live DJ proof still requires audible deck audio + a controller move + resolved deck rows + `audio_delta`** — current smoke correctly stays `diagnosis=missing_physical_proof`. That is the parked `§EARNED-LIVE-MASTERED-VERIFY`-class live verify.

### Agent / LiveKit / Co-host Brain

Streaming-pipe chunk gating (TTFT speed-fix) plus the new deck-audio Gemini Parts path: Deck A/B WAV Parts attach on MIX_MOVE/TRANSITION_OPPORTUNITY/KEY_CLASH/MANUAL events, behind `VIBEMIX_GEMINI_DECK_AUDIO_PARTS` (default `auto`) and the `VIBEMIX_DECK_AUDIO_CHANNELS` gate. **All 16 pieces verified WIRED.**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| `_streaming_pipe.py` | chunk-by-chunk TTS yield gate | committed | **WIRED** — `dj_cohost.py:55,2536` | included in agent suite |
| Deck-audio Parts (`_deck_audio_part_snapshots`) | WAV snapshot of Deck A/B rings → Gemini contents P4/P5 | **dirty** | **WIRED** — `dj_cohost.py:1778-1853,2321` | `test_dj_cohost.py:538-750` (+534 dirty) |
| `_deck_audio_parts_mode()` resolver | reads env, gates attachment | **dirty** | **WIRED** — `dj_cohost.py:240-250` | agent suite |
| Prompt grounding `_build_attached_audio_context_clause` | renders deck-audio context lines beside Parts | **dirty** | **WIRED** — `:339-500` | agent suite |
| `live_claim_policy(... deck_audio_parts_attached=)` | supported-verdict gate requires two-lane window | **dirty** | **WIRED** — `:439-445` | `test_dj_cohost_linter.py` (+6) |
| `audio_capture_context` via `Event.extra` | per-turn override of cached context | **dirty** | **WIRED** (was claimed partial; verified wired) | `test_llm_node_..._event_audio_capture_context` |
| Token accounting | sums 32 tok/s across all Parts | **dirty** | **WIRED** — `:2283-2297` | covered |

### Viber / Library / Curate (Codex set-prep)

The live-deck-context grounding chain: Viber chat now receives a labeled, fenced live-context packet (provenance/freshness/TTL), classifies turns `active_live_context` vs `silent_guard`, surfaces a `live read` receipt row, and fails closed on active live questions with no packet. **All 9 pieces WIRED** — full chain `main.ts → mountLibrary → library_chat (Rust) → chat_with_codex (Python) → live-context CLI`.

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| `library/codex_curate.py` | `chat_with_codex` backend, live-context normalization, public-reply hygiene | **dirty** | **WIRED** — `__main__.py:3232`, CLI `chat`/`live-context` | 78 fns `test_codex_curate.py` (+857) |
| `library_cmds.rs` | `library_chat` Tauri cmd | **dirty** | **WIRED** — `main.rs:111`, spawns subprocess | cargo `chat_library_args` |
| `library/api.ts` | `libraryChat` + receipt normalizer | **dirty** | **WIRED** — `:2402` | 44 fns `api.test.ts` (+437) |
| `library/index.ts` | `mountLibrary` + `runChat` + live-verification rows | **dirty** | **WIRED** — `:1578,1737` | chat suite |
| `library live-context` CLI | samples :8765, `--require-proof` gate | **dirty** | **WIRED** — `__main__.py:4705` | 39 fns `test_live_context_cli.py` (+797) |
| `chat.test.ts` | live verifier render | **dirty** | **WIRED** | 28 fns (+500) |

> **⚠ Boundary regression (caught by baseline, not the workflow):** `codex_curate.py:160`
> now has a **top-level** `from vibemix.state.music_state import MusicState`
> (`_music_state_from_live_context()` at `:2251`). This breaks
> `test_curate_unify.py::test_curator_does_not_import_musicstate`, which forbids
> the curator from leaking `MusicState`/`EventDetector` as module attributes. Fix
> = move the import function-local (codebase idiom). See § Test Baseline Health.

### Pill (the "what next" floating surface)

Core state machine, DJ-KNOWS hover drawer, move-grade vocabulary (NEG/MID/CLEAN/SEXY/BOMB/LIT_AFF parity with `intel/move_grade.py`), and CSS are committed + live-wired at 30Hz from the backend `next_suggestion` dict. **The three Playwright browser-test files are untracked, not in CI, and test dev-only demo surfaces — PARTIAL.**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| `pill/index.ts` | state machine, ws subscribe, render | **dirty (+48)** | **WIRED** — `main.rs:196` creates pill window | `index.test.ts` (230+, +86 dirty) |
| `next-suggestion.ts` | DJ KNOWS drawer render | **dirty (+15)** | **WIRED** | `next-suggestion.test.ts` (151+, +67 dirty) |
| `move-grade-vocabulary.json/.ts` | shared grade table, backend parity | committed | **WIRED** — backend `next_suggestion.py:457/809` | 5 `test_move_grade.py` |
| `pill.css` (+133) | rails, capsules, NEG badge | **dirty** | **WIRED** | css-contract tests |
| `browser-care-hover.pw.ts` (843) | 11 hover/care/ARIA tests | **untracked-NEW** | **PARTIAL** — not in CI, mocks the bus, not run against live endpoint | manual `test:e2e:pill` only |
| `browser-demo-reactions.pw.ts` (288) | 5 demo-pad smoke tests | **untracked-NEW** | **PARTIAL** — exercises dev-only `VITE_VIBEMIX_DEMO_NEXT=1` surface (zero-wired in prod), not in CI | manual only |
| `playwright.config.ts` | Vite dev server :5190, demo on | **untracked-NEW** | **PARTIAL** — dev tooling, baseURL ≠ prod pill, not in CI | n/a |

### Memory + Runtime + WS-Bus

Memory signatures + recall queries now carry all four deck-audio context fields with an anti-slop guard (`omitted_untrusted_audio_window` strips conflicting dual-deck `P2/P2` atoms). `coach_loop` + `ws_broadcast` thread `audio_capture_context` and call the four `render_deck_audio_*` functions. **All wired except Course-3 lens which is orthogonal/partial.**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| `memory/ingest.py` | `SIG_TEMPLATE_VERSION v9-...deck-audio-context`, anti-slop strip | **dirty** | **WIRED** | `test_ingest.py` (+61) |
| `memory/retrieval.py` | `build_recall_query` mirror + `_has_sound_change_evidence` | **dirty** | **WIRED** | `test_retrieval.py` (+96) |
| `runtime/coach.py` | `coach_loop` threads context, populates `event.extra` | **dirty** | **WIRED** — `__main__.py:2200/2223` | `test_coach.py` (+89) |
| `runtime/ws_bus.py` | `ws_broadcast` renders 4 contexts on 30Hz frame | **dirty** | **WIRED** — `__main__.py:2148/2160` | `test_ws_bus_deck_state.py` (+196 NEW) |
| `state/deck_context.py` render funcs | pure read-only renderers | **dirty** | **WIRED** | shared with deck-context suite |
| `test_ws_bus_course3_lens.py` | Course 3 lens serialization | **dirty (+15)** | **PARTIAL** — orthogonal to deck audio; coexists on same tick, no collision | 2 tests |

### The 417 Committed Commits (macro — what LANDED, not dirty)

The committed backbone: tozpembe DesktopShell fold, 36-lesson curriculum + IPC v2, Track-Relation S1 grounding, config-store convergence, skill-onboarding wizard step, planning artifacts. **3 pieces ORPHANED (the v11.0 mastery engine), 3 PARTIAL.**

| Piece | What | State | Wired (verified) | Tests |
|---|---|---|---|---|
| LearnProgress v1→v2 data model | migration loaded at boot | committed | **WIRED** — `__main__.py:1961` | 20/20 |
| **Skill-Tree engine (`skill_tree.py` `SkillTree.compute`)** | 6-skill manifest, recital AND-gate, quality fill | committed | **ORPHANED** — no import in `__main__`/coach; zero call site | 20/20 (dead code) |
| **`skill_recognizer.recognize()`** | citation-gated event→skill credit | committed | **ORPHANED** — never imported/called from live code | 9/9 (dead code) |
| **`record_live_demo()` writer** | Mastered flip at threshold N | committed | **PARTIAL** — correct + tested, but only reachable via orphaned `recognize()` | covered, unreachable |
| One Mind S1 (Track Relation) | `compute_relation` → coach evidence | committed | **WIRED** — `state/coach.py:446-467` | 16/16 `test_track_relation.py` |
| One Mind S2-S6 | taste/decision/claim/projection infra | committed | **PARTIAL** — exists in `intel/`, opinion-poll routing deferred (KAAN-ACTION) | infra tests |
| Shell tozpembe DesktopShell | 5-surface fold, v5→v6 retone, Cmd+K, grounding receipt | committed | **WIRED** — `main.ts:213 → mountShellApp → mountSurfacesInto` | 7 shell spec files green |
| 36-lesson curriculum | Course 1 (16) + 2 (14) + 3 (6) | committed | **WIRED** — `curriculum.py` CURRICULUM | 69 learn tests |
| IPC schema (81 defs, 15 learn) | envelopes + codegen | committed | **WIRED** (handoff claimed 78; actual 81 — minor doc drift) | `check_ipc_schema.py` |
| Learn window + MIDI mirror + LessonRuntime | P91-92 spine | committed | **WIRED** — `__main__.py:1992-2004` | learn suite |
| Config store convergence (m4m) + skill onboarding (ifq) | quick tasks | committed | **WIRED** — `runtime.config_store`, WizardSetSkill | wizard tests |
| Pill polish (21 commits) | move-grade, feedback buttons | committed | **PARTIAL** — feedback button infra wired, taste_model opinion-poll deferred (no `taste_model` import in `pill/index.ts`) | move-grade parity |
| Planning artifacts/handoffs | ROADMAP/REQUIREMENTS/STATE/handoffs | committed | **WIRED** | n/a |

### Gear-Aware Sound Tuner + Cross-Cutting Docs

No wired claims to verify. The gear-aware "Tune" sound-tuner is **exploration/spec-prep only** — it lives as research (`.planning/research/2026-05-29-gear-aware-sound-tuner-exploration.md`, committed) with **no `src/vibemix/` module and no `docs/` page**. It is pending Kaan/Francesco section 7 sign-off (per memory). Not built, not wired, not this sprint.

## Integration Status — "Is it in the real app?"

| Capability | Status | Proof / Gap (file:line) |
|---|---|---|
| Deck-context brain (lanes/reference/source/audio packets) | **WIRED** | `deck_context.py` imported by `dj_cohost.py`+`coach.py`+`ws_bus.py`; threaded from `__main__.py:1056` — *but entire subsystem uncommitted (dirty/untracked)* |
| Multichannel deck-pair capture (`DeckAudioCapture`) | **WIRED** | `__main__.py:90,1056`, audio callback `:471`; default-off behind `VIBEMIX_DECK_AUDIO_CHANNELS` — *untracked file* |
| Gemini Deck A/B audio Parts | **WIRED** | `dj_cohost.py:1778-1853,2321`; `auto` mode gates on event type + RMS |
| Streaming-pipe chunk TTS gate (TTFT fix) | **WIRED** | `dj_cohost.py:2536` `can_yield_chunks` |
| Anti-slop live claim policy (refuse fake "great transition") | **WIRED** | `live_claim_policy(..., deck_audio_parts_attached=)` `dj_cohost.py:439`; verifier rejects single-deck transition praise |
| Viber live-context grounding + receipt row | **WIRED** | `chat_with_codex` ↔ `library_chat` Tauri ↔ `libraryChat` TS ↔ `mountLibrary` |
| Viber fail-closed on active live Q with no packet | **WIRED** | `chat_with_codex` returns `stop_reason=live_context_required` before spawning Codex |
| Now-Playing non-deck source guard | **WIRED** | `DeckPoller` rejects `com.apple.WebKit.GPU` etc.; `client_bundle_id` provenance |
| Memory signatures carry deck-audio context (anti-slop) | **WIRED** | `ingest.py` `SIG_TEMPLATE_VERSION v9-...`; `omitted_untrusted_audio_window` strip |
| Learn harmonic-pair (Course 2 L2.11) | **WIRED** | `__main__.py:1964-1981` → `runtime.py:1531`; emits L211 tutor line w/ `[track:]` citation |
| LearnProgress v1→v2 (skills block) | **WIRED** | `__main__.py:1961` `_load_progress()` |
| 36-lesson Learn curriculum + practice booth | **WIRED** | committed; `non_external_ready=true`; only Course-3 routed-audio gate open |
| Pill core (DJ KNOWS, move-grade, reactions) | **WIRED** | `pill/index.ts` ↔ backend `next_suggestion`; `main.rs:196` |
| Tozpembe DesktopShell (5-surface fold) | **WIRED** | `main.ts:213 → mountShellApp → mountSurfacesInto` |
| One Mind S1 Track-Relation grounding | **WIRED** | `state/coach.py:446-467` blend `[why verdict]` → evidence |
| **v11.0 Skill-Tree engine (`SkillTree.compute`)** | **ORPHANED** | committed + 20/20 green, but **no import / no call site** in `__main__`/coach |
| **v11.0 Skill recognizer (`recognize()`)** | **ORPHANED** | committed + 9/9 green, but **never called** from live code |
| **v11.0 Mastered flip (`record_live_demo`)** | **PARTIAL** | correct + tested, reachable only through orphaned `recognize()` — dead at runtime |
| One Mind S2-S6 (taste/decision/claim opinion-poll) | **PARTIAL** | infra in `intel/`; routing-to-coach deferred (KAAN-ACTION) |
| Pill taste-feedback opinion-poll | **PARTIAL** | feedback buttons render w/ `data-feedback`, handlers stubbed; no `taste_model` import in pill |
| Pill Playwright e2e (3 files) | **PARTIAL** | untracked, not in CI, dev-only demo surface / mocked bus |
| Gear-aware "Tune" sound tuner | **NOT BUILT** | research doc only; no module, no docs page |

## Test Baseline Health (2026-05-30 full-suite run)

Full `uv run pytest -q` on the dirty tree: **14 failed, 6716 passed, 27 skipped, 1 xfailed, 4 xpassed** in 435.97s. The 14 failures are ship-readiness gates + two real logic regressions, NOT flaky noise:

**Real logic regressions (deck-context work):**
1. `tests/library/test_curate_unify.py::test_curator_does_not_import_musicstate` — `codex_curate.py:160` added a top-level `MusicState` import (boundary violation). Fix: function-local import inside `_music_state_from_live_context()`.
2. `tests/agent/test_dj_cohost_ground_secondary.py::test_flag_off_byte_identical` — the new `AUDIO CONTEXT MAP FOR ATTACHED P1` block reworded the v8.0 baseline string `"(audience perspective)"` → `"perspective; global mix, not isolated deck stems)"`. The byte-identity pin needs updating to the new intended prompt shape (deliberate change, stale pin).

**Packaging / ship gates (artifact regen):**
3. `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` — untracked modules dirty the orphan diff vs `.planning/codebase/orphans.csv`. Resolves on committing the islands + regenerating the baseline.
4-5. `tests/security/test_capability_snapshot.py` (×2) — `SNAPSHOT.json` drift vs canonicalized `default.json` (SEC-09). `default.json` is NOT dirty → drift is from a committed change. **Inspect the diff before regen** (security artifact — confirm new capabilities are legit, not an over-grant) via `scripts/dist/snapshot_capabilities.py`.
6-7. `tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules` (macos+windows) — frozen-build specs must filter test submodules; new test modules need the filter / spec update.

**Doc / meta drift (update committed docs/snapshots):**
8-9. `tests/scripts/test_sync_github_meta.py` — topics list + homepage URL (note: memory says public domain moved to `bravoh.ai`; reconcile with the `altidus`-expecting assertion).
10-11. `tests/repo/test_readme_feature_matrix_sync.py` (×2) — README feature matrix drift vs completed phases.
12. `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` — STATE.md phase-16 annotation drift.
13. `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` — new `viber-gemini-*` docs likely tripped the "no Gemini Viber fallback" doc-pin guard.
14. `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent` — audit-md generator non-idempotent.

## WHAT'S LEFT — Punch List

### Needs commit (dirty/untracked work to land)
- **[claude]** Commit the entire **deck-context / live-tuning brain** — the branch namesake, ~12.4k insertions, currently 100% dirty. Untracked: `src/vibemix/audio/deck_capture.py`, `tests/audio/test_deck_capture.py`. Dirty: `state/deck_context.py` (+1348), `state/refresh.py`, `state/coach.py`, `state/deck_poller.py`, `state/deck_state.py`, `agent/dj_cohost.py` (+534 tests), `runtime/ws_bus.py`, `runtime/coach.py`, `memory/ingest.py`, `memory/retrieval.py`, `library/codex_curate.py`, `__main__.py`, `tauri/src-tauri/src/library_cmds.rs`+`ws_client.rs`, `tauri/ui/src/library/{api,index,chat}.ts(+.test)`.
- **[claude]** Commit the **Learn harmonic-pair** island: untracked `src/vibemix/learn/harmonic_practice.py`, `tests/learn/test_harmonic_practice.py`, `tests/learn/test_harmonic_practice_runtime.py`; dirty `learn/runtime.py`, `learn/lesson_flow.py`, `learn/curriculum.py`, the L2.11 transcript, `curriculum-meta.ts`, `operator-action.ts`, `ws-client.ts`.
- **[claude]** Commit the **pill polish** dirty set (`index.ts/.test`, `next-suggestion.ts/.test`, `pill.css`); decide on the untracked `tauri/ui/tests/pill/` Playwright dir (see Needs-wiring).
- **[claude]** **Commit discipline (CLAUDE.md hard rule):** the tree has 75 changes from ≥2 concurrent sessions — `git add <paths>` surgically per island, never `-A`; verify `git diff --cached --name-only` before each commit (concurrent commits absorb every staged file). Bundle each untracked module WITH its importer (clean-checkout CI gate).

### Needs wiring (built but orphaned/partial — connect to the real app)
- **[claude — BACKEND, in scope]** **v11.0 Skill-Tree mastery engine** — `skill_tree.py` + `skill_recognizer.py` are committed, fully tested, and **dead code** (no caller). The backend live-firing call-site (wrap `EvidenceRegistry.has` as the `citation_check`, call `recognize()` per detected event in `runtime/coach.py`/`__main__.py`) is the biggest orphan and is backend wiring. *Originally deferred to P104; per the 2026-05-30 ship-ready directive the backend recognizer call-site is in this session's lane (the UI panel + Mastered vocal stay with the frontend session).*
- **[frontend session]** **Phase 104** UI surface — skill-tree panel + Competent cue + rare grounded "Mastered" vocal. Not this session's lane.
- **[kaan]** **Pill taste-feedback / One Mind S2-S6 opinion-poll** — buttons exist (`data-feedback`), `intel/taste_model.py` exists, but routing the click into a taste opinion-poll is parked.
- **[frontend session]** **Pill Playwright e2e** — wire `test:e2e:pill` into CI if these are meant to gate (currently untracked, manual-only, mock-bus, dev-surface).

### Bugs / risks / invariant concerns
- **[claude]** **`features.py` PARTIAL:** `deck_capture.py` defines its own `_deck_frame_features()` locally instead of importing `audio/features.py::snapshot_features` — duplicate feature logic, drift risk. Either consolidate or document the intentional split.
- **[claude]** The two real logic regressions in § Test Baseline Health (curator import, byte-identical pin) — fix before relying on full-suite green.
- **[claude]** A **`GroundingPanel.ts` `NodeList` iterator** build-blocker was patched with `Array.from(...)` to keep the build gate meaningful — verify it stuck.
- **Invariants:** all four cardinal invariants held by additive design (single-writer, citation grounding, one socket :8765, idle≠fault). The deck-context anti-slop guard (`omitted_untrusted_audio_window`) is the new Invariant-#2/#3 enforcement surface — keep it test-pinned.

### Ear-pass / Kaan design decisions (parked, never faked)
- **[kaan]** 🔴 `§EARNED-LIVE-MASTERED-VERIFY` (P103) — real DDJ-FLX4 live verify: a **cited** event advances Mastered, an **un-cited** moment does not.
- **[kaan]** 🔴 `§EARNED-MASTERED-VOCAL-EAR` (P104) — ear-pass on the rare grounded "Mastered" unlock vocal (real friend vs gamification slop).
- **[kaan]** 🔴 **Live deck-context DJ proof** — live socket sampled (schema v2, `frames_seen=62`) but stays `missing_physical_proof`: needs audible deck audio + controller move + resolved deck rows + `audio_delta` on real gear (Rekordbox → BlackHole 16ch route). The real ear-test for the live-tuning brain.
- **[kaan]** 🔴 **Course 3 routed-audio proof** — Learn release gate: route Rekordbox `DDJ-FLX4 @48k` → `BlackHole 16ch @48k`, play a real track, raise faders, rerun Course-3 live proof. Only remaining Learn release blocker.
- **[kaan]** 🟡 `§EARNED-SURFACE-DESIGN-GATE` (P104 panel layout) + 🟡 `§EARNED-MASTERY-THRESHOLD-TUNE` (per-skill N).
- **[kaan]** Carried v10.0 ear-passes (tool_starvation tone, clarification tone, env-propagation, doc-readthrough) + v9.0 Learn course ear-passes + legal disclaimer.
- **[kaan]** Gear-aware "Tune" sound-tuner — section-7 sign-off with Francesco before any build.

### Test / doc gaps
- **[claude]** Untracked tests (`test_deck_capture.py`, both harmonic tests, the 3 pill Playwright files) are **not in the committed suite** — land with their source modules (clean-checkout CI gate per memory `feedback_clean_checkout_ci_gate`).
- **[claude]** IPC schema doc drift: handoff says "78 message types", actual is **81 definitions** — reconcile.
- **[claude]** EQ exemplar ear-pass artifact approved locally (`learn-exemplar-ear-pass-current.json`, digest `34e7aafe…`) but lives in `/tmp` — ensure the durable approval is where release tooling reads it.

## Open Workstreams (carried, not this sprint)

- **v4.0 SHIP** — engineering-complete 8/8 since 2026-05-21; **publish gated on Apple Developer ID + SignPath signature clock** (external, multi-day). All 11 GitHub Apple/Tauri secrets wired (rc1 audit, 2026-05-27); 5 SignPath secrets wait on OSS-program approval. The external Apple/SignPath approval is the true critical path per CLAUDE.md.
- **v0.1.0-rc1 ship work** — bundle/launchd fixes in flight; pretag at last check 5 pass / 1 fail (Phase-16 hallucination ear-pass) / 2 warn. Known rc1 bug: installed app squatting :8765 collides with `cargo tauri dev` (free :8765 first). Sidecar bundle is FROZEN — verify backend on current source or `VIBEMIX_DEV_SIDECAR=1`, not the bundled binary.
- **LiveKit-upgrade** — `__main__.py:1353` `turn_handling` + livekit-agents 1.5.8→1.5.14; streaming speed-fix landed (chunk-by-chunk yield). Stale local sidecar on old livekit throws `cannot import name 'cli'` → use `VIBEMIX_DEV_SIDECAR=1`.
- **Gear-aware "Tune"** — exploration/spec-prep only (research doc committed); no module. eqMac (Apache-2.0) + EqualizerAPO (hot-reload) identified as host targets, biquad to reimplement. Pending Kaan/Francesco section-7 decision.
