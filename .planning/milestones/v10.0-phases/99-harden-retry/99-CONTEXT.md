# Phase 99: HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9) - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Auto-resolved via `--auto` (default-YES on grey-area per `gsd-autonomous fully`). All gray areas auto-selected; each pick logged inline with rationale.

<domain>
## Phase Boundary

**From ROADMAP.md § Phase 99:** Close the Factor-9 partial from the 2026-05-28 humanlayer/12-factor-agents audit. Today Viber silently degrades on empty/error tool sequences — Codex's MCP harness retries internally but vibemix has no consecutive_errors counter or terminal `stop_reason` for tool starvation, so a curation run on an empty library returns "no playlist" with no diagnosis. Add per-curation-run error counter; after N consecutive empty `search_vibe` / errored tool calls, emit terminal `stop_reason="tool_starvation"` with an actionable user-facing hint. CLI non-zero exit. Uniform propagation through `codex_curate.curate_with_codex` + `build_set_with_codex` so callers (CLI + Telegram + GUI) see the same stop_reason regardless of starvation origin.

**Acid test (from PROJECT.md):** Codex backend against an intentionally empty library (no Rekordbox cache) currently returns "no playlist" with no diagnosis; after this phase it returns honest `tool_starvation: library has 0 tracks — run \`library ingest\` first` with a non-zero exit on the CLI.

**Island scope:** `src/vibemix/library/codex_curate.py` + `src/vibemix/library/toolset.py` + `tests/library/` only. NOT `agent/`, NOT `__main__.py`, NOT `intel/`, NOT `tauri/ui/`. Disjoint from the LiveKit-upgrade handoff and the frontend wiring handoff (parallel sessions on same working tree per `feedback_concurrent_sessions_one_tree`).

**Cardinal invariants (additively held):**
- **#1 single-writer (analog):** counter writes confined to `LibraryToolset` instance for the duration of one curation run. AST/grep gate pins it.
- **#2 citation grounding:** counter is additive telemetry on the existing `LibraryToolset`. Never relaxes the `seen`-set validation or the `create_playlist` library re-validation. A `tool_starvation` termination MUST short-circuit BEFORE any partial-playlist write.
- **#3 trust the audio:** N/A (live co-host untouched).
- **#4 one socket:** N/A (CLI + MCP STDIO + Telegram long-poll surfaces only; no new ws traffic).

</domain>

<decisions>
## Implementation Decisions (auto-resolved gray areas)

### Decision 1 — Counter location

**Question:** Where does the consecutive-error counter live?

**Options considered:**
1. **(recommended)** `LibraryToolset` instance attribute (`self._consecutive_empties: int = 0`), mirroring the lifetime of `self.seen` / `self.seen_sections` / `self.issued_*`. One instance == one curation run, so counter scope == run scope.
2. Module-level mutable state in `library/toolset.py`.
3. Pass an explicit `RetryContext` dataclass between handlers.

**[auto] Selected: Option 1 — `LibraryToolset` instance attribute.**

**Why:** The toolset already owns per-run state (`seen`, `seen_sections`, `created`, `exported`). Adding `_consecutive_empties` + `_starvation_stop_reason: dict | None` to the same instance keeps the grounding spine and the starvation spine in the same lifecycle (closes the "instance dies → counter dies → no leak across runs" path by construction). Mirrors REQ-RETRY-01 exactly.

### Decision 2 — What increments the counter

**Question:** Which tool-call outcomes increment `_consecutive_empties`?

**Options considered:**
1. **(recommended)** Both: (a) `search_vibe` returning zero candidates, AND (b) any handler returning `{"error": ...}` from the dispatch table.
2. `search_vibe` empty results only — ignore other tool errors.
3. Any tool error only — ignore empty `search_vibe`.

**[auto] Selected: Option 1 — both empty `search_vibe` AND any `{"error": ...}` response from `dispatch()`.**

**Why:** REQ-RETRY-01 names both explicitly. Empty `search_vibe` is the silent-degradation symptom on a too-narrow theme; tool error is the symptom on a crashed/timed-out handler. Both are "the agent cannot make progress" signals. Counter resets on any successful non-empty tool return (REQ-RETRY-06 spec).

### Decision 3 — Threshold N

**Question:** How many consecutive empty/error calls trigger `tool_starvation`?

**Options considered:**
1. **(recommended)** `N = 3` as a module constant `TOOL_STARVATION_THRESHOLD = 3` in `library/toolset.py`. Tunable.
2. `N = 2` — fastest feedback but false-fires on a single missed search followed by a retry.
3. `N = 5` — most permissive; risks slow degradation feedback.

**[auto] Selected: Option 1 — `TOOL_STARVATION_THRESHOLD = 3`.**

**Why:** REQ-RETRY-02 explicitly names default 3 with rationale: "fast feedback on real failure modes without false-firing on a single missed search". `N=2` would trip on a normal "narrow first search, broaden, find" sequence. `N=5` would let a stuck loop burn the user's Codex turn budget. 3 is the documented standard for retry-with-error-in-context patterns (matches 12-factor-agents Factor 9's example).

### Decision 4 — Stop-reason surface

**Question:** How does `codex_curate` learn the toolset hit `tool_starvation`?

**Options considered:**
1. **(recommended)** New instance attribute `self.stop_reason: dict | None = None` on `LibraryToolset`. When the counter hits the threshold, the next `dispatch()` call writes `self.stop_reason = {"reason": "tool_starvation", "hint": "...", "tool": "<last_tool_name>"}` and returns it directly. Mirrors the existing `self.created` / `self.exported` attribute-as-result-spine.
2. A new `dispatch()` return convention (sentinel dict key like `"_stop_reason"`).
3. Raise a custom `ToolStarvationError` exception.

**[auto] Selected: Option 1 — `self.stop_reason: dict | None` attribute, parallel to `self.created` / `self.exported`.**

**Why:** Matches the existing toolset pattern (`created`, `exported` are how the agent surfaces terminal results today — see `library/toolset.py:101-105`). Adding `stop_reason` to the same row keeps the read seam in `codex_curate` simple (one place to check). Exception path (option 3) breaks the "handlers RETURN error dicts, never raise" no-hang contract (see `library/toolset.py` module docstring). Sentinel dict key (option 2) is fragile.

### Decision 5 — Hint generation policy

**Question:** How is the actionable user-facing hint generated?

**Options considered:**
1. **(recommended)** Deterministic, generated from the toolset's view of the world at threshold-trip time. Three named cases: (a) library has zero tracks → `"library has 0 tracks — run \`library ingest\` first"`; (b) library has tracks but `search_vibe` returned zero on the run's theme → `"no tracks matched '<theme>' — try a broader theme or different BPM range"`; (c) repeated tool-error → `"tool '<name>' kept failing — check Codex MCP harness logs"`.
2. Let Codex synthesize the hint (LLM-generated).
3. Fixed single hint regardless of cause.

**[auto] Selected: Option 1 — deterministic case-based hint.**

**Why:** Deterministic copy is testable (REQ-RETRY-06 covers exactly these three cases). LLM-generated hints (option 2) violate Cardinal Invariant "trust the audio" extended to the curation surface — the hint must reflect the REAL counter state, never invented text. Fixed hint (option 3) buries the cause and fails REQ-RETRY-03's "names the most likely root cause" requirement.

**Hint copy seed (KAAN-ACTION ear-pass §HARDEN-PHASE-A-EAR-PASS will polish these):**
- Zero-track library: `library has 0 tracks — run \`library ingest\` first`
- No theme matches: `no tracks matched '<theme>' — try a broader theme or different BPM range`
- Tool error: `tool '<name>' kept failing — try again or check codex installation`

### Decision 6 — CLI exit codes

**Question:** What exit code does the CLI emit on `tool_starvation`?

**Options considered:**
1. **(recommended)** `exit code 10` for `tool_starvation`. Reserved range: 10-19 for terminal `stop_reason` codes (10=tool_starvation, 11=clarification_needed (Phase 100), 12-19=future). Existing code path keeps using 1 for unhandled errors and 0 for success.
2. Generic `exit code 1` for all errors.
3. Use sysexits.h convention (EX_DATAERR=65).

**[auto] Selected: Option 1 — exit 10 for `tool_starvation`, reserve 10-19 range for stop_reasons.**

**Why:** REQ-RETRY-04 + REQ-CLARIFY-04 both call for distinct non-zero codes that scripts can branch on. Exit 1 (option 2) loses the signal. sysexits (option 3) is a Unix mail-system convention nobody scripts against in the DJ-software world. The 10-19 range is unused by every shell/process tool we touch and gives Phase 100 a sibling slot.

### Decision 7 — Test seam

**Question:** How are tests written against a Codex-free environment?

**Options considered:**
1. **(recommended)** Unit-test `LibraryToolset` directly with fake `embedder` / `store` / `library` objects. The counter/threshold/stop_reason logic lives in the toolset, so the Codex CLI never needs to be present. Codex propagation is covered with the existing `_runner` injection seam in `codex_curate.py:392`.
2. Spawn a fake Codex subprocess.
3. End-to-end with real Codex on a CI runner with a fixture library.

**[auto] Selected: Option 1 — toolset-direct unit tests + `_runner` injection seam for `codex_curate` propagation.**

**Why:** Mirrors the existing test posture (`tests/library/test_toolset_*.py` already directly exercise the toolset). Decouples the test suite from a Codex install. End-to-end with real Codex (option 3) is what KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS handles on funded-key.

### Decision 8 — Telegram propagation

**Question:** Does the Telegram bridge need a branch for `tool_starvation` in `format_reply`?

**Options considered:**
1. **(recommended)** Yes — `format_reply` adds a `tool_starvation` branch alongside the existing playlist + error branches. Renders the hint via `strip_leaks` (privacy preserved).
2. No — let it fall through to the generic error branch.

**[auto] Selected: Option 1 — explicit `tool_starvation` branch in `format_reply`.**

**Why:** The whole point of REQ-RETRY-03's actionable hint is wasted if the Telegram surface shows a generic error. Path-leak-strip via `strip_leaks` keeps the privacy posture. Single-line change to `format_reply` — covered in REQ-RETRY-07 (uniform propagation).

</decisions>

<code_context>
## Existing Code Insights (scouted at discuss-time, deeper map in research)

**Files to touch:**

- `src/vibemix/library/toolset.py:72` — `LibraryToolset` class. Per-run state already lives here: `seen`, `seen_sections`, `created`, `exported`, etc.
- `src/vibemix/library/toolset.py:115-145` — handler entry points (`search_vibe`, `get_track_features`, ...). Each returns `dict[str, Any]`; error responses already use `{"error": "..."}` convention.
- `src/vibemix/library/toolset.py:982` — `dispatch(name, args)` method. The single seam where every handler call passes through; counter logic lands here.
- `src/vibemix/library/codex_curate.py:382-487` — `curate_with_codex(...)` outer wrapper. Already has process-level timeout/auth/empty-output guards; parses Codex's `last_message.json` for the final result. The stop_reason propagation lands here.
- `src/vibemix/library/codex_curate.py:642-` — `build_set_with_codex(...)` parallel wrapper. Same stop_reason propagation.
- `src/vibemix/library/telegram_bridge.py:107` — `format_reply(norm)`. Adds the `tool_starvation` branch.
- `src/vibemix/__main__.py` CLI commands `library curate` / `library build-set` (currently around the CLI dispatcher block) — exit code branching. **Note:** these are CLI dispatchers in `__main__.py` so editing must be surgical (the LiveKit handoff also touches `__main__.py:1353`; commit by named-path only, never `git add -A`).

**Files explicitly NOT touched:**
- `src/vibemix/agent/*` (live co-host)
- `src/vibemix/__main__.py` LiveKit handler / session_loop wiring (parallel handoff)
- `tauri/ui/*` (parallel frontend handoff)
- `src/vibemix/intel/*`

**Patterns to mirror:**
- `library/toolset.py:1006-1013` — `dispatch()`'s per-tool timeout + `{"error": ...}` swallow. The starvation check rides in `dispatch()` AFTER the handler call returns.
- `library/toolset.py:101-105` `self.created` / `self.exported` — the existing "terminal result surfaces as instance attribute" pattern. `self.stop_reason` mirrors it.
- `library/codex_curate.py:_runner` — injection seam for unit tests. Same posture for propagation tests.

</code_context>

<specifics>
## Specific Ideas (locked at this phase)

- **`TOOL_STARVATION_THRESHOLD = 3`** module constant in `library/toolset.py`. Tunable for ear-pass.
- **`self._consecutive_empties: int = 0`** + **`self.stop_reason: dict | None = None`** on `LibraryToolset.__init__`. Reset on every successful non-empty/non-error tool return.
- **`self.stop_reason`** payload shape: `{"reason": "tool_starvation", "hint": "<string>", "tool": "<last_tool_name>", "consecutive": <int>}`.
- **Hint copy** (seeded — KAAN-ACTION ear-pass tunes the wording): three named cases per Decision 5.
- **CLI exit codes**: 10 = `tool_starvation`. (11 reserved for `clarification_needed` in Phase 100.)
- **Test posture**: `tests/library/test_toolset_starvation.py` + `tests/library/test_codex_curate_stop_reason.py`. Both unit-only, no Codex install required.
- **CLI surface**: pretty-print the hint to stderr; the playlist M3U is NEVER written when `stop_reason == "tool_starvation"`. Stdout stays clean for scripting.

</specifics>

<deferred>
## Deferred Ideas (captured, NOT in scope)

- **Telemetry / metrics on starvation rate** — tracking how often real users hit `tool_starvation` in production. Deferred to a future telemetry milestone; today's vibemix has no telemetry pipeline and CLAUDE.md's privacy hard-rule rules out anything that ships data home.
- **Auto-retry with broadened theme** — "the agent could re-search with widened BPM tolerance after the first empty search." DEFERRED: violates 12-factor-agents Factor 9 "self-healing trap" — better to surface the cause and let the user broaden, than to silently grow the search and ship a non-matching playlist.
- **`tool_starvation` recovery loop** — multi-turn retry where the user widens the theme via Telegram and the agent picks up. DEFERRED to HARDEN-FUTURE-01 (multi-turn Viber state persistence) per REQUIREMENTS.md.
- **Hint copy A/B testing** — deferred to post-launch ear-pass + KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS.

</deferred>
