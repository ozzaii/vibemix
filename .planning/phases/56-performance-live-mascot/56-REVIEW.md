---
phase: 56-performance-live-mascot
reviewed: 2026-05-21T10:08:00Z
depth: deep
files_reviewed: 10
files_reviewed_list:
  - tauri/ui/src/mascot/event-dispatcher.ts
  - tauri/ui/src/mascot/index.ts
  - tauri/ui/src/mascot/__fixtures__/event-traces.json
  - tauri/ui/src/mascot/event-dispatcher.test.ts
  - tauri/ui/src/mascot/state-machine-fixtures.test.ts
  - tests/runtime/test_ttft.py
  - tests/llm/test_thinking_gate.py
  - tests/runtime/test_soak_stability.py
  - tests/e2e/test_phase_41_latency_stack_integration.py
  - tests/integration/test_mascot_dispatch_latency.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 56: Code Review Report

**Reviewed:** 2026-05-21T10:08:00Z
**Depth:** deep (cross-language: TS guard vs Python `phase.py` source-of-truth)
**Files Reviewed:** 10 (2 production TS, 1 fixture, 2 TS tests, 5 Python tests)
**Status:** issues_found (1 warning, 3 info — no blockers)

## Summary

Phase 56's production surface is small and well-contained: a music-confirmation
defence-in-depth guard in `event-dispatcher.ts` (`stateForPhase` now takes a
`music` level; `drop`/`peak` require `music >= PEAK_RMS`, `breakdown` requires
`music < LOW_RMS`; a contradiction returns `null` → current mode held), plus the
`music`/`voice` threading into `SnapshotSlice` (live frame: flat floats in
`index.ts`; fixture frame: nested `{rms}` in the harness). The rest of the diff
is test-only (TTFT budget pin, thinking-gate PERF-01 pins, both-mode soak,
mode-transition latency frame).

I verified the work against the actual code rather than the plan claims:

- **Guard logic is correct in isolation.** `music >= PEAK_RMS` (drop/peak) and
  `music < LOW_RMS` (breakdown) are the right comparison directions, no
  off-by-one, and the contradiction path returns `null` which the `PHASE` case
  short-circuits at `if (target === null) return null` → the prior mode genuinely
  persists (not a drop-to-idle). Confirmed by replaying `anti_slop_drop_quiet`:
  the harness records NO transition after the contradictory quiet drop.
- **Constants match Python.** TS `PEAK_RMS = 0.11` / `LOW_RMS = 0.04` are
  numerically identical to `src/vibemix/audio/constants.py` `PEAK_RMS = 0.110` /
  `LOW_RMS = 0.040`, and `levels.music` (EMA of normalized RMS / 32768, [0,1]) is
  the same domain as the `curve` values `phase.py` thresholds against — so the
  comparison is domain-correct, not just numerically coincidental.
- **FSM purity preserved.** `grep -nE "Date\.now|setTimeout|setInterval|from
  'three'"` on `event-dispatcher.ts` returns zero matches.
- **No NaN/undefined break.** Both readers gate on `typeof === "number"` /
  `typeof === "object"` and default to a numeric prior (ultimately `0`). JSON
  can't transport `NaN` (it becomes `null` → `typeof null === "object"` → falls
  to the default in the live reader). Even a hypothetical `NaN` reaching the
  guard fails safe: `NaN >= PEAK_RMS` and `NaN < LOW_RMS` are both `false` → mode
  held. No defect.
- **All scoped tests green** as of this review: vitest 38/38 (`event-dispatcher`
  + `state-machine-fixtures`), `tsc --noEmit` clean, Python 41 passed
  (ttft/thinking_gate/soak incl. `slow`), 6 passed (e2e/integration incl.
  `e2e`/`integration` markers).

One real semantic divergence between the TS guard and the Python phase classifier
is worth a WARNING (it cannot regress anti-slop, but it can make the mascot SKIP
a legitimate `breakdown`/`peak` mode). The rest are info-level documentation/test
robustness notes.

## Warnings

### WR-01: TS music-confirmation guard does not mirror Python's `breakdown`/`peak` semantics — legitimate modes can be silently dropped

**File:** `tauri/ui/src/mascot/event-dispatcher.ts:144-164`
(vs `src/vibemix/state/phase.py:43-63`)

**Issue:** The plan and the file's own comment claim the thresholds "MIRROR the
Python source-of-truth … so the mascot's mode boundaries agree with state.phase."
For `drop` they do. For `breakdown` and `peak` they do NOT — and the divergence is
in the direction of suppressing real modes (not slop), so it is a quality defect,
not an anti-slop hole.

Python `_classify_phase_v4` (`phase.py:57-62`):

```python
if last >= PEAK_RMS and any(v < LOW_RMS for v in recent[:3]):
    return "drop"
if earlier_max >= 0.040 and last < 0.5 * earlier_max:   # breakdown
    return "breakdown"
if all(v >= 0.045 for v in recent):                     # peak
    return "peak"
```

- **`breakdown`:** Python emits `breakdown` whenever the level has dropped to
  below *half its recent max* — it does NOT require `last < LOW_RMS`. A breakdown
  off a loud section (earlier_max = 0.30) fires while `last` is anywhere under
  0.15, i.e. *far above* `LOW_RMS = 0.040`. The TS guard requires `music <
  LOW_RMS (0.040)` to enter `idle_breathe`. So for the common case (a breakdown
  that settles around 0.05–0.14), the bus says `phase == "breakdown"` but the TS
  guard returns `null` and the mascot stays in whatever loud mode it was in. The
  "breakdown/chill" mode in the LIVE-05a 6-mode contract is effectively
  unreachable for a large class of real breakdowns.

- **`peak`:** Python's `peak` threshold is `0.045` (`all(v >= 0.045 …)`), not
  `PEAK_RMS = 0.110`. The TS guard requires `music >= PEAK_RMS (0.110)` for
  `peak`. A genuine Python `peak` section sitting between 0.045 and 0.110 will be
  classified `phase == "peak"` on the bus but rejected by the TS guard → no
  `dance_hard`, mode held. (The plan deliberately reused PEAK_RMS for `peak`
  "same family as drop", but that does not match the Python definition the comment
  says it mirrors.)

This won't produce slop (it only ever HOLDS the prior mode, never fabricates), so
it is not a BLOCKER. But it silently undermines the headline LIVE-05a deliverable
("≥6 distinct modes, each reachable from a real event"): two of the six contract
modes can fail to enter on legitimate, correctly-classified bus frames. The
fixtures pass only because they hand-pick `music.rms` values (breakdown at 0.02,
drop at 0.30) that satisfy the TS thresholds — they don't exercise the
half-of-earlier-max breakdown that real audio produces.

**Fix:** Make the guard a sanity floor, not a re-derivation of the classifier.
`state.phase` already encodes the full breakdown/peak logic upstream; the guard's
job is only to reject the *drop-during-silence* misclassification (RESEARCH
Pitfall 6). Keep the strict `drop` confirmation, but loosen `breakdown`/`peak` so
they don't fight the classifier:

```ts
function stateForPhase(phase: string, music: number): MascotState | null {
  switch (phase) {
    case "drop":
      // Drop is the slop-prone case: a real drop is loud. Keep the hard floor.
      return music >= PEAK_RMS ? "dance_hard" : null;
    case "peak":
      // Python peak floor is 0.045 (NOT PEAK_RMS). Confirm "not silent",
      // don't re-impose the drop threshold (that drops legit peaks 0.045–0.110).
      return music >= LOW_RMS ? "dance_hard" : null;
    case "breakdown":
      // Python breakdown = "fell to < half recent max", which can sit well
      // above LOW_RMS. Only reject the absurd "loud breakdown" — gate on
      // "not at full peak" rather than "< LOW_RMS".
      return music < PEAK_RMS ? "idle_breathe" : null;
    // groove/build/low/silent unchanged
    ...
  }
}
```

At minimum, if the strict thresholds are intentional, fix the comment
(event-dispatcher.ts:56-60 + 144-152) to stop claiming the guard "mirrors" /
"agrees with state.phase" — it imposes *stricter* boundaries than the classifier,
and that intentional asymmetry should be documented as such with the
mode-suppression tradeoff called out, plus a fixture that drives a
half-of-earlier-max breakdown to pin the chosen behaviour.

## Info

### IN-01: Anti-slop fixtures don't cover the real-audio breakdown shape

**File:** `tauri/ui/src/mascot/__fixtures__/event-traces.json:355-356, 421`
(breakdown snapshots use `music.rms` 0.02)

**Issue:** Every `breakdown` step in `multi_mode_sequence` and
`six_mode_reachability` uses `music.rms = 0.02` (< LOW_RMS), the one value that
satisfies the TS guard. None exercise a breakdown that settled above LOW_RMS but
below half-of-earlier-max — exactly the case WR-01 shows the guard mishandles.
Result: the fixture suite reports the 6-mode contract as met while a realistic
breakdown frame would not enter `idle_breathe`. The tests are internally
consistent but don't represent the production input distribution, so they give
false confidence in the headline deliverable.

**Fix:** Add a trace where a loud section (`music.rms` 0.30) is followed by a
`phase: "breakdown"` snapshot at `music.rms` 0.10 (above LOW_RMS, below half of
0.30) and assert the contract behaviour you actually want (enter `idle_breathe`
per the contract, or document the held-mode behaviour if WR-01 is accepted as-is).

### IN-02: `voice` is threaded into `SnapshotSlice` but never read by any consumer

**File:** `tauri/ui/src/mascot/event-dispatcher.ts:81-82`,
`tauri/ui/src/mascot/index.ts:210-217`

**Issue:** `voice` is added to `SnapshotSlice`, defaulted, and populated from both
the live frame and the fixture harness, but nothing in `event-dispatcher.ts`
(or any consumer in the diff) reads `snapshot.voice`. The UI-SPEC speaking-mode
contract is enforced via the `AI_GENERATING_REPLY`/talk-block path
(`speaking_overrides_music`), not via the `voice` level. So `voice` is currently
dead data on the slice. Not a bug — it is plausibly forward-wiring for a future
`voice > 0` speaking confirmation — but as shipped it is an unused field, and the
JSDoc ("Same flat-vs-nested duality as `music`") implies a guard parity that
doesn't exist.

**Fix:** Either wire a `voice`-confirmation into the speaking path (mirror the
music guard: only enter `talk_loop` from a music event if `voice` corroborates),
or drop `voice` from `SnapshotSlice` until a consumer exists, or add a one-line
comment that it is intentionally carried for a not-yet-wired speaking
confirmation.

### IN-03: TTFT "no resurrected gate" assertion uses a string-split obfuscation that reads as a smell

**File:** `tests/runtime/test_ttft.py:179`
(`assert not hasattr(meter, "".join(["should", "_fire"]))`)

**Issue:** The negative assertion that the retired `should_fire` runtime gate
isn't resurrected is written as `"".join(["should", "_fire"])`. The intent
(documented two lines up) is to avoid a literal `should_fire` token that a
purity/anti-resurrection grep would false-positive on. It works, but the
construct is opaque at the call site and a future reader may "simplify" it back
to the literal and silently break a grep gate elsewhere. The same obfuscation
trick appears intentionally in production purity comments — but here it is in an
assertion, where clarity matters more.

**Fix:** Inline a short comment at the assertion (not just the section header)
explaining the string-split is deliberate grep-avoidance, e.g.
`# split literal so the should_fire-resurrection grep doesn't trip on this test`.
No behaviour change.

---

_Reviewed: 2026-05-21T10:08:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
