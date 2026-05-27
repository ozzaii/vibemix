---
phase: 69-oss-fully-integrated
plan: 03
wave: 2
subsystem: oss-proxy-fallback
tags: [oss, proxy, fallback, anti-slop, integration, wave-2, gemini]
requirements:
  - OSS-02
provides:
  - "ProxyUnavailable sentinel + classify_proxy_error + probe_proxy_health in src/vibemix/agent/proxy_client.py — the contract surface for the 4 client-side fallback trigger classes (5xx / timeout / connection_refused / bad_body)"
  - "dj_cohost.py orchestration: 5 new instance attributes + 3 new helper methods (_maybe_emit_proxy_unavailable / _maybe_emit_proxy_recovery / _check_proxy_health_canary) + a pre-call 60s /health canary hook + an else-branch recovery on next-successful-LLM-call"
  - "tests/integration/test_proxy_fallback.py (31 GREEN under integration marker, all 31 GREEN under default grid) pinning the 4 trigger classes + 4xx/429 fall-through boundary + 60s recovery flow + direct-mode (BYO) bypass"
  - "KAAN-ACTION-LEGAL.md §V7-PROXY top-level cluster (161 lines, 6 sections, 5 verification snippets, 7-line sign-off) routing server-side hardening to the Bravoh ops repo coordination clock"
affects:
  - src/vibemix/agent/proxy_client.py (additive: 137 insertions; existing build_proxy_genai_client + build_proxy_tts_chain byte-unchanged)
  - src/vibemix/agent/__init__.py (additive: 3 names exported in __all__)
  - src/vibemix/agent/dj_cohost.py (additive: import line + 5 init attrs + 3 helper methods + pre-call canary hook + except classifier + else recovery branch; 141 insertions, 0 deletions)
  - tests/integration/test_proxy_fallback.py (NEW: 439 lines, 31 tests)
  - KAAN-ACTION-LEGAL.md (additive: §V7-PROXY cluster appended at line 4248; pre-existing §SHIP-V4 / §V7-LIVE / §V7-LIVE-NN byte-unchanged)
tech-stack:
  added: []
  patterns:
    - "Sentinel exception + pure classifier (`classify_proxy_error` returns `ProxyUnavailable | None`) — separates type-detection from orchestration, makes the fallback contract testable in isolation (22 of the 31 tests exercise the classifier alone)"
    - "isinstance(TimeoutException) checked BEFORE isinstance(ConnectError) because ConnectTimeout subclasses both — pinned by parametrized timeout test (5 subclasses) so the ordering can't silently rot"
    - "Helper-method-shaped orchestration on the agent (not session_loop) — Rule-1 doc-vs-code reconciliation: the LiveKit cascade reality is that SessionLoop does NOT directly call dj_cohost; dj_cohost owns the generate_content_stream call AND the transcript_sink ref, so the orchestration goes where the failure happens"
    - "One-shot guards + monotonic-time debounce (60s canary cadence) — anti-slop contract: refusing to lie when grounding is missing is on-thesis; silently retrying = slop"
    - "Pre-staged top-level §V7-PROXY cluster (mirrors §SHIP-V4 shape) for cross-repo coordination — engineering ships green in vibemix; the live discharge clock is the Bravoh ops repo + Kaan"
key-files:
  created:
    - tests/integration/test_proxy_fallback.py
    - .planning/phases/69-oss-fully-integrated/69-03-SUMMARY.md
  modified:
    - src/vibemix/agent/proxy_client.py
    - src/vibemix/agent/__init__.py
    - src/vibemix/agent/dj_cohost.py
    - KAAN-ACTION-LEGAL.md
  deleted: []
decisions:
  - "ARCHITECTURAL Rule-1 reconciliation: orchestration lives in dj_cohost.py (the LLM call site + transcript_sink owner), NOT session_loop.py (which the plan nominally targeted). SessionLoop does not invoke dj_cohost — dj_cohost IS the LiveKit cascade agent. The transcript line still surfaces via the existing _push_transcript → SessionLoop._transcript_unsent → snapshot.transcript_delta path unchanged. This honored the underlying contract (transcript-delta one-shot emission, no cohost_status schema change, cardinal-invariant zero-touch) while binding the new state to the module that actually owns the failure boundary."
  - "Classifier checks isinstance(httpx.TimeoutException) BEFORE isinstance(httpx.ConnectError) because httpx.ConnectTimeout subclasses BOTH — would otherwise classify as connection_refused. The 5 timeout-subclass parametrize row pins this ordering against future refactors."
  - "Bad-body detection accepts both json.JSONDecodeError AND google.genai.errors.UnknownApiResponseError (gated by hasattr to survive SDK upgrades that rename/remove the class) — defensive coupling to the genai SDK's exception hierarchy."
  - "Direct-mode (BYO) bypass implemented by gating ALL three helpers on `_proxy_base_url is not None` (None in direct mode at __init__). The boundary is defended by test_agent_direct_mode_never_arms_fallback so a future env-var refactor can't accidentally arm the fallback for BYO users."
  - "Default-grid baseline lift accepted: the project's pytest config does NOT auto-deselect the integration marker (verified by reading pyproject.toml [tool.pytest.ini_options].addopts), so all 31 new tests count in the default grid. Phase 68's prior baseline of 4160 included integration tests from P67/P68 for the same reason. New baseline: 4191 passed / 26 skipped / 4 xpassed / 2 failed (+31 from Wave 1)."
metrics:
  duration: ~28 min
  completed_date: 2026-05-24
  files_touched: 5
  insertions: 884
  deletions: 0
  baseline_before: 4160 passed / 26 skipped / 4 xpassed / 2 failed (Wave 1 close at SHA ffc425a)
  baseline_after_default_grid: 4191 passed / 26 skipped / 4 xpassed / 2 failed (Wave 2 close at SHA 573422d)
  baseline_after_integration_grid: 47 passed / 4176 deselected (was 16 from P67/P68 → +31 from Plan 69-03)
  baseline_delta: "+31 tests (test_proxy_fallback.py: 22 classifier parametrize rows + 3 probe_health + 3 emit-unavailable parametrize rows + 1 recovery + 1 canary debounce + 1 direct-mode bypass); 2 pre-existing P68 feature-matrix drift failures unchanged (see deferred-items.md from Plan 69-01)"
  wall_clock_full_suite_default_grid: 235.00s
  wall_clock_integration_grid: 7.03s
  task_commit_shas:
    - cf370ab (Task 1: src/vibemix/agent/proxy_client.py + __init__.py — ProxyUnavailable + classifier + probe_health)
    - 57e9635 (Task 2: src/vibemix/agent/dj_cohost.py — orchestration helpers + wired except-classifier + else-recovery)
    - a536142 (Task 3: tests/integration/test_proxy_fallback.py — 31-test matrix)
    - 573422d (Task 4: KAAN-ACTION-LEGAL.md §V7-PROXY cluster)
---

# Phase 69 Plan 03: OSS-02 Client-Side Proxy Fallback Summary

**One-liner:** Shipped the v7.0 OSS-02 client-side proxy fallback — when the Bravoh proxy at `api.altidus.world` is unreachable (5xx / timeout / connection_refused / bad-body), the dj_cohost agent classifies the error via the new `classify_proxy_error` sentinel surface, emits a one-shot "Co-host unavailable this session" transcript line through the existing snapshot path, and skips LLM emission for the duration; a 60s `probe_proxy_health` canary (or the next successful LLM call) emits a one-shot "Co-host back online" line and resumes normal operation. The server-side hardening (per-install-UUID rate-limit + token-bucket + Prom /metrics + Sentry + /health endpoint) routes to the new `KAAN-ACTION-LEGAL.md §V7-PROXY` top-level cluster for Bravoh ops repo coordination on Kaan's clock.

## Objective

Wave 2 of Phase 69. Close OSS-02 engineering-side (client-side): when the proxy is offline the brain refuses to lie. NOT a crash, NOT a hallucinated coach line. The brain refusing to lie when grounding is missing is on-thesis (anti-slop). 4xx / 429 paths are preserved unchanged (those have their own existing per-error messaging from prior v3.x SHIP-CUT work — must NOT be conflated with "unavailable"). Server-side hardening source edits live in the separate Bravoh ops repo at `api.altidus.world` — routed via the new §V7-PROXY cluster.

This plan touches `src/vibemix/agent/` (proxy_client.py + dj_cohost.py + __init__.py) ONLY. Zero touches to `src/vibemix/{coach,llm,state,memory,recall,decks,grounding}/`. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by construction.

## What Shipped (4 atomic commits)

### Task 1 — `cf370ab` — `feat(69-03): src/vibemix/agent/proxy_client.py — ProxyUnavailable + classify + probe_health for OSS-02`

`src/vibemix/agent/proxy_client.py` extended (137 insertions, 0 deletions; existing `build_proxy_genai_client` + `build_proxy_tts_chain` byte-unchanged):

1. **`class ProxyUnavailable(Exception)`** — sentinel with `reason: str` + `original: Exception | None` attributes. Documented reasons: `"5xx"` / `"timeout"` / `"connection_refused"` / `"bad_body"`.

2. **`classify_proxy_error(exc: Exception) -> ProxyUnavailable | None`** — pure function that inspects the exception against the 4 trigger classes. Critically checks `isinstance(httpx.TimeoutException)` BEFORE `isinstance(httpx.ConnectError)` because `httpx.ConnectTimeout` subclasses both (would otherwise misclassify as `connection_refused`). 4xx (including 429) and programming errors fall through to None.

3. **`probe_proxy_health(proxy_base_url, timeout_s=5.0) -> bool`** — synchronous best-effort GET against `{proxy_base_url}/health`. Returns True iff HTTP 200, False on anything else. NEVER raises. Docstring documents the no-`/health`-yet failure mode and the §V7-PROXY auto-detection contract.

`src/vibemix/agent/__init__.py` exports the 3 new names (`ProxyUnavailable` + `classify_proxy_error` + `probe_proxy_health`) in `__all__` (alphabetical position preserved).

Smoke verified at write time:

```
$ uv run python -c "from vibemix.agent.proxy_client import ProxyUnavailable, classify_proxy_error, probe_proxy_health; import httpx; ..."
OK — all 8 classification + probe smokes pass
```

### Task 2 — `57e9635` — `feat(69-03): src/vibemix/agent/dj_cohost.py — wire ProxyUnavailable + recovery for OSS-02`

Architectural Rule-1 reconciliation: Plan 69-03 sub-task 2b nominally targeted `session_loop.py`, but the LiveKit cascade reality is that SessionLoop does NOT directly call dj_cohost — dj_cohost IS the LiveKit agent that owns the `generate_content_stream` call AND already writes back via `transcript_sink` (line 575). The orchestration therefore belongs in dj_cohost itself; the emitted transcript line flows out through the existing `_push_transcript` → `SessionLoop._transcript_unsent` → `snapshot.transcript_delta` path unchanged. Documented in this SUMMARY's Deviations section.

Surface added to dj_cohost.py (141 insertions):

- **Imports:** `ProxyUnavailable` + `classify_proxy_error` + `probe_proxy_health` from `vibemix.agent.proxy_client`.
- **5 new `__init__` instance attributes** (default-init to "not armed"):
  - `_proxy_unavailable: bool = False`
  - `_proxy_unavailable_message_emitted: bool = False`
  - `_proxy_recovery_message_emitted: bool = False`
  - `_last_proxy_health_probe: float = 0.0` (monotonic seconds)
  - `_proxy_base_url: str | None = None` (resolved from `VIBEMIX_LLM_MODE` + `VIBEMIX_PROXY_BASE_URL` env vars at construction; None in direct mode so the fallback NEVER arms — BYO users see their own errors per existing v3.x behavior)
- **3 new helper methods on the agent:**
  - `_maybe_emit_proxy_unavailable(reason)`: one-shot "Co-host unavailable this session" transcript line + `events.jsonl` `proxy_unavailable` log line.
  - `_maybe_emit_proxy_recovery()`: one-shot "Co-host back online" line + flag clear + `events.jsonl` `proxy_recovered` log line.
  - `_check_proxy_health_canary(now_monotonic)`: 60s-debounced sync probe; on 200 fires `_maybe_emit_proxy_recovery`.
- **Pre-call canary hook in `llm_node`** (cheap; NEVER raises): `self._check_proxy_health_canary(time.monotonic())` runs before the `try` block around `generate_content_stream`.
- **Existing `try/except Exception` around `generate_content_stream`** now calls `classify_proxy_error(exc)`; on match arms the fallback via `_maybe_emit_proxy_unavailable`. Original exception still flows through the legacy `[llm err]` path so downstream silence-short-circuit + recorder behavior is byte-identical for non-proxy-mode errors.
- **New `else` branch:** on stream success while the fallback is armed, fires `_maybe_emit_proxy_recovery` (the "next real LLM success" recovery trigger, complementing the /health canary).

Cardinal invariants verified at commit:

```
$ git diff --stat -- src/vibemix/coach src/vibemix/state src/vibemix/memory src/vibemix/recall src/vibemix/decks src/vibemix/grounding
(empty — zero touches to reaction-path modules)
```

### Task 3 — `a536142` — `test(69-03): tests/integration/test_proxy_fallback.py — 31-test matrix for OSS-02`

NEW file `tests/integration/test_proxy_fallback.py` (439 lines; integration marker on every test). 31 GREEN under `pytest -m integration`; also 31 GREEN under the default grid (the project's pytest config does NOT auto-deselect the integration marker, verified by reading `[tool.pytest.ini_options].addopts` in `pyproject.toml`).

Test breakdown (31 total):

| Group | Count | What it pins |
|-------|------:|--------------|
| 5xx classifier (parametrize 500/502/503/504) | 4 | 5xx range → `ProxyUnavailable("5xx")` |
| Timeout classifier (parametrize 5 httpx timeout subclasses) | 5 | `ConnectTimeout` ordering (subclasses both `TimeoutException` AND `ConnectError`; MUST classify as "timeout", not "connection_refused") |
| Connection-refused classifier | 1 | `httpx.ConnectError` → `ProxyUnavailable("connection_refused")` |
| Bad-body classifier | 1 | `json.JSONDecodeError` → `ProxyUnavailable("bad_body")` |
| 4xx anti-regression (parametrize 400/401/403/404/422/429) | 6 | **T-69P03-01 boundary** — 4xx including 429 MUST NOT classify; future "just retry on any error" refactor fails red |
| Random-exception fall-through (parametrize 5 types) | 5 | `ValueError` / `RuntimeError` / `KeyError` / `AssertionError` / `TypeError` → None |
| probe_health network error | 1 | NEVER raises; returns False |
| probe_health 200 | 1 | Returns True; asserts canary URL ends with `/health` |
| probe_health non-200 (503) | 1 | Returns False per cascade-degraded /health contract |
| Agent emit-unavailable one-shot (parametrize 3 reasons) | 3 | EXACTLY ONE transcript line per unavailable-streak even with repeated calls + different reasons |
| Agent recovery one-shot | 1 | "Co-host back online" lands once + clears flag; second call is no-op |
| Agent 60s canary debounce | 1 | Probes inside the 60s window are no-ops; probes ≥60s fire; on 200 recovery lands |
| Agent direct-mode (BYO) bypass | 1 | `_proxy_base_url is None`, all 3 helpers no-op, transcript empty, no recorder events |
| **TOTAL** | **31** | |

Smoke verified at commit:

```
$ uv run pytest tests/integration/test_proxy_fallback.py -m integration -v --tb=short
============================== 31 passed in 1.05s ==============================
```

### Task 4 — `573422d` — `docs(69-03): KAAN-ACTION-LEGAL.md §V7-PROXY — server-side hardening cluster for OSS-02`

NEW top-level cluster `## §V7-PROXY — Bravoh proxy production hardening (OSS-02 server-side)` appended at line 4248 of `KAAN-ACTION-LEGAL.md` (after §V7-LIVE's Cross-references end at line 4246). 161 insertions, 0 deletions; pre-existing §SHIP-V4 / §V7-LIVE / §V7-LIVE-NN content byte-unchanged.

6-section shape (mirrors §SHIP-V4 top-level-cluster shape, NOT a §V7-LIVE-NN sub-entry):

1. **Header + frontmatter:** REQ-ID OSS-02 (server-side half); Owner Kaan + Bravoh ops; 6-checkbox Status row.
2. **Why this lives in a separate repo:** the closed-source-by-design carveout (CONTRIBUTING.md Plan 69-01) + the client-side-already-shipped decoupling argument.
3. **Pre-staged server-side spec (5 ordered sub-sections):**
   - a. Per-install-UUID rate limit (slowapi suggestion; 60-token / 1-tok/s refill bucket; 429 + Retry-After header contract — fall-through-not-conflated with "unavailable" per Plan 69-03 Task 1 classifier).
   - b. Prom /metrics with 4 required metric families: `rate_limit_hits_total{install_uuid}` / `tokens_remaining_bucket{install_uuid}` / `proxy_request_duration_seconds{route, status}` / `proxy_upstream_errors_total{kind}`.
   - c. Sentry DSN env var (`SENTRY_DSN`; PII scrubbing on; install-UUID as sole identifier).
   - d. /health endpoint (200 healthy / 503 cascade-degraded; no auth on canary).
   - e. Coordination point (suggested branch + 4 file targets + independent landing cadence).
4. **Verification (fenced bash, 5 numbered snippets):** curl `/health` → 200; curl `/metrics` grep 4 families; 120-request abuse → ≥1 429; SSH echo `SENTRY_DSN` prefix; end-to-end client-side recovery walk (block firewall → "Co-host unavailable" line → unblock → within 60s "Co-host back online" line).
5. **Sign-off block (7 lines):** rate limit / /metrics / Sentry DSN / /health / synthetic 429 / client-side recovery + Sign-off by: Kaan.
6. **Cross-reference (5 in-repo + 2 plan-doc):** the 3 client-side artifacts from Tasks 1-3, §V7-LIVE-11 (parallel pattern), §SHIP-V4 (parallel shape), 69-CONTEXT.md decisions block.

Grep proofs:

```
$ grep -c "^## §V7-PROXY — Bravoh proxy production hardening" KAAN-ACTION-LEGAL.md
1
$ grep -c "rate_limit_hits_total" KAAN-ACTION-LEGAL.md
2
$ grep -c "/health endpoint" KAAN-ACTION-LEGAL.md
3
$ grep -c "^§V7-PROXY rate limit live on:" KAAN-ACTION-LEGAL.md
1
$ awk '/^## §V7-PROXY/{print NR}' KAAN-ACTION-LEGAL.md
4248
```

## Acceptance Criteria — All Met

| Criterion | Result |
| --------- | ------ |
| `src/vibemix/agent/proxy_client.py` ships `ProxyUnavailable` + `classify_proxy_error` + `probe_proxy_health` | ✓ 137 insertions; 8-smoke round-trip verified |
| Existing `build_proxy_genai_client` + `build_proxy_tts_chain` byte-unchanged | ✓ `git diff` shows only additions after line 67 |
| `vibemix.agent.__init__` exports the 3 new names | ✓ |
| `classify_proxy_error(httpx.ConnectError)` → reason == "connection_refused" | ✓ |
| `classify_proxy_error(httpx.ReadTimeout)` → reason == "timeout" | ✓ |
| `classify_proxy_error(ValueError)` → None | ✓ |
| `classify_proxy_error(<4xx>)` → None (anti-regression boundary T-69P03-01) | ✓ parametrized over 6 codes |
| `probe_proxy_health` never raises; returns False on any non-200 | ✓ 3 probe tests pin this |
| dj_cohost.py: try/except around `generate_content_stream` re-classifies + arms fallback | ✓ |
| dj_cohost.py: 5 new `__init__` attrs + 3 new helper methods + pre-call canary | ✓ |
| In direct mode (`VIBEMIX_LLM_MODE != "proxy"`), fallback NEVER arms | ✓ pinned by `test_agent_direct_mode_never_arms_fallback` |
| `cohost_status: Literal["LISTENING", "TALKING", "IDLE"]` schema UNCHANGED | ✓ verified by `grep -n "cohost_status" src/vibemix/ui_bus/messages.py` |
| `tests/integration/test_proxy_fallback.py` exists, all 31 tests GREEN under `pytest -m integration` | ✓ 31 passed in 1.05s |
| All 4 trigger classes covered (5xx / timeout / connection-refused / bad-body) | ✓ |
| Recovery via /health canary tested | ✓ `test_agent_canary_60s_debounce_and_recovery` |
| Anti-regression: 4xx does NOT trigger | ✓ pinned by 6-row parametrize |
| Direct-mode (BYO) test asserts flag never arms | ✓ |
| KAAN-ACTION-LEGAL.md §V7-PROXY cluster grep-count == 1 | ✓ |
| 6 required subsections present in §V7-PROXY | ✓ Header / Why-separate-repo / Pre-staged spec / Verification / Sign-off / Cross-reference |
| 4 required Prom metric families named | ✓ rate_limit_hits_total / tokens_remaining_bucket / proxy_request_duration_seconds / proxy_upstream_errors_total |
| SENTRY_DSN env var named | ✓ |
| /health + /metrics endpoint paths documented | ✓ |
| Verification block has 5 numbered shell snippets | ✓ |
| Sign-off block has 7 lines (6 §V7-PROXY rows + Sign-off by:) | ✓ |
| §V7-PROXY appears AFTER line 4167 (well after §V7-LIVE Sign-off block) | ✓ line 4248 |
| Pre-existing §SHIP-V4 / §V7-LIVE content byte-unchanged | ✓ `git diff` shows only additive insertion |
| Default-grid baseline preserved (modulo the +31 new tests) | ✓ 4191 passed (+31 from 4160); 0 regressions |
| Cardinal invariant: zero touches to coach/state/memory/recall/decks/grounding | ✓ `git diff --stat HEAD~4..HEAD -- src/vibemix/coach...` is empty |
| Zero net-new deps (`pyproject.toml` + `uv.lock` untouched) | ✓ `git diff --stat HEAD~4..HEAD -- pyproject.toml uv.lock` is empty |
| All commits on `live-tuning-or-brain` follow existing commit-message style | ✓ |

## Deviations from Plan

### Auto-fixed Issues

None. All four tasks executed exactly as written in `69-03-PLAN.md`.

### Plan-text vs Code Reconciliation (Rule 1 — documented, not a deviation)

**ARCHITECTURAL: orchestration lives in dj_cohost.py, NOT session_loop.py.** The plan's Task 2 sub-task 2b targeted `src/vibemix/runtime/session_loop.py` lines 1050-1140 for the try/except + orchestration. Reading the actual code revealed that SessionLoop does NOT directly call dj_cohost — dj_cohost runs in the LiveKit cascade and writes back via `transcript_sink` (a `collections.deque` injected at construction; lines 394, 546, 575 of dj_cohost.py). There is no "coach-call site" inside session_loop to wrap.

The correct architectural placement is INSIDE dj_cohost.py:
- The `try/except Exception` around `generate_content_stream` already exists at line 1314 (the LLM call site itself).
- `_push_transcript` (line 575) is the existing chokepoint that writes to the same `transcript_sink` that SessionLoop drains into `snapshot.transcript_delta` (session_loop.py line 1101).
- The plan's contract (one-shot transcript line via the existing transcript_delta mechanism; no cohost_status schema change; cardinal-invariant zero-touch) is honored — the orchestration just moved to the module that owns the failure boundary.

This is exactly the same Rule-1 doc-vs-code reconciliation precedent set by Plan 69-02 SUMMARY ("Plan-text vs Code Reconciliation" section): the code is truth.

**Default-grid baseline lift accepted:** The executor prompt expected the default grid to stay at `4160 passed` because integration tests are "opt-in". Verified by reading `pyproject.toml [tool.pytest.ini_options].addopts` — the project's pytest config does NOT auto-deselect the integration marker (Phase 68's prior baseline of 4160 already included integration tests from P67/P68 for the same reason). The 31 new tests land in the default grid as expected. New baseline: 4191 passed / 26 skipped / 4 xpassed / 2 failed. The 2 pre-existing P68 AUTO-GEN drift failures unchanged.

**Test count exceeded prompt estimate (+31 vs +10):** The executor prompt expected +4 to +10 new tests. The planner's parametrization granularity produced 31 (4×5xx + 5×timeout + 1×connection_refused + 1×bad_body + 6×4xx + 5×random-exc + 3×probe_health + 3×emit-unavailable + 1×recovery + 1×canary + 1×direct-mode). This is a positive deviation — more anti-regression coverage at the cost of a larger commit diff. The 6-row 4xx parametrize alone defends the T-69P03-01 boundary against the future "just retry on any error" refactor across the entire 4xx range.

### Deferred Issues (Out of Scope per SCOPE BOUNDARY)

**`tests/repo/test_readme_feature_matrix_sync.py` — same 2 pre-existing failures (Phase 68 AUTO-GEN drift)** — both failures reproduce on Wave 1 baseline (`ffc425a`) and were already documented in `.planning/phases/69-oss-fully-integrated/deferred-items.md` by Plan 69-01. Wave 2 does not touch README's feature-matrix block; the drift remains parked per the deferred-items disposition.

### Auth Gates

None.

### Architectural Changes (Rule 4)

None. The Rule-1 reconciliation moved orchestration BETWEEN modules within the same `src/vibemix/agent/` subsystem the plan already authorized — no new subsystems, no new dependencies, no new IPC envelopes, no schema changes.

## Baseline Reconciliation

|                  | Wave 1 baseline (SHA ffc425a) | Wave 2 close (SHA 573422d) | Delta | Explained by |
| ---------------- | ----------------------------- | -------------------------- | ----- | ------------ |
| `uv run pytest -q` passed | 4160 | 4191 | +31 | `test_proxy_fallback.py`: 22 classifier parametrize rows + 3 probe_health + 3 emit-unavailable parametrize rows + 1 recovery + 1 canary + 1 direct-mode |
| skipped          | 26   | 26   | 0     | unchanged |
| xpassed          | 4    | 4    | 0     | §V7-LIVE-01 BlackHole (3) + §V7-LIVE-04 sidecar (1) unchanged |
| failed           | 2    | 2    | 0     | pre-existing Phase 68 feature-matrix drift, deferred per scope boundary |
| `pytest -m integration -q` passed | 16 | 47 | +31 | same 31 rows; existing 16 from P67/P68 unchanged |
| `tests/integration/test_proxy_fallback.py` | (file did not exist) | 31/31 GREEN | +31 | new matrix |
| wall-clock (default grid) | ~254s | 235.00s | -19s | within normal variance |
| wall-clock (integration grid) | (n/a) | 7.03s | +7.03s | new dedicated marker run |

**The new default-suite baseline is `4191 passed / 26 skipped / 4 xpassed / 2 failed`** at `573422d` — the 2 failures stay pre-existing Phase 68 drift, NOT Wave 2-caused. Waves 3 and 4 target a +N lift from here as their starting point.

## Known Stubs / Threat Flags

None. The fallback ships real, runnable code; the test is a positive-and-anti-regression-control-verified matrix; the §V7-PROXY cluster is a pre-staged cross-repo coordination handoff with no engineering blocker hidden behind it. The /health endpoint not existing yet on api.altidus.world is the documented failure mode (per the proxy_client.py docstring + the §V7-PROXY cluster); the next-real-LLM-success recovery path covers that case without /health.

## Threat-model verification

| Threat ID | Disposition | How verified |
| --------- | ----------- | ------------ |
| T-69P03-01 (Tampering: silent-fallback 4xx conflation) | mitigate | 6-row parametrized `test_classify_proxy_error_4xx_returns_none` (400/401/403/404/422/429) pins the boundary; a future refactor that "just retries on any error" fails CI red across the entire 4xx range. |
| T-69P03-02 (Denial of Service: retry storm) | mitigate | NO retries on the 4 trigger classes (verified by code-reading the `_maybe_emit_proxy_unavailable` helper — it sets the flag + emits one-shot, never re-tries); 60s canary cadence enforced via `time.monotonic` delta + `test_agent_canary_60s_debounce_and_recovery` parametric coverage of the debounce; anti-slop "refuse to lie" semantics. |
| T-69P03-03 (Information Disclosure: transcript leak) | accept | The transcript line is shown to the user ONLY — intended user-facing message; no PII or proxy internals leaked. The exception's `original` field is logged to events.jsonl (existing log path) but not surfaced via the UI. Verified by reading `_maybe_emit_proxy_unavailable` body — the recorder log gets `reason=<one of 4 strings>` only, not the full traceback. |
| T-69P03-04 (Tampering: schema drift) | mitigate | The plan explicitly does NOT extend the cohost_status Literal. Verified: `src/vibemix/ui_bus/messages.py` `cohost_status: Literal["LISTENING", "TALKING", "IDLE"]` byte-unchanged in this plan. Future PR adding "UNAVAILABLE" triggers Phase 19 oss_hygiene + readme_shape gates + ui_bus schema regen (separate review surface). |
| T-69P03-05 (Spoofing: proxy-imposter via /health) | accept | /health is a best-effort canary; an attacker who can MITM api.altidus.world to return 200 on /health while serving 503 on real endpoints can falsely clear the unavailable flag. Mitigation: the next real LLM call's 5xx will re-arm the flag within one tick — the `_maybe_emit_proxy_unavailable` one-shot guard is per-streak, not per-session, so the second armed streak emits the line again. ASVS L1 mTLS for the proxy is out of scope (v7.0 acid test — no new product capability). |
| T-69P03-SC (Supply Chain: package installs) | accept | Plan 69-03 ships zero new package-install tasks. `httpx` is already a transitive dep via google-genai (no `pyproject.toml` / `uv.lock` touched — verified). `slowapi` is referenced ONLY in §V7-PROXY as a Bravoh-side recommendation (separate repo); no vibemix-side install. No Package Legitimacy Gate required. |

## Self-Check: PASSED

Verified post-write:

- **Files created exist:**
  - `tests/integration/test_proxy_fallback.py` — FOUND (439 lines, 31/31 GREEN under integration marker AND default grid)
  - `.planning/phases/69-oss-fully-integrated/69-03-SUMMARY.md` — this file
- **Files modified exist + integrity:**
  - `src/vibemix/agent/proxy_client.py` — `ProxyUnavailable` + `classify_proxy_error` + `probe_proxy_health` grep-confirmed; existing builders byte-unchanged
  - `src/vibemix/agent/__init__.py` — 3 new names in `__all__` grep-confirmed
  - `src/vibemix/agent/dj_cohost.py` — 5 init attrs + 3 helper methods + canary hook + classifier in except + else-recovery all grep-confirmed
  - `KAAN-ACTION-LEGAL.md` — §V7-PROXY cluster (grep-count 1) at line 4248; 6 required subsections; all 4 Prom metric families; SENTRY_DSN; /health + /metrics; 5-snippet Verification; 7-line Sign-off
- **Commits exist:**
  - `cf370ab` (Task 1) — confirmed via `git log --oneline`
  - `57e9635` (Task 2) — confirmed
  - `a536142` (Task 3) — confirmed
  - `573422d` (Task 4) — confirmed
- **Cardinal invariant:** `git diff --stat HEAD~4..HEAD -- src/vibemix/coach src/vibemix/state src/vibemix/memory src/vibemix/recall src/vibemix/decks src/vibemix/grounding` empty (zero touches to reaction-path modules).
- **Zero net-new deps:** `git diff --stat HEAD~4..HEAD -- pyproject.toml uv.lock` empty.

## What's Next

OSS-02 CLOSED engineering-side (client-side). Phase 69 Wave 2 SHIPPED.

Live discharge (server-side hardening on the Bravoh ops repo: rate limit + token bucket + Prom /metrics + Sentry + /health endpoint, then the end-to-end client-side recovery walk against the live proxy) rides Kaan's clock via `KAAN-ACTION-LEGAL.md §V7-PROXY`.

Wave 2 was independent of Waves 0 / 1 / 3 / 4 — execution order across Phase 69 is parallelizable. Remaining unblocked waves:

- **Wave 3 (Plan 69-04) — OSS-05 packaging scaffolds** — `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` + `packaging-audit.yml` workflow + `test_packaging_scaffolds_present.py`.
- **Wave 4 (Plan 69-05) — OSS-04 §SHIP-V4 wiring** — `cut_release.sh --dry-run v0.1.0-rc1` re-verify + §SHIP-V4 v7.0 sub-section + `test_ship_v4_section_exists.py`.

When all five waves ship, OSS-01..05 close together and Phase 69 ENGINEERING-COMPLETE flips. Live discharge (real signature + real `gh release create` + Bravoh ops repo §V7-PROXY landings) rides Kaan's clock.

## EXECUTION COMPLETE
