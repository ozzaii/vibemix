---
phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire
plan: 03
subsystem: agent
tags: [latency, gemini-context-cache, ttft, anti-hallucination, pitfall-11, cache-floor]
requires:
  - 19-01  # CancelGate chokepoint (the telemetry callback that will eventually call invalidate_cache)
  - 19-02  # diet dispatch + ACK_ELIGIBLE_EVENTS (sets up the per-call gen_cfg pattern this plan extends)
provides:
  - "GeminiContextCache class — create/current_name/invalidate/refresh_loop API"
  - "src/vibemix/agent/cache.py — single chokepoint for caches.create across src/vibemix/"
  - "GEMINI_CACHE_TTL_S=300.0 / GEMINI_CACHE_REFRESH_S=240.0 / GEMINI_CACHE_TOKEN_FLOOR=1024 module constants"
  - "_CACHE_PAD_BLOCK — deterministic ~5KB whitespace+comment block (cache-key stability)"
  - "DJCoHostAgent.__init__ optional cache=None kwarg (preserves Phase 4 backward compat)"
  - "DJCoHostAgent.llm_node three-branch dispatch — disabled/cold/warm cache states"
  - "DJCoHostAgent.invalidate_cache() — async chokepoint Plan 19-01 CancelGate + Plan 19-04 ack-bank wire through"
  - "events.jsonl llm_invoke payload: cache_state ∈ {warm, cold, disabled} for Phase 16 telemetry"
affects:
  - src/vibemix/agent/cache.py  # new
  - src/vibemix/agent/dj_cohost.py  # cache wiring + invalidate_cache method
  - tests/agent/test_cache.py  # new
  - tests/agent/test_dj_cohost_cached_content.py  # new
tech-stack:
  added: []
  patterns:
    - "atomic-swap on refresh — new cache created BEFORE old deleted; current_name never None mid-session unless explicit invalidate"
    - "graceful-degradation on create() failure — refresh_loop keeps the OLD _current_name + skips delete (one more cycle on the old cache)"
    - "best-effort delete in invalidate() — swallows exceptions (cache may be expired server-side); _current_name still cleared locally"
    - "per-call gen_cfg construction on warm path — Gemini rejects passing BOTH cached_content + system_instruction, so warm path OMITS system_instruction"
    - "char-length // 4 token-proxy for the floor check (matches Plan 19-02; project has no tiktoken dep)"
    - "deterministic pad block — fixed module-level string ensures identical inputs → identical padded outputs (cache-key stability invariant if Gemini hashes the prefix)"
    - "lazy-typed genai.Client via TYPE_CHECKING (matches runtime/coach.py:30-33 pattern; testable without LiveKit if needed)"
key-files:
  created:
    - src/vibemix/agent/cache.py
    - tests/agent/test_cache.py
    - tests/agent/test_dj_cohost_cached_content.py
  modified:
    - src/vibemix/agent/dj_cohost.py  # +1 import + cache kwarg + 3-branch dispatch + invalidate_cache method
decisions:
  - "Pad block lives in this module (not in vibemix.prompts) — pad is INTERNAL to the cache mechanism (prevents the 1024-token floor 400 error), not part of the prompt's user-visible contract. Keeping it local prevents accidental coupling with prompt-matrix tests that golden-pin the v4 SYSTEM_INSTRUCTION byte-identity."
  - "Cache invalidation is a CHOKEPOINT METHOD ON DJCoHostAgent (DJCoHostAgent.invalidate_cache), NOT a CancelGate subscription on the cache. This matches the planner's deviation #3 — keeps the cache module independent of CancelGate's import surface; Plan 19-04 ack-bank wiring + the CancelGate telemetry callback BOTH reach the cache through this single agent-side method."
  - "Warm-path per-call gen_cfg deliberately OMITS system_instruction (not just sets it to None). Gemini's documented behavior: when cached_content is set, system_instruction in the same config is IGNORED. Setting it to None or omitting it are both fine; we omit to keep the per-call gen_cfg minimal + the diff narrow vs self._gen_cfg."
  - "refresh_loop uses asyncio.wait_for(stop_event.wait(), timeout=refresh_s) — one statement does both 'sleep refresh_s' + 'check stop' in a single await, avoiding the busy-loop trap that polling stop.is_set() inside a sleep would cause."
  - "On create() failure during refresh, we explicitly RESTORE _current_name = old_name in the except branch. The current create() implementation does NOT clear _current_name on raise (the line that captures cache.name only runs after the await succeeds), but the explicit restore is defensive — if a future refactor changes that contract, the graceful-degradation invariant survives."
  - "Token-proxy chosen as len(body) // 4 (cl100k baseline). Pad block sized to ~5KB so body+pad always exceeds floor for any input ≥1 char. The pad-skipped branch (body already ≥1024 token-proxy) is the production case once Plan 18 grammar block + Phase 4 v4 SYSTEM_INSTRUCTION + persona body are concatenated — the pad becomes a defensive net for shorter test fixtures or stripped-down personas."
metrics:
  duration: ~25min
  completed: 2026-05-14
  tasks: 2
  files_created: 3
  files_modified: 1
  tests_added: 23  # 12 cache + 11 dj_cohost_cached_content
  test_delta: "1663 → 1686 passing, 9 pre-existing failures unchanged"
  commits: 4  # test-RED + feat-GREEN per task
---

# Phase 19 Plan 03: Gemini Context Cache Summary

Ships the Gemini context-caching layer that shaves 500-1500ms off TTFT per
turn by reusing a server-side cached prefix containing the static prompt
header (system instruction + persona + Phase 18 citation grammar). Closes
Pitfall 11 (cache-floor under-pad) by padding the system instruction above
the 1024-token Gemini cache floor BEFORE the cache is created — Gemini
rejects under-floor cache creation with a non-obvious 400 error.

## What shipped

### `src/vibemix/agent/cache.py` (NEW — 214 LoC)

The single chokepoint for `caches.create` across `src/vibemix/` (verified
via `grep -rE "caches\.create" src/vibemix/` returning exactly 3 hits in
this one file: 1 docstring mention, 1 inline comment, 1 actual call).

**Module constants (CONTEXT D-08 lock):**
- `GEMINI_CACHE_TTL_S = 300.0` — 5-min minimum, never lower.
- `GEMINI_CACHE_REFRESH_S = 240.0` — 4-min refresh < 5-min TTL → race-buffered.
- `GEMINI_CACHE_TOKEN_FLOOR = 1024` — Pitfall 11.
- `_CACHE_PAD_BLOCK` — deterministic ~5KB string of fixed `# vibemix-pad-...`
  lines. Generated at module import time; identical across refresh cycles
  for cache-key stability if Gemini hashes the prefix as part of the cache key.

**`GeminiContextCache` class — public API:**

| Method | Async | Returns | Purpose |
|---|---|---|---|
| `__init__(client, body, *, model, ttl_s, refresh_s, time_fn)` | no | — | Stores args; does NOT call API |
| `padded_body() -> str` | no | str | Body unchanged if ≥1024 token-proxy; else body + `\n\n` + `_CACHE_PAD_BLOCK` |
| `create() -> str | None` | yes | str | `caches.create(model, config=CreateCachedContentConfig(ttl='300s', system_instruction=padded_body, display_name='vibemix-{monotonic_int}'))`; stores returned name |
| `current_name() -> str | None` | no | str/None | Returns name; None when uncreated/invalidated |
| `invalidate() -> None` | yes | — | Clears `_current_name` + best-effort `caches.delete(name=...)`; swallows exceptions (cache may already be expired) |
| `_invalidate_name(name)` | yes | — | Internal best-effort delete by explicit name (no `_current_name` mutation) — used by `refresh_loop` for atomic-swap semantics |
| `refresh_loop(stop_event)` | yes | — | Long-running coroutine: every `refresh_s` create new + swap atomically (new-then-delete-old); on stop_event clean exit; on create failure, KEEP old name (graceful degradation, never None mid-session) |

### `src/vibemix/agent/dj_cohost.py` (modified — +53 / −2)

1. **Import:** `from vibemix.agent.cache import GeminiContextCache`.
2. **Constructor kwarg:** `cache: GeminiContextCache | None = None` (positioned after `evidence_registry`); stored as `self._cache`.
3. **llm_node three-branch dispatch** (after the prompt+audio+diet block, before `recorder.log_event("llm_invoke", ...)`):
   - `cache=None` (construction default) → `cache_state="disabled"`, `gen_cfg = self._gen_cfg` by reference (byte-identical Phase 4 path).
   - `cache.current_name()=None` (warm-up window OR post-invalidate gap) → `cache_state="cold"`, same `self._gen_cfg` fallback.
   - `cache.current_name()` returns string → `cache_state="warm"`, per-call `gen_cfg = types.GenerateContentConfig(cached_content=name, thinking_config=...minimal..., temperature=1.0, max_output_tokens=220)` — `system_instruction` OMITTED (Gemini rejects passing both).
4. **generate_content_stream call:** `config=gen_cfg` (was `config=self._gen_cfg`).
5. **events.jsonl llm_invoke payload:** `cache_state` field added (between `diet` and `prompt`).
6. **print line:** `... cache={cache_state} ...` added to per-invocation summary.
7. **`async def invalidate_cache(self) -> None`** — public chokepoint. Awaits `self._cache.invalidate()` when `_cache` non-None; clean no-op when None. The single agent-side surface for cache invalidation.

## Cancel-aware invalidate hook (planner deviation #3)

The cache module does NOT subscribe to CancelGate's telemetry callback
directly. Instead, `DJCoHostAgent.invalidate_cache()` is the chokepoint:

```
CancelGate.try_cancel returns True (cancel-and-refire)
  → CancelGate telemetry callback fires (Plan 19-01)
  → upstream caller (Plan 19-04 ack-bank wiring or coach loop refactor)
    invokes await dj_cohost_agent.invalidate_cache()
  → DJCoHostAgent.invalidate_cache() awaits self._cache.invalidate()
  → GeminiContextCache.invalidate() clears _current_name + best-effort
    server-side delete
  → next llm_node call sees current_name()=None → cache_state="cold" →
    falls back to self._gen_cfg (system_instruction inline) → next
    explicit cache.create() rebuilds from scratch
```

This pattern keeps `cache.py` independent of `runtime/cancel.py`'s import
surface — the cache module only depends on `google.genai.types` +
`vibemix.agent.config`. Plan 19-04 ack-bank wiring wires the actual
`invalidate_cache()` call on cancel-and-refire fire.

## Padding logic detail

The pad block construction:

```python
_CACHE_PAD_BLOCK = "\n".join(
    ["# vibemix-pad-block-do-not-edit-cache-key-stability"]
    + ["# " + ("x" * 60) for _ in range(80)]
)
```

→ 1 header line + 80 lines × ~64 chars = ~5169 chars (≥4096 → ≥1024
token-proxy on its own). For ANY body ≥1 char, `body + "\n\n" +
_CACHE_PAD_BLOCK` exceeds the 1024-token floor. The pad block is a fixed
module-level string — every `padded_body()` call on a body of length L
produces the IDENTICAL output, so if Gemini's cache-hit logic hashes the
prefix the cache survives session resume.

The pad branch is the DEFENSIVE path: in production, the v4
SYSTEM_INSTRUCTION + persona body + Plan 18 citation grammar block are
already well above 1024 token-proxy, so `padded_body()` returns the body
unchanged. The pad activates for stripped-down test fixtures, future
mood-only personas, or any path where the prompt header shrinks below
the floor.

## Refresh-loop cadence

`asyncio.wait_for(stop_event.wait(), timeout=refresh_s)` — one statement
does both "sleep up to refresh_s" + "check stop" in a single await. On
TimeoutError (the normal case, every 240s) the tick fires:

1. Capture `old_name = self._current_name`.
2. `await self.create()` — flips `_current_name` to the NEW name.
3. If create succeeded AND old_name was non-None: `await
   self._invalidate_name(old_name)` (best-effort delete of the OLD cache
   AFTER the new one is current — atomic-swap order).
4. If create raised: log to stderr, restore `_current_name = old_name`,
   continue. The old cache is preserved → `current_name()` keeps returning
   the old name → graceful degradation, never None mid-session unless
   the user explicitly invalidates.

On `stop_event.set()`: the wait returns cleanly, `is_set()` is true, loop
exits.

## Tests delta

- **+12 tests** in `tests/agent/test_cache.py`: module constants, padding floor (short body padded, long body unchanged, determinism), create() builds correct config + stores name, invalidate() clears + deletes, invalidate swallows delete exception, invalidate no-op when never created, refresh_loop atomic A→B swap, refresh_loop keeps old on create failure, refresh_loop stops on event.
- **+11 tests** in `tests/agent/test_dj_cohost_cached_content.py`: constructor accepts/defaults cache kwarg, warm cache passes cached_content + omits system_instruction, warm cache preserves thinking/temperature/max_tokens, cold cache falls back to system_instruction, disabled cache uses self._gen_cfg by reference, cache_state log payload (warm/cold/disabled), invalidate_cache chokepoint awaits cache.invalidate, invalidate_cache no-op when disabled.
- **Net suite delta:** 1663 passing → 1686 passing (+23). 9 pre-existing failures unchanged (test_persona_02_byte_identical_to_v4, test_smoke_05_cleanup_closes_all_streams, test_g5_poc_files_untouched, etc. — all pre-existed at HEAD before this plan).

## Verification commands (all pass)

```
pytest tests/agent/test_cache.py tests/agent/test_dj_cohost_cached_content.py \
       tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_silence_short_circuit.py \
       tests/agent/test_dj_cohost_matrix_dispatch.py tests/agent/test_dj_cohost_prompt_diet.py -x
# → 88 passed

grep -c "GEMINI_CACHE_TOKEN_FLOOR = 1024" src/vibemix/agent/cache.py    # → 1
grep -c "GEMINI_CACHE_TTL_S = 300.0" src/vibemix/agent/cache.py        # → 1
grep -c "GEMINI_CACHE_REFRESH_S = 240.0" src/vibemix/agent/cache.py    # → 1
grep -rE "from vibemix.agent.cache import GeminiContextCache" src/vibemix/  # → 1 (dj_cohost.py)
grep -c "invalidate_cache" src/vibemix/agent/dj_cohost.py              # → 1 (method def)
grep -rE "caches\.create" src/vibemix/                                  # → 3 lines, all in cache.py (single chokepoint)
```

## Deviations from Plan

None — plan executed exactly as written.

The only minor implementation detail vs the plan's pseudocode: the plan
sketched `padded_body()` as `static or instance`; chose `instance` (reads
self._body) since the input body is captured by `__init__` and per-instance
is the cleaner Python idiom. Behavior identical to a static `(body) ->
str` — tests verify the contract, not the binding shape.

## Authentication gates

None.

## Known stubs

None — every line wires real behavior. The placeholder for the
CancelGate→invalidate wiring lives intentionally in Plan 19-01's
telemetry-callback design + Plan 19-04's ack-bank scope; this plan exposes
the chokepoint method (`DJCoHostAgent.invalidate_cache`) so those plans
have the agent-side surface ready.

## Self-Check: PASSED

- src/vibemix/agent/cache.py — FOUND
- tests/agent/test_cache.py — FOUND
- tests/agent/test_dj_cohost_cached_content.py — FOUND
- src/vibemix/agent/dj_cohost.py — FOUND (modified)
- All four commits present in `git log --oneline -5`
