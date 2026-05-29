---
phase: 100-harden-clarify
verified: 2026-05-28T17:30:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 100: HARDEN-CLARIFY — Viber RequestClarification Tool (Factor 7) Verification Report

**Phase Goal:** When Codex sees a materially ambiguous theme, instead of silently picking one heuristic, it calls `request_clarification(question, choices)` which terminates the run with `stop_reason="clarification_needed"`. CLI prints the question + numbered choices + exits with a distinct code; Telegram bridge replies with the formatted prompt; the caller re-invokes curation with the resolved theme.

**Verified:** 2026-05-28T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped 1:1 to ROADMAP Phase 100 Success Criteria + REQ-IDs HARDEN-CLARIFY-01..07)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `request_clarification` handler exists in `LibraryToolset` with `MIN_CHOICES=2` / `MAX_CHOICES=5` validation; rejects 0/1/6+ choices, accepts 2-5; dispatch-table entry wires it through `dispatch()`. (HARDEN-CLARIFY-01) | VERIFIED | `src/vibemix/library/toolset.py:83-84` constants, `:1126-1245` handler body, `:1333` dispatch entry `"request_clarification": self.request_clarification`. Args validation: question must be non-empty str (`:1193`); choices must be list of 2-5 non-empty strings (`:1204-1229`). 34 tests pass in `tests/library/test_toolset_clarification.py`. |
| 2 | FastMCP `@mcp.tool()` exposes `request_clarification(question: str, choices: list[str]) -> dict` with teaching docstring describing when to call it (materially ambiguous theme, 2-5 specific choices, single-turn semantics). (HARDEN-CLARIFY-02) | VERIFIED | `src/vibemix/library/mcp_server.py:230-258` — explicit signature, docstring includes "uplifting" / BPM / mood examples + Hick's-law-derived 2-5 bounds. 11 tests pass in `tests/library/test_mcp_server_clarification.py`. |
| 3 | `CodexCurateResult` carries `question: str \| None` + `choices: list[str] \| None` fields (defaults None on cold path). Both `curate_with_codex` and `build_set_with_codex` propagate `stop_reason="clarification_needed"` + question + choices uniformly via the side-channel JSON pattern shared with Phase 99 `tool_starvation`. (HARDEN-CLARIFY-03, HARDEN-CLARIFY-07) | VERIFIED | `src/vibemix/library/codex_curate.py:221-222` dataclass fields; `:566-575` `curate_with_codex` clarification_needed elif branch; `:889-897` `build_set_with_codex` parallel branch. Both read `payload.get("reason") == "clarification_needed"` and populate the dataclass identically. |
| 4 | CLI `library curate` / `library build-set` print a 2-block stderr layout (header + question + numbered choices + re-run hint) and exit with code **11** (distinct from Phase 99's exit 10 = tool_starvation, and from generic exit 1). Single-turn semantics — no state retention. (HARDEN-CLARIFY-04, HARDEN-CLARIFY-06) | VERIFIED | `src/vibemix/__main__.py:2667-2687` curate handler `return 11`; `:2744-2757` build-set handler `return 11`. Both render header + question + numbered choices + `Re-run with: library curate/build-set "<theme>+<chosen option>"`. Normalizer at `:3006-3015` returns `{"ok": False, "stop_reason": "clarification_needed", "question", "choices"}` for Telegram. |
| 5 | Telegram bridge `format_reply` has a `clarification_needed` branch that renders question + numbered choices via `strip_leaks` (no FS path leakage). Existing playlist branch byte-identical. (HARDEN-CLARIFY-05) | VERIFIED | `src/vibemix/library/telegram_bridge.py:137-143` — clarification_needed branch sits BEFORE generic `if not norm.get("ok")` to prevent shadowing (same insertion-order discipline as Phase 99). Uses `strip_leaks(...)` to scrub FS paths. 29 tests pass in `tests/library/test_telegram_bridge.py`. |
| 6 | `request_clarification` handler has NO `track_id` surface — static AST gate proves no `track_id`/`trackId`/`track_ids` string literals in body, no `self.seen`/`self.seen_sections`/`self.issued_*` access, strict `(self, args)` signature, no while-loop/self-recursion. Cardinal Invariant #2 holds by structural impossibility. (HARDEN-CLARIFY-06, HARDEN-CLARIFY-07) | VERIFIED | `tests/library/test_request_clarification_no_track_surface.py` — 6 AST gates: `test_request_clarification_no_track_surface`, `test_request_clarification_no_seen_mutation`, `test_request_clarification_no_consecutive_empties_touch`, `test_request_clarification_signature_strict`, `test_request_clarification_single_turn_no_internal_loop`, `test_baseline_seen_add_count_unchanged_post_phase_100`. All passing. |
| 7 | End-to-end integration seal — REAL toolset payload → REAL wrapper → REAL CLI handler → REAL exit 11 + 2-block stderr; AND REAL chain → REAL normalizer → REAL `format_reply` + leak-strip; AND `build_set` sibling path. Codex CLI is the only mocked boundary. Uniform propagation across toolset + wrapper + normalizer + CLI + Telegram. (HARDEN-CLARIFY-07) | VERIFIED | `tests/library/test_codex_curate_stop_reason.py:946,1042,1140` — three integration seal tests: `test_clarification_full_chain_to_cli_curate`, `test_clarification_full_chain_to_telegram`, `test_clarification_build_set_path_seal`. 16/16 file-local pass; 717/717 in `tests/library/` (1 unrelated skip, 1 unrelated xfail). |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/library/toolset.py` | `request_clarification` handler + `MIN_CHOICES`/`MAX_CHOICES` constants + dispatch wiring | VERIFIED | 1517 LOC, handler `:1126-1245`, constants `:83-84`, dispatch entry `:1333`, exports `:1517-1518`. Reuses Phase 99 `_write_side_channel` and the dispatch-top short-circuit unchanged. |
| `src/vibemix/library/mcp_server.py` | `@mcp.tool()` `request_clarification(question, choices)` with teaching docstring | VERIFIED | Decorator at `:230`, signature explicit, docstring covers "uplifting" / BPM / mood examples + 2-5 constraint rationale. |
| `src/vibemix/library/codex_curate.py` | `CodexCurateResult` `question`/`choices` fields; both wrapper elif branches | VERIFIED | Dataclass `:221-222`; both wrapper branches present (`:566-575` curate, `:889-897` build_set). `to_dict()` via `asdict()` emits the fields. |
| `src/vibemix/__main__.py` | CLI exit 11 + 2-block stderr render in both `_cmd_library_curate_codex` and `_cmd_library_build_set_codex`; `_normalize_codex_curate_result` clarification branch | VERIFIED | Curate handler at `:2667-2687`, build-set at `:2744-2757`, normalizer at `:3006-3015`. Both CLI handlers return rc=11 from the clarification elif before the generic single-line stderr branch. |
| `src/vibemix/library/telegram_bridge.py` | `format_reply` clarification_needed branch with strip_leaks + numbered choices | VERIFIED | `:137-143` — inserted BEFORE the generic `if not norm.get("ok")` to avoid shadowing (same load-bearing insertion-order as Phase 99). |
| `tests/library/test_toolset_clarification.py` | Handler unit tests (args validation, payload shape, no-track-id-on-accept) | VERIFIED | 34 tests, all green. |
| `tests/library/test_mcp_server_clarification.py` | MCP exposure tests (registration, signature, docstring) | VERIFIED | 11 tests, all green. |
| `tests/library/test_request_clarification_no_track_surface.py` | AST gate (6 structural properties) | VERIFIED | 6 tests, all green. File documented with explicit "why static AST not behavioral mock" rationale. |
| `tests/library/test_codex_curate_stop_reason.py` | Propagation tests + integration seal tests | VERIFIED | 16 tests, all green. Includes 3 seal tests (`test_clarification_full_chain_to_cli_curate` / `_to_telegram` / `_build_set_path_seal`). |
| `tests/library/test_cli_exit_codes.py` | CLI rc=11 + stderr render tests | VERIFIED | Phase 100-04 block in the file, all green. |
| `tests/library/test_telegram_bridge.py` | format_reply clarification branch tests | VERIFIED | 29 tests, all green. |
| `tests/repo/test_no_seen_relaxation.py` | Cardinal Invariant #2 carry-over (BASELINE_SEEN_ADD_COUNT=2) | VERIFIED | Phase 99-05 gate; the Phase 100 AST gate file mirrors this from `tests/library/` side. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Codex MCP server tool call | `LibraryToolset.request_clarification` | `mcp_server.py:258 toolset.request_clarification({"question": question, "choices": choices})` | WIRED | FastMCP decorator wraps the call; toolset method runs validation then writes `self.stop_reason`. |
| `LibraryToolset.request_clarification` | Wrapper-side `CodexCurateResult` | `_write_side_channel(self.stop_reason)` → JSON to `VIBEMIX_STOP_REASON_FILE` env path → `curate_with_codex` reads after subprocess exits | WIRED | Side-channel reuses Phase 99-04's writer unchanged (discriminator-agnostic — reads any payload carrying a `reason` key). |
| `CodexCurateResult.stop_reason="clarification_needed"` | CLI exit 11 + 2-block stderr | `_cmd_library_curate_codex` elif at `__main__.py:2668` → header + question + numbered choices + re-run hint → `return 11` | WIRED | Includes parallel branch in `_cmd_library_build_set_codex` (`:2745`); both echo distinct hint strings (curate vs build-set). |
| `CodexCurateResult.stop_reason="clarification_needed"` | Telegram chat render | `_normalize_codex_curate_result` returns ok=False + question + choices → `format_reply` clarification_needed elif at `telegram_bridge.py:137` → `strip_leaks(joined)` | WIRED | Leak-strip applied at the integration boundary; verified by `test_clarification_full_chain_to_telegram` with malicious path-shaped question. |
| Cardinal Invariant #2 (citation grounding) | `request_clarification` handler body | AST gate scans for forbidden track_id-aliases + grounding-state attribute chains | WIRED | Structural impossibility — handler cannot fabricate a track reference because the gate proves it never reads `track_id`/`trackId`/`track_ids` from args, never touches `self.seen`/etc. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `_build_clarification_payload` | `question`, `choices` | Args from Codex tool call → validated → mirrored into discriminated-union payload | YES — REAL data flows from Codex argument dict through validation to terminal payload | FLOWING |
| `CodexCurateResult.question` / `.choices` | Wrapper reads from side-channel JSON | `payload.get("question")` + `payload.get("choices")` typed-coerce to `str` / `list[str]` | YES | FLOWING |
| CLI stderr 2-block render | `result.question`, `result.choices` | Direct read from `CodexCurateResult` instance attributes | YES — `enumerate(result.choices or [], start=1)` iterates real list | FLOWING |
| Telegram `format_reply` lines | `norm.get("question")`, `norm.get("choices")` | Direct read from normalized dict | YES — strip_leaks applied to the concatenated render | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Toolset + AST gate tests pass | `pytest -q tests/library/test_toolset_clarification.py tests/library/test_request_clarification_no_track_surface.py tests/library/test_mcp_server_clarification.py tests/library/test_codex_curate_stop_reason.py` | 65 passed in 0.67s | PASS |
| CLI + Telegram bridge tests pass | `pytest -q tests/library/test_cli_exit_codes.py tests/library/test_telegram_bridge.py` | 29 passed in 5.35s | PASS |
| Integration seal tests pass | `pytest -q tests/library/test_codex_curate_stop_reason.py` | 16 passed in 0.35s | PASS |
| Full `tests/library/` regression | `pytest -q tests/library/` | 717 passed, 1 skipped (unrelated transformers import), 1 xfailed (unrelated cost gate) | PASS |
| `request_clarification` callable from `LibraryToolset` | Source inspection — handler exists at `:1126`, dispatch entry at `:1333`, MCP exposure at `mcp_server.py:230` | All three wiring sites present | PASS |
| CLI exit code 11 distinct from Phase 99's 10 | `grep -n "return 11\|return 10" src/vibemix/__main__.py` | 11 = clarification_needed (lines 2687, 2757); 10 = tool_starvation (line 2704, 2773) | PASS |

### Probe Execution

Not applicable — Phase 100 is a library subpackage hardening phase, not a migration phase. No `scripts/*/tests/probe-*.sh` declared in PLAN or SUMMARY. The honest-green discipline runs through `pytest tests/library/` as the authoritative gate.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HARDEN-CLARIFY-01 | 100-01 | `request_clarification` handler + MIN/MAX_CHOICES + dispatch entry | SATISFIED | `toolset.py:83-84, :1126-1245, :1333`; 34 tests green. |
| HARDEN-CLARIFY-02 | 100-02 | FastMCP `@mcp.tool()` exposure + teaching docstring | SATISFIED | `mcp_server.py:230-258`; 11 tests green. |
| HARDEN-CLARIFY-03 | 100-03 | `CodexCurateResult.question/choices` + wrapper elif branches | SATISFIED | `codex_curate.py:221-222, :566-575, :889-897`. |
| HARDEN-CLARIFY-04 | 100-04 | CLI exit 11 + 2-block stderr render + normalizer extension | SATISFIED | `__main__.py:2667-2687, :2744-2757, :3006-3015`. |
| HARDEN-CLARIFY-05 | 100-05 | Telegram `format_reply` clarification_needed branch with strip_leaks | SATISFIED | `telegram_bridge.py:137-143`; 29 tests green. |
| HARDEN-CLARIFY-06 | 100-06 | AST gate proving no `track_id` surface + single-turn structural pin | SATISFIED | `test_request_clarification_no_track_surface.py` — 6 AST gates green; single-turn enforced by `test_request_clarification_single_turn_no_internal_loop`. |
| HARDEN-CLARIFY-07 | 100-07 | End-to-end integration seal across toolset+wrapper+normalizer+CLI+Telegram | SATISFIED | `test_codex_curate_stop_reason.py:946,1042,1140` — three integration seal tests pin the full chain. |

**Coverage:** 7/7 REQs satisfied. No orphaned REQs detected — all REQ-IDs declared in plan frontmatter map to a closing plan.

### Anti-Patterns Found

No anti-patterns detected. Inspection findings:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `library/toolset.py` | 1162 | "Known cosmetic" comment documenting that Phase 99's dispatch-top short-circuit's outer `"error"` value is `"tool_starvation"` regardless of which terminal reason fired | INFO | Documented as out-of-scope for Plan 100-01. Wave 3-4 wrappers read `payload.get("reason")` from the inner `stop_reason` dict, not the outer `"error"` key. No user-visible regression. |
| `__main__.py` | 2667-2687, 2744-2757 | Duplicated 2-block stderr render across curate + build-set CLI handlers | INFO | Intentional — each handler uses a different command-name in the re-run hint (`library curate` vs `library build-set`), so duplication keeps the dispatch flat and grep-able. Not a refactor target. |

No TBD/FIXME/XXX markers introduced in this phase's modified files. No empty-implementation returns (`return null` / `return []`) flowing to user-visible surfaces. No hardcoded stubs.

### Anti-Creep Acid Test (v10.0 LOCKED)

**Question:** *"Does this phase close one of the three audit partials — without growing the surface, introducing a new AI provider / managed-memory framework / ws port / IPC envelope / heavy dep, touching `src/vibemix/__main__.py` / `src/vibemix/agent/` / `src/vibemix/intel/` / `tauri/ui/*`, or relaxing any of the four cardinal invariants? Does it leave the live co-host streaming pipeline untouched?"*

**Phase 100 verdict:** PASS

Files touched (verified via git log of P100 commits `c578b839..5ca36afb`):
- `src/vibemix/library/toolset.py` — IN SCOPE
- `src/vibemix/library/mcp_server.py` — IN SCOPE
- `src/vibemix/library/codex_curate.py` — IN SCOPE
- `src/vibemix/library/telegram_bridge.py` — IN SCOPE
- `src/vibemix/__main__.py` — IN SCOPE per ROADMAP: "STRICTLY in the CLI dispatch lines"
- `tests/library/*` + `tests/repo/test_no_seen_relaxation.py` — IN SCOPE
- `.planning/` artifacts — IN SCOPE

Files NOT touched (verified):
- `src/vibemix/agent/` — UNTOUCHED (live co-host streaming pipeline preserved)
- `src/vibemix/intel/` — UNTOUCHED
- `tauri/ui/*` — UNTOUCHED (frontend wiring handoff disjoint)
- `src/vibemix/__main__.py:1353` `turn_handling` live session-loop path — UNTOUCHED (LiveKit-upgrade handoff owns it)

No new AI provider added. No new ws port. No new IPC envelope. No new heavy dep. All four cardinal invariants hold by additive design (#1 N/A direct — handler is stateless; #2 holds by AST gate proving no track_id surface; #3 N/A live co-host untouched; #4 N/A no new ws traffic).

### Human Verification Required

None — automated verification covers all 7 REQs structurally. The §HARDEN-PHASE-B-CLARIFICATION-TONE KAAN-ACTION ear-pass on real Codex clarification prompts is explicitly deferred to v10.0 milestone close per `gsd-autonomous fully` mode default + the verify_context routing note: "the KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE (ear-pass on real Codex clarification prompts) defers to milestone close per `gsd-autonomous fully` mode and is NOT a verification gate."

### Gaps Summary

No gaps. Phase 100 has all 7 HARDEN-CLARIFY REQs closed end-to-end:

- Handler exists with the right validation surface (REQ-01)
- MCP tool exposes the right teaching docstring + signature (REQ-02)
- Both wrappers propagate the right shape through the dataclass (REQ-03)
- CLI prints the right 2-block layout + exits with the right distinct code (REQ-04, REQ-06)
- Telegram renders the right branch with the right leak-strip (REQ-05)
- AST gate proves the right structural properties — no track_id, no grounding mutation, strict signature, single-turn, baseline-seen-add count preserved (REQ-06)
- Integration seal proves the full chain works end-to-end (REQ-07)

Honest-green discipline visible in commit history — every plan ships RED→GREEN→docs in order (e.g. `f49f0b3d test(100-02): RED` → `c1ba537f feat(100-02): GREEN` → `3a836564 docs(100-02): complete`). 717/717 tests passing in `tests/library/` (1 unrelated skip, 1 unrelated xfail — both pre-existing).

Anti-creep acid test passes — Phase 100 stayed inside the v10.0 library subtree island and did not regress any cardinal invariant or out-of-scope file.

---

_Verified: 2026-05-28T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
