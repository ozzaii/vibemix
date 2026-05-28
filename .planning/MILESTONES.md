# vibemix — Milestones

## v10.0 12-Factor Hardening (Shipped: 2026-05-28)

**Phases completed:** 3 phases (P99 HARDEN-RETRY · P100 HARDEN-CLARIFY · P101 HARDEN-CONTRACT), 18 plans, 21/21 REQ-IDs satisfied.

**Stats:** 72 commits since `e06e7ecf` · 60 files changed · +15,897 / -72 LOC · ~7 hours autonomous (14:41 → 21:59 TRT).

**Key accomplishments:**

- **Factor 9 closed (P99 HARDEN-RETRY)** — `LibraryToolset` gained an additive per-run `_consecutive_empties` counter (`toolset.py:137`) with handler-entry / handler-exit single-writer discipline pinned by AST gate. Threshold-trip detection writes terminal `stop_reason="tool_starvation"` payload via `_write_side_channel` (`toolset.py:1379`) with a deterministic 3-case actionable hint generator (empty library / narrow theme / dispatch error). Both `curate_with_codex` and `build_set_with_codex` propagate uniformly to all callers. CLI exit code 10 distinct from "no playlist found" success.
- **Factor 7 closed (P100 HARDEN-CLARIFY)** — NEW grounded MCP tool `request_clarification(question, choices)` lands on the FastMCP surface (`mcp_server.py:230-258`) with a teaching docstring Codex reads. `MIN_CHOICES=2`/`MAX_CHOICES=5` validation rejects 0/1 (no real disambiguation) and 6+ (choice paralysis). Sibling `stop_reason="clarification_needed"` rides the SAME side-channel seam P99 established. CLI exit code 11 + 2-block stderr render distinct from `tool_starvation` exit 10. Telegram `format_reply` clarification branch through `strip_leaks`. 6-property AST gate proves the handler has NO `track_id` surface → Invariant #2 holds by structural impossibility (a clarification cannot fabricate a track reference).
- **Factor 3 closed (P101 HARDEN-CONTRACT)** — NEW `docs/PROMPT-COMPOSITION.md` (269 lines, ASCII-only) enumerates the live co-host prompt surface as a single named contract: 9 EventTypes × 11 EVIDENCE_SOURCES × `MIN_EVENT_GAP_PER_TYPE` cooldowns × `ACK_ELIGIBLE_EVENTS` diet-mode eligibility × recall-fragment shapes. 82 `file:line` citations, zero stale (grep-verified at write-time via the §8 appendix loop). New contributors read ONE doc and know what enters the prompt per event type without reverse-engineering `coach.py` / `evidence_registry.py` / `event_detector.py`. CLAUDE.md Architecture section gained a one-line pointer.
- **All 4 cardinal invariants HELD by additive design** — Invariant #1 single-writer (counter writes confined to LibraryToolset instance, AST gate pins); #2 citation grounding (`seen`-set + `create_playlist` re-validation untouched; `request_clarification` has zero track_id surface; doc enumerates existing 11 sources, does NOT extend); #3 trust the audio (live co-host streaming pipeline untouched — Factor 10 honored, zero `src/vibemix/agent/` touches across 65 commits); #4 one socket (no new ws traffic; CLI + MCP STDIO + Telegram long-poll are existing transports).
- **Disjointness contract HELD end-to-end** — Zero touches to `src/vibemix/agent/`, `src/vibemix/intel/`, `tauri/ui/*`, or the live session-loop path at `__main__.py:1353` `turn_handling` block. Per `feedback_concurrent_sessions_one_tree`: surgical commits with named paths, never `git add -A`. Three parallel sessions on this working tree (v10.0 library-subtree island + LiveKit-upgrade handoff + frontend-wiring handoff) rode together cleanly with disjoint new-file islands.
- **Honest-green test seal** — 116/116 tests pass on the v10.0 chain (`test_codex_curate_stop_reason` + `test_toolset_starvation` + `test_toolset_clarification` + `test_cli_exit_codes` + `test_telegram_bridge` + `test_request_clarification_no_track_surface` + `test_no_seen_relaxation` + `test_mcp_server_clarification`) in 5.79s on current source.
- **Zero tech debt introduced** — every plan shipped honest-green; no `TODO`, no `FIXME`, no commented-out code. The single optional-deferred item (CI smoke check for `file:line` resolution) is explicitly marked OPTIONAL by REQ-CONTRACT-05 and parked as HARDEN-FUTURE-04 (not tech debt).

**Anti-creep acid test:** *"Does this close one of the three audit partials (Factor 9 / Factor 7 / Factor 3) without growing the surface, introducing a new AI provider / managed-memory framework / ws port / IPC envelope / heavy dep, touching `__main__.py` / `agent/` / `intel/` / `tauri/ui/*`, or relaxing any of the four cardinal invariants?"* — All 3 phases passed. No HARDEN-FUTURE items leaked into v10.0 scope.

**E2E flows verified (4/4 complete):** Flow A (`tool_starvation` full chain to CLI exit 10) · Flow B (`clarification_needed` full chain to CLI exit 11 + 2-block stderr) · Flow C (Telegram bridge for either stop_reason through `strip_leaks`) · Flow D (doc-first contributor onboard via CLAUDE.md pointer → `docs/PROMPT-COMPOSITION.md`).

**Known deferred items at close: 4 KAAN-ACTION ear-pass / read-through items.** Per `gsd-autonomous fully` mode, these defer to public-ship discharge on Kaan's clock (NOT engineering blockers): §HARDEN-PHASE-A-EAR-PASS (P99 `tool_starvation` tone in wild) · §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY (P99 env var on real Codex CLI) · §HARDEN-PHASE-B-CLARIFICATION-TONE (P100 clarification prompt tone in wild) · §HARDEN-PHASE-C-DOC-READTHROUGH (P101 contributor "is this useful as a contract?" feel-check). See `.planning/STATE.md` § Deferred Items.

**HARDEN-FUTURE backlog (out of v10.0 scope · tracked):** Multi-turn Viber state persistence (HARDEN-FUTURE-01) · BAML/Pydantic-strict schema enforcement on FastMCP tool surface (HARDEN-FUTURE-02) · Discord / iMessage trigger transports (HARDEN-FUTURE-03) · CI smoke check for doc `file:line` resolution (HARDEN-FUTURE-04).

**Audit:** `.planning/v10.0-MILESTONE-AUDIT.md` — passed, 21/21 REQs, 4/4 E2E flows, 0 gaps, 0 tech debt, 0 BLOCKER, 0 WARNING.

**Archive:** `.planning/milestones/v10.0-ROADMAP.md` · `.planning/milestones/v10.0-REQUIREMENTS.md`

---

## v9.0 Lesson One (Shipped: 2026-05-28)

**Phases completed:** 11 phases, 35 plans, 52 tasks

**Key accomplishments:**

- 1. [Rule 3 - Blocking Issue] Added `tauri/ui/src/learn/learn-window.ts` placeholder
- 5 Python test files + 14 vitest/playwright TS test stubs scaffolded under `tests/learn/` + `tests/ipc/` + `tests/runtime/` + `tauri/ui/tests/learn/` — every REQ-ID for P91 now has at least one automated test file an executor can flip from red to green, and 5 grep gates are GREEN day-one as permanent invariant-pin contracts.
- MidiMirror class + ws_broadcast wiring + __main__ port_watcher layering — the engine that turns a physical MIDI knob twist into a wire frame the Learn webview can consume, riding the existing 30 Hz tick on the SAME ws:8765 socket (Invariants #1 + #4 preserved).
- Tauri 2.x `learn_window.rs` module + main.rs wire-in: `LEARN_WINDOW_LABEL = "learn"` const, `open_learn_window` command (focus-existing semantics, 1280×720 default), trimmed mirror of debrief precedent (no sidecar lifecycle).
- 11 frontend files under `tauri/ui/src/learn/` ship the user-facing artifact: the LearnWindow webview now opens a ws:8765 client, mounts the FLX4 inline SVG (25 hit-regions) on `ipc.learn.controller_detected`, and mirrors physical knob positions onto the SVG via transform-only updates inside a rAF-coalesced drainer — P95 synthetic latency 0.66ms (target 50ms, red 80ms).
- All 10 supported controllers + generic now render as parity-clean inline SVGs under `tauri/ui/src/learn/controllers/`; the 11 Plan-02 parameterised gate rows go fully GREEN; brand-safety + currentColor + ARIA + dual-cue + lazy-chunk-budget gates hold across the closed roster.
- Status:
- 1. [Rule 1 - Bug] Bumped `tests/llm/test_model_router.py::test_router_paths_is_frozen_tuple` count 9 → 10
- 18 new test files landed in 3 named-path-strict commits, pinning every P92 phase-requirement to an automated verification gate that runs as part of CI — 3 AST gates LIVE day-one (Invariant #1, TONE-02, P13 mascot mitigation), 11-envelope round-trip + parity LIVE (Plan 92-01 foundations), 6 module-level stubs that flip skip → pass the moment Plans 92-03..06 land their production modules.
- LessonRuntime FSM (8 states / 5 transitions / 1 Hz tick_loop / single-writer of LearnState) + LearnState mutable dataclass + CURRICULUM dispatch with 1 hello-world lesson + build_tutor_system_instruction composing 5 fragments with 4-forbidden-moves lock LAST for strongest recency + hand-authored JSON fixture — the Python brain of P92.
- Atomic JSON persistence (mirror of `config_store.save()` os.replace pattern) + corruption-recovery + reset CLI subcommand + LessonRuntime wired into `__main__.main()` alongside MidiMirror — the seam that takes Plan 92-03's standalone FSM into a real running service. The live app now boots with both `-> midi_mirror wired` (P91) and `-> lesson_runtime wired` (P92) in stderr, and the 1 Hz tick_loop runs alongside ws_broadcast's 30 Hz without stutter.
- 3 new component files (~520 lines) + 122-line extension to controller-stage.ts (applyHighlight / clearHighlight / setHighlightHintIntensity) + 285-line extension to learn-window.ts (11 envelope listeners + ack-emit + lazy-mount + toast helper) + 379-line additive extension to learn.css (ZERO new design tokens) + Plan 92-02's highlight-paint.test.ts flipped from skip-stub to 3/3 LIVE PASS (P95 = 0.547 ms in jsdom, 29× under the 16 ms RENDER-04 budget) — the user-facing slice of P92.
- Files modified:
- Status:
- 11 RED-state pytest stubs covering EXEMPLAR-01..05 — self-gated module-level skips named to each downstream plan (93-02..93-06), zero new dependencies, suite stays green today
- DSP-band ranker foundation — sidecar `band_shares` sqlite table inside `library-clap.db` + pure-compute `compute_band_shares()` / `_kick_correlation()` primitives with spectral-leakage-gated Pearson r against a 0.8 compressed-kick threshold; flipped 3 Plan 93-01 RED stubs to GREEN with no regression
- Dedicated headphone ``sd.OutputStream`` + stereo PyAV decode + persisted ``learn.headphone_device_index`` settings field — the load-bearing audio-routing surface for tutor exemplar playback that P94/P95 lessons consume; never touches the mic-gated co-host playback queue (Pitfall 2 architectural rule, grep-gated)
- ExemplarFinder.find(band, k) — library-first kick-guarded ranker + packaged CC-BY honest-null fallback with EvidenceRegistry write per pick (Invariant #2 binding); 2 Plan 93-01 RED test stubs lifted, 5 sub-tests GREEN against the production class with 3 graceful inner skips for the §EXEMPLAR-BANK-SOURCING KAAN-ACTION
- 4-site schema-mirror lock for `[exemplar:<track_id>]` landed atomically — EVIDENCE_SOURCES 9 → 10, _SOURCE_ALT alternation extended, CITATION_GRAMMAR_BLOCK Forms list gains the 10th entry, _build_citation_strip allow-list 5-tuple → 6-tuple; the v6 [recall:] precedent (commits 2016e36b → 977c0140 → 0bfc8bd0) mirrored EXACTLY into 3 commits c2c8aa41 / 2a49e0f4 / 853e776a. With Plan 93-04's `ExemplarFinder.find()` pre-registration write, a fabricated `[exemplar:bogus]` now strips the whole AI turn via the existing Phase 20 CitationLinter — Invariant #2 binding closed.
- `ingest_folder(compute_band_shares=True)` opt-in landed (additive side-car write, default-False byte-identical, best-effort per-track error swallow) + `vibemix learn exemplar <band>` CLI dispatch wired into the existing `learn` block (band allow-list → ExemplarFinder.find → 4-line stdout block on success / honest-null on empty / exit 2 on unknown band). The last Plan 93-01 stub module (`test_cli_learn_exemplar.py`) flipped GREEN; cumulative 10 of 10 Phase 93 test modules now collect with ZERO module-level skips. Phase 93 Exemplar Engine + `[exemplar:]` Evidence Source SHIPPED — engine + CLI test surface complete; lesson UI wiring lands in Plan 94 (CURR-1.14).
- 16 hand-authored Course 1 lesson JSON fixtures landed under src/vibemix/learn/transcripts/course_1_anatomy/ with L1.01 iconic dialog byte-locked, L1.14 EQ-as-Tutor exemplar_cycle declared, and L1.16 recital_pool + outcomes copy ready — plus curriculum.py extended with COURSE_FRAMES['course_1_anatomy'] + 16 L1.NN entries that maintain addendum byte-equality with their fixtures.
- Two mechanical enforcers of v9.0 "real DJ friend in your ear, no AI slop" landed: (1) scripts/launch/check_no_tutor_slop.py — 35-token tutor-tic blocklist deep-scanning every JSON lesson fixture, sibling to the Phase 44 SHIP-TWEET copy gate; (2) tests/learn/test_tutor_prompts_byte_equality.py — pins the iconic 4-line L1.01 opening dialog byte-equal to a single source of truth tuple, smoke-tested with deliberate U+2019 drift to confirm it bites red. Both gates inherited automatically by Course 2 + 3 + onboarding fixtures.
- ExemplarLessonController + RecitalRuntime + LearnProgress.course_2_unlocked + LessonRuntime observer seam shipped — Course 1's marquee EQ-as-Tutor demo and 5-prompt unlock gate both have backend logic ready, wired through an emit-only observer pattern that preserves the single-writer Invariant #1.
- Status:
- 14 hand-authored Course 2 lesson fixtures landed under src/vibemix/learn/transcripts/course_2_transitions/, curriculum.py extended with COURSE_FRAMES + 14 L2.NN entries (every addendum byte-equal to fixture), RecitalRuntime extended for Course 2 mode (pool-shape detection + 3-distinct-transition-type variety floor as anti-grind gate + course_3_unlocked persistence), and 69 new tests pin the curriculum dispatch + Course 2 recital contracts at 190 pass / 3 skip across the full tests/learn/ suite.
- 1. [Rule 1 — Bug] `_has_opt_out_comment` lookback too narrow
- 1. [Rule 1 — Bug] P93 exemplar mirror test site-4 regex was closed-form
- `tests/learn/test_course_3_curriculum.py`
- Status:
- 1. [Rule 3 - Concurrent-session staging contamination] Sibling-session edits in MY commits
- [Rule 3 - Blocking issue] IPC schema parity check exit code
- P98 engineering-complete.

---

## v8.1 One Mind (Shipped: 2026-05-26)

**Phases completed:** 6 phases, 19 plans, 29 tasks

**Key accomplishments:**

- 1. [Rule 1 - Bug] Eager seam import regressed the memory no-live-path boundary
- The live co-host now grounds reactions on what's actually playing — the armed Grounding engine is wired into DJCoHostAgent via the proven Phase-65 4-point off-loop seam ([track:<id>] injection resolves against register_library, cold path byte-identical) — and memory.db finally fills on the live main() path via gated _fire_ingest boot+close, without doubling retention.
- Three new test files install the Nyquist safety net for PERCEIVE — 9 strict-xfail behavior scaffolds (deltas / trajectory / genre-prototype build+classify / genre single-writer feed / genre reconciliation) plus a REAL-GREEN cold-path byte-identity pin that captures the v8.0 baseline implementation must preserve.
- The EAR now speaks in CHANGE: two additive single-writer MusicState fields (`prev_perceive`, `trajectory_narrative`) + a pure `deltas.py` feed gated `Δ[kick density rose 18% (clear)]` and `trajectory[build→drop→groove; building; last move: bass-swap 20s ago]` into the prompt — abstaining below floor (anti-slop) and byte-identical to the v8.0 baseline on the cold path.
- `library/genre_prototypes.py` delivers the €0 mean-centered nearest-prototype genre lookup — build centered-mean prototypes per folder-label, classify a cached track embedding with floor/tie-margin anti-slop abstain, and hold the result in a thread-safe `GenrePrototypeLookup` (generation-token discard) that NEVER writes the live state dataclass — composing `centering` + `_cosine` + `rekordbox` with zero duplicated math.
- A pure `state/genre/genre_reconcile.py` solves THE flagged risk — an affine rescale that maps the embedding lookup's centered-cosine confidence (≈0.25 floor) into coach.py's `>= 0.5` render band, plus an embedding-wins-when-confident reconciliation — and `refresh._tick_once` now reads the off-loop `GenrePrototypeLookup` holder inside its lock, reconciles it with the DSP `score_genre`, and writes ONE coherent `detected_genre`/`genre_confidence` (single-writer invariant #1), dispatching the lookup off-loop on TRACK_CHANGE. PERCEIVE-03 closes; phase 78 complete.
- Task 1 — `tests/prompts/test_lens.py` (NEW, 213 lines):
- `LENS_TO_MODE_MOOD` map + `build_lens_instruction` validate-and-delegate wrapper — three grounded lenses (hype/critique/tutor) over the SAME untouched `build_system_instruction`, default hype byte-identical to today's co-host default.
- ONE shared `ConfigStore.extra["lens"]` (set via the new `_apply_lens` settings-bus handler) is read by BOTH the live co-host AND the curator — choose the lens once, it flows to both. Extra-only: no IPC envelope, no schema bump, no codegen. Both cold paths byte-identical.
- Task 1 — real-green pins (must KEEP passing through Plan 02):
- Task 1 — gated secondary-ear framing in `build_parts_description` (`matrix.py`):
- Installed the offline honest-green gate for Phase 81 BEFORE any `bench/` source: 14 xfail-strict scaffolds pinning every BENCH-01/02/03 acceptance criterion (flip in Plans 02/03/04), a zero-network `_FakeClient`/`_RaisingClient` + real `MusicState`/snapshot fixture suite, 6 in-repo `.mp3` excerpts, and a real-green bench-scoped model-literal guard.
- Built the `src/vibemix/bench/` harness as THIN COMPOSITION over the real Phase 77-80 seams: a `BenchCell` 6-D point -> `build_cell_prompt` (reuses `build_lens_instruction` / `AICoach.build_prompt` / `build_parts_description` / `model_router.resolve`, never re-authored text) -> `run_study` with an injected client + the mandatory per-cell 429 fail-safe + a verbatim JSON recorder + SessionMeter cost feed -> the `vibemix bench run` CLI. Flipped the 7 BENCH-01 assemble/run xfail scaffolds to real-green; zero model literals under `bench/`.
- Built `src/vibemix/bench/eval.py` as three PURE, deterministic, offline scorers over a recorded `BenchResult` plus a SORT-ONLY ranker. Groundedness REUSES `CitationLinter.check(output, dsp_snapshot, mode="debrief")` VERBATIM (the linter IS the product's anti-slop gate, Invariant #2 — no bespoke atom parser). Specificity is a deterministic `NEGATIVE_PHRASES` penalty + concrete-measure reward; lens-fidelity hits the per-lens `LENS_ANCHORS` vocab. `score_cell` composes all three into a `CellScore` with a weighted-mean `aggregate` for sorting only; `rank_cells` SORTS by aggregate — there is NO winner/verdict/decision anywhere (Pitfall 5 / T-81-07; Kaan's ear is BENCH-03). An errored cell scores all-zero + `errored=True` so it sinks in the rank, never fabricated-high. Flipped the 4 BENCH-02 eval xfail scaffolds to real-green.
- Built `src/vibemix/bench/review.py` — `render_review(results, scores) -> str`, a PURE JSON→Markdown renderer that lays the recorded bench cells out for Kaan's ear. It ranks each grounding-dimension group by auto-score (via `rank_cells`, a SORT), renders every cell's 6-D coordinates + the three auto-scores + the assembled prompt + the recorded output, and ends with a literally-EMPTY `## VERDICT (Kaan fills this)` block. THE HARD HUMAN GATE is honored: no code path writes a winner, picks an architecture, or synthesizes a verdict (Pitfall 5 / T-81-09). An errored cell renders `
- 1. [Rule 3 - Blocking] Reframed pin (f) no-MusicState from a sys.modules scan to a static-attribute check

---

## v8.0 Proof & Polish (Shipped: 2026-05-25)

**Phases completed:** 6 phases (71–76), `tech_debt` accepted, `gsd-autonomous fully`.

**Delivered:** Took the system from "engineering-sound on paper" to **proven, easy, and on GitHub** — everything logged · simulated · reported · tested · fixed · verified · GitHub-done, plus ease-of-use + a design level-up loop, with **zero new product capability / dependency / ws-port / IPC-envelope** and **zero reaction-path rewrite** (562 insertions / 7 src files; cardinal invariants held). The pre-milestone deep audit found the system already sound; v8.0 proved and polished it.

**Key accomplishments (one per phase):**

- **P71 Land & Verify:** landed ~773 lines of in-flight `live-tuning-or-brain` work in 3 atomic commits — the BlackHole master-capture device-select fix (was listening to the controller, not the master), robust multi-path `.env` loading + `[FATAL]` exit-4 on a missing key, loud secret-free `connection_error` surfacing (events.jsonl + UI transcript), and a unified Rust+TS debug-log surface + tray-mood.
- **P72 Logged & Simulated:** `--debug-log`/`VIBEMIX_DEBUG_LOG` switch (default-off, byte-identical baseline) + per-turn `reaction_evidence` log; `scripts/sim/simulate_session.py` drives device-select + FLX4 + the full reaction path with **no hardware, no Gemini**, emitting a deterministic `sim_report.json` — covering **everybody × every interaction** (6 personas × 7 event types).
- **P73 Reported · Tested · Fixed · Verified:** `pytest` 4270/0, opt-in marker grid 111/0 (7 Windows/live-FLX4 KAAN-ACTION skips), vitest 816, cargo 63; closed all 4 ALL-MILESTONES-DEEP-AUDIT findings (ack-bank traceability, Phase-68 VERIFICATION.md, citation-bypass confirm, doc-drift); reports RPT-01..03.
- **P74 Ease of Use:** `api-key-missing` (exit-4, the #1 "co-host never speaks" cause) now surfaces actionable UI guidance via the crash-banner — closing the P71 loud-failure loop end-to-end; error-state test coverage that was missing.
- **P75 Design Level-Up Loop:** permanent design-slop gate locking the no-AI-slop brand promise (Saira + JetBrains Mono only, every font stack token-led) — the review→fix→re-review loop made continuous.
- **P76 GitHub Done:** pushed the **539-commit backlog** (the entire v2.1→v8.0 history, never pushed before) to origin + opened **PR #8** to sync `main`. First-ever CI on origin revealed a **GitHub account billing lock** (all jobs fast-fail ~3s) — code verified green locally.

**KAAN-ACTION at close (ride forward):** §GH-BILLING (resolve GitHub billing → CI green + §V7-LIVE-05), §GH-MAIN-MERGE (merge PR #8, no squash), §SHIP-V4/GH-04 (signed release + social, Apple Dev + SignPath signatures — v4.0 closes alongside), §V7-LIVE (real-hardware ear-passes — software-simulated by P72), felt UX/design sign-off, and the user-level (BEG/INT/PRO) UI control (a cross-stack follow-up, surfaced not half-built). All in `KAAN-ACTION-LEGAL.md` + `.planning/v8.0-MILESTONE-AUDIT.md`.

Full audit: `.planning/v8.0-MILESTONE-AUDIT.md` · Requirements: `.planning/REQUIREMENTS.md` · Roadmap: `.planning/ROADMAP.md` (v8.0 section).

---

## v7.0 Open House (Shipped: 2026-05-24)

**Phases completed:** 4 phases, 20 plans, 37 tasks

**Delivered:** Turned vibemix from engineering-green internal code into a publishable, contributable, install-anywhere OSS project — a WIRING + DISCHARGE + POLISH milestone with zero new product capability, zero net-new dependencies, and zero reaction-path edits (cardinal invariants held by zero-touch).

**Key accomplishments (one per pillar):**

- **TEST (Phase 67):** default `uv run pytest -q` flipped from 9-red to 0-red; 21-job `full-test-matrix.yml` CI (OS × marker grid, SHA-pinned, fork-PR-safe); two AST-walk static gates lock the no-silent-skip / no-silent-flake invariants at collection time; 10× flake-hunt baseline 10/10 GREEN; `docs/flake-hunt.md` contributor protocol. 65 opt-in tests triaged into §V7-LIVE clusters (no marker is a graveyard).
- **DEV (Phase 68):** all 10 bundled MIDI profiles contract-tested + synthetic-MIDI-smoked; the duplicate `midi/controllers/` ↔ `midi/profiles/` catalogs reconciled atomically to a single `profiles/` source of truth; 3-profile hot-plug matrix + 4-fixture audio-backend matrix (BlackHole 2ch/16ch + WASAPI loopback + edge fallback) in CI; "Add Your Controller" contributor recipe (`scripts/discover_midi_port.py` + `_template.json` + `add-a-controller.md`).
- **OSS (Phase 69):** 4 OSS docs (CONTRIBUTING/CoC/SECURITY/MAINTAINERS) + presence test with Bravoh carveout sentinel; client-side proxy fallback ("Co-host unavailable this session" — no crash, no hallucinated coach line, /health canary offloaded off the reaction path, 31 integration tests); `docs/byo-key.md` BYO-key path; Homebrew+Scoop scaffolds + `packaging-audit.yml`; `cut_release.sh --dry-run v0.1.0-rc1` re-verified GREEN with the real cut pre-staged in §SHIP-V4.
- **GH (Phase 70):** asset reproducibility pipeline (`regenerate_assets.sh` + `MANIFEST.yaml` + `asset-bitrot.yml`); auto-generated 1200×630 og-card (Chrome-rendered, byte-deterministic, hash-pinned); CDJ-Whisper GitHub Pages landing (UI-review PASS 23/24 — reads as Pioneer-grade hardware, not slop; anti-backsliding grep zero; lighthouse CI gate); demo poster + hero-hash green; one-stop `tests/repo/test_github_presence.py` (validates the real `.yml` GitHub-Forms ISSUE_TEMPLATE shape).

**Engineering:** 19/19 REQ-IDs satisfied engineering-side · 4/4 phases verified · 6/6 cross-phase wirings sound · default grid 4233+ passed / 0 failed.

**Known deferred items at close: 2 verification gaps (Phase 69 + 70, both `human_needed`)** — acknowledged under `gsd-autonomous fully`; all KAAN-ACTION external-clock / live-hardware / felt-quality discharges (see STATE.md Deferred Items + `.planning/v7.0-MILESTONE-AUDIT.md`). The one HARD external gate (OSS-04 publish, gated on Apple Dev + SignPath) closes v4.0 "SHIP" alongside when the real cut fires.

**Git tag + branch merge deferred** to Kaan (consistent with v4.0/v5.0/v6.0): the `v7.0` tag + `live-tuning-or-brain` → main merge ride the same signature clock as the OSS-04 publish.

---

## v6.0 The Memory Turn (Shipped: 2026-05-23 — tech_debt accepted)

**Phases completed:** 4 phases (63–66), 12 plans, ~19 tasks
**Audit:** 14/14 requirements satisfied · 6/6 integration seams WIRED · 53/53 must-haves verified · 247/247 v6.0 surface tests GREEN · 4 cardinal invariants HOLD · 3 anti-feature gates GREEN · zero new dependencies · zero new IPC ports
**Status:** Engineering-green; `VIBEMIX_RECALL_ENABLED=0` default until §RECALL-EAR Kaan-ear pass

**Delivered:** vibemix shifts from a *reactive* co-host to a *forward-leaning* **copilot**. A local per-install `memory.db` + ~50-line `MemoryStore` wrapper land entirely on the shipped `src/vibemix/library/` primitives (zero net-new deps). An off-hot-path post-session ingest job (+ boot sweep) turns each session's `events.jsonl`+evidence+`ai_text` into deterministic TEXT "reaction moment" records — no audio, no LLM-extraction (CI-guarded). The coach prompt grounds in top-k past moments via a new existence-only `recall` evidence source (zero new linter code, mirror of P59 `key:`) + a PAST-tense-fenced gated block in `evidence_line` (cold/empty-memory golden byte-identical). A fabricated `[recall:<id>]` strips the whole turn. Two visible copilot moves (transition-shape callback + vocabulary callback) bottom out in real registered past moments — linter-grounded, cited, warm, non-nagging. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by reuse.

**Key accomplishments:**

- **Phase 63 — Memory Store** (STORE-01..04): MemoryStore storage spine with `SqliteVecMemoryStore` (vec0 primary) + `NumpyStore` fallback, Mac/Win bit-identical `cosine_topk` parity, raw-in/raw-out records, model resolved via `model_router.resolve("embedding")` on FLEX. Path-traversal-defended atomic `delete_session` cascade + boot `reconcile_orphans` + `run_memory_retention_sweep` (oldest-session-first whole-session eviction). All 19 `tests/memory/` GREEN; zero new deps.
- **Phase 64 — Session Ingest** (INGEST-01..03): `ingest.py` ships `build_coach_line_signature` (deterministic, model-free) + `ingest_session` (one `coach_line` per emitted `ai_text`; silenced citation strips skipped; signature-keyed embed-cache idempotency) + `run_ingest_sweep` (boot path-traversal-defended). Wired into `session_loop` at boot + close via `run_in_executor`. Static gate: ingest never imports the coach loop.
- **Phase 65 — Memory Retrieval Seam (ANTI-SLOP RELEASE GATE)** (RECALL-01..04): new existence-only `recall` source added to `EVIDENCE_SOURCES` + `_SOURCE_ALT` + `CITATION_GRAMMAR_BLOCK` (3 schema-mirror sites, lockstep) with zero new linter code. `MemoryRecall` service (event-gated, 0.7-cosine-floored, current-session-excluded). Gated PAST-tense `recall[…]` block in `evidence_line` (byte-identical when cold). Agent pre-dispatches off-loop with hard deadline; survivors registered BEFORE per-turn snapshot. Fabricated `[recall:<id>]` strips the whole turn — pinned by a static gate.
- **Phase 66 — Visible Copilot Move** (COPILOT-01..03): transition-shape callback + vocabulary/register callback templates in `coach.py::recall_fragment_for_event`. Recall chip rides the existing `cohost-reaction` IPC envelope (no new socket). 120s cooldown discipline with arm-on-emit at both bus + bus-less paths. Static anti-feature gate (`tests/repo/test_no_recall_antifeatures.py`) catches 20 forbidden phrases × coach.py + matrix.py. Engineering ships behind `VIBEMIX_RECALL_ENABLED=0`; Kaan flips after §RECALL-EAR ear-pass.

**Known deferred items at close: 18** (12 verification gaps + 6 UAT gaps — all intentional KAAN-ACTION carry-forwards; see STATE.md Deferred Items + KAAN-ACTION-LEGAL.md §SHIP-V4 / §RECALL-EAR). Of those, 11 are unchanged v4.0+v5.0 external-clock / live-confirm items; 6 are v6.0 P66 §RECALL-EAR felt-quality discharge (transition feel, voice/register match, FELT cooldown rhythm, runtime Gemini drift on anti-features). One STORE-03 call-site is deferred to a future recordings-UI-delete phase (out of v6.0 scope).

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock — `live-tuning-or-brain` is unmerged and v4.0 is also untagged/open.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

---

## v5.0 The Useful Cut (Shipped: 2026-05-21)

**Phases completed:** 12 phases, 42 plans, 67 tasks

**Key accomplishments:**

- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- FLOOR (REAL `EventDetector`)
- Extended Phase 54's anti-slop spine to COACH (feedback) mode: the REAL CitationLinter strips an unbacked coach citation and passes the grounded one; coach-relevant events fire grounded across ≥2 genres through the REAL EventDetector; empty evidence never fires — all with real primitives, no mocks, no network.
- Registry from the real fixture.
- Closed the LIVE-05a anti-slop gap on the shipped Three.js rig: SnapshotSlice now carries music/voice levels and drop/peak/breakdown mode entry requires the music level to confirm the phase — a spurious `phase=drop` during a quiet section no longer fires the peak animation.
- Extended four existing perf tests to lock the PERF-01 TTFT telemetry floor and the MINIMAL-thinking gate, plus the PERF-02 zero-underrun floor under both-mode reaction traffic — all CI-runnable without real hardware, zero production code changed.
- Closed the remaining LIVE-05a contract items on the shipped Three.js rig: all six contract modes are proven reachable from real canonical bus events, the AI-speaking path provably overrides every music mode via the existing talk-block rule, mood/emotion are pinned as renderer tints (never FSM branches), and a synthetic mode-transition frame in the dispatch-latency test confirms the mode machine adds no measurable sidecar->client latency (p95 ~0.22ms, well under the 50ms PERF-03 budget).
- Five headless regression assertions (2 new pytest gates, 1 new vitest spec, 1 extended chrome spec) that pin the three v0.1.0-rc1 carryover-bug fixes shipped in `fac4c4a` so the drag capability, JS drag fallback, chrome strip hide, deep-link form, and TCC prime path can no longer silently regress.
- Task 1 — Friction audit (`docs/internal/first-run-friction-audit.md`):
- Rebuilt the AIza-clean vibemix-core sidecar for both apple-darwin triples, produced an unsigned macOS `.dmg` for Gate 2 to inspect (notarization blocked on the EXTERNAL Apple agreement — documented, not forced), and GENERATED `.planning/v4.0-MILESTONE-AUDIT.md` reading `overall_verdict: WIRED` after fixing a generator bug that was reporting false-MISSING seams.
- Fixed the latent REPO_ROOT double-`..` path bug in record_50a_walk.sh (now cwd-independent, target pinned to docs/e2e/2026-05-walk.webm) and proved the Gate-6b producer→consumer path green on a REAL rendered report with Hallucination honestly PARTIAL pending Kaan's ear.
- `cut_release.sh` re-pointed to the v0.1.0-rc public tag + v4.0 milestone audit, with a `--dry-run` signature-stub mode that exits GREEN on the real Plan-01/02 artifacts (everything but the EXTERNAL signature ready) while the `gh release create` hard guard stays absolute and regression-pinned.
- Task 1 — `harmonics.to_camelot` (the load-bearing pure function):
- Added a dedicated existence-only `key:` evidence source (body `<deck>:<camelot>`, e.g. `[key:A:8A]`) across all 5 schema-mirror touchpoints so the existing CitationLinter strips any fabricated harmonic clash — the un-cited-harmonic-feedback retrofit (Risk 2) lands BEFORE any Phase 60 harmonic prompt text.
- Registered KEY_CLASH (pri 7 / 28s) + TRANSITION_OPPORTUNITY (pri 5 / 20s) event types as plumbing-only, and landed the DECK-05 strictly-read-only repo test (tokenize-stripped two-tier scan + SQLCipher dormancy) that fails if any future commit writes a DJ-software DB.
- Task 2 — `_tick_once` single-writer wiring (TDD RED→GREEN):
- A SEPARATE structured-output Gemini deck-read (`DeckVisionReader`) + a real-screenshot accuracy eval harness + a KAAN-ACTION accuracy-floor gate — the universal cross-app fallback leg of the source ladder, shipped DORMANT (vision_enabled=False) behind the eval so it can never feed a misread key until Kaan signs off the real-rig corpus.
- Pure table-driven `is_clash`/`compatible`/`semitone_distance` on top of `to_camelot` — the anti-slop core where the LLM narrates a Camelot clash the code already proved, never computing intervals (HARMONIC-01).
- Wired `_melodic_overlap_gate` + the KEY_CLASH and TRANSITION_OPPORTUNITY branches into `EventDetector.detect()` behind a default-off `harmonic_clash_enabled` flag — a clash is structurally impossible to reach the audience unless the melodic-overlap gate passes, both decks clear the 0.6 cite floor, `is_clash()` returns True, AND the Kaan-ear ship gate flips the flag.
- Task 1 — corpus + veto test (`6c5805c`):
- Replaced the two Phase-59 stub coach arms with real cited harmonic fragments — KEY_CLASH hands the LLM a system-decided verdict + both decks' keys to cite + a hard "do NOT compute intervals" rule; TRANSITION_OPPORTUNITY is a strictly past-tense retrospective blend note — and reconciled the matrix [ev:<TYPE>] grammar.
- Built `pill_window.rs` as a clone-with-subtraction of `mascot_window.rs` (transparent/on-top/decoration-less/non-focus-steal, interactive — NOT click-through), with pill-scoped 200ms-debounced geometry persistence, a display-change re-clamp hook, `.focused(false)` as the macOS focus floor, and the `"pill"` capability-allowlist entry that closes the v0.1.0-rc1 drag-capability debt. The process-wide Accessory policy was removed after runtime verification showed it demoted the main app window and broke foreground reachability.
- Added the `primary_surface` tri-state config (`pill` default | `mascot` opt-in | `none`) to `config.rs` and wired `main.rs` setup() to create the pill, the mascot, or neither at session start — making the floating pill the primary in-set surface while keeping the mascot buildable on demand and the mascot-audit fence green.
- Additive read-only `deck_state` field ({side: {title, camelot, key, bpm, confidence}}) serialized onto the EXISTING flat 30Hz mascot frame on ws://127.0.0.1:8765 — honest-null keys, golden-equivalence on empty, single-writer untouched, no new port.
- The pill consumes the existing ws:8765 bus (direct-WS, no new port) and renders idle/listening/speaking/expand from real wire data — a pure 4-state machine, a real voice.rms TTS waveform (meter.ts tokens), and a verbatim citation strip — all decoupled from src/mascot/ so the mascot-audit fence stays green.
- Honest deck-context chips (`a · 8a · 128`, dim `unknown` on null, `decks · unknown` when nothing resolves) consuming the 62-03 `deck_state` wire field, wired into the pill expand panel, plus the explicit `var(--glass-3)` rgba surface that guarantees mac+win transparency parity (no OS vibrancy, DMG-#13415-resistant).

---

Living history of shipped milestones. One entry per milestone, newest first. Detailed archives in `.planning/milestones/`.

---

## v3.1 — Distribution-Ready Pass

**Shipped:** 2026-05-18 (engineering-complete; `tech_debt` accepted — 7 Kaan-action carveouts ride the v3.0 external clock per `gsd-autonomous fully` mode)
**Phases:** 5 (46 — 50) | **Plans:** 32 | **Mode:** `gsd-autonomous fully`
**Git range:** `v3.0` (2026-05-17) → `HEAD` (2026-05-18) — 61 commits, 382 files, +57,597 / -2,541
**Audit:** `.planning/milestones/v3.1-MILESTONE-AUDIT.md` (tech_debt accepted, 44/44 reqs, 5/5 phases, 5/5 integration, 4/4 flows)
**Known deferred items at close: 7** (see STATE.md Deferred Items — all 7 are `human_needed` external-clock carveouts: §INSTALL-COMPANION-SIGN, §INSTALL-VM-RUN, §SHIP-CONTACT-VBAUDIO, §E2E-50A-WALK, §VIS-04, §VIS-05, DEPS-07/DEPS-08 documented decisions).

### Key Accomplishments

1. **Dependency audit + lockfile shipped** — hermetic `uv.lock` regen in `python:3.12-slim-bookworm` container; `cargo-deny` license allowlist with GPL ban; CycloneDX + SPDX SBOMs on release assets; `docs/AUDIT.md` 3-table surface with green/yellow/red install-impact ratings; freshness gate fails any PR with stale AUDIT.md; Dependabot wired for 4 ecosystems with weekly cadence. 45 passing + 1 xfail (pinact mechanical rewrite deferred to CI).
2. **Mascot real-GLB-land scaffolded** — retarget CLI extended from 5 to 28 slots across 5 families (Base / Emotion / Anticipation / Reaction / legacy_prep); MANIFEST.yaml provenance schema + MIXAMO-CLIP-SOURCES.md selection guidance; 23 placeholder GLB stubs at slot paths so dev loader doesn't 404; EVENT_LAYER_PRIORITY_MAP single-source-of-truth for 15 event classes × 4-layer state machine; 63 Python + 177 TypeScript tests pass.
3. **Opportunity scan locked steady state** — `docs/dep-opportunities/2026-05-scan.md` rates 24 candidates under 4-color rubric (1 Green / 8 Yellow / 9 Red-constraint / 6 Red-risk); ADR sidecar for the one green-adopt (OBS browser-source docs-only); 8 Yellow stubs carry forward to `.planning/archive/2026-05-27-stale-v2-v3-research/v3-buckets/`; zero new runtime deps introduced; exclusion-set memories quoted verbatim.
4. **Win + Mac one-click installer chain live** — Inno Setup `[Run]` + `[Code]` license dialog for VB-CABLE silent install; `fetch_drivers.{sh,ps1}` + `driver_manifest.json` with SHA-256 verify; `companion-sign` workflow + verifier (SignPath cert pending Kaan discharge); `INSTALL_READY` event with 60s CI gate (median 41,000 ms across SHIP-04 simulated matrix, p95 52,000 ms); BlackHole 48 kHz post-install probe; WCAG-AA a11y on wizard; uninstall preserves user data unless opt-in clean. 68 passing + 1 platform-gated skip.
5. **End-to-end MacBook + OS-matrix harness shipped** — `tests/e2e/macbook/` with privacy-fixture asserting zero off-limits writes; Playwright + pixelmatch at `maxDiffPixelRatio: 0.02` baselined on Phase 47 placeholders; audio-loopback VCR cassette pinned to v3.0 GATE-02 (zero live Gemini); Gate 6b wired into `cut_release.sh`; 50a Kaan-walk checklist + Nielsen 10 + screencast capture rig; 50b OS-matrix smoke composes Phase 49 `install_vm_matrix.sh`. 16 passing + 5 CI-tolerant skips.

### Status

- 44 / 44 v3.1 REQ-IDs engineering-satisfied (100% coverage).
- 7 Kaan-action carveouts deferred to STATE.md, all external-clock dependent: §INSTALL-COMPANION-SIGN (SignPath cert) → unblocks §INSTALL-VM-RUN (real Tart VM) → enables §E2E-50A-WALK full pass; §VIS-04 (28 Mixamo retargets via Adobe walk) + §VIS-05 (5 legacy_prep follow-up); §SHIP-CONTACT-VBAUDIO (future OEM optimization); DEPS-07 pinact mechanical-rewrite + DEPS-08 livekit-plugins-openai cull both documented in `docs/AUDIT.md § Decisions`.
- Local annotated git tag `v3.1` to be created on milestone-close commit (NOT pushed — Kaan publishes after external discharges land per §SHIP-CUT cookbook in v3.0).

### Carveouts at close (`gsd-autonomous fully` mode)

Critical-path discharge order (per audit):

1. §INSTALL-COMPANION-SIGN — SignPath OSS Foundation cert grant (Authenticode for `.ps1` + `.py`).
2. §INSTALL-VM-RUN — Real Tart VM execution on macOS 12.3 / 14 / 15 + Win 10 / 11.
3. §E2E-50A-WALK — Kaan's MacBook walk with real DJ-set audio; `docs/e2e/2026-05-walk.webm` capture.
4. §VIS-04 / §VIS-05 — Mixamo Adobe-account retarget walk (independent of 1-3, runs in parallel).
5. §SHIP-CONTACT-VBAUDIO — VB-Audio OEM redistribution email (future Win optimization).

### Tech Debt Acknowledged

- DEPS-07: pinact binary unavailable on local executor; mechanical SHA rewrite deferred to first CI run.
- DEPS-08: `livekit-plugins-openai` cull blocked by direct imports in `src/vibemix/agent/tts_chain.py` + 3 test files; documented for a focused TTS proxy fallback refactor post-v3.1.

### Archives

- Roadmap: `.planning/milestones/v3.1-ROADMAP.md`
- Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md`
- Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

---

## v3.0 — Clean OSS Ship

**Shipped:** 2026-05-17 (engineering-complete; `tech_debt` accepted — KAAN-ACTION-LEGAL discharges pending external clock for public RC publish)
**Phases:** 6 (40 — 45) | **Plans:** 41 | **Mode:** `gsd-autonomous fully`
**Git range:** `v2.1.0` (2026-05-16) → `2aeb020` (2026-05-17) — 250 commits, 529 files, +62,215 / -1,029
**Audit:** `.planning/milestones/v3.0-MILESTONE-AUDIT.md` (passed, 57/57 reqs, 6/6 phases, 3/3 integration, 5/5 flows)
**Known deferred items at close: 6** (see STATE.md Deferred Items — all 6 are `human_needed` verification carveouts that are by-design Kaan-action under autonomy mode; all routed to `KAAN-ACTION-LEGAL.md` §AUDIO-05..07 / §LAT-09 / §GATE-01..05 / §VIS-04 / §LAUNCH-03/04/06/07/08 / §SHIP-01..13 discharge runbooks).

### Key Accomplishments

1. **Anti-slop audio path closed** — Mic-as-Part-2 (12s ring + AI-talk zero-fill) + lookahead-as-Part-3 (3s `NOT YET HEARD BY AUDIENCE` from source file via ffmpeg+mdfind+nowplaying-cli). Closes "AI invents what Kaan said" + "AI reacts after the moment passed" hallucination classes; v4 chat-tested cooldowns re-tuned.
2. **Latency stack v2 shipped** — `ModelRouter` config-driven seam with zero hardcoded model literals (CI grep gate); ServiceTier.FLEX wired for batch paths (50% cost cut); live coach pinned Standard + thinking=MINIMAL; LLM→TTS streaming pipe with bracket-depth-aware sentence boundary; 3.1 Flash TTS 6-tag DSL.
3. **Hybrid hallucination gate in force** — Autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto wired via `check_gate.sh` Gate 2b in `cut_release.sh`; P85 Phase 16 ear-test override formally retired (`P85-OVERRIDE-RETIRED.md`); public `eval/README.md` documents regime + redacts session content.
4. **CDJ Whisper visual lock** — Tier-1 surfaces (session, mascot overlay, wizard, calibration) pass paired `gsd-ui-checker` + `gsd-ui-auditor` with zero HIGH findings; 22-site `--glow-faint` hover-glow sweep; hardware-LED-strip meter rebuild (16 segments, amber peak-hold, silk-12 grid); Mixamo retarget pipeline scaffolded; 8-cut 30s storyboard re-mock with chip overlays.
5. **Launch positioning pre-staged** — README hero locked to "the only AI co-host that actually listens to your set" with 3-gate CI lock + AI-slop blocklist; EvidenceRegistry citation strip in live UI (click → debrief 2s region highlight); Bravoh waitlist toggle (UTM-tracked, opt-in, default-OFF); 16 SVG wordmark placeholders; outreach calendar + T-7 → T+30 launch sequence locked.
6. **External discharge cookbook complete** — KAAN-ACTION-LEGAL §SHIP-01..13 (45-06) ships 13 discharge runbooks in canonical 8-block format covering Apple Dev / SignPath / Bravoh-server / SHIP-CUT / 5-channel social / Discord / repo transfer / 24h rotation / SmartScreen / SHIP-V1-DECISION; SHIP-CUT is one-button after approvals land.

### Status

- 57 / 57 v3.0 REQ-IDs engineering-satisfied (100% coverage).
- 22 of 57 awaiting external clock + Kaan-discharge (legal capacity P46 × 2 + customer-facing publishes × 8 + real-hardware × 3 + real-asset × 1 + corpus × 4 + spike × 1 + visual-regression-test × 1 + sign-off × 2).
- Local annotated git tag `v3.0` created (NOT pushed — Kaan publishes when ready per §SHIP-07 discharge).

### Carveouts at close (`gsd-autonomous fully` mode)

- **Legal-capacity (P46)**: Apple Dev Agreement update (Francesco), SignPath OSS Foundation (Kaan, ~1-week SLA).
- **Customer-facing publishes**: SHIP-CUT (gh release create v3.0.0-rc1 --draft), SHIP-TWEET (5-channel social publish), SHIP-DISCORD, SHIP-TRANSFER, SHIP-ROTATE (24h monitoring rotation), SHIP-V1-DECISION (T+30 ~2-week bake verdict), LAUNCH-06 (bravoh GH org standup), LAUNCH-07 (SHIP-TWEET Kaan+Francesco sign-off), LAUNCH-08 (Discord live-execute).
- **Real-hardware**: INSTALL-VM-RUN matrix execution (SHIP-04), INSTALL-60S-CHECK (SHIP-05), AUDIO-07 fresh-Mac BlackHole probe walk, INSTALL-DEFENDER SmartScreen observation (SHIP-12).
- **Real-asset production**: VIS-04 5 Mixamo retargets (Adobe-account-gated download + Kaan-aesthetic Pioneer-CDJ-headbob selection).
- **Corpus**: GATE-01 ack-bank 20/40 (Gemini quota reset), GATE-02 VCR cassettes, GATE-03 6 × 30-min DJ session WAVs (200 MB git-LFS), GATE-05 ear-test session execution.
- **Spike**: LAT-09 Gemini 3.1 Flash Live music spike (real 5-min DJ clip + offline listen + verdict write).
- **Pre-stage**: AUDIO-05 PGP key, AUDIO-06 Tauri ed25519 updater key, LAUNCH-03/04 real logo swaps (16 SVG placeholders shipped).

### Tag

- `v3.0` (annotated, LOCAL ONLY — `git push origin v3.0` is documented Kaan-action in KAAN-ACTION-LEGAL §SHIP-07).

---

*See `.planning/milestones/v3.0-ROADMAP.md` for full phase narrative + decisions + technical debt. See `.planning/milestones/v3.0-REQUIREMENTS.md` for full REQ-ID traceability with outcomes.*

---

## v2.1 — The Unified Cut

**Shipped:** 2026-05-16 (`tech_debt` accepted) | **Phases:** 13 (27 — 39) | **Plans:** 96 | **Mode:** `gsd-autonomous fully`
**Git range:** `v2.0` → `8c6e668` — 225 commits, +114,845 / -69,617 across 947 files | **Tag:** `v2.1.0` (LOCAL)
**Audit:** `.planning/milestones/v2.1-MILESTONE-AUDIT.md` (105/105 REQ-IDs engineering-satisfied; 15 carveouts deferred to KAAN-ACTION-LEGAL)

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md`.
Expanded phase-detail plans were moved to `.planning/archive/2026-05-27-v2.1-phase-detail/`
because they are historical and include retired product guidance.

---

## v2.0 — Research-Driven Ship

**Shipped:** 2026-05-14 (`tech_debt` accepted) | **Phases:** 12 (15 — 26) | **Plans:** 38 | **Tests:** 1961 passing
**Tag:** `v2.0` | **Audit:** `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md`.

---

## v0.1.0 — MVP Foundation

**Shipped:** 2026-05-13 | **Phases:** 14 (1 — 14) | **Tag:** `v0.1.0-rc1`

Full archive: `.planning/milestones/v0.1.0/`.
