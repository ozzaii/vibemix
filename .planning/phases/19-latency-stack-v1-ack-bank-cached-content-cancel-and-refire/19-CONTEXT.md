# Phase 19: Latency Stack v1 — Ack Bank + Cached Content + Cancel-and-Refire - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

Sub-300ms perceived first reaction + sub-2s actual voice-to-voice via four levers stacked together: (1) 40-OPUS ack-bank fallback that fires within 100ms when rolling TTFT degrades, (2) Gemini context caching keeping `prompt_cached_tokens > 0` sustained, (3) prompt diet trimming audio Part 18s→6s on non-PHASE events + skipping screen Part on MIX_MOVE/HEARTBEAT, (4) `SpeechHandle.interrupt(force=True)` cancel-and-refire when a higher-priority event arrives mid-generation.

**Critical scope boundary:** All four mitigations ship together in v2.0 — none deferred to v2.x follow-up. Specifically: cancel-budget cap (`CANCEL_COOLDOWN_S=8.0` hard + 30/session soft + auto-disable on cap breach) ships WITH the cancel-fire impl (Pitfall 1), ack rotation deque + per-event-class buckets ship WITH the ack bank (Pitfall 8), 1024-token cache floor padding asserted on cache creation (Pitfall 11). Predictive drop firing stays OFF by default in v2.0; telemetry guard is pre-wired only for v2.1 turn-on after Phase 16 ear-test baseline (Pitfall 10).

</domain>

<decisions>
## Implementation Decisions

### Cancel-and-Refire Caps (LOCKED — per STATE.md)
- `CANCEL_COOLDOWN_S = 8.0` HARD cap. No exceptions.
- 30 cancels per session SOFT cap with telemetry-driven auto-disable on breach.
- Priority bumping uses fixed numeric ladder: DROP=10 > MIX_MOVE=5 (extend ladder per event taxonomy at plan-time).
- Wrapper around `SpeechHandle.interrupt(force=True)` lives in `src/vibemix/runtime/cancel.py` — single chokepoint, instrumented for telemetry from day one.

### Ack Bank Layout (LOCKED — per STATE + roadmap success criteria)
- 40 OPUS clips total, partitioned into 5 event-class buckets (8 clips per bucket).
- Per-event-class rotation `deque(maxlen=10)` prevents same-sample-within-30s collisions on synthetic 60-fire burst (Pitfall 8 mitigation).
- Trigger gate: fires within 100ms of `EventDetector.detect()` return when `rolling_ttft_avg_ms > 800`.
- Min-ack-to-response gap: 400ms enforced (avoid ack stomping on real Gemini reply).
- Asset path: `src/vibemix/audio/ack_bank/<bucket>/<NN>.opus` — bundled in PyInstaller `--onedir`. AIza scan re-runs across bundled OPUS at P21 release gate (must stay 0).

### Gemini Context Caching (LOCKED — per Pitfall 11)
- `cached_content` passed via `extra_kwargs` on the LiveKit `google.LLM` plugin call site.
- Cache lifecycle manager refreshes every 4 minutes (TTL 5 min minimum — buffer against TTL expiry race).
- System instruction PADDED above 1024 tokens with deterministic context (genre profiles + grounding rules + citation grammar EBNF from Phase 18). Padding asserted on cache creation; CI test fails if system instruction drops below 1024 tokens.
- Telemetry surface: `prompt_cached_tokens` exposed via `ipc.session.cache` IPC message for live dashboard.

### Prompt Diet (LOCKED — per success criteria)
- Audio Part: 18s window trimmed to 6s on non-PHASE events.
- Screen Part: skipped entirely on MIX_MOVE + HEARTBEAT.
- Observed TTFT win target: ≥500ms (gates phase pass).

### Predictive Drop Firing (Claude's Discretion within constraint)
- OFF by default in v2.0. Code path lives behind `predictive_enabled=False` flag in config.
- Telemetry guard pre-wired so v2.1 can flip on after Phase 16 ear-test baseline establishes false-positive rate.

### Test Harness (Claude's Discretion within constraint)
- Synthetic burst-event harness lives at `tests/runtime/test_burst.py` — 20 events in 30s, asserts ≤3 `interrupted=True` outcomes.
- Synthetic 60-fire burst at `tests/runtime/test_ack_rotation.py` asserts no same-sample collisions within 30s.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/runtime/session_loop.py` — Phase 4 LiveKit `AgentSession` cascade host; cancel + ack hooks attach here.
- `src/vibemix/state/event_detector.py` — Phase 17 priority-aware EventDetector; emits typed events with priority field consumed by cancel logic.
- `src/vibemix/coach/prompt_builder.py` — Phase 4/10 prompt builder; prompt diet logic lands here as event-type-aware truncation.
- `cohost_v4.py` POC — port-from reference for ack-bank clip taxonomy (DO NOT modify per CLAUDE.md POC rule).

### Established Patterns
- Single-writer `state_refresh_loop` @100ms (Phase 6+ pattern).
- Typed Event objects with `MIN_EVENT_GAP_PER_TYPE` cooldown.
- Hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 for IPC (no pydantic per STATE).
- Telemetry over `ipc.session.*` messages on the existing UI bus.

### Integration Points
- LiveKit `google.LLM` plugin call site in `runtime/session_loop.py` — `extra_kwargs={"cached_content": ...}`.
- `SpeechHandle` returned by `session.generate_reply()` — wrapped in `runtime/cancel.py` interrupt helper.
- Ack-bank trigger fires from `EventDetector` consumer side, BEFORE `session.generate_reply()` is called when TTFT-avg gate trips.
- Telemetry dashboard reads from existing `ipc.session.*` bus → settings → diagnostics panel.

</code_context>

<specifics>
## Specific Ideas

- Wave 1: cancel-and-refire wrapper + 8s cooldown + 30/session cap (Pitfall 1 closes here).
- Wave 2: ack bank loader + 5-bucket rotation deque + 100ms trigger gate (Pitfall 8 closes here).
- Wave 3: Gemini context caching + 1024-token padding + 4min refresh manager (Pitfall 11 closes here).
- Wave 4: prompt diet event-type-aware truncation.
- Wave 5: synthetic burst + ack-rotation test harness, telemetry IPC wiring.

</specifics>

<deferred>
## Deferred Ideas

- Predictive drop firing turn-on (v2.1 — needs Phase 16 ear-test baseline first).
- v2.x latency stack (chunked audio Part streaming, partial-prefix re-use) — not needed if v1 hits success criteria.
- Multi-language ack bank — English-only for v2.0 (Italian/Turkish ack samples deferred to v2.x).
- Adaptive cache TTL based on session length — fixed 4min refresh in v2.0.
</deferred>

---

*Phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
