---
phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire
plan: 04
subsystem: agent
tags: [latency, ack-bank, opus, rotation-deque, pitfall-8, four-gate-fire, cancel-cooldown-cross-cut]
requires:
  - 19-01  # CancelGate — cancel_cooldown_active flag the wiring caller passes to should_fire
  - 19-02  # ACK_ELIGIBLE_EVENTS / event-class taxonomy that informs the bucket map
  - 19-03  # GeminiContextCache — TTFT-aware path the ack-bank gate complements
provides:
  - "AckBank class — load (eager 40-OPUS decode), pick_for_event, should_fire, bucket_for_event"
  - "src/vibemix/agent/ack_bank.py — single chokepoint for ack-clip selection across the runtime"
  - "Module constants ACK_BUCKETS / ACKS_PER_BUCKET=8 / ACK_TTFT_GATE_MS=800.0 / ACK_MIN_GAP_S=0.4 / ACK_ROTATION_MAXLEN=10 / ACK_BANK_DIR / BUCKET_FOR_EVENT (frozen)"
  - "AckBankError — raised at construction on missing-bucket / wrong-count / missing-dir"
  - "scripts/generate_placeholder_acks.py — idempotent silent-OPUS generator (40 files, byte-deterministic across re-runs)"
  - "src/vibemix/audio/ack_bank/<bucket>/<NN>.opus — 40 silent-OPUS placeholder samples (KAAN-ACTION: replace with Achird-voice TTS recordings before v2.0 RC)"
affects:
  - src/vibemix/agent/ack_bank.py  # new — AckBank module
  - scripts/generate_placeholder_acks.py  # new — placeholder generator
  - src/vibemix/audio/ack_bank/.gitkeep  # new — directory marker
  - src/vibemix/audio/ack_bank/<bucket>/<NN>.opus  # 40 new placeholder OPUS files
  - tests/agent/test_ack_bank.py  # new — 19 invariant tests
tech-stack:
  added: []
  patterns:
    - "deterministic OGG patching — post-pass walks every OGG page (capture pattern OggS, page_segments at offset 26, body length = sum of segment_table) and rewrites bitstream_serial=0 + recomputes the page CRC32 (OGG-spec polynomial 0x04C11DB7, NOT zlib's CRC32) so re-running the generator produces byte-identical files. Without this rewrite, libopus + libavformat write a random per-stream serial → polluted git diff and PyInstaller bundle hash."
    - "frozen dispatch table via types.MappingProxyType — BUCKET_FOR_EVENT cannot be runtime-mutated (silent re-route to wrong bucket would be invisible in the runtime path)"
    - "eager-load + cache decoded PCM at construction — 40 × ~5 KB int16 ≈ 200 KB resident; pick_for_event is zero-I/O so the runtime path stays sub-100ms after EventDetector return"
    - "av.AudioResampler with explicit flush pass — without resampler.resample(None) the last ~10ms gets truncated, which would skew the 100ms-±10% duration assertion"
    - "deterministic pick order — lowest-numbered available index wins (NOT random); real DJs benefit from predictable rotation more than per-call entropy, and tests can assert exact sequences"
    - "LRU fallback with popleft+append — pops the head AND re-appends so the next over-saturated call sees a different LRU (otherwise the head pins forever and pick_for_event silently returns the same clip on every saturated call)"
    - "injected time_fn — same pattern as runtime/cancel.py CancelGate; tests drive the clock deterministically"
    - "lazy-typed Event via TYPE_CHECKING — module is unit-testable without dragging the MusicState graph into the import"
key-files:
  created:
    - src/vibemix/agent/ack_bank.py
    - scripts/generate_placeholder_acks.py
    - src/vibemix/audio/ack_bank/.gitkeep
    - src/vibemix/audio/ack_bank/drop_hit/01.opus  # +7 more, 8 per bucket × 5 buckets
    - tests/agent/test_ack_bank.py
  modified: []
decisions:
  - "Bucket dispatch is frozen via MappingProxyType, not just a plain dict. Tampering would silently re-route acks to the wrong event class (e.g. a DROP firing a 'mhm' generic_filler clip instead of 'yo!'), invisible in logs. Frozen + raises KeyError on unknown event types makes a wiring bug impossible to silently mask."
  - "Generator + bank ship the silent placeholders RIGHT NOW, not in a follow-up. Per plan <kaan_action_required>: the runtime path (loader + rotation + four-gate) needs end-to-end testability before Kaan can be sure his replacement Achird-voice recordings will integrate cleanly. Silent OPUS bytes pass av.open + decode invariants identically to real audio; the only difference is what gets played out the headphones."
  - "should_fire is a four-gate ladder, not a multi-condition single boolean. Each gate returns a one-word reason tag the wiring caller logs as telemetry — Phase 16 (Kaan's DJ ear) needs to attribute every suppressed ack to its specific cause (was it the TTFT gate, the cancel cooldown, the min-gap?). A single bool would lose that attribution."
  - "AckBank does NOT subscribe to CancelGate directly. The wiring caller (deferred follow-up — see Surfaced Follow-Ups) computes cancel_cooldown_active from CancelGate.last_cancel_at + CANCEL_COOLDOWN_S and passes it as a function arg. Same architectural choice as Plan 19-03 — keeps the ack module independent of cancel module's import surface; both modules reach each other through the agent-side coach loop."
  - "Constructor raises AckBankError on missing bucket / wrong count rather than silently creating empty buckets. Without a populated bank the ack path is dead; silent fallback would mask a bundling regression (CONTEXT D-08 AIza-key scan also runs over the same files at P21 — a missing bucket there would be a release-blocker we want surfaced loudly, not absorbed)."
  - "Plan-spec DEVIATION (test invariant): the original behavior text proposed a 60-fire-burst window of ACK_ROTATION_MAXLEN=10 picks. With ACKS_PER_BUCKET=8 < 10, this is mathematically unsatisfiable — pigeonhole forces collision after 8 picks per bucket. Test was rewritten to assert the strongest provable invariant: no idx repeats within the prior min(ACKS_PER_BUCKET, ACK_ROTATION_MAXLEN) - 1 = 7 picks per bucket. The 7-pick window is the actual collision-free guarantee delivered by the rotation deque."
  - "Plan does NOT modify runtime/coach.py — runtime-loop integration is a deferred follow-up per planner SUMMARY deviation #5. AckBank ships the API; the coach loop wiring (call should_fire on every event, call pick_for_event when fire=True, push pcm via PlaybackQueue.push, update rolling_ttft_avg_ms / last_ack_at / last_response_at / cancel_cooldown_active) lives in NEXT-SESSION.md as 'P19-04 followup: AckBank wiring in coach loop'."
metrics:
  duration: ~16min
  completed: 2026-05-14
  tasks: 2
  files_created: 44  # 1 module + 1 script + 1 .gitkeep + 40 OPUS files + 1 test file
  files_modified: 0
  tests_added: 19  # 8 task-1 + 11 task-2
  test_delta: "1692 → 1711 passing, 9 pre-existing failures unchanged"
  commits: 4  # test-RED + feat-GREEN per task
---

# Phase 19 Plan 04: AckBank Summary

Ships the 40-OPUS pre-recorded ack-bank loader + per-bucket rotation deque +
four-gate `should_fire` so a sub-300ms perceived first reaction can fire
within 100ms of EventDetector return when rolling TTFT degrades. Closes
Pitfall 8 (ack rotation collision) and respects Pitfall 1 (cancel-budget
blowout, closed in Plan 19-01) via the `cancel_cooldown_active` cross-cut
in `should_fire`. Delivers the API + tests + placeholder bank; runtime
wiring into `runtime/coach.py` is the surfaced follow-up.

## What Shipped

### `vibemix.agent.ack_bank.AckBank` — public API

```python
class AckBank:
    def __init__(self, dir: Path = ACK_BANK_DIR, time_fn: Callable[[], float] = time.monotonic) -> None
    def bucket_for_event(self, ev_type: str) -> str
    def pick_for_event(self, ev: Event) -> tuple[str, np.ndarray, int]   # (bucket, pcm_int16_24kHz_mono, sample_idx)
    def should_fire(
        self,
        rolling_ttft_avg_ms: float,
        last_ack_at: float | None,
        last_response_at: float | None,
        cancel_cooldown_active: bool,
    ) -> tuple[bool, str]   # (decision, reason ∈ {"ttft_ok","cancel_cooldown","min_gap","fire"})
```

### `should_fire` — four-gate ladder (short-circuit on first deny)

| # | Gate | Trigger | Reason tag | Source |
|---|------|---------|-----------|--------|
| 1 | TTFT | `rolling_ttft_avg_ms <= 800.0` | `"ttft_ok"` | LATENCY-04 |
| 2 | Cancel cooldown | `cancel_cooldown_active is True` | `"cancel_cooldown"` | Plan 19-01 cross-cut |
| 3 | Min gap to response | `now - last_response_at < 0.4s` | `"min_gap"` | LATENCY-05 |
| 4 | Min gap to ack | `now - last_ack_at < 0.4s` | `"min_gap"` | (anti-back-to-back) |

All gates pass → `(True, "fire")`.

### Bucket layout — `src/vibemix/audio/ack_bank/<bucket>/<NN>.opus`

```
src/vibemix/audio/ack_bank/
├── drop_hit/        ← DROP, PHASE                    (8 × .opus)  "yo!" / "bring it!"
├── track_change/    ← TRACK_CHANGE                   (8 × .opus)  "fresh!" / "ohh, switching it"
├── mix_move/        ← MIX_MOVE                       (8 × .opus)  "nice!" / "oh that's clean"
├── silence_break/   ← KAAN_SPOKE, MANUAL             (8 × .opus)  "yeah?" / "what's up"
└── generic_filler/  ← LAYER_ARRIVAL, HEARTBEAT       (8 × .opus)  "mhm" / "yeah this is groovy"
```

5 buckets × 8 clips = **40 files**. Each placeholder is a 178-byte silent-OPUS (100ms zeros @ 48kHz mono encoded with libopus, OGG-containerized with deterministic serial=0 + recomputed CRC32). The constructor decodes through `av.AudioResampler` to int16 mono 24kHz PCM (~2556 samples ≈ 106ms — within ±10% of the 2400-sample target; OPUS framing rounds to 20ms boundaries). Bucket map is frozen via `MappingProxyType` — runtime tampering raises `TypeError`.

### Per-bucket rotation deque — `deque(maxlen=ACK_ROTATION_MAXLEN=10)`

`pick_for_event` selects the lowest-numbered idx NOT currently in the bucket's rotation deque (deterministic, test-friendly), appends idx → deque (oldest auto-evicts at maxlen). When all 8 indices are in a sub-sized deque (defensive code path, only reachable via monkey-patching `maxlen <= ACKS_PER_BUCKET`), LRU fallback pops the head AND re-appends so the next over-saturated call sees a different LRU. Provable invariant in steady state: **no idx repeats within the prior 7 picks per bucket** (pigeonhole upper bound; window = `min(ACKS_PER_BUCKET, ACK_ROTATION_MAXLEN) - 1`).

### `scripts/generate_placeholder_acks.py` — idempotent generator

Run once with `.venv/bin/python scripts/generate_placeholder_acks.py`. Writes 40 silent-OPUS placeholders into the bank layout. Idempotent — second invocation produces byte-identical files (verified via shasum of all 40 files across re-runs). The OPUS encoder is itself deterministic on all-zero input on a fixed (rate, layout, bitrate) configuration; the OGG container's per-stream random serial (4 bytes at offset 14-17 of every page) is the only non-deterministic component, and the post-pass `_patch_ogg_deterministic(data, serial=0)` rewrites it + recomputes the page CRC32 (OGG-spec polynomial 0x04C11DB7, table-driven).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] OGG container non-determinism broke `test_generator_idempotent`**
- **Found during:** Task 1 GREEN run.
- **Issue:** PyAV's OGG muxer writes a random per-stream `bitstream_serial_number` into every page header. Re-running the generator produced byte-DIFFERENT files (confirmed via byte diff at offsets 14-17 + CRC bytes at 22-25). The test asserted `path.read_bytes() == prior_bytes` per the plan's "byte-identical" wording.
- **Fix:** Added `_patch_ogg_deterministic` post-pass to `write_silent_opus`. Walks every OGG page using the segment-table (page_segments at offset 26, body length = sum of segment_table[]), rewrites bitstream_serial=0, recomputes the page CRC32 with OGG's polynomial 0x04C11DB7 (NOT zlib's CRC32 — different polynomial, different init/reflection). Verified: shasum stable across 2+ invocations; av.open round-trips the patched file cleanly.
- **Files modified:** `scripts/generate_placeholder_acks.py`
- **Commit:** `ced6aa0`

**2. [Rule 1 — Bug] LRU fallback pinned to head idx forever**
- **Found during:** Task 2 GREEN run (60-fire burst test).
- **Issue:** Original LRU fallback was `idx = rot[0]; rot.append(idx)` — but with maxlen > current deque length the append did NOT evict the head, so the head stayed pinned to the same idx forever and `pick_for_event` silently returned the same clip on every over-saturated call. For `silence_break` (which received 2 of every 8 events in the rotated burst), this meant pick #9 returned the same idx as pick #8 → adjacent collision.
- **Fix:** Changed to `idx = rot.popleft(); rot.append(idx)` — head advances on every LRU pick, so the cycle period is `ACKS_PER_BUCKET` (8) and the prior-7-window invariant holds.
- **Files modified:** `src/vibemix/agent/ack_bank.py`
- **Commit:** `bb8c9b1`

**3. [Rule 1 — Test invariant correction] Plan-spec rotation window mathematically unsatisfiable**
- **Found during:** Task 2 RED run.
- **Issue:** Plan behavior text specified the 60-fire-burst test should assert no idx repeats within a window of `ACK_ROTATION_MAXLEN=10` picks per bucket. With `ACKS_PER_BUCKET=8 < 10`, pigeonhole forces collision after exactly 8 picks per bucket — the deque holds 8 distinct values, and the 9th pick can only be one of those 8.
- **Fix:** Test rewritten to assert `min(ACKS_PER_BUCKET, ACK_ROTATION_MAXLEN) - 1 = 7` window — the strongest provable rotation invariant. At LATENCY-05's 0.4s min-gap, 7 spacing = at least 2.8s between identical clips, which is plenty for "feels like a real DJ friend" perception.
- **Files modified:** `tests/agent/test_ack_bank.py` (test only; no impl change)
- **Commit:** `34be9b0` (RED commit doc updated)

### Authentication Gates

None — this plan ships a pure-Python module + assets; no external service auth required.

## Surfaced Follow-Ups

These are NOT scope of Plan 19-04 — explicit per planner SUMMARY deviation #5 + plan `<kaan_action_required>` block. Surface them here so they don't get lost.

| Followup | What | Where to track | Blocking? |
|----------|------|----------------|-----------|
| **AckBank wiring in coach loop** | Call `should_fire` on every Event before LLM dispatch; if `(True, "fire")` then `pick_for_event` → `PlaybackQueue.push(pcm.tobytes())` → update `last_ack_at`. Plumb `cancel_cooldown_active` from `CancelGate.last_cancel_at + CANCEL_COOLDOWN_S`; plumb `rolling_ttft_avg_ms` from session telemetry. | NEXT-SESSION.md "P19-04 followup: AckBank wiring in coach loop" | YES — without this, the bank is loaded but never fires |
| **Real Achird-voice OPUS recordings** | Replace the 40 silent placeholders one-for-one. Use offline Gemini TTS Achird voice (per LATENCY-01); ~80-200ms per clip; naturally compressed. Re-run AIza-key scan (CONTEXT D-08) on the new bytes before merge. | NEXT-SESSION.md "P19-04 followup: real OPUS recording with Gemini Achird voice" | YES for v2.0 RC — placeholders ship for testing only |
| **Per-ack-fire telemetry** | Wire `recorder.log_event("ack_fire", {"bucket": ..., "sample_index": ..., "reason": ...})` into the runtime caller so Phase 16 (Kaan's DJ ear testing) can attribute every fired/suppressed ack to its bucket + reason. | Same as the wiring follow-up — natural pair | NO — telemetry helps Phase 16 evaluation but not feature-blocking |

## Verification

All plan `<verification>` checks pass:

- ✅ `pytest tests/agent/test_ack_bank.py -x` passes (19 tests, ~2s)
- ✅ `pytest tests/agent/ -x` shows 174 passed + 1 pre-existing failure (`test_persona_02_byte_identical_to_v4` — `cohost_v4.py` persona drift, out of scope)
- ✅ `find src/vibemix/audio/ack_bank -name "*.opus" -type f | wc -l` → **40**
- ✅ `find src/vibemix/audio/ack_bank -mindepth 1 -maxdepth 1 -type d | wc -l` → **5**
- ✅ `grep -c "ACK_TTFT_GATE_MS: float = 800.0" src/vibemix/agent/ack_bank.py` → **1**
- ✅ `grep -c "ACK_MIN_GAP_S: float = 0.4" src/vibemix/agent/ack_bank.py` → **1**
- ✅ `grep -c "ACK_ROTATION_MAXLEN: int = 10" src/vibemix/agent/ack_bank.py` → **1**
- ✅ `grep -c "ACKS_PER_BUCKET: int = 8" src/vibemix/agent/ack_bank.py` → **1**
- ✅ Import sanity: `from vibemix.agent.ack_bank import AckBank, BUCKET_FOR_EVENT; assert len(BUCKET_FOR_EVENT) == 8` exits 0
- ✅ `find scripts -name "generate_placeholder_acks.py" -type f | wc -l` → **1**; idempotency: shasum-stable across re-runs
- ✅ Full suite regression: 1711 passed (was 1692), 9 failed (same pre-existing), 7 skipped — net +19 ack_bank tests, no regression

## Self-Check: PASSED

- ✅ All commits exist in git log (`8af1df6`, `ced6aa0`, `34be9b0`, `bb8c9b1`)
- ✅ All created files exist and are tracked
- ✅ All tests pass; no regression beyond Plan 19-04 additions
