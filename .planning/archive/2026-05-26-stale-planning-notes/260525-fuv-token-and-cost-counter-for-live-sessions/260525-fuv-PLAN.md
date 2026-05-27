---
phase: quick-260525-fuv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/vibemix/library/budget.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/audio/recorder.py
  - tests/library/test_session_meter.py
autonomous: true
requirements: [COST-COUNTER]
must_haves:
  truths:
    - "A SessionMeter records per-call token usage keyed by router-path (live_coach, embedding, debrief, tts)."
    - "The billing split is correct: fresh_input=(prompt-cached) billed at input rate, cached billed at cached rate, output billed at output rate."
    - "After a session ends, session.json contains a cost block: total tokens by router-path, total EUR, cache-hit rate, and EUR saved by caching."
    - "A human-readable cost summary prints to stderr at session end."
    - "The existing BudgetTelemetry €50 ceiling projection test still passes."
    - "OpenRouter brain calls (usage_metadata=None) are counted as untracked, never crash the meter."
    - "Cost math is covered by default-selection pytest (no network/integration markers)."
  artifacts:
    - path: "src/vibemix/library/budget.py"
      provides: "ROUTE_PRICING (router-path keyed) + SessionMeter class + get_session_meter() singleton"
      contains: "class SessionMeter"
    - path: "src/vibemix/audio/recorder.py"
      provides: "Cost block written into session.json at finalize + stderr summary print"
      contains: "cost"
    - path: "tests/library/test_session_meter.py"
      provides: "Billing-split unit tests (fresh/cached/output), cache-savings math, untracked-call handling"
      min_lines: 40
  key_links:
    - from: "src/vibemix/agent/dj_cohost.py"
      to: "vibemix.library.budget.get_session_meter"
      via: "record() call inside the existing usage_metadata block in llm_node"
      pattern: "get_session_meter\\(\\)\\.record"
    - from: "src/vibemix/audio/recorder.py"
      to: "vibemix.library.budget.get_session_meter"
      via: "summary() read inside _finalize_session_meta"
      pattern: "get_session_meter\\(\\)\\.summary"
---

<objective>
Add a token + cost counter for live vibemix sessions so that after a full DJ set Kaan can see total tokens, total € spent, the cache-hit rate, and € saved by the Gemini context cache.

Purpose: The brain (gemini-3.5-flash) bills cached input at 10% of fresh input (90% discount). Right now nothing surfaces what a set actually costs or what caching saved. This makes spend and cache value visible at session end.

Output:
- `SessionMeter` (token-level meter, router-path keyed) + `ROUTE_PRICING` in `budget.py`, sitting next to the existing `PRICING`/`BudgetTelemetry`.
- Wiring in `dj_cohost.py` (brain path) and `recorder.py` (session.json cost block + stderr summary).
- Billing-split unit tests in the default pytest selection.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

<interfaces>
<!-- Existing patterns the executor extends. Use these directly — no exploration needed. -->

From src/vibemix/library/budget.py (the pattern to EXTEND, not replace):
```python
# Module-level pricing/constants. ADD ROUTE_PRICING here — keep PRICING + the
# €50 projection (project_monthly_cost / CostProjection) UNTOUCHED.
USD_TO_EUR = float(os.environ.get("VIBEMIX_USD_TO_EUR", "0.92"))
PRICING = {"text_per_1m_tokens_usd": 0.20, "audio_per_1m_tokens_usd": 6.50}

class BudgetTelemetry:        # COUNTS-level (embeds, cache_hits). Leave as-is.
    def increment_audio_embed(self) -> None: ...
    def increment_text_embed(self) -> None: ...
    def as_dict(self) -> dict: ...
    def reset(self) -> None: ...   # test-only

_TELEMETRY: BudgetTelemetry | None = None
def get_telemetry() -> BudgetTelemetry: ...   # singleton accessor pattern to mirror
```

From src/vibemix/agent/dj_cohost.py (the EXISTING cache_hit capture — extend it, do NOT add a parallel capture):
```python
# ~line 1465 — direct-Gemini stream path uses `LLM_MODEL` (imported from
# vibemix.agent.config). The OpenRouter path (self._or_client is not None)
# returns chunks with usage_metadata=None.
usage = getattr(chunk, "usage_metadata", None)          # ~1476
if usage is not None:
    cached_tokens = getattr(usage, "cached_content_token_count", None) or 0
    # also available on the same usage object:
    #   prompt_token_count       (TOTAL input incl. cached)
    #   candidates_token_count   (output)
    #   total_token_count
    if cached_tokens > 0 and cached_tokens != last_cache_hit_emitted:
        self._recorder.log_event("cache_hit", cached_tokens=..., model=LLM_MODEL,
                                 path="live_coach", cache_state=cache_state)
```

From src/vibemix/audio/recorder.py:
```python
def log_event(self, kind: str, **fields) -> None: ...   # {t, kind, **fields} -> events.jsonl
def _finalize_session_meta(self) -> None:               # ~328, rewrites session.json at close()
    # self._session_meta is the dict written via _atomic_write_json(... "session.json").
    # Best-effort: wrapped in try/except, must never raise out.
def close(self) -> None: ...                             # calls _finalize_session_meta()
```

From src/vibemix/llm/_router_config.py (model literals live ONLY here — pricing keys by router-PATH string, never by raw model name):
```python
_ROUTES = {
    "live_coach":     ("gemini-3.5-flash",              ServiceTier.STANDARD),
    "live_coach_tts": ("gemini-3.1-flash-tts-preview",  ServiceTier.STANDARD),
    "debrief":        ("gemini-3-pro-preview",          ServiceTier.FLEX),
    "embedding":      ("gemini-embedding-2",            ServiceTier.FLEX),
}
```
</interfaces>

<pricing_facts>
Gemini USD per 1M tokens (May 2026), keyed by ROUTER PATH (do NOT duplicate model literals — CI grep gate forbids it):
- live_coach:  input 1.50, output 9.00, cached_input 0.15
- live_coach_tts: input 1.00, output 20.00 (no cache)
- debrief:     input 2.00, output 12.00, cached_input 0.20
- debrief_tts: input 1.00, output 20.00 (no cache)
- embedding:   input 0.20, output 0.00 (no cache)

Billing split per call (from usage_metadata):
- fresh_input_tokens = prompt_token_count - cached_content_token_count
- cost_usd = fresh_input_tokens * input_rate/1e6
           + cached_content_token_count * cached_input_rate/1e6
           + candidates_token_count * output_rate/1e6
- cache savings (per call) = cached_content_token_count * (input_rate - cached_input_rate)/1e6
  (what those cached tokens WOULD have cost at fresh rate, minus what they actually cost)
EUR = USD * USD_TO_EUR. Cache-hit rate = total_cached_input / total_input across live_coach calls.
</pricing_facts>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SessionMeter + ROUTE_PRICING (token-level meter, router-path keyed)</name>
  <files>src/vibemix/library/budget.py, tests/library/test_session_meter.py</files>
  <behavior>
    - record("live_coach", prompt=1000, cached=800, output=200) → fresh_input=200.
      cost_usd = 200*1.50/1e6 + 800*0.15/1e6 + 200*9.00/1e6. EUR = usd*USD_TO_EUR.
    - cache_savings for that call = 800*(1.50-0.15)/1e6 USD (in EUR after convert).
    - record with cached=0 (cold cache) → savings 0, fresh_input == prompt.
    - record("embedding", prompt=1000, cached=0, output=0) → output rate 0, only input billed.
    - record_untracked() → increments untracked_calls; summary() exposes it; no cost added.
    - summary() returns: per_path dict {input_tokens, cached_tokens, output_tokens, cost_eur},
      total_cost_eur, total_savings_eur, cache_hit_rate (cached/input over cache-eligible paths,
      0.0 when no input), untracked_calls. cache_hit_rate clamps to [0,1], no ZeroDivision.
    - Unknown router path → recorded under that path key with cost 0 + flagged (do not crash; the
      meter must never raise into the LLM stream consumer).
  </behavior>
  <action>
    In src/vibemix/library/budget.py, ADD a new `ROUTE_PRICING` dict keyed by router-path string
    (live_coach, live_coach_tts, debrief, debrief_tts, embedding) with input/output/cached_input
    USD-per-1M rates from <pricing_facts>. Add a `SessionMeter` class (threading.Lock guarded, mirror
    BudgetTelemetry's style) with: per-path token accumulators, `record(path, prompt, cached, output)`
    doing the fresh/cached/output billing split per <pricing_facts>, `record_untracked()` for the
    OpenRouter path, and `summary()` returning the dict described in <behavior>. Add a
    `get_session_meter()` singleton accessor mirroring `get_telemetry()`, plus a test-only `reset()`.
    Export the new names in `__all__`. DO NOT touch PRICING, project_monthly_cost, CostProjection,
    or BudgetTelemetry — the €50 ceiling test must keep passing. Keys are router-PATH strings only;
    never reference a Gemini model literal here (CI grep gate). Write tests/library/test_session_meter.py
    FIRST covering the <behavior> cases; tests must import from vibemix.library.budget and run under the
    DEFAULT pytest selection (no network/integration/slow markers). Use SessionMeter() instances directly
    in tests (not the singleton) to avoid cross-test state; call reset() if the singleton is touched.
  </action>
  <verify>
    <automated>source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/library/test_session_meter.py tests/library/test_budget.py::test_monthly_projection_under_50_eur -q</automated>
  </verify>
  <done>SessionMeter billing-split tests pass; the €50 projection gate still passes; no model literals added to budget.py.</done>
</task>

<task type="auto">
  <name>Task 2: Wire the meter to the brain path + write session.json cost block + stderr summary</name>
  <files>src/vibemix/agent/dj_cohost.py, src/vibemix/audio/recorder.py</files>
  <action>
    In dj_cohost.py llm_node, INSIDE the EXISTING `if usage is not None:` block (~line 1477) — reuse
    the same usage object, do NOT add a parallel capture path — call
    `get_session_meter().record("live_coach", prompt=usage.prompt_token_count or 0,
    cached=cached_tokens, output=usage.candidates_token_count or 0)` wrapped in the same best-effort
    try/except that already guards the cache_hit log_event (a meter write must NEVER break the stream
    consumer). Record once per stream when the final usage chunk arrives (guard with a
    `usage_recorded` flag alongside the existing `last_cache_hit_emitted`, since usage_metadata can
    repeat across chunks — only the final chunk carries authoritative totals; record on the chunk
    whose total_token_count is highest, or simply overwrite-on-each by tracking last seen and
    recording once after the stream completes — pick the once-per-stream approach to avoid double
    billing). On the OpenRouter branch (`self._or_client is not None`), call
    `get_session_meter().record_untracked()` once per generation (best-effort). Import
    get_session_meter from vibemix.library.budget at top of file.

    In recorder.py `_finalize_session_meta`, INSIDE the existing try block, read
    `get_session_meter().summary()` and store it under `self._session_meta["cost"]` BEFORE the
    `_atomic_write_json`. Best-effort: wrap the summary read in its own try/except so a meter failure
    never aborts the session.json finalize. After writing, print a concise human-readable summary to
    stderr (use the recorder's existing stderr/print convention): total tokens by path, total EUR,
    cache-hit rate as a %, and EUR saved by caching. Import get_session_meter from
    vibemix.library.budget.
  </action>
  <verify>
    <automated>source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/ -q -k "session_meter or budget or recorder" && python3 -c "import ast,sys; ast.parse(open('src/vibemix/agent/dj_cohost.py').read()); ast.parse(open('src/vibemix/audio/recorder.py').read()); print('parse-ok')"</automated>
  </verify>
  <done>llm_node records live_coach usage via the meter (single record per stream); OpenRouter generations count as untracked; session.json gains a "cost" block at finalize; a cost summary prints to stderr at session end; both modules import cleanly and existing recorder/budget tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Gemini API → vibemix | usage_metadata fields are attacker-irrelevant but may be None/absent; meter must tolerate missing fields. |
| meter → session.json | telemetry write crossing into the persisted session record; must never block recorder finalize. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-fuv-01 | Denial of Service | SessionMeter.record in llm_node hot path | mitigate | Wrap record() in best-effort try/except (mirrors existing cache_hit guard); meter never raises into the stream consumer. |
| T-fuv-02 | Tampering | usage_metadata None / partial on OpenRouter path | mitigate | `getattr(..., 0) or 0` defaults; OpenRouter path uses record_untracked() — no crash, no fabricated tokens. |
| T-fuv-03 | Information disclosure | cost block in session.json | accept | Local-only file, no PII, no API key; same trust level as existing events.jsonl. |
</threat_model>

<verification>
- `pytest tests/library/test_session_meter.py` passes (billing split correct).
- `pytest tests/library/test_budget.py::test_monthly_projection_under_50_eur` still passes (ceiling untouched).
- No new model literals in src/vibemix/ outside _router_config.py: `bash scripts/release/check_no_hardcoded_model.sh` (if present) passes.
- dj_cohost.py + recorder.py parse and import cleanly.
- Default pytest selection (no markers) runs the new cost-math tests.
</verification>

<success_criteria>
- After a real set, session.json has a `cost` block: per-path tokens, total EUR, cache-hit rate, EUR saved by caching.
- A readable cost summary prints to stderr at session end.
- The billing split (fresh vs cached vs output) is unit-tested and correct.
- Existing €50 ceiling gate unbroken; reuses the existing cache_hit capture; pricing keyed by router-path; Gemini-only.
</success_criteria>

<output>
Create `.planning/quick/260525-fuv-token-and-cost-counter-for-live-sessions/260525-fuv-SUMMARY.md` when done.
</output>
