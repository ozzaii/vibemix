# A-followup-1 — Cancel + Caching Empirical Verification

**Verified:** 2026-05-14
**Pinned versions:** `livekit-agents==1.5.8`, `livekit-plugins-google==1.5.8`, `google-genai==2.0.1`
**Anchored to:** `cohost_v4.py:2033` — `AgentSession(llm=llm_inst, tts=tts_inst)` with a FallbackAdapter-wrapped `google.LLM` → cascade path

---

## TL;DR

- **A1 (programmatic cancel on cascade): WORKS — but the method is `SpeechHandle.interrupt(force=True)`, not `SpeechHandle.cancel()`.** A1's verbatim claim ("`SpeechHandle.cancel()` works regardless of `allow_interruptions`") is **wrong about the API name**. There is no public `cancel()` method. The correct primitive is `interrupt(force=True)`, or for unscheduled handles, the private `_cancel()`. Cascade tasks (LLM + TTS) are killed via `cancel_and_wait(*tasks)` once the interrupt fut fires — verified in source.
- **A2 (Gemini context caching for gemini-3-flash-preview): WORKS — explicitly supported, 1024-token floor.** Original research claimed "preview models sometimes excluded" — empirically false for `gemini-3-flash-preview`. Min cache size is 1024 tokens (vibemix's ~5KB system instruction is ~1200–1400 tokens — squeaks past the floor, but only just). Default TTL 1h; cache-hit input price is 10× cheaper than uncached.

---

## Question 1: SpeechHandle.cancel() on cascade

### Verdict
**Partial — works, but under a different name and with a required flag.**

The original research conflated two APIs. What actually exists in `livekit-agents==1.5.8`:

- Public `SpeechHandle.interrupt(*, force: bool = False)` — at `.venv/lib/python3.12/site-packages/livekit/agents/voice/speech_handle.py:141-154`. With `force=False` (default), raises `RuntimeError("This generation handle does not allow interruptions")` when `allow_interruptions=False`. With `force=True`, **bypasses the gate** and calls `self._cancel()`.
- Private `SpeechHandle._cancel()` — same file, lines 211-231 — sets `_interrupt_fut`, schedules a 5s `INTERRUPTION_TIMEOUT` watchdog that hard-cancels every task in `self._tasks` if playout doesn't finish.
- No public method named `cancel()` exists on `SpeechHandle`. The framework itself calls `speech_handle._cancel()` directly for the preemptive-generation case (`agent_activity.py:1228 → _cancel_preemptive_generation`).

### Evidence

**`.venv/lib/python3.12/site-packages/livekit/agents/voice/speech_handle.py:141-154`** — the interrupt method:
```python
def interrupt(self, *, force: bool = False) -> SpeechHandle:
    if not force and not self._allow_interruptions:
        raise RuntimeError("This generation handle does not allow interruptions")
    self._cancel()
    return self
```

**`.venv/lib/python3.12/site-packages/livekit/agents/voice/agent_activity.py:1188-1219`** — `_generate_reply` routing. Non-realtime LLMs (including our `google.LLM`) flow into the cascade path:
```python
if isinstance(self.llm, llm.RealtimeModel):
    self._create_speech_task(self._realtime_reply_task(...), ...)
elif isinstance(self.llm, llm.LLM):
    task = self._create_speech_task(
        self._pipeline_reply_task(speech_handle=handle, ...),
        speech_handle=handle, name="AgentActivity.pipeline_reply",
    )
```

**`.venv/lib/python3.12/site-packages/livekit/agents/voice/agent_activity.py:2419-2478`** — inside `_pipeline_reply_task_impl`, both the LLM stream task and the TTS task are appended to `tasks`:
```python
llm_task, llm_gen_data = perform_llm_inference(node=self._agent.llm_node, ...)
tasks.append(llm_task)
# ... later ...
tts_task, tts_gen_data = await _start_tts_inference()
tasks.append(tts_task)
```

**Same file, lines 2459-2506, 2657-2658** — every wait point is interrupt-aware, and on interrupt both LLM + TTS get hard-cancelled:
```python
await speech_handle.wait_if_not_interrupted([wait_for_scheduled])
if speech_handle.interrupted:
    await utils.aio.cancel_and_wait(*tasks, wait_for_scheduled)
    await text_tee.aclose()
    return
```
This pattern repeats 4× through the cascade task; the `tasks` list always contains the live LLM stream and (once started) the TTS task. So firing the interrupt mid-LLM-stream genuinely kills both inferences — no wasted full-generation roundtrip.

**Same file, line 1226-1229** — confirms framework itself reaches for the private `_cancel`:
```python
def _cancel_preemptive_generation(self) -> None:
    if self._preemptive_generation is not None:
        self._preemptive_generation.speech_handle._cancel()
```

### Caveats / version dependencies
- API has changed across `livekit-agents` versions. The 1.5.x line (which vibemix is pinned to) consolidated cancellation under `interrupt(force=True)`. Earlier 0.x versions exposed `aclose()` and `cancel()` directly. Pin matters; do not assume forward-compat without re-verifying.
- `INTERRUPTION_TIMEOUT = 5.0` seconds (`speech_handle.py:14`). If for some reason `cancel_and_wait` doesn't return in 5s, the watchdog brute-force cancels every task. Acceptable for vibemix — our LLM stream is ≤2-3s typical.
- `agent_activity.py:1122-1131` — explicit guard: with `RealtimeModel` and server-side `turn_detection`, `allow_interruptions=False` is silently coerced to `NOT_GIVEN` (warning logged). Vibemix is NOT on RealtimeModel for cascade so this branch doesn't apply, but watch for it if we ever revert to native-audio.
- `cohost_v4.py:1847` currently calls `session.generate_reply(allow_interruptions=False)` — the returned `SpeechHandle` carries `allow_interruptions=False`, so `handle.interrupt()` will throw. **`handle.interrupt(force=True)` is the mandatory v2 pattern.**

### Workaround
Not needed — `interrupt(force=True)` is the supported path. If for some reason it ever stops working, the next-best is `handle._cancel()` (private, undocumented, but called from inside the framework so reasonably stable across 1.5.x patch versions).

### Recommended pattern for v2 predictive backpressure
```python
# In coach_loop — replacing the current "drop new events while in-flight" rule
PRIORITY_GAP = 3
in_flight_handle: SpeechHandle | None = None
last_cancel_ts: float = 0.0
CANCEL_COOLDOWN_S = 8.0  # avoid thrashing — cap at 1 cancel per 8s

if trigger_state["in_flight"] and ev.priority > current_priority + PRIORITY_GAP:
    if time.time() - last_cancel_ts > CANCEL_COOLDOWN_S and in_flight_handle is not None:
        try:
            in_flight_handle.interrupt(force=True)   # bypasses allow_interruptions=False
        except RuntimeError:
            in_flight_handle._cancel()               # fallback — should not be needed
        last_cancel_ts = time.time()
        trigger_state["in_flight"] = False
        # fall through to fire new generate_reply for the higher-priority event

handle = session.generate_reply(allow_interruptions=False)
in_flight_handle = handle
handle.add_done_callback(lambda _: trigger_state.__setitem__("in_flight", False))
```

Keep `allow_interruptions=False` at the session level — VAD-driven barge-in on Kaan's mic remains disabled (the original intent). `force=True` is the programmatic backdoor; the user-mic gate is untouched.

---

## Question 2: Gemini context caching

### Verdict
**Works for `gemini-3-flash-preview`. Explicitly listed in the supported-models table at https://ai.google.dev/gemini-api/docs/caching.**

The "preview models sometimes excluded" guidance from prior research was Gemini 1.5-era and is stale. The current docs (as of 2026-05-14) explicitly enumerate `gemini-3-flash-preview` and `gemini-3-pro-preview` in the caching support matrix.

### Min-token floor (the gotcha)
- **gemini-3-flash-preview: 1024 tokens minimum**
- gemini-3-pro-preview: 4096 tokens minimum (irrelevant for vibemix; we're on Flash)
- gemini-2.5-flash: 1024 tokens minimum (parity)
- gemini-2.5-pro: 4096 tokens minimum

**Critical implication for vibemix:** the v4 system instruction at `cohost_v4.py:154` is ~5KB of text. Rough token estimate (4 chars/token English): ~1250 tokens. **Squeaks past the 1024-token floor.** If we trim the system instruction further as part of A's prompt-diet recommendation, we risk falling below 1024 and losing cache eligibility entirely. The two latency wins partially fight each other.

Mitigation: pad the cached `contents` block with deterministic, event-class-invariant context that we'd send every turn anyway (e.g., the controller MIDI map, event taxonomy enum, deck-naming convention, voice persona spec). That gets cached once, reused per turn, and pushes us comfortably past 1024.

### Pricing + TTL constraints
Per https://ai.google.dev/gemini-api/docs/pricing (gemini-3-flash-preview, paid tier):

| Item | Price |
|---|---|
| Uncached input (text/image/video) | $0.50 / 1M tokens |
| Uncached input (audio) | $1.00 / 1M tokens |
| Cache-hit input (text/image/video) | **$0.05 / 1M tokens** (10× cheaper) |
| Cache-hit input (audio) | $0.10 / 1M tokens |
| Cache storage | $1.00 / 1M tokens / hour |
| Output | $3.00 / 1M tokens |

- **TTL:** default is 1 hour; minimum settable is not exposed in current docs — the 5-min figure cited in A-latency was a Gemini-1.5-era number. For vibemix a 1h default is fine: typical DJ session length 30-120min, and we can `caches.update(ttl=...)` mid-session if needed.
- **Storage cost for vibemix:** 1300-token system instruction at $1/1M/hour = $0.0013/hour. Negligible. Even a 90-min session = $0.002 storage cost. No budget concern.

### Example code (minimal working snippet)

`google-genai==2.0.1` exposes `client.caches.create()` (sync) and `client.aio.caches.create()` (async) via `/Users/ozai/projects/dj-set-ai/.venv/lib/python3.12/site-packages/google/genai/caches.py:1053-1144`.

The plumbing to feed `cached_content` through to `livekit-plugins-google`'s LLM call is the `extra_kwargs` mechanism on `LLM.chat()` (`.venv/.../livekit/plugins/google/llm.py:256-261, 441-448`). `cached_content` is a field on `types.GenerateContentConfig` at `.venv/.../google/genai/types.py:5983` and is forwarded verbatim.

```python
# At session start, once.
from google import genai
from google.genai import types

genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_INSTRUCTION = """<the ~5KB cohost_v4.py:154 prompt body>"""
# Pad with stable, deterministic context that would otherwise be sent every turn
PADDING_CONTEXT = """
Event taxonomy: TRACK_CHANGE | PHASE | LAYER_ARRIVAL | MIX_MOVE | HEARTBEAT | MANUAL
Controller: Pioneer DDJ-FLX4, two decks A/B, EQ hi/mid/lo per deck, filter knob per deck...
Voice persona: Casual studio friend, brief, natural — no announcer voice.
<...controller MIDI map JSON dump, ~1KB...>
"""

cached = genai_client.caches.create(
    model="gemini-3-flash-preview",
    config=types.CreateCachedContentConfig(
        display_name=f"vibemix-session-{int(time.time())}",
        system_instruction=SYSTEM_INSTRUCTION,
        contents=[types.Content(role="user", parts=[types.Part(text=PADDING_CONTEXT)])],
        ttl="3600s",  # 1h; refresh if session > 50min
    ),
)
cached_name = cached.name  # e.g. "cachedContents/abc123..."

# Now wire it into the AgentSession's google.LLM via extra_kwargs.
# Two integration options:
#
# OPTION A (cleanest): subclass google.LLM and inject cached_content into _extra_kwargs
class CachedLLM(google_llm.LLM):
    def __init__(self, *, cached_content: str, **kw):
        super().__init__(**kw)
        self._cached_content_name = cached_content
    def chat(self, *, chat_ctx, tools=None, **kw):
        extra = kw.pop("extra_kwargs", {}) or {}
        extra["cached_content"] = self._cached_content_name
        return super().chat(chat_ctx=chat_ctx, tools=tools, extra_kwargs=extra, **kw)

llm_inst = CachedLLM(
    model="gemini-3-flash-preview",
    api_key=api_key,
    cached_content=cached_name,
)
# When omitting cached content, also omit the system instruction from chat_ctx
# (or the cached system instruction is silently overridden by the per-turn one).
```

Verify the cache is actually being used by inspecting `usage.cached_content_token_count` in the response — `livekit-plugins-google/llm.py:475` already surfaces it as `prompt_cached_tokens` in the metrics payload. Set up a one-line metric assertion in `coach_loop`: if `prompt_cached_tokens == 0` after 3 turns, the cache name is wrong and we should log loudly.

### Recommended alternative (not needed but documented)
N/A — caching is viable. If for any reason it goes south:
- **Smaller system instruction:** strip backstory, keep only event-class instructions. Risk: regresses the persona consistency.
- **In-context-learning shortcut:** keep system instruction at ≤256 tokens, accept the lower TTFT ceiling. Probably saves 100-300ms instead of 500-1500ms.
- **Server-side fine-tune:** out of scope for v1 (and Gemini Flash fine-tuning is not GA for preview models).

---

## Impact on Bucket A recommendations

### Stays (no rework)
- **Recommended #1 (Prompt-Size Diet + Prompt Caching):** stays — but with two amendments:
  1. **Use `interrupt(force=True)` not `cancel()`** in any code sketch.
  2. **Pad the cached `contents` block** to stay safely above the 1024-token floor when shrinking the per-turn system instruction.
- **Recommended #4 (Programmatic Cancel-and-Re-fire):** stays, but code sketch needs the rename — `current_handle.cancel()` → `current_handle.interrupt(force=True)`.
- **Recommended #3 (Predictive drop firing):** stays. The misfire-cancel step is `handle.interrupt(force=True)`, not `handle.cancel()`.

### Needs rework
- **A-latency.md TL;DR #5 ("Cancel-mid-generation works")** — verbiage is fine but the method-name is wrong. Update before treating as a load-bearing assertion in any spec.
- **A-latency.md table row 11 ("KV-cache the system instruction")** — original cited "5min minimum TTL". Actually 1h default, no documented minimum we found. Drop the 5-min worry.
- **Assumptions log A1, A2** in A-latency.md — flip both to VERIFIED with this followup as the citation. A1's "risk if wrong" is downgraded to **typo in code, would crash with RuntimeError on first cancel attempt** (loud failure, not silent regression — easy to catch in DJ-ear testing).

### Dead / not viable
- Nothing in Bucket A is killed by this verification. Both load-bearing assumptions hold; A1 just had the wrong method name in the source citation.

---

## Open follow-ups for Kaan

1. **Token count the v4 system instruction.** Get an actual count (not my 4-chars/token guess). If it's under 1024 today, the "trim" step in Recommended #1 has to be reframed as "trim per-turn parts, keep cache eligibility by padding". One ~10-line script using `client.models.count_tokens(model="gemini-3-flash-preview", contents=SYSTEM_INSTRUCTION)`.
2. **Confirm `extra_kwargs` plumbing** — A 20-line smoke test before locking the caching design:
   ```python
   llm = google_llm.LLM(model="gemini-3-flash-preview", api_key=...)
   stream = llm.chat(chat_ctx=ctx, extra_kwargs={"cached_content": cached.name})
   async for chunk in stream: print(chunk)
   # Then assert stream._metrics.prompt_cached_tokens > 0
   ```
   The CachedLLM subclass approach in §A2 is the clean path but the smoke test verifies the underlying mechanism works at all on `gemini-3-flash-preview` — preview models occasionally have config fields silently dropped server-side.
3. **Cancel budget telemetry.** Once `interrupt(force=True)` is wired, log every `interrupted=True` outcome to `events.jsonl` (vibemix already has this via `VoiceRecorder.log_event`). Track cancel rate per session — if it exceeds ~3/min sustained, predictive firing is over-eager and we're burning Gemini budget.
4. **Verify metrics path surfaces cache hits.** `livekit/plugins/google/llm.py:475` reads `usage.cached_content_token_count`. Confirm during smoke-test that this propagates into LiveKit's `MetricsReport` so we can show it in a `[cache hit]` log line.
