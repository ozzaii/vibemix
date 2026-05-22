---
phase: 65-memory-retrieval-seam
reviewed: 2026-05-22T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 12
files_reviewed_list:
  - src/vibemix/__main__.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/memory/retrieval.py
  - src/vibemix/prompts/matrix.py
  - src/vibemix/state/coach.py
  - src/vibemix/state/evidence_registry.py
  - tests/agent/test_dj_cohost_linter.py
  - tests/coach/test_citation_linter.py
  - tests/memory/test_retrieval.py
  - tests/prompts/test_matrix.py
  - tests/state/test_coach.py
  - tests/state/test_evidence_registry.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 65: Code Review Report — Iteration 2 (Re-Review)

**Reviewed:** 2026-05-22 (iteration 2, post-fix-pass)
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Iteration 2 re-review of Phase 65 (anti-slop release gate of v6.0 "The Memory
Turn"). The 7 fix commits address the iteration-1 findings as follows:

- **CR-03 (corpus footer before recall fence)** — CORRECTLY FIXED. The
  ordering in `state/coach.py:187-226` now appends `evidence_corpus[…]` before
  the `FROM A PAST SESSION` fence. Pinned by
  `tests/state/test_coach.py::test_evidence_line_recall_block_after_corpus_footer`.
- **CR-04 (per-dispatch generation token)** — CORRECTLY FIXED. The
  `_inflight_gen` field bumped under `_lock` at the start of both `on_event`
  and `clear` closes the executor-write-after-clear race. Pinned by
  `tests/memory/test_retrieval.py::test_clear_during_inflight_on_event_discards_stale_latch`.
- **WR-01 (recall pull failure stale latch)** — CORRECTLY FIXED. The
  `dj_cohost.py:670-678` defense-in-depth clear after a `get_latest()`
  exception eliminates the cross-turn leak. (But introduces a CR-04 interaction
  — see WR-03 below.)
- **WR-02 (snapshot query fields under MusicState lock)** — CORRECTLY FIXED
  in `retrieval.py:build_recall_query`. Duck-typed `_lock` lookup preserves
  the no-live-path / no-MusicState-import invariant.
- **WR-03 (`_pending_event` clear via try/finally)** — CORRECTLY FIXED.
- **WR-05 (v5.0 cold-memory absolute byte-identity test)** — CORRECTLY PINNED
  by `tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline`.

**BUT** — **CR-01 is NOT fully closed**. The strict-subset invariant the fix
claims is broken on a real cross-turn sequence: prior-turn `[recall:…]` ids
registered in the EvidenceRegistry are never cleared on subsequent turns whose
`recall_moments` is empty, opening exactly the superset leak the fix targets.
The agent path also leaks across the unwired-linter / no-registry edge.

Findings classified by tier below. The headline-poisoning gate
(`test_fabricated_recall_strips_turn`) still passes on iteration 2 because the
test uses a SINGLE-turn fabrication scenario; the cross-turn scenario the
review identifies is not pinned by any test.

## Critical Issues

### CR-01: Per-turn recall registration is NOT cleared on subsequent empty-recall turns — superset leak survives the fix

**File:** `src/vibemix/agent/dj_cohost.py:679-712` (the recall registration block)
**Issue:**

The fix gates the `_registry.clear_source("recall")` call inside
`if recall_moments and self._registry is not None:` (line 679). This is a
strict subset of the broader "every turn rescopes recall" rule the fix's own
docstring claims (lines 680-693). The clear runs ONLY when this turn has
non-empty survivors. Consequence:

```
Turn N (track-aware event):
  - recall_moments = [A, B]
  - clear_source("recall") runs   ← OK
  - write("recall", A, t); write("recall", B, t)
  - prompt shows recall block with A, B
  - linter snapshot: snapshot["recall"] = {A: [t], B: [t]}
  - end-of-turn: self._recall.clear() clears _latest (NOT the registry)

Turn N+1 (any event):
  - recall._latest = [] → get_latest() → []
  - recall_moments = []
  - `if recall_moments and self._registry is not None:` SKIPS (empty list is falsy)
  - clear_source("recall") IS NEVER CALLED
  - Registry still contains snapshot["recall"] = {A: [...], B: [...]} from turn N
  - The PROMPT for turn N+1 does NOT show any recall block (recall_moments=[])
  - Gemini fabricates `[recall:A]` (an id it saw in a previous turn's prompt,
    now invented because it's not in this turn's evidence)
  - Linter existence-only branch: body "A" in snapshot.get("recall", {}) → TRUE
  - Turn N+1 emits with a fabricated recall — exactly the superset leak this
    fix exists to close
```

This isn't theoretical. The CitationLinter's existence-only check
(`coach/citation_linter.py:212`) is pure key-membership on the snapshot —
timestamps are irrelevant for `recall`. So any registered `recall` id from any
prior turn remains "valid forever" until the next turn that happens to have
non-empty survivors.

The end-of-turn `self._recall.clear()` at line 1515 only resets
`MemoryRecall._latest`. It does NOT touch the EvidenceRegistry's `"recall"`
bucket. There is no codepath that clears the registry's recall bucket between
turn N and turn N+1 when turn N+1 has empty `recall_moments`.

**Why iteration-2 tests don't catch this:** `test_fabricated_recall_strips_turn`
exercises one turn against an empty registry. The leak requires a sequence of
two turns, the first registering survivors, the second fabricating against the
leftover registration. No iteration-2 test pins this sequence.

**Fix:**

Move `clear_source("recall")` OUT of the `if recall_moments` branch so EVERY
turn rescopes recall — even when this turn has no survivors:

```python
# Run BEFORE the recall pull/register block — strict per-turn scoping
# regardless of whether this turn has survivors. Closes the cross-turn
# superset leak from prior-turn registrations.
if self._registry is not None:
    try:
        self._registry.clear_source("recall")
    except Exception as _e:
        print(f"[recall registry clear err] {_e}", file=sys.stderr)

if self._recall_enabled and self._recall is not None:
    try:
        recall_moments = self._recall.get_latest()
    except Exception as _e:
        # ... unchanged
    if recall_moments and self._registry is not None:
        t_session = ...
        kept: list = []
        for m in recall_moments:
            try:
                self._registry.write("recall", m.record_id, float(t_session))
                kept.append(m)
            except Exception as _e:
                print(f"[recall register err] {_e}", file=sys.stderr)
        recall_moments = kept
```

Also add a regression test pinning the two-turn sequence:

```python
def test_recall_registry_cleared_between_turns_no_superset_leak(mocker, tmp_path):
    """Turn N registers [A, B]; turn N+1 has empty recall_moments and Gemini
    fabricates [recall:A]. The whole turn N+1 MUST strip — proving the registry
    no longer carries the prior-turn id."""
    # ... drive turn 1 with recall_enabled=True + a fake MemoryRecall
    # returning [A, B], assert ai_text emitted with both recall ids.
    # Then make get_latest() return []; have Gemini emit "[recall:A] something".
    # Assert citation_strip fires with ("recall", "A") in missing.
```

## Warnings

### WR-01: Unwired-linter / no-registry edge can emit recall block without grounding

**File:** `src/vibemix/agent/dj_cohost.py:679-762`
**Issue:**

When `recall_enabled=True` AND `_recall` is non-None BUT `_registry` is None
(legacy/test configuration), the registration block at line 679 is skipped
(`self._registry is not None` is False), so `recall_moments = kept` (line 712)
is NEVER reached. `recall_moments` stays as the raw list pulled from
`get_latest()` at line 666.

At line 761, `if recall_moments and not diet:` then injects the recall block
into the prompt. Gemini may cite `[recall:<id>]`. The legacy path (no
`_linter_wired`) emits everything verbatim — Gemini's unverified recall
citation lands in the user's ear without grounding.

This is a configuration-degeneracy bug rather than a regression of the
iteration-1 fixes, but it sits in the same window the fix attempted to harden.
It also means the new "strict subset" invariant only holds when the registry
is wired; the loose alternative (no registry) silently widens the trust
surface.

**Fix:**

Either:
(a) Gate `_recall_enabled` to require `_registry is not None` (refuse to flip
the recall-enabled flag when no registry is wired); OR
(b) Skip prompt-side recall injection when registration was bypassed:

```python
# At line 762, replace the kwarg threading with:
if recall_moments and not diet and (self._registry is not None or not self._recall_enabled):
    # Only inject recall into the prompt if either we managed to register
    # the ids (linter can validate) OR recall is disabled (defensive — won't
    # actually fire because get_latest returns []).
    _bp_kwargs["recall_moments"] = recall_moments
```

The cleanest answer is (a): refuse to construct the agent in
`recall_enabled=True, evidence_registry=None` mode. Add an `__init__`-time
guard. The current `__main__.py` boot path always wires both together, so the
guard's only effect is to surface the misconfiguration in tests / future
embedders early.

### WR-02: `prev.cancel()` on a `_recall_task` does not call `recall.clear()` — late executor write can latch a stale survivor list

**File:** `src/vibemix/agent/dj_cohost.py:606-634` (`_maybe_dispatch_recall._run`)
**Issue:**

When `_maybe_dispatch_recall` cancels a pending task via `prev.cancel()` at
line 633, the `_run` coroutine's `await asyncio.wait_for(...)` raises
`asyncio.CancelledError`. `CancelledError` is a `BaseException` (NOT
`Exception`) in Python 3.8+ so the broad `except Exception` at line 622 does
NOT catch it. The `recall.clear()` in the timeout/exception handlers
therefore does NOT run on cancellation.

The executor thread inside `run_in_executor` continues to completion
(cancellation in asyncio does not interrupt blocking threads). When event B
is also track-aware and dispatches before event A's executor finishes, B
bumps `_inflight_gen` first → A's late write checks token mismatch → drops.
This is the happy path closed by CR-04.

The unhappy path: event A is cancelled BUT event B is NOT track-aware (e.g.,
a MANUAL or HEARTBEAT fires next), so B's `_maybe_dispatch_recall`
short-circuits at the `ev.type not in RECALL_EVENT_GATE` gate WITHOUT bumping
`_inflight_gen`. Event A's executor then completes, sees
`my_gen == _inflight_gen`, and latches its (no-longer-relevant) survivors.
The next track-aware event's `get_latest()` returns these zombie survivors —
they get registered + injected. The linter validates them (they're in the
registry now), so Gemini can cite them. They're not "fake" per se but they're
tied to a cancelled event, which violates the design's "survivors latched are
survivors for the event that dispatched" contract.

CR-04's regression test (`test_clear_during_inflight_on_event_discards_stale_latch`)
exercises the clear-during-inflight case; this case (cancel-without-followup)
is not pinned.

**Fix:**

Catch `CancelledError` explicitly and call `recall.clear()` before re-raising:

```python
async def _run() -> None:
    try:
        await asyncio.wait_for(
            loop.run_in_executor(...), timeout=RECALL_DEADLINE_S,
        )
    except (TimeoutError, asyncio.TimeoutError):
        recall.clear()
    except asyncio.CancelledError:
        recall.clear()  # cancellation = "this dispatch's result is stale"
        raise           # propagate per asyncio cancellation contract
    except Exception as _e:
        recall.clear()
        print(f"[recall dispatch err] {_e}", file=sys.stderr)
```

The bump-on-clear from CR-04 then guarantees the late executor write is
discarded.

### WR-03: `_recall.clear()` inside the `except` for failed `get_latest()` reads happens on the agent thread — `_inflight_gen` is bumped, which silently drops a healthy concurrent dispatch

**File:** `src/vibemix/agent/dj_cohost.py:675-678` (WR-01 iteration-1 fix)
**Issue:**

The WR-01 defense-in-depth from iteration 1 calls `self._recall.clear()` after
a `get_latest()` exception. CR-04's `clear()` now bumps `_inflight_gen`. This
means: if a `_run` background task happens to be in mid-`query_topk` when
`llm_node` runs and `get_latest()` raises, the agent-thread `clear()` bumps
the generation counter and the background task's pending write becomes
gen-stale → drops survivors that were genuinely retrieved for the CURRENT
event.

Real-world likelihood: low (a `get_latest()` raise + a concurrent in-flight
dispatch for the same turn requires `_latest` access to fail while the
dispatch is still running). But it's a real interaction between two of the
iteration-1 fixes — WR-01's "clear on read failure" and CR-04's "clear bumps
gen" pull in opposite directions.

**Fix:**

Either:
(a) Don't bump `_inflight_gen` in `clear()` when there's no `_latest` to
discard (cheap check); OR
(b) Make the WR-01 read-failure recovery a soft reset that ONLY zeroes
`_latest`, not the generation counter. Add a dedicated `_soft_clear` /
`_reset_latest_only` for this case.

```python
# memory/retrieval.py
def _reset_latest_only(self) -> None:
    """Clear _latest without bumping _inflight_gen. Used by the agent's
    defensive read-failure recovery (WR-01) which must NOT cancel a healthy
    concurrent dispatch (CR-04 interaction)."""
    with self._lock:
        self._latest = []
```

Then `dj_cohost.py:676` calls `self._recall._reset_latest_only()` instead of
`self._recall.clear()`.

## Info

### IN-01: No dormancy test for `vibemix.memory.retrieval`

**File:** `tests/memory/test_no_live_path_import.py`
**Issue:**

`test_importing_memory_loads_no_coach_loop` covers `vibemix.memory.store`;
`test_importing_ingest_loads_no_coach_loop` covers `vibemix.memory.ingest`.
There is NO subprocess-dormancy parallel for `vibemix.memory.retrieval`. The
static AST scan (`test_memory_does_not_import_live_path_statically`) does
cover `retrieval.py` via `rglob("*.py")`, so the gate is partially present —
but a runtime gate matching the store/ingest pattern would close
sys.modules-leak threats that pure-AST cannot (e.g., a future indirect
import via `if TYPE_CHECKING` mistakenly promoted at runtime).

**Fix:** Add a near-clone of `test_importing_ingest_loads_no_coach_loop` for
`vibemix.memory.retrieval`.

### IN-02: Two duplicated literal `max_output_tokens=1024` with drift-prone comments

**File:** `src/vibemix/agent/dj_cohost.py:478` and `:957`
**Issue:**

The "2026-05-20 — lifted from 220 for gemini-3.5-flash …" comment is
duplicated verbatim on two `max_output_tokens=1024` lines (one in
`self._gen_cfg`, one in the per-call `cached_content` branch). A future bump
needs to touch both sites; one will inevitably drift. Not a Phase 65 finding
per se, but the duplicated literal is in the same `gen_cfg` neighborhood the
review touched.

**Fix:** Extract a module-level `LIVE_MAX_OUTPUT_TOKENS: int = 1024` constant
and reference it twice.

---

_Reviewed: 2026-05-22 (iteration 2)_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
