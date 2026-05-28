---
phase: 99-harden-retry
plan: 03
subsystem: library/toolset
tags: [dispatch-hook, hardening, factor-9, retry, terminal-stop-reason, deterministic-hint]
requires:
  - TOOL_STARVATION_THRESHOLD (module constant, library/toolset.py:73 from 99-01)
  - LibraryToolset._consecutive_empties (instance attr, library/toolset.py:120 from 99-01)
  - LibraryToolset.stop_reason (instance attr, library/toolset.py:121 from 99-01)
  - LibraryToolset._is_empty_or_error (private method, library/toolset.py:1051 from 99-02; renumbered from :998 by Plan 99-03's helper insertion)
  - Counter increment block in dispatch() (library/toolset.py:1123-1124 from 99-02; renumbered from :1059-1060)
provides:
  - LibraryToolset._build_starvation_payload (private method, library/toolset.py:998-1049 — three-case deterministic hint)
  - Terminal short-circuit at top of dispatch() (library/toolset.py:1070-1079)
  - Threshold-trip terminal write inside the counter-increment branch (library/toolset.py:1135-1141)
affects:
  - src/vibemix/library/toolset.py (+81 insertions, 0 deletions; 3 additive edits, all inside the dispatch region)
  - tests/library/test_toolset_starvation.py (+257 insertions; 7 new behavior tests for the threshold-trip + hint cases + idempotence)
tech-stack:
  added: []
  patterns:
    - "deterministic-three-case-hint-generator (D-05: no LLM in the hint path — counter state is the source of truth)"
    - "first-write-wins idempotence via `self.stop_reason is None` guard (T-99-03 mitigation; ride the same dispatch-calling-thread serialization the counter rides)"
    - "top-of-dispatch terminal short-circuit returns SHALLOW COPY (`dict(self.stop_reason)`) — caller cannot mutate internal payload (RESEARCH.md Open Q2)"
    - "module-globals constant lookup at call time (direct symbol `TOOL_STARVATION_THRESHOLD`, NOT a captured-at-import copy) honors `monkeypatch.setattr(tool_mod, ...)` — Pitfall 7 closed"
key-files:
  created: []
  modified:
    - src/vibemix/library/toolset.py
    - tests/library/test_toolset_starvation.py
decisions:
  - "D-05 (Decision 5, locked): three deterministic hint cases — A=zero-track library, B=no theme match, C=repeated tool error. Hint is generated from `self._library.tracks` + `last_tool` + `args.get('query', '')` at trip time. Never LLM-generated."
  - "Pitfall 7 resolution: direct-symbol form `TOOL_STARVATION_THRESHOLD` (module-globals lookup at call time) used in `dispatch()`. `monkeypatch.setattr(tool_mod, 'TOOL_STARVATION_THRESHOLD', 2)` actually tunes runtime behavior — `test_threshold_is_tunable` PASSED FIRST TRY. Module-attribute fallback (`sys.modules[__name__].TOOL_STARVATION_THRESHOLD`) NOT needed."
  - "RESEARCH.md Open Q2 (locked): subsequent `dispatch()` calls after the trip return `{'error': 'tool_starvation', 'stop_reason': dict(self.stop_reason)}`. The `dict(...)` shallow copy is REQUIRED — `test_terminal_idempotence_after_starvation` includes a mutation-isolation assertion that the caller's payload tampering does not corrupt internal state."
  - "Counter freezes at threshold after trip — the `else: self._consecutive_empties = 0` branch becomes unreachable because the top-of-`dispatch()` short-circuit returns before the counter hook runs (T-99-01 mitigation)."
metrics:
  duration: "~10 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2
  tests_added: 7
  tests_passing: 624 (full tests/library/ suite; up from 617 in 99-02 by exactly +7 new tests)
  regressions: 0
---

# Phase 99 Plan 03: Threshold Trip + Three-Case Hint + Terminal Short-Circuit Summary

Closed the in-process side of Factor 9. When `LibraryToolset.dispatch()` sees `_consecutive_empties` reach `TOOL_STARVATION_THRESHOLD`, it writes the deterministic three-case payload to `self.stop_reason` and turns into an idempotent terminal echo for every subsequent call — no handler invocation, no counter advance, no second payload write. The cross-process side-channel (Plan 99-04), the CLI exit-code routing (Plan 99-07), the Telegram `format_reply` branch (Plan 99-06), and the AST/grep single-writer gate (Plan 99-05) build on top of the surface this plan lands.

## What Shipped

**Source change (`src/vibemix/library/toolset.py`, +81 insertions, 0 deletions):**

| Symbol / Block | Line(s) | Purpose |
|---|---|---|
| `_build_starvation_payload(self, last_tool, args)` private method | **998-1049** | Deterministic three-case hint generator. Returns the D-04 payload shape `{"reason": "tool_starvation", "hint": <str>, "tool": <str>, "consecutive": <int>}`. Case order: A (zero-track library) → B (search_vibe empty) → C (other tool error). Cases evaluated by `if/elif/else` — first match wins. |
| Terminal short-circuit at top of `dispatch()` | **1070-1079** | `if self.stop_reason is not None: return {"error": "tool_starvation", "stop_reason": dict(self.stop_reason)}`. Lives BEFORE the handler-map dict construction and BEFORE the `ThreadPoolExecutor` block — handler is NEVER invoked after a trip. `dict(...)` is a shallow copy so callers cannot mutate the internal payload. |
| Threshold-trip terminal write | **1135-1141** | Inside the `if self._is_empty_or_error(...)` branch, immediately after the existing `+= 1` (line 1124). `if (self._consecutive_empties >= TOOL_STARVATION_THRESHOLD and self.stop_reason is None): self.stop_reason = self._build_starvation_payload(last_tool=name, args=args)`. The `is None` guard makes the write idempotent (first-write-wins, T-99-03 mitigation). |
| Plan-99-04 signpost | **1134** | `# Side-channel write lands in Plan 99-04.` — Plan 99-04 inserts its `self._write_side_channel(self.stop_reason)` call immediately above (between this comment and the `if` of the threshold check) so the side-channel write rides the same first-write-wins guard. |

**Test changes (`tests/library/test_toolset_starvation.py`, +257 insertions):**

| Test | Pins | Notes |
|---|---|---|
| `test_threshold_trip_sets_stop_reason` | D-03 + D-04: 3 empty `search_vibe` writes the full payload shape (`reason`, `hint`, `tool`, `consecutive`). Fixture library has 5 tracks so this exercises Case B. | The trip happens on the third dispatch (counter=3 == threshold). `consecutive` == 3. |
| `test_threshold_is_tunable` | Pitfall 7: `monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 2)` actually changes runtime behavior. | After 1 empty: `stop_reason is None`. After 2 empties: trip; `consecutive == 2`. PASSED FIRST TRY — direct-symbol form honors monkeypatch. |
| `test_hint_zero_track_library` | D-05 Case A: empty library → hint substrings `"library has 0 tracks"` + `"library ingest"`. | Uses a fresh `LibraryToolset` with `lib.tracks = {}` (not the fixture). Substring match — ear-pass tolerant. |
| `test_hint_no_theme_match` | D-05 Case B: library has tracks, last tool = `search_vibe`, query = `"uplifting 200 BPM ambient"` → hint substrings `"no tracks matched"` + `"'uplifting 200 BPM ambient'"` + `"BPM"`. | Pins the `args.get("query", "")` interpolation behavior. |
| `test_hint_tool_error` | D-05 Case C: 3 consecutive `get_track_features` errors on a non-empty library → hint substrings `"tool 'get_track_features'"` + `"kept failing"`. | Library has tracks (so Case A is skipped) and last tool is NOT `search_vibe` (so Case B is skipped). |
| `test_terminal_idempotence_after_starvation` | RESEARCH Q2 + T-99-01: post-trip dispatch returns `{"error": "tool_starvation", "stop_reason": <copy>}`. Counter frozen at threshold. Shallow-copy mutation isolation — `echo["stop_reason"]["reason"] = "tampered"` MUST NOT corrupt `toolset.stop_reason["reason"]`. | Pins that subsequent `dispatch()` calls on the SAME OR DIFFERENT tools return the idempotent echo. Counter does NOT advance past threshold (top-of-dispatch short-circuit returns first). |
| `test_starvation_short_circuits_subsequent_dispatch` | Short-circuit lives AT TOP of `dispatch()`, BEFORE the `ThreadPoolExecutor` block — the handler is NEVER invoked after a trip. | After trip, patches `toolset.search_vibe` to a function that raises `RuntimeError`. If the short-circuit lived below handler dispatch, the call would crash; instead it returns the terminal echo. |

## Insertion-Site Line Numbers (for Plan 99-04)

After this plan, the dispatch region looks like:

| Line | Symbol |
|---|---|
| 73 | `TOOL_STARVATION_THRESHOLD: int = 3` (module constant, from 99-01) |
| 120 | `self._consecutive_empties: int = 0` (instance attr, from 99-01) |
| 121 | `self.stop_reason: dict[str, Any] \| None = None` (instance attr, from 99-01) |
| 998-1049 | `def _build_starvation_payload(self, last_tool, args) -> dict[str, Any]:` (NEW in 99-03) |
| 1051 | `def _is_empty_or_error(self, name, result) -> bool:` (from 99-02; renumbered from :998 by helper insertion above) |
| 1069 | `def dispatch(self, name, args) -> dict[str, Any]:` |
| 1070-1079 | TERMINAL SHORT-CIRCUIT (NEW in 99-03) |
| 1081-1099 | handler-map dict + lookup |
| 1101-1106 | `ThreadPoolExecutor → result = fut.result(...)` capture block |
| 1108-1122 | Phase 99 counter-hook comment block |
| 1123 | `if self._is_empty_or_error(name, result):` (from 99-02) |
| 1124 | `    self._consecutive_empties += 1` (from 99-02) |
| 1125-1133 | Phase 99 threshold-trip comment block (NEW in 99-03) |
| 1134 | `# Side-channel write lands in Plan 99-04.` ← **PLAN 99-04 INSERTS its `self._write_side_channel(self.stop_reason)` call HERE, between this comment and the `if` at 1135 (or immediately after the assignment at 1139, inside the same `if` branch — either is acceptable). The write must ride the same first-write-wins guard so it fires exactly once.** |
| 1135-1141 | THRESHOLD-TRIP block (NEW in 99-03) |
| 1142-1143 | `else: self._consecutive_empties = 0` (from 99-02; unreachable after trip) |
| 1145 | `return result` (unchanged exit, from 99-02) |

## Threshold-Constant Reference Form (Pitfall 7 closure)

**Chosen form: DIRECT symbol `TOOL_STARVATION_THRESHOLD`** (module-globals lookup at call time). This is what the RESEARCH.md Code Example recommended.

**Why it works:** Python looks up bare names inside a function body via `LOAD_GLOBAL`, which reads the function's `__globals__` dict at call time. For methods defined in `vibemix.library.toolset`, `__globals__ is vibemix.library.toolset.__dict__`. `monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 2)` writes to that same dict. So the dispatch hook always sees the live module value, not a captured-at-import copy.

**Verified empirically:** `test_threshold_is_tunable` PASSED FIRST TRY. No fallback to `sys.modules[__name__].TOOL_STARVATION_THRESHOLD` was needed.

## Verification Gates (per plan `<verification>` block)

**Test gates:**
- `pytest -q tests/library/test_toolset_starvation.py tests/library/test_toolset_starvation_concurrency.py tests/library/test_toolset.py` → **33/33 green** (9 prior starvation [3 99-01 + 5 99-02 + 1 concurrency] + 7 new in 99-03 + 17 canonical = 33).
- `pytest -q tests/library/` → **624 passed, 1 skipped (pre-existing, no transformers), 1 xfailed (pre-existing budget gate)**. Up from 617 in 99-02 by exactly +7 new tests this plan added. Zero regressions.
- Wider sanity: `pytest -q tests/ --ignore=tests/e2e -k "dispatch or toolset or curate or codex_curate or mcp"` → **146 passed, 5651 deselected, 8 pre-existing deprecation warnings — zero regressions.**

**Grep gates (all exact match):**
- `grep -c "self\.stop_reason" src/vibemix/library/toolset.py` → **5** (init at line 121 + guard read in short-circuit at 1078 + dict-copy read in short-circuit at 1079 + guard read in trip block at 1137 + assignment in trip block at 1139). Matches plan spec exactly. Required one comment-line rephrase during Task 2 verification — three explanatory comments used the literal substring `self.stop_reason` (inflating the textual count to 8); rephrased to bare `stop_reason` to keep the textual gate aligned with the semantic gate. Same minor-textual-fix pattern Plan 99-02 used. No behavior change.
- `grep -c "TOOL_STARVATION_THRESHOLD" src/vibemix/library/toolset.py` → **2** (constant declaration at line 73 + threshold check at line 1136). Matches plan spec exactly.
- `grep -n "Side-channel write lands in Plan 99-04" src/vibemix/library/toolset.py` → **1 hit, line 1134**. Matches plan spec.
- `grep -c "self\.seen\.add" src/vibemix/library/toolset.py` → **2** (UNCHANGED from the pre-99-01 baseline). **Baseline for Plan 99-05's AST/grep gate: 2.** Cardinal Invariant #2 holds.

## Cardinal Invariants — Status After This Plan

- **#1 single-writer (analog):** Holds. `self.stop_reason` has exactly ONE write site outside `__init__` — the threshold-trip block at line 1139, guarded by `self.stop_reason is None` for first-write-wins idempotence. The dispatch-calling-thread serialization (lazy `_genre_lookup` precedent, `toolset.py:407-411`) the counter rides also serializes the trip write. Plan 99-05 will tighten this into an AST gate.
- **#2 citation grounding:** Untouched. `self.seen.add` count UNCHANGED at 2 from pre-99-01 baseline. The grounding spine is not modified anywhere in this plan; `create_playlist` two-gate validation is structurally unaffected. The 17 canonical `tests/library/test_toolset.py` tests stay green, including `test_search_populates_seen_set`, `test_create_rejects_invented_id`, `test_create_persists_grounded_playlist`.
- **#3 trust the audio (extended to curation surface, D-05):** Honored. Hint is generated from `self._library.tracks` + `last_tool` + `args.get("query", "")` at trip time — never LLM-generated. The hint reflects REAL counter state.
- **#4 one socket:** N/A (no ws traffic introduced).

## STRIDE Threat-Register Mitigations (from plan `<threat_model>`)

- **T-99-02 (Tampering, hint string with user-input theme):** Mitigated. The `theme` (Case B) is interpolated via f-string ONLY — never `exec`/`eval`. The seeded hint copy quote-wraps the theme (`'{theme}'`) so a hostile user-supplied value cannot escape into hint structure. Output destinations are stderr (CLI) + `strip_leaks` (Telegram, scrubs FS paths).
- **T-99-01 (Tampering, counter overflow past threshold):** Mitigated. Top-of-`dispatch()` short-circuit returns BEFORE the counter hook can advance, so the counter is FROZEN at `>= TOOL_STARVATION_THRESHOLD` after trip. `test_terminal_idempotence_after_starvation` pins this.
- **T-99-04 (Tampering, Invariant #2 `seen`-set grounding leak):** Mitigated. `self.seen.add` count UNCHANGED (= 2 baseline). Plan 99-05's AST gate will pin this across the phase.
- **T-99-03 (Tampering race, idempotent payload write):** Mitigated. The `self.stop_reason is None` guard makes the write idempotent. The shallow copy on the echo (`dict(self.stop_reason)`) prevents caller mutation from corrupting internal state — `test_terminal_idempotence_after_starvation` includes a mutation-isolation assertion.
- **T-99-SC (Tampering, npm/pip/cargo installs):** Accepted. Zero new packages.

## Commits

| Task | Hash | Type | Message head |
|---|---|---|---|
| 1 (RED) | `a9bcab5f` | `test(99-03)` | add failing threshold-trip + 3-case hint + idempotence tests |
| 2 (GREEN) | `fecf9a3e` | `feat(99-03)` | wire threshold trip + 3-case hint + terminal short-circuit |

Both commits used **named-path staging only** (`git add tests/library/test_toolset_starvation.py` / `git add src/vibemix/library/toolset.py`), NEVER `git add -A` or `git add .`. Pre-commit `git diff --cached --name-only` verified empty before staging each plan-file, and again after staging to confirm only this plan's files were captured — safe alongside the parallel sessions touching `tauri/ui/*`, `src/vibemix/intel/claim_validator.py`, `src/vibemix/prompts/*`, `docs/launch/*`, `.planning/research/2026-05-27-intel-16-implementation-readiness-checklist.md`, etc. **Zero cross-session bleed into either commit.** Both commits passed the post-commit deletion check (`git diff --diff-filter=D --name-only HEAD~1 HEAD` returned empty for both).

## Deviations from Plan

**One minor textual deviation (no behavior impact):**

**1. [Rule 1 - Bug] Three explanatory comments initially used the literal substring `self.stop_reason`, breaking the plan's `grep -c "self\.stop_reason" src/vibemix/library/toolset.py == 5` gate (returned 8).**
- **Found during:** Task 2 grep-gate verification.
- **Issue:** Three comment lines (in the short-circuit comment block and in the threshold-trip comment block) referenced the attribute with the leading `self.` for readability — inflating the textual grep count to 8 even though the executable-reference count was the prescribed 5.
- **Fix:** Rephrased three comment lines from `self.stop_reason` → bare `stop_reason` (e.g. "Once the threshold has tripped (the ``stop_reason`` attr is set)" rather than "Once the threshold has tripped (``self.stop_reason`` is non-None)"). Preserves the semantic intent; the AST gate Plan 99-05 will install would catch the same thing more robustly. Same minor-textual-fix pattern Plan 99-02 used.
- **Files modified:** `src/vibemix/library/toolset.py` (three comment-line rewrites within Task 2 GREEN's diff).
- **Commit:** included in `fecf9a3e` (Task 2 GREEN).

**No other deviations.** Wiring executed exactly as the plan specifies:
- `_build_starvation_payload` placed immediately above `_is_empty_or_error` (the dispatch region private-helper convention).
- Short-circuit at the TOP of `dispatch()`, BEFORE the `handlers = {...}` dict construction.
- Threshold trip immediately after the `+= 1` and BEFORE the `else: = 0` branch.
- Direct-symbol form `TOOL_STARVATION_THRESHOLD` (no `sys.modules[__name__]` fallback needed; Pitfall 7 closed first try).
- Inline signpost `# Side-channel write lands in Plan 99-04.` at line 1134.
- No file I/O / env-var reads / `import os` use (Plan 99-04's scope).
- No handler bodies touched. No `agent/`, `__main__.py`, `intel/`, `mcp_server.py`, `codex_curate.py`, `tauri/ui/`, or `library/telegram_bridge.py` touched.

## Out-of-Scope Discoveries (Logged, NOT Fixed)

- None this plan. The pre-existing `tests/e2e/macbook/conftest.py` jinja2 collection error documented in 99-02 is still in place, still out-of-scope, still skip-markered in default runs.

## What's Left for Future Plans (per Phase 99 scope)

- **Plan 99-04**: Cross-process side-channel. Insert `self._write_side_channel(self.stop_reason)` immediately after the assignment at toolset.py:1139 (inside the same `if` branch, so the side-channel write rides the first-write-wins guard and fires exactly once). Reads `VIBEMIX_STOP_REASON_FILE` env var; best-effort write (per RESEARCH.md). The line-1134 inline comment is the signpost.
- **Plan 99-05**: AST/grep single-writer gate — `tests/repo/test_no_seen_relaxation.py` plus a tight assertion that `self._consecutive_empties` has exactly one write site outside `__init__` (the `+= 1` at 1124, the `= 0` at 1143) and `self.stop_reason` has exactly one write site outside `__init__` (the assignment at 1139). Baseline `self.seen.add` count from this plan = **2** (record for the gate).
- **Plan 99-06**: Telegram bridge `format_reply` branch for `tool_starvation` (renders the hint via `strip_leaks`).
- **Plan 99-07**: CLI exit-code dispatch — `library curate` / `library build-set` exit with code **10** when `stop_reason["reason"] == "tool_starvation"`.
- **Plan 99-08**: Env-propagation cross-process verification checkpoint.

## KAAN-ACTION Reminder

Hint copy is **SEEDED per D-05**. The three seed strings are:

| Case | Seed copy |
|---|---|
| A — zero-track library | ``"library has 0 tracks — run `library ingest` first"`` |
| B — no theme match | ``f"no tracks matched '{theme}' — try a broader theme or different BPM range"`` |
| C — tool error | ``f"tool '{last_tool}' kept failing — try again or check codex installation"`` |

**KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS** (parked at milestone close per `PROJECT.md` § Current Milestone) will polish the wording on funded-key DJ-set testing. Tests pin SUBSTRINGS of key phrases (`"library has 0 tracks"`, `"library ingest"`, `"no tracks matched"`, `f"'{theme}'"`, `"BPM"`, `"tool '{name}'"`, `"kept failing"`), not full-string equality, so ear-pass refinements should not break tests.

Anti-slop self-check on the seed copy: no "I apologize", no "Sorry, I cannot", no "Let me know if..." — passes the `stop-slop` blocklist on its face. The runtime co-host filter (`src/vibemix/prompts/negative_dict.py`) is upstream of this surface and is unaffected.

## Self-Check: PASSED

**Files claimed:**
- `[ FOUND ]` `src/vibemix/library/toolset.py` (modified, +81 insertions, 0 deletions)
- `[ FOUND ]` `tests/library/test_toolset_starvation.py` (extended, +257 lines)
- `[ FOUND ]` `.planning/phases/99-harden-retry/99-03-SUMMARY.md` (this file)

**Commits claimed:**
- `[ FOUND ]` `a9bcab5f` (Task 1 RED, `test(99-03)`)
- `[ FOUND ]` `fecf9a3e` (Task 2 GREEN, `feat(99-03)`)

**Symbol locations claimed:**
- `[ FOUND ]` `_build_starvation_payload` at `src/vibemix/library/toolset.py:998`
- `[ FOUND ]` `_is_empty_or_error` at `src/vibemix/library/toolset.py:1051` (renumbered from 99-02's :998 by helper-insertion above)
- `[ FOUND ]` `dispatch` at `src/vibemix/library/toolset.py:1069`
- `[ FOUND ]` terminal short-circuit at `src/vibemix/library/toolset.py:1078-1079`
- `[ FOUND ]` counter `+= 1` at `src/vibemix/library/toolset.py:1124`
- `[ FOUND ]` Plan-99-04 signpost at `src/vibemix/library/toolset.py:1134`
- `[ FOUND ]` threshold-check assignment at `src/vibemix/library/toolset.py:1139`
- `[ FOUND ]` counter `= 0` at `src/vibemix/library/toolset.py:1143`

**Grep-gate counts claimed:**
- `[ VERIFIED ]` `self.stop_reason` = 5
- `[ VERIFIED ]` `TOOL_STARVATION_THRESHOLD` = 2
- `[ VERIFIED ]` `Side-channel write lands in Plan 99-04` = 1 hit at line 1134
- `[ VERIFIED ]` `self.seen.add` = 2 (UNCHANGED — Plan 99-05 baseline)

**Test count claimed:**
- `[ VERIFIED ]` `tests/library/` = 624 passed, 1 skipped, 1 xfailed (up from 617 in 99-02 by +7).
- `[ VERIFIED ]` `tests/library/test_toolset_starvation.py` = 15 passed (3 99-01 + 5 99-02 + 7 99-03).
- `[ VERIFIED ]` `tests/library/test_toolset_starvation_concurrency.py` = 1 passed (unchanged from 99-02).
- `[ VERIFIED ]` `tests/library/test_toolset.py` = 17 passed (zero regression on canonical fixture).
- `[ VERIFIED ]` 33-test focal triplet (toolset / starvation / starvation_concurrency) = 33/33 green.
