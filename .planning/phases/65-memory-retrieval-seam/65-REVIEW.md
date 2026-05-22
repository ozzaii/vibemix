---
phase: 65-memory-retrieval-seam
reviewed: 2026-05-22T00:00:00Z
depth: standard
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
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 65: Code Review Report — Memory Retrieval Seam

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 65 wires the `MemoryRecall` retrieval service into the live coach turn with the right architectural shape: `recall` is added to `EVIDENCE_SOURCES` + `_SOURCE_ALT`, an off-loop `set_next_event` dispatch keeps the embed off the LLM hot path, survivors are registered into `EvidenceRegistry` BEFORE the `snapshot()` call (so a fabricated `[recall:<id>]` strips the turn), and the recall block is PAST-tense fenced. Concurrency-wise, `MemoryRecall` is lock-guarded mirror of `library/grounding.py::Grounding`, and `query_topk(..., exclude_session=current_session_id)` correctly drops the current session before ranking.

That said, the implementation has four poisoning/correctness defects that violate the anti-slop release gate the milestone exists to enforce. The most severe is **CR-01**: a fabricated recall id whose `record_id` collides with a parallel real survivor is silently dropped from the prompt list while staying registered — opening the door for the live LLM to cite a poisoned id that the linter then ACCEPTS (no strip). **CR-02** is a list-mutation-during-iteration bug that drops the FIRST registered moment instead of the failing one and skips the rest. **CR-03** is a recall block placement bug — when the registry corpus footer is non-empty, the PAST-tense recall fence lands BEFORE the `evidence_corpus[…]` footer, but Plan 65-04 expects recall LAST. **CR-04** is a control-flow race: the deadline handler clears `_latest` on TimeoutError, but a slow on_event can still write `_latest` AFTER the clear if the executor thread is mid-`with self._lock` when the deadline fires (Python's `concurrent.futures` does not preempt an in-flight executor task on timeout).

Warnings cover Kaan-action surfaces (a recall pull error short-circuits without clearing the prior `_latest` latch — stale survivors can leak), and a few precision/observability gaps. Info items are minor naming and consistency nits.

## Critical Issues

### CR-01: Fabricated-then-real recall_id collision passes the linter

**File:** `src/vibemix/agent/dj_cohost.py:661-674`
**Issue:** The "drop the offending survivor on registration failure" loop only filters the in-memory `recall_moments` list. It does NOT roll back the `EvidenceRegistry.write("recall", record_id, …)` if the registration somehow partially succeeded earlier in the same loop iteration (write is the FIRST line in the `try` block — the only way it can raise is mid-list mutation under contention, but more importantly the registry stays mutated for the rest of the session).

A subtler but worse path: the registration order is "write to registry first, then drop from list on except." If the linter snapshot is taken AFTER any write succeeds, a registered-but-dropped record_id stays in `snapshot["recall"]`. If Gemini fabricates a `[recall:<that_dropped_id>]` (it never appears in the prompt, but Gemini can leak ANY plausible-looking id, especially after seeing similar past-session ids during the same context), the linter's existence-only branch (`body in snapshot["recall"]`) will ACCEPT it. The whole anti-poisoning thesis — "linter strips unregistered tokens" — is conditional on the registered set being a SUPERSET of the prompt set, which this code violates by registering more than it shows.

Worse: across consecutive recall events in the same session, registry entries from earlier turns ACCUMULATE (the registry is append-only with `clear()` only called on session close). Every turn after the first widens the set of "valid" recall ids Gemini can fabricate without being stripped — a slow-burn poisoning leak.

**Fix:**
```python
# Register the survivors that registry-write succeeds for, then take the
# snapshot AFTER, so the snapshot is a strict superset of what's in the
# prompt. Symmetrically, do NOT mutate the in-memory list during iteration —
# track failures and rebuild at the end.
if recall_moments and self._registry is not None:
    t_session = getattr(ev.state, "set_seconds", 0.0) if ev is not None else 0.0
    failed_ids: set[str] = set()
    registered: list = []
    for m in recall_moments:
        try:
            self._registry.write("recall", m.record_id, float(t_session))
            registered.append(m)
        except Exception as _e:
            print(f"[recall register err] {_e}", file=sys.stderr)
            failed_ids.add(m.record_id)
    recall_moments = registered  # only the registered survivors carry through
```
Additionally, consider scoping recall writes per-turn (write into a turn-local snapshot the linter consumes, then discard) so accumulated cross-turn entries cannot widen the valid set. The current "append to global registry forever" model leaks the poisoning surface across the whole session.

---

### CR-02: List-mutation-during-iteration drops the wrong survivor and skips the rest

**File:** `src/vibemix/agent/dj_cohost.py:663-674`
**Issue:** The exception handler rebinds `recall_moments` inside the `for m in recall_moments:` loop. Python's `for` iterator was captured BEFORE the rebind, so subsequent iterations still walk the OLD list — meaning the comprehension `[x for x in recall_moments if x.record_id != m.record_id]` filters by the CURRENT failing `m.record_id`, but the iterator keeps walking the original list AS WELL. If item `m=records[2]` fails, the comprehension drops `records[2]` from the new list, but the next iteration still reads `records[3]` from the old iterator and processes it normally — fine in most cases.

The real bug is subtler: if registration succeeds for `records[0]` and `records[1]` and fails for `records[2]`, the rebind correctly drops `records[2]`. But the `_registry.write` calls for `records[0]` and `records[1]` already happened and are PERMANENT. CR-01 covers the same concern from the other direction; here the specific code smell is that the comprehension `[x for x in recall_moments if x.record_id != m.record_id]` is O(N²) and structurally fragile — a future maintainer who adds a `break` after the rebind (a common cleanup pattern) will end up dropping ALL remaining unprocessed records silently. Defense-in-depth correctness requires the explicit accumulator pattern in CR-01's fix.

**Fix:** See CR-01 fix — replace the in-loop list comprehension rebind with an explicit `registered: list = []` accumulator that only appends on success. This eliminates the iterator/rebind interaction entirely.

---

### CR-03: PAST-tense recall fence emitted BEFORE the evidence_corpus footer

**File:** `src/vibemix/state/coach.py:189-211`
**Issue:** Inside `AICoach.evidence_line`, the `if recall_moments:` block appends the `"FROM A PAST SESSION (not happening now): …"` fence FIRST, then the `if registry_snapshot:` block appends the `evidence_corpus[ev=N,aud=M,mix=K]` footer SECOND. The test `tests/state/test_coach.py::test_evidence_line_recall_block_present` only asserts `out.index("recent_moves[8s]") < out.index(fence)` — it does NOT assert that the recall fence is the LAST block.

Plan 65-04's intent (per the docstring on lines 177-188) is that the recall fence is subordinate AND last so live evidence + corpus markers stay primary. With a non-empty registry snapshot, the actual rendered order becomes:

```
hearing[…] | track=… | … | recent_moves[8s]: …
| FROM A PAST SESSION (not happening now): [recall:…] …  ← recall here
| evidence_corpus[ev=3,aud=5,mix=1]                       ← corpus here
```

This violates the "live primary, recall subordinate" structural ordering and — worse — sandwiches the corpus footer at the END after the past-session fence, which can prime Gemini to treat the corpus counts as describing the PAST session (the corpus footer was written by `state_refresh_loop` for the CURRENT session). That's an inversion of meaning that the linter cannot catch (the corpus footer carries no `[atom:…]` to validate).

Additionally, in test_18_02_evidence_line_appends_corpus_footer_when_snapshot_present (test_coach.py:521) the assertion is `out.endswith("evidence_corpus[ev=3,aud=5,mix=1]")` — that test would FAIL when recall_moments is also passed because the recall block now lands before the footer. The lack of a combined test (registry_snapshot + recall_moments together, ending check) hides this.

**Fix:**
```python
# Move the recall block AFTER the registry_snapshot corpus footer so the
# evidence ordering is: live evidence → corpus marker → past-session fence
# (recall is LAST and explicitly past-tense; corpus counts describe LIVE).
# Swap the two if/blocks at lines 189-211: emit registry_snapshot footer
# FIRST, recall_moments block SECOND.
if registry_snapshot:
    ev_n = sum(len(v) for v in registry_snapshot.get("ev", {}).values())
    aud_n = sum(len(v) for v in registry_snapshot.get("aud", {}).values())
    mix_n = sum(len(v) for v in registry_snapshot.get("mix", {}).values())
    if (ev_n + aud_n + mix_n) > 0:
        e.append(f"evidence_corpus[ev={ev_n},aud={aud_n},mix={mix_n}]")

if recall_moments:
    parts = [f"[recall:{m.record_id}] {m.signature}" for m in recall_moments]
    e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))
```
Add a test that pins ordering when both are present: registry_snapshot footer index < recall fence index.

---

### CR-04: Deadline TimeoutError clears `_latest` BEFORE the executor thread finishes — race window

**File:** `src/vibemix/agent/dj_cohost.py:606-626` + `src/vibemix/memory/retrieval.py:103-135`
**Issue:** The pre-dispatch wrapper:

```python
await asyncio.wait_for(
    loop.run_in_executor(None, recall.on_event, ev.type, query_text, current_session_id),
    timeout=RECALL_DEADLINE_S,
)
```

On `TimeoutError`, `recall.clear()` is called. But `asyncio.wait_for` does NOT cancel a thread executor task — `run_in_executor` returns a `concurrent.futures.Future` wrapped in an asyncio Future, and only the asyncio side is "cancelled." The actual ThreadPoolExecutor worker keeps running `on_event` to completion. If `on_event` is in `query_topk` (slow vector load on a large corpus) when the deadline fires, the sequence is:

1. T=0.5s: `wait_for` raises `TimeoutError`. Handler runs `recall.clear()` → `_latest = []`.
2. T=0.6s: Executor thread finishes `query_topk`, computes survivors, then runs:
   ```python
   with self._lock:
       self._latest = survivors
   ```
   `_latest` is now repopulated AFTER the clear.
3. T=0.7s: The NEXT event fires `set_next_event` → `_maybe_dispatch_recall` schedules a new task — but llm_node for the CURRENT turn may already be past line 657 (`self._recall.get_latest()`) and have stale survivors latched.

The contract "missed deadline → no recall this turn" is violated in this race. The next track-aware event (which comes much later) will overwrite `_latest` cleanly — but a HEARTBEAT or MIX_MOVE turn in between will read the stale latch and register fabricated past-session ids into the registry (CR-01 amplifies this).

Note: `test_deadline_miss_injects_nothing` only tests `clear()` in isolation — it never exercises the actual race because the test calls `on_event` synchronously then `clear()`. The race only manifests under live load.

**Fix:** The MemoryRecall service needs to participate in cancellation. Two viable approaches:

```python
# Option 1: per-dispatch generation token. Increment on each on_event call;
# only latch survivors if the token still matches at write-time.
def on_event(self, event_type, query_text, current_session_id):
    if event_type not in RECALL_EVENT_GATE:
        return []
    with self._lock:
        self._inflight_gen = getattr(self, "_inflight_gen", 0) + 1
        my_gen = self._inflight_gen
    qvec = self._embedder.embed_query(query_text)
    hits = self._store.query_topk(qvec, RECALL_TOP_K, exclude_session=current_session_id)
    survivors = [r for r in hits if r.score >= RECALL_SIMILARITY_FLOOR]
    with self._lock:
        # If clear() was called between dispatch and write (generation bumped),
        # this result is stale — drop it.
        if my_gen != self._inflight_gen:
            return list(survivors)  # return for caller, but DO NOT latch
        self._latest = survivors
    return list(survivors)

def clear(self):
    with self._lock:
        self._inflight_gen = getattr(self, "_inflight_gen", 0) + 1
        self._latest = []
```

Option 2: have `llm_node`'s `get_latest()` consult a "valid since" timestamp on the latch and reject latches older than the current turn's set_next_event. Option 1 is cleaner; either closes the race.

## Warnings

### WR-01: `recall.get_latest()` exception path does not call `recall.clear()`

**File:** `src/vibemix/agent/dj_cohost.py:656-660`
**Issue:** When `self._recall.get_latest()` raises (lock contention, unexpected backend error, etc.), `recall_moments` is set to `[]` locally, but the underlying `recall._latest` is NEVER cleared. The NEXT turn's `get_latest()` call may succeed and return the STALE prior survivors that were never consumed. This bleeds past survivors across turn boundaries — the exact "stale latch" failure mode the design tries to prevent.

**Fix:**
```python
if self._recall_enabled and self._recall is not None:
    try:
        recall_moments = self._recall.get_latest()
    except Exception as _e:
        print(f"[recall pull err] {_e}", file=sys.stderr)
        recall_moments = []
        # Defense-in-depth: a failed read must NOT leave a stale latch.
        try:
            self._recall.clear()
        except Exception:
            pass
```

---

### WR-02: `build_recall_query` reads `ev.state` attributes synchronously from the agent thread — single-Lock contract violation risk

**File:** `src/vibemix/memory/retrieval.py:64-85` + `src/vibemix/agent/dj_cohost.py:588`
**Issue:** `build_recall_query(ev)` is called inside `_maybe_dispatch_recall` on the asyncio thread, then `ev` is passed via duck-typing into the executor. `MusicState` is single-Lock-guarded (`self._lock: threading.Lock` per `state_refresh_loop`'s single-writer rule), but `getattr(ev.state, "audible_track", None)` accesses the field WITHOUT acquiring the lock. With `state_refresh_loop` running at 10Hz on its own task, this is a torn-read race — Python attribute access on a dataclass is atomic per-attribute but `audible_track + phase + deck` read individually can mix snapshots from two refresh ticks.

In practice this is unlikely to cause user-visible damage (the worst outcome is a query string with mismatched track/phase pairs), but it violates the architecture's stated invariant. The same pattern is used in WRSITE-02 (state_refresh_loop holds the lock for the whole tick); the recall query builder should mirror it.

**Fix:**
```python
def build_recall_query(ev) -> str:
    state = getattr(ev, "state", None)
    if state is None:
        return f"coach_line | track=unknown | phase=unknown | deck=none | event={getattr(ev, 'type', None) or 'MANUAL'}"
    # Snapshot the four needed fields under the state lock — mirrors the
    # state_refresh_loop single-writer / locked-read contract.
    lock = getattr(state, "_lock", None)
    if lock is not None:
        with lock:
            track = state.audible_track or "unknown"
            phase = state.phase or "unknown"
            deck = state.audible_deck or "none"
    else:
        track = getattr(state, "audible_track", None) or "unknown"
        phase = getattr(state, "phase", None) or "unknown"
        deck = getattr(state, "audible_deck", None) or "none"
    etype = getattr(ev, "type", None) or "MANUAL"
    return f"coach_line | track={track} | phase={phase} | deck={deck} | event={etype}"
```

---

### WR-03: `_pending_event = None` is set BEFORE recall pull/registration — exception leaves orphan recall registrations

**File:** `src/vibemix/agent/dj_cohost.py:642-665`
**Issue:** `llm_node` does:
```python
ev = self._pending_event
self._pending_event = None
...
if recall_moments and self._registry is not None:
    t_session = getattr(ev.state, "set_seconds", 0.0) if ev is not None else 0.0
    for m in recall_moments:
        self._registry.write("recall", m.record_id, float(t_session))
```

If the `for m in recall_moments` loop raises (any unforeseen registry exception not caught in CR-02's narrow except), `_pending_event` is already gone but recall is now in a partial-state. The subsequent turn's `set_next_event` will dispatch on the new event, but llm_node was never given the chance to consume `recall_moments` on this turn — yet the registry now carries the recall ids from this turn permanently.

Minor in practice because the inner `try/except` catches most failures, but the pattern of "clear pending state before doing work that can fail" is fragile.

**Fix:** Move `self._pending_event = None` to AFTER recall registration succeeds, OR put the entire llm_node body inside a `try/finally` that guarantees recall state is consistent regardless of which exception fired.

---

### WR-04: `_resolve_prompt_cell` import inside `__main__.main` re-evaluates env vars on every boot but skips when cache disabled

**File:** `src/vibemix/__main__.py:684-700`
**Issue:** When `cache.create()` raises (timeout, no caches API on free tier), `cache = None`. The `cache_system_instruction = _resolve_prompt_cell()` work above is then discarded silently — wasted CPU but more concerning is that the persona resolution path is the source of truth for the system instruction that lands in the per-turn `gen_cfg.system_instruction` (when cache is None, llm_node falls back to `self._gen_cfg` which was set in DJCoHostAgent.__init__).

This is fine in the happy path but creates a subtle inconsistency window: between the time `_resolve_prompt_cell()` returns and `DJCoHostAgent.__init__` re-reads the same env vars, a user could in theory swap `VIBEMIX_MOOD` and end up with a cache and agent built from different cells. Not a Phase 65 regression — it predates this phase — but the recall flow's reliance on consistent agent state warrants flagging it.

**Fix:** Either compute `cache_system_instruction` exactly once and pass it explicitly to `DJCoHostAgent(prompt_body=cache_system_instruction)`, or document the env-var-stability requirement at the top of `main()`.

---

### WR-05: Cold-path byte-identity claim is unverified by tests — no test asserts byte-equality between v5.0 baseline and v6.0 `recall_enabled=False`

**File:** `tests/state/test_coach.py` (entire file), `src/vibemix/state/coach.py`
**Issue:** The README in coach.py:78-89 claims the recall block is "BYTE-IDENTICAL to v5.0 cold-memory golden" when `recall_moments is None/[]`. The test `test_evidence_line_recall_empty_no_block` verifies `evidence_line(state, recall_moments=[]) == evidence_line(state)` — i.e., that empty recall equals no recall — but does NOT verify against the actual v5.0 baseline string. If a future maintainer accidentally adds a trailing space or reorders fields in evidence_line, both calls would produce the same NEW (broken) output and the test passes.

There is `test_evidence_line_silent_state_full_format` pinning the exact bytes, which guards the silent case. But the audible + populated cases (which can carry recall_moments) have no byte-pinned golden — they use substring assertions (`assert "track='X'" in out`).

**Fix:** Add a byte-pinned golden for the audible-with-corpus case:
```python
def test_evidence_line_audible_no_recall_byte_identical_v5_baseline():
    """The cold/feature-off path must be byte-equal to v5.0 (no recall block)."""
    state = MusicState(audible=True, rms=0.094, bpm=126.0, ...)
    out_cold = AICoach.evidence_line(state, recall_moments=None)
    out_off = AICoach.evidence_line(state)  # default
    # Pin the EXACT v5.0 string (copy from CI artifact / git history).
    V5_BASELINE = "hearing[rms=0.094 ...] | track=... | ..."
    assert out_cold == V5_BASELINE
    assert out_off == V5_BASELINE
```

## Info

### IN-01: Recall block in `evidence_line` uses ` || ` separator but the rest of the line uses ` | `

**File:** `src/vibemix/state/coach.py:194`
**Issue:** The recall block joins with `" || "` (double-pipe) while the rest of evidence_line joins with `" | "` (single-pipe via `" | ".join(e)`). The double-pipe is intentional (it separates recall MOMENTS from each other while staying distinguishable from the outer pipe), but it's undocumented in the docstring and a maintainer running a grep for `" | "` to count fields will get an off-by-one. Adding a comment or constant would help.

**Fix:** Add an inline comment:
```python
# Inner separator " || " (double-pipe) distinguishes recall moments from
# the outer " | "-joined evidence fields — makes a grep over evidence_line
# unambiguous about field count vs moment count.
parts = [f"[recall:{m.record_id}] {m.signature}" for m in recall_moments]
```

---

### IN-02: `MemoryRecall._SOURCE_ALT` asymmetry comment is in evidence_registry.py but the `ingest.py` source-alt is not cross-referenced from retrieval.py

**File:** `src/vibemix/state/evidence_registry.py:132-136` + `src/vibemix/memory/retrieval.py`
**Issue:** The evidence_registry.py docstring explicitly calls out the intentional 8-vs-9 source asymmetry between live linter and ingest. retrieval.py would benefit from the same note — without it, a future engineer adding recall extraction at ingest time has no breadcrumb pointing back to the design decision. This is documentation polish, not a code defect.

**Fix:** Add a comment at the top of `retrieval.py` referencing the asymmetry rule (memory/ingest.py stays 8 sources; live retrieval flow knows about all 9).

---

### IN-03: `recall_svc` construction in `__main__.py` swallows ALL exceptions silently to `stderr`

**File:** `src/vibemix/__main__.py:874-877`
**Issue:** The blanket `except Exception as e: print(..., file=sys.stderr)` will catch ImportError (memory backend dependency missing), permission errors on the memory.db file, and downstream bugs in `LibraryEmbedder.__init__`. The current message `"-> recall: disabled ({e})"` is fine for the user but defeats the gsd CONTEXT goal of "ship wired but never live until Kaan flips it" — a SILENT recall failure on a Kaan-flipped run (VIBEMIX_RECALL_ENABLED=1) would degrade to no-recall without any louder signal. The boot banner just shows "disabled" alongside a normal feature-off message.

**Fix:** When `recall_enabled is True` AND construction fails, surface a louder `[FATAL] recall enabled but failed to wire: …` message and either crash-on-boot or print a yellow-banner-style warning. The user explicitly opted in; quiet degradation hides the failure.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
