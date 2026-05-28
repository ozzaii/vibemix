---
phase: 100-harden-clarify
plan: 06
subsystem: testing
tags: [factor-7, clarification, ast-gate, invariant-2-citation-grounding, single-turn-contract, structural-safety, regression-pin]

# Dependency graph
requires:
  - phase: 100-harden-clarify
    provides: "Plan 100-01 shipped the request_clarification handler in LibraryToolset (toolset.py:1126)"
  - phase: 100-harden-clarify
    provides: "Plan 100-02 shipped the FastMCP exposure wrapper (mcp_server.py:231)"
  - phase: 99-harden-retry
    provides: "Plan 99-05 BASELINE_SEEN_ADD_COUNT=2 baseline + STOP_REASON_WHITELIST + _consecutive_empties single-writer gate (tests/repo/test_no_seen_relaxation.py)"
provides:
  - "tests/library/test_request_clarification_no_track_surface.py — 6 static AST gates pinning request_clarification handler structural-safety"
  - "tests/repo/test_no_seen_relaxation.py Gate 4: test_request_clarification_handler_two_file_pattern"
  - "Phase 100 carry-over docstring section in tests/repo/test_no_seen_relaxation.py"
  - "Two-layer regression defense for Cardinal Invariant #2 seen-add baseline count (repo + library gates)"
affects: [phase-100-07, HARDEN-FUTURE-01]

# Tech tracking
tech-stack:
  added: []  # Python stdlib only — ast, pathlib
  patterns:
    - "Static AST gating for handler structural-safety (no runtime instantiation needed)"
    - "ast.parse + ast.walk + attribute-chain analysis as the structural-safety primitive"
    - "FORBIDDEN_TRACK_ID_KEYS / FORBIDDEN_GROUNDING_ATTRS module-level constants for explicit failure messages"
    - "Two-layer defense: tests/repo gate + tests/library gate for the same invariant (Plan 99-05 + Plan 100-06)"

key-files:
  created:
    - "tests/library/test_request_clarification_no_track_surface.py — 357 lines, 6 AST tests"
  modified:
    - "tests/repo/test_no_seen_relaxation.py — +95 lines (docstring extension + Gate 4)"

key-decisions:
  - "Used ast.parse + walk + attribute-chain analysis (stdlib only) — no third-party static analyzer; the gate cannot be lied to because AST is the authoritative grammar"
  - "Coarse FORBIDDEN_GROUNDING_ATTRS detection (any chain starting with self.seen / etc.) — a READ of these attrs from the clarification handler is a code-smell even before a write, so the gate flags reads too"
  - "Accepted Task 2 optional sub-test in disposition (a): two-file pattern allow-list (toolset.py + mcp_server.py) mirrors search_vibe — a third definition is a duplication bug caught by the new Gate 4"
  - "Kept BASELINE_SEEN_ADD_COUNT at 2 (unchanged from Plan 99-03); Plan 100-01's request_clarification writes to self.stop_reason (not self.seen), so the count is correctly preserved"
  - "Kept STOP_REASON_WHITELIST at the same 4 files — Plan 100-03's clarification_needed propagation lives inside those same four files, so no whitelist expansion needed"

patterns-established:
  - "Static AST gate template: import ast → REPO_ROOT/TOOLSET path constants → _find_function_in_class helper → _walk_strings / _walk_attribute_chains helpers → 1 test per structural property with precise failure message naming the offending key/chain"
  - "Structural-safety gating complements behavioral gating: behavioral tests prove the happy path works; AST gates prove the bad path cannot exist regardless of mock setup"
  - "When a Cardinal Invariant has both a count-based pin (BASELINE_SEEN_ADD_COUNT) and a surface-based pin (no track_id keys), ship BOTH — they catch orthogonal drift patterns"

requirements-completed: [HARDEN-CLARIFY-06, HARDEN-CLARIFY-07]

# Metrics
duration: 5min
completed: 2026-05-28
---

# Phase 100 Plan 06: AST gates for `request_clarification` structural safety Summary

**Static AST gate proving the request_clarification handler has zero track_id surface, never mutates self.seen / seen_sections / issued_*, never touches the Phase 99 starvation counter, follows the dispatch-convention signature, and stays single-turn — Cardinal Invariant #2 held by construction at every PR.**

## Performance

- **Duration:** ~5 min (Task 1 + Task 2 + verification + summary)
- **Started:** 2026-05-28T16:14:25Z
- **Completed:** 2026-05-28T16:20:00Z (approx)
- **Tasks:** 2 (both `auto` + `tdd="true"`, GREEN-only — structural property already present from Plan 100-01)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- 6 static AST gates over `LibraryToolset.request_clarification` proving structural safety at PR time (not customer time):
  1. No `track_id` / `trackId` / `track-id` / `track_ids` / `trackIds` string literal in the body — Cardinal Invariant #2 by construction.
  2. No attribute chain starting with `self.seen` / `self.seen_sections` / `self.issued_transition_candidates` / `self.issued_cue_proposals` / `self.issued_context_packets` / `self.seen_urls` — grounding spine disjoint from disambiguation path.
  3. No `_consecutive_empties` reference — Phase 99 starvation counter independence (CONTEXT.md Decision 4).
  4. Strict `(self, args)` signature — dispatch-table uniform calling convention (CONTEXT.md Decision 1).
  5. No `while`-loop, no self-recursion — HARDEN-CLARIFY-06 single-turn contract held structurally.
  6. `self.seen.add(` count in `toolset.py` remains at the Plan 99-03 baseline (2) — two-layer regression defense for Cardinal Invariant #2 (Phase 99 gate + Phase 100 gate).
- New `Gate 4` in `tests/repo/test_no_seen_relaxation.py` — `test_request_clarification_handler_two_file_pattern` — pins `def request_clarification(` to the toolset.py + mcp_server.py two-file pattern that mirrors `search_vibe`. Catches future copy-paste duplication into `agent/` / `runtime/` / etc.
- Phase 100 carry-over documentation added to `tests/repo/test_no_seen_relaxation.py` docstring: BASELINE_SEEN_ADD_COUNT stays at 2, STOP_REASON_WHITELIST stays at the same four files, the clarification path is structurally independent of `_consecutive_empties`.

## Task Commits

Each task was committed atomically with named-path staging:

1. **Task 1: NEW AST gate — test_request_clarification_no_track_surface.py** — `b5ee3cbc` (test)
2. **Task 2: Extend tests/repo/test_no_seen_relaxation.py with Phase 100 carry-over notes + Gate 4** — `77b95563` (test)

_Note: Plan 100-06 is structurally GREEN-only (the property already exists in source from Plan 100-01); no RED commit needed, both tasks are GREEN-direct._

## Files Created/Modified

- **CREATED:** `tests/library/test_request_clarification_no_track_surface.py` (357 lines)
  - 6 AST-walking pytest functions
  - 2 module-level frozensets: `FORBIDDEN_TRACK_ID_KEYS`, `FORBIDDEN_GROUNDING_ATTRS`
  - 3 helper functions: `_find_function_in_class`, `_walk_strings`, `_walk_attribute_chains`
- **MODIFIED:** `tests/repo/test_no_seen_relaxation.py` (+95 lines, 0 deletions)
  - Docstring extension: "Phase 100 carry-over" + "Phase 100 + `_consecutive_empties` independence" sections
  - New module constant: `REQUEST_CLARIFICATION_DEF_ALLOWED`
  - New gate: `test_request_clarification_handler_two_file_pattern`
  - Zero changes to existing Gate 1 / 2 / 3 (Phase 99 carry-over untouched)

## AST Gate Technique (for future contributors)

The pattern is reusable for any handler that needs structural-safety pinning:

```python
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "src" / "vibemix" / "<path>.py"

def _find_function_in_class(source, class_name, func_name) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == func_name:
                    return item
    raise AssertionError(...)
```

Once you have the FunctionDef node, two helpers cover most structural checks:

- `_walk_strings(node)` returns every `ast.Constant` string value reachable from the node — catches `args.get("forbidden_key")` and any other string-literal mention.
- `_walk_attribute_chains(node)` returns dotted chains like `self.seen.add` — catches any read or write of `self.<forbidden_attr>`.

For control-flow constraints: `any(isinstance(n, ast.While) for n in ast.walk(func))` for loop detection; iterate `ast.walk(func)` and match `ast.Call(func=ast.Attribute(value=Name('self'), attr='<method_name>'))` for self-recursion.

The gate runs in O(file_size) and adds ~5ms per test on the 4000-line toolset.py — negligible cost for a per-PR pin.

## Six Gate Properties + Failure Messages

| # | Gate | Property pinned | What trips it | Failure message names |
|---|------|----------------|---------------|------------------------|
| 1 | `test_request_clarification_no_track_surface` | No track_id alias in body | A string-literal `"track_id"` / `"trackId"` / `"track-id"` / `"track_ids"` / `"trackIds"` appears anywhere in the function body | The specific forbidden key(s) seen |
| 2 | `test_request_clarification_no_seen_mutation` | No grounding-state attribute access | Any chain matching `self.seen.*` / `self.seen_sections.*` / `self.issued_*.*` / `self.seen_urls.*` | The full chain string(s) |
| 3 | `test_request_clarification_no_consecutive_empties_touch` | No starvation counter coupling | Any chain containing `_consecutive_empties` | The full chain string(s) |
| 4 | `test_request_clarification_signature_strict` | Dispatch-convention signature | Positional args not `[self, args]`, OR any kwonly/varargs/varkw | The actual arg_names list |
| 5 | `test_request_clarification_single_turn_no_internal_loop` | Single-trip semantics | An `ast.While` node OR `self.request_clarification(...)` self-call | The structural class (while-loop / recursion) |
| 6 | `test_baseline_seen_add_count_unchanged_post_phase_100` | Cardinal Invariant #2 count | `self.seen.add(` count != 2 in toolset.py | The current count |

Failure messages all name the specific offending element and point at the recipe for legitimate change (Cardinal Invariant modification justification + constant bump).

## Single-turn Contract Evidence

HARDEN-CLARIFY-06 single-turn semantics held STRUCTURALLY by Gate 5:

- Handler body contains zero `ast.While` nodes — no internal retry loop.
- Handler body contains zero `Call(func=Attribute(value=Name('self'), attr='request_clarification'))` — no self-recursion.
- The `for choice in choices:` validation loop is bounded by `MAX_CHOICES` (module constant) and runs to completion in one dispatch — not extending the run.

Combined with Plan 100-01's terminal-write to `self.stop_reason` (which trips the dispatch-top short-circuit on the next call), the gate proves: one call → one payload → terminal. Multi-turn would require either a while-loop (caught by Gate 5) or a self-call (caught by Gate 5) or a fresh handler — none of which can land without an explicit Plan-level decision (HARDEN-FUTURE-01).

## Optional Task 2 Disposition

Plan 100-06 Task 2's optional sub-test was ADDED, in disposition (a) — two-file allow-list. Rationale:

- The `def request_clarification(` literal appears in exactly two places: `toolset.py:1126` (the bound handler) and `mcp_server.py:231` (the FastMCP exposure wrapper).
- This mirrors `search_vibe`, `find_similar`, `get_track_features`, etc. — the established two-file pattern for any handler that needs MCP exposure.
- A third definition (e.g. someone copying the handler into `agent/dj_cohost.py` to bypass the dispatch table) would be a single-dispatch-table-contract violation.

Gate 4 (`test_request_clarification_handler_two_file_pattern`) catches this with a precise error message naming the offending file(s) and the allow-list recipe.

## Decisions Made

- Used Python stdlib `ast` module only — no third-party static analyzer. Rationale: ast is the authoritative Python grammar, the dependency is zero-risk, and the gate cannot be lied to (a clever mock setup cannot fool ast.parse).
- Coarse forbidden-attr matching: `c == f"self.{attr}"` OR `c.startswith(f"self.{attr}.")` — flags both reads and writes of grounding state. Rationale: even a read from the clarification handler suggests a write is being planned; better to fail at the read.
- Did NOT extend `STOP_REASON_WHITELIST`. Rationale: Plan 100-03's `clarification_needed` propagation lives inside the same four whitelisted files (toolset.py, codex_curate.py, __main__.py, telegram_bridge.py); the existing Gate 3 already covers it reason-agnostically.
- Did NOT bump `BASELINE_SEEN_ADD_COUNT`. Rationale: Plan 100-01's handler writes to `self.stop_reason` (not `self.seen`), so the per-Phase count is preserved.
- Accepted Task 2's optional sub-test in disposition (a) (two-file allow-list). Rationale: the search_vibe pattern is the established two-file convention; a third definition is a structural bug worth pinning.

## Deviations from Plan

None — plan executed exactly as written. Both tasks landed GREEN on first run since the source code from Plan 100-01 already satisfies the contract; this plan ships the enforcement that prevents drift, not the implementation.

## Issues Encountered

None during Plan 100-06 execution.

Note: a baseline full-tree pytest run shows 4 pre-existing failures unrelated to Plan 100-06:
- `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`
- `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback`
- `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync`
- `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases`

Verified these fail on a stashed/clean checkout — they pre-exist Plan 100-06 and are about STATE.md / README content drift, not clarification logic. Not in scope for this plan.

## User Setup Required

None — pure test-only plan, no environment configuration, no manual steps.

## Next Phase Readiness

- Plan 100-07 unblocked — the structural-safety regression net is in place for any follow-up that touches `request_clarification`.
- HARDEN-FUTURE-01 (multi-turn clarification refactor) is now EXPLICITLY blocked by Gate 5's single-turn check; a multi-turn proposal must include either a Plan-level relaxation of Gate 5 or a separate handler (not a while-loop in the existing one).
- Two-layer regression defense locked in: `tests/repo/test_no_seen_relaxation.py` (Phase 99 + Phase 100 Gate 4) + `tests/library/test_request_clarification_no_track_surface.py` (Phase 100 six-gate AST suite). Cardinal Invariant #2 (citation grounding) is now pinned from both the repo-level and library-level perspectives.

## Self-Check: PASSED

- `tests/library/test_request_clarification_no_track_surface.py` exists (357 lines).
- `tests/repo/test_no_seen_relaxation.py` modified with Phase 100 carry-over + Gate 4 (verified via `git diff --stat` showing +95 lines, 0 deletions).
- Commit `b5ee3cbc` exists on branch live-tuning-or-brain (`git log --oneline | grep b5ee3cbc` succeeds).
- Commit `77b95563` exists on branch live-tuning-or-brain (`git log --oneline | grep 77b95563` succeeds).
- All 10 gate tests across both files PASS on current source.
- Plan 100-01 + Plan 100-02 + Plan 100-03 + Plan 100-04 + Plan 100-05 regression suites: 112 passed / 0 failed in 5.72s.

---
*Phase: 100-harden-clarify*
*Completed: 2026-05-28*
