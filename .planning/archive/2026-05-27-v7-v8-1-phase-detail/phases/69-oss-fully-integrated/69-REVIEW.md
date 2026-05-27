---
phase: 69-oss-fully-integrated
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/vibemix/agent/proxy_client.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/agent/__init__.py
  - tests/integration/test_proxy_fallback.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
finding_status:
  WR-01: fixed  # 58a17f1 — offloaded /health canary off the reaction path
  WR-02: fixed  # 5171ba8 — float(-inf) debounce sentinel
  IN-01: open
  IN-02: open
  IN-03: open
status: findings
---

# Phase 69: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Plan 69-03 (OSS-02 client-side proxy fallback) is a tight, well-scoped change.
The classifier logic is **correct on its central contract**: I verified
against the live `google.genai` SDK that `ServerError.code` / `ClientError.code`
are real ints, that the 5xx/4xx/429 boundary holds, and that the
`TimeoutException`-before-`ConnectError` ordering correctly tags `ConnectTimeout`
as `timeout` (it subclasses both). All 31 tests pass; the test mocks use real
`httpx.Response` / real SDK error objects, not bare `MagicMock`, so the
false-green risk is low. The anti-slop contract (fixed message, no LLM call on
the fallback path, no silent retry, one-shot guard) holds by construction.

Two real defects keep this from clean:

- **WR-01 (most important):** the 60s `/health` canary runs a **synchronous,
  blocking 5s-timeout HTTP GET directly on the asyncio event loop** inside
  `llm_node`, with no `run_in_executor` offload — unlike the recall path two
  methods up which correctly offloads. When the proxy is down this stalls the
  audio/TTS/reaction pipeline for up to 5s on the recovery-check tick.
- **WR-02:** the canary debounce uses `0.0` as the never-probed sentinel, so on
  a host whose `time.monotonic()` is currently < 60.0 the first canary tick is
  silently swallowed (off-by-one against a real clock origin).

Neither is a security or correctness-of-classification bug; both are
async-safety / robustness. No Critical findings.

## Warnings

### WR-01: `/health` canary blocks the asyncio event loop (no executor offload) — **FIXED (58a17f1)**

**File:** `src/vibemix/agent/dj_cohost.py:1332` (call site) and `:688` (the blocking call)
**Issue:**
`llm_node` is an `async` coroutine running on the LiveKit/asyncio event loop.
At line 1332 it calls `self._check_proxy_health_canary(time.monotonic())`
synchronously. That helper (line 671-689) calls `probe_proxy_health(...)`
(line 688), which in `proxy_client.py:197` does a **synchronous blocking**
`httpx.Client(timeout=timeout_s).get(url)` with `timeout_s=5.0`.

There is no `run_in_executor` / `asyncio.to_thread` wrapping — confirmed by
grep: the only `run_in_executor` in the file is the recall path (line 809),
which is the correct pattern this code should have mirrored. When the proxy is
unreachable (exactly the state in which the canary is armed), the GET will hang
until the 5s timeout, **blocking the entire event loop** — audio frame
delivery, TTS playback, WS snapshot broadcast, and the reaction path all stall
for up to 5 seconds. The docstring at line 676 calls this "cheap", which is
true only on the 200-in-milliseconds happy path; the documented "proxy down /
no /health endpoint yet" failure mode is precisely the slow path, and it fires
every 60s on the next reaction turn for the whole outage.

This contradicts the cardinal "never block the reaction path" intent and the
project's own established pattern (the recall pre-dispatch offloads its network
work for exactly this reason).

**Fix:** Offload the probe, mirroring the recall path. Make the canary async and
await it off-loop, e.g.:

```python
async def _check_proxy_health_canary(self, now_monotonic: float) -> None:
    if self._proxy_base_url is None or not self._proxy_unavailable:
        return
    if now_monotonic - self._last_proxy_health_probe < 60.0:
        return
    self._last_proxy_health_probe = now_monotonic
    loop = asyncio.get_running_loop()
    ok = await loop.run_in_executor(
        None, probe_proxy_health, self._proxy_base_url
    )
    if ok:
        self._maybe_emit_proxy_recovery()
```

and at the call site: `await self._check_proxy_health_canary(time.monotonic())`.
Alternatively keep it sync but fire-and-forget via
`asyncio.create_task(loop.run_in_executor(None, ...))` with the recovery
emission scheduled in the task. The tests drive the helper directly with a
monkeypatched `probe_proxy_health`, so making it async will require the canary
test (`test_agent_canary_60s_debounce_and_recovery`) to `await` it — a small,
warranted test update. Lower the 5s timeout (e.g. 2s) regardless, since a
canary should fail fast.

### WR-02: canary debounce uses `0.0` sentinel — first probe lost when `monotonic()` origin < 60s — **FIXED (5171ba8)**

**File:** `src/vibemix/agent/dj_cohost.py:568` (init), `:685` (the gate)
**Issue:**
`_last_proxy_health_probe` initializes to `0.0` (line 568), and the gate at
line 685 is `if now_monotonic - self._last_proxy_health_probe < 60.0: return`.
`time.monotonic()` has an **unspecified origin** — on a freshly booted machine
or a process that starts shortly after boot it can legitimately return values
below 60.0. In that window the first canary tick computes `now - 0.0 < 60.0`
→ True → returns without ever probing, even though the fallback has been armed
and a probe is due. The recovery canary is then dead until `monotonic()` crosses
60.0. The real recovery still eventually fires via the "next successful LLM call"
path (the `else` branch at line 1455), so this is a degraded-canary, not a total
failure — hence Warning, not Critical. Note the existing test masks this because
it drives `_check_proxy_health_canary` with explicit `now_monotonic=10.0/60.0/121.0`
values rather than real `time.monotonic()`.

Contrast `_last_recall_callback_at` (line 541) which deliberately uses
`float("-inf")` as its never-armed sentinel for the exact same class of bug,
with a 30-line comment explaining why `0.0` is wrong. The proxy canary should
follow that established precedent.

**Fix:**
```python
self._last_proxy_health_probe: float = float("-inf")  # never-probed sentinel
```
This guarantees the first armed tick always passes the debounce regardless of
the monotonic clock origin, matching the `_last_recall_callback_at` precedent.

## Info

### IN-01: `__repr__` and `bad_body` SDK-wrapper branch are excluded from coverage but untested by the matrix

**File:** `src/vibemix/agent/proxy_client.py:116-117`, `:170-172`
**Issue:** `ProxyUnavailable.__repr__` carries `# pragma: no cover` (fine, trivial).
But the `UnknownApiResponseError` bad-body branch (line 170-172) — one of the two
documented `bad_body` triggers — has **no test**. The 31-test matrix exercises
only the `json.JSONDecodeError` path for `bad_body`. The SDK-wrapper branch is
defensively `hasattr`-gated and the class does exist (verified), so the branch is
live but unpinned; an SDK rename would silently drop a real trigger class with no
red test.
**Fix:** Add one parametrized row constructing a `genai_errors.UnknownApiResponseError`
and assert `classify_proxy_error(...).reason == "bad_body"`.

### IN-02: `original` attribute not asserted on timeout / connection_refused / bad_body

**File:** `tests/integration/test_proxy_fallback.py:148-178`
**Issue:** Only the 5xx test (`:134`) asserts `result.original is exc`. The
timeout, connection-refused, and bad-body tests assert `reason` but not that
`original` carries the underlying exception. Since `original` is what
`events.jsonl` records for root-cause (per the docstring at proxy_client.py:106),
a regression that dropped `original` on those paths would not be caught.
**Fix:** Add `assert result.original is exc` to the three other classifier tests.

### IN-03: env-var default base-url hard-codes the prod proxy

**File:** `src/vibemix/agent/dj_cohost.py:573-576`
**Issue:** When `VIBEMIX_LLM_MODE=proxy` and `VIBEMIX_PROXY_BASE_URL` is unset,
the code defaults to `"https://api.altidus.world"`. This is consistent with the
rest of the codebase (sec_check.py references the same host) and is not a secret,
so it's Info not a finding-of-substance — but a magic URL literal duplicated
across modules is a drift risk. Consider sourcing it from
`vibemix.agent.config` alongside the other endpoint constants so the prod host
lives in one place.

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
