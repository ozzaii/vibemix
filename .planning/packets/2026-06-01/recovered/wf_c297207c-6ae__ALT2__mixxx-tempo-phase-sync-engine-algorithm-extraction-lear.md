# MIXXX TEMPO/PHASE SYNC ENGINE — ALGORITHM EXTRACTION (learn-from-spec, GPL never vendored)

## (1) THE ALGORITHM IN YOUR OWN WORDS (clean-room reimplementable in numpy)

Mixxx's sync engine answers two distinct questions that vibemix conflates as "are these decks beatmatched":
- **(a) the static comparison** — "right NOW, by how many beats/ms/degrees is deck B's beat phase off from deck A's?" — this is the grading primitive.
- **(b) the closed-loop corrector** — "what playback-rate nudge brings B back into phase-lock with A over the next callbacks?" — this is the auto-sync PI-ish controller.

vibemix needs (a) verbatim for grading and (b) as the *teaching target* ("nudge the jog +0.7% to catch up").

### Core data model: beat-distance, not absolute time
Mixxx never compares wall-clock positions directly. Each deck reduces its playhead to a **beat distance** — a scalar in `[0, 1)` = the fraction of the way through the current beat (`0.0` = exactly on a beat, `0.5` = halfway to the next). This is the whole trick: two decks at different absolute positions but identical beat-distance ARE phase-aligned. (`bpmcontrol.cpp:650 getBeatDistance`, `:732 getBeatContextNoLookup`.)

```
beatPercentage = (thisPosition - prevBeatPosition) / (nextBeatPosition - prevBeatPosition)
beatDistance   = beatPercentage - userOffset    # wrap into [0,1)
```
`prevBeatPosition`/`nextBeatPosition` come from the beatgrid lookup (`findPrevNextBeats`). `beatLengthFrames = next - prev`. `userOffset` is a learned manual-nudge bias (see below).

### The phase-error math (THE grading core)
Beat distance is **modular** — `0.99` and `0.01` are 0.02 apart, not 0.98. So the signed error must take the shorter of forward vs wrapped path. Mixxx's `shortestPercentageChange` (`bpmcontrol.cpp:479`) is a branchy hand-expansion of exactly this; the compact equivalent (already used in vibemix `beatmatch_judge._phase_error`) is:

```
error = (target_distance - cur_distance + 0.5) % 1.0 - 0.5   # signed, in [-0.5, 0.5]
```
- `error > 0` → this deck is *behind* the target (needs to speed up / jump forward).
- `error == 0` → phase-locked.
- `|error|` is the beats-off; **`error · beatLengthFrames / sampleRate · 1000` = ms off**; **`error · 360` = degrees off**.

### The decision thresholds (state machine) — `calcSyncAdjustment`, `bpmcontrol.cpp:572`
After computing `error`, Mixxx classifies into bands (all on `|error|` in beat-fraction units):

| band | constant | value | meaning | action |
|---|---|---|---|---|
| locked | `kErrorThreshold` | **0.01** beat | in sync | adjustment = 1.0 (no correction) |
| drifting | between 0.01 and 0.2 | — | proportional pull | `adjust = 1.0 + (−error · 0.7)` (`kSyncAdjustmentProportional`) |
| trainwreck | `kTrainWreckThreshold` | **0.2** beat | so far off we can't even tell ahead vs behind | `adjustment = 1.0 + 0.05` (just speed up to catch) |

Two rate-limiters protect the audio from a jerk:
- **`kSyncDeltaCap = 0.02`** — the per-callback change in adjustment is clamped to ±0.02 (slew-rate limit).
- **`kSyncAdjustmentCap = 0.05`** — the total rate deviation is clamped to ±5% (so sync never warps pitch more than ±5%).
The drifting branch is a clamped proportional controller with hysteresis carried in `m_dLastSyncAdjustment` — a leaky integrator, not a one-shot. (`bpmcontrol.cpp:606-637`.)

### The octave fold (half/double tempo) — `synccontrol.cpp:290 determineBpmMultiplier`
A 70-BPM track beatmatches a 140-BPM track. Mixxx decides whether to treat B as same / half / double tempo of A using the **square** of the BPM ratio against 2.0 and 0.5, i.e. the real crossover is √2 ≈ 1.414 (the unbiased symmetric split):

```
r = myBpm / targetBpm ; r2 = r*r
multiplier = 2.0  if r2 > 2.0     # target is ~half my speed -> double it
           = 0.5  if r2 < 0.5     # target is ~double -> halve it
           = 1.0  otherwise       # √2 inclusive at the edge
```
The folded effective ratio is `ratio / multiplier`; `|folded − 1|` is the true tempo error. When folded, the target *beat distance* must also be remapped because a long beat spans two short beats — `synccontrol.cpp:306 updateTargetBeatDistance` does the `±0.5` halfway-point correction (if doubling and target ≥ 0.5, subtract 0.5 then ×2; if halving, ×0.5 then add 0.5 if the long beat is past its midpoint). This is the subtle part: it's not just ×2/÷2, you must account for *which half* of the long beat you're in.

### "Late button push" forgiveness — `kPastBeatMatchThreshold = 1/8` beat (`bpmcontrol.cpp:41`)
When matching to align playheads (`getBeatMatchPosition`, `getNearestPositionInPhase`), if the other deck's fraction is within `1/8` beat *past* the beat (`otherBeatFraction > 1.0 − 1/8`), Mixxx assumes you pressed sync slightly late and matches the *previous* beat instead of forcing a forward jump. This is the "you were a hair late, I'll forgive and catch the beat you meant" rule.

### Master/follower handoff (state machine) — `enginesync.cpp`
SyncMode enum (`syncable.h:11`): `None(0) < Follower(1) < LeaderSoft(2) < LeaderExplicit(3)`.
- **Soft leader** = auto-chosen by Mixxx; **explicit** = user-pinned (won't be displaced unless stopped/ejected).
- `pickLeader` (`enginesync.cpp:219`) ranking under the default `PREFER_SOFT_LEADER`: if exactly 1 audible-playing synced deck → it's leader; if >1 → keep the current valid leader (stability/hysteresis) else first other playing deck; else first inaudible-playing; else first stopped deck. An explicit leader with valid BPM short-circuits all of this.
- The **InternalClock** (`internalclock.cpp`) is a phantom metronome: it free-runs its own `m_dClockPosition += bufferSize/2` each callback and `fmod`s by `m_dBeatLength = sampleRate·60/bpm` (`:219 onCallbackEnd`) — the fallback leader when no deck qualifies, and the thing followers chase when there's no human-driven master.
- Followers don't read the leader's playhead directly — the leader **pushes** `(bpm, beatDistance)` to all followers via `updateLeaderBpm`/`updateLeaderBeatDistance` (`enginesync.cpp:658/684`), one-writer-fan-out. A follower stores the target in `m_dSyncTargetBeatDistance` and chases it. (This is structurally the same single-writer discipline as vibemix Invariant #1.)

### The userOffset (the human-nudge memory) — `bpmcontrol.cpp:594-605`
When the DJ manually nudges pitch while synced, Mixxx doesn't fight it — it absorbs the current error as a *deliberate* offset (`m_dUserOffset = fmod(error + curUserOffset, 1.0)`) and thereafter holds *that* phase relationship. For grading purposes this is the difference between "drifting (mistake)" and "deliberately offset (style)".

### Signal flow per audio callback (the loop)
```
each block:
  for each deck: updateBeatDistance()              # playhead -> beat distance
  leader pushes (bpm, beatDistance) to followers   # fan-out
  for each follower:
     error = shortestPercentageChange(targetBD, myBD)
     adjustment = calcSyncAdjustment(error)        # banded + slew/cap limited
     rate = (instBpm/localBpm + userTweak) * adjustment   # calcSyncedRate :514
  apply rate to playback resampler
```

---

## (2) MIXXX FILE:LINE REFERENCES (method, not code to lift)

- **Beat distance / phase fraction**: `engine/controls/bpmcontrol.cpp:650` `getBeatDistance`; `:699` `getBeatContext`; `:732` `getBeatContextNoLookup` (the `(pos−prev)/beatLen` core).
- **Signed modular phase error**: `engine/controls/bpmcontrol.cpp:479` `shortestPercentageChange` (the verbose branchy form; compact `(d+0.5)%1−0.5` equivalent).
- **Sync correction state machine + thresholds**: `engine/controls/bpmcontrol.cpp:572` `calcSyncAdjustment` — `kErrorThreshold=0.01` (`:608`), `kTrainWreckThreshold=0.2` (`:612`), `kSyncAdjustmentCap=0.05` (`:613`), `kSyncAdjustmentProportional=0.7` (`:620`), `kSyncDeltaCap=0.02` (`:621`).
- **Synced rate composition**: `engine/controls/bpmcontrol.cpp:514` `calcSyncedRate` (`rate = instBpm/localBpm + userTweak`, then `× adjustment`).
- **Past-beat forgiveness**: `engine/controls/bpmcontrol.cpp:41` `kPastBeatMatchThreshold = 1/8`; used `:1059`.
- **Phase-align target position**: `engine/controls/bpmcontrol.cpp:756` `getNearestPositionInPhase`; `:926` `getBeatMatchPosition` (cross-samplerate transpose factor `:1022`); `:1134` `getPhaseOffset`.
- **userOffset (human-nudge memory)**: `bpmcontrol.cpp:594-605`, `:676`, `:1316` `resetSyncAdjustment`.
- **Octave half/double fold (√2)**: `engine/sync/synccontrol.cpp:290` `determineBpmMultiplier`; constants `kBpmDouble=2.0`/`kBpmHalve=0.5`/`kBpmUnity=1.0` (`synccontrol.cpp:17-19`); folded-beat-distance remap `:306` `updateTargetBeatDistance`, inverse `:206` `adjustSyncBeatDistance`.
- **localBpm (BPM around the playhead)**: `bpmcontrol.cpp:1261` `updateLocalBpm`, span `kLocalBpmSpan=4` (`:37`) — averages ±4 beats; matters for variable-tempo tracks.
- **Leader/follower handoff state machine**: `engine/sync/enginesync.cpp:33` `requestSyncMode`; `:219` `pickLeader`; `:326` `findBpmMatchTarget`; fan-out `:658/671/684`; SyncMode enum + helpers `engine/sync/syncable.h:11-61`.
- **Phantom metronome leader**: `engine/sync/internalclock.cpp:177` `updateBeatLength` (`beatLen=sr·60/bpm`); `:219` `onCallbackEnd` (free-run `+= bufferSize/2`, `fmod`).
- **Beatgrid model (constant-tempo `anchor+k·beatLen`)**: `track/beats.cpp` (referenced by vibemix `grid.py` dossier as §17/§2/§5; `findPrevNextBeats`, `findClosestBeat`, `findNthBeat`).

---

## (3) TORCH-FREE FEASIBILITY — fully clean, ALREADY HALF-DONE

100% feasible with **only `numpy` + stdlib `math`** — no torch, transformers, librosa, ONNX, or any C++ dependency. Every primitive is scalar arithmetic on beat-distances, `fmod`, and a square-root comparison. There is no DSP, no FFT, no model inference anywhere in the sync math. Confirmation: vibemix **already ports the static-comparison half clean-room**:
- `src/vibemix/audio/grid.py` `BeatGrid` — the `anchor + k·beatLen`, `beat_distance`, `closest_beat` (ports `beats.cpp`).
- `src/vibemix/audio/miniplayer.py` `_do_scale_block` — the linear-interpolation resampler that lets us OWN the playhead (ports `enginebufferscalelinear.cpp`).
- `src/vibemix/learn/beatmatch_judge.py` `grade_beatmatch` / `_phase_error` / `_octave_fold_multiplier` — ports `shortestPercentageChange` + `determineBpmMultiplier` + the 0.01/0.2/(1/8) thresholds, all numpy/math only, with scar citations in the docstring.

What is **NOT yet ported and is the high-value next pull** (all still torch-free):
1. **`calcSyncAdjustment` as a teaching controller** — the banded proportional corrector (0.7 gain, ±0.02 slew, ±0.05 cap). vibemix currently only *grades a snapshot*; porting the controller gives "to fix this, nudge +0.7%" actionable coaching AND an auto-sync for the practice deck. ~30 lines numpy.
2. **`getNearestPositionInPhase` / `getPhaseOffset`** — "snap deck B to phase" for a practice "show me the fix" button and for an automix engine. The cross-samplerate transpose factor (`:1022`) is needed only if A and B differ in sample rate; for our own decoded-to-one-rate slabs it's 1.0 (simplifiable).
3. **`updateLocalBpm` (±4-beat windowed BPM)** — only matters once we grade variable-tempo tracks; constant-grid is enough for v1.

Caveat worth carrying into the port: Mixxx assumes *infinite tempo-locked beatgrids* (its own TODO at `:859` warns `findNthBeat(-2)` breaks on marker grids). vibemix's `BeatGrid` is constant-tempo by design, so that assumption holds — but the day we ingest Rekordbox marker-based variable grids (`anlz_ingest.AnlzBeatGrid`, which already stores per-beat `times_s`/`bpms`), the `beat_distance` math must switch from `anchor+k·beatLen` to a marker bisect. The two grid types already coexist in the tree (`audio/grid.BeatGrid` constant vs `library/anlz_ingest.AnlzBeatGrid` marker), so this is a known seam.

---

## (4) VIBEMIX GAP → NEAREST INTEGRATION POINT (codegraph-verified)

**Primary gap: g14 — "real beatgrid/downbeat for beatmatch grading + a live producer."** The math is ported and tested; what's missing is the **live wiring**. Codegraph proof:
- `grade_beatmatch` (`learn/beatmatch_judge.py:83`) → **`codegraph_callers` returns "No callers found"** (only `tests/learn/test_beatmatch_judge.py` + `test_judge_credits_beatmatch.py` import it). It is an orphan engine.
- `MiniDeck.render_block` (`audio/miniplayer.py:130`) → callers are only `scripts/miniplayer_smoke.py`, `scripts/automix_demo_smoke.py`, and tests. The practice deck exists but nothing in the runtime drives it.
- The **consumer is already live and waiting**: `learn/skill_recognizer.py:154-171` has a `BEATMATCH_GRADED` branch that credits `"beatmatching"` skill ONLY on a cited, non-abstain, `tempo_matched AND phase_locked` grade (the v11.0 "Earned → Mastered" gate). Its comment literally says it's "the tempo/phase signal v11.0 was waiting for." So the recognizer end is wired; the **producer end is the hole**.

**The exact integration point to close g14** (the missing middle):
A live practice loop that, per block: drives `MiniDeck.render_block(n)` (`audio/miniplayer.py:130`), snapshots `MiniDeck.state()` → `DeckState`, calls `grade_beatmatch(grid_a, grid_b, state)` (`learn/beatmatch_judge.py:83`), and on a non-abstain grade emits a `BEATMATCH_GRADED` event whose `extra` is `grade_to_event_extra(grade)` (`beatmatch_judge.py:145`) **plus registers the matching `("ev", "BEATMATCH_GRADED", t_session)` citation** in the `EvidenceRegistry` — without that citation, the recognizer (`skill_recognizer.recognize`) credits nothing and the coach strips to the ack-bank fallback (Cardinal Invariant #2). That producer is the single new module. It belongs beside the existing engine in `src/vibemix/learn/` (e.g. a `practice_loop.py` / owned-deck session driver), reading `BeatGrid` from `audio/grid.py` and the live `DeckState` from `audio/miniplayer.py`, and firing through the same event/citation path the recognizer already consumes.

**Secondary gap this also feeds — "Call It Before It Lands" / transition timing.** The same `getPhaseOffset`/`getNearestPositionInPhase` port gives a *predictive* phase-offset (ms-to-aligned) that `state/transition_clock.py` (which already takes "~1 bar from the BeatGrid" per its docstring at `:360/:381`) and the deterministic Vibe Judge / `intel/transition_judge` can use to announce "they line up in 2 bars / you're 14 ms late on the 1" — a measured countdown rather than an inferred one, grounded by Invariant #3.

**The half/double octave-fold port** (`_octave_fold_multiplier`, already in `beatmatch_judge.py`) is also directly reusable by the Camelot/harmonic layer's tempo-compatibility check and by `library/next_suggestion.py`'s "what's mixable next" so it doesn't reject a 174↔87 pairing as a tempo clash.

**Net:** the Mixxx sync algorithm is not a thing vibemix needs to *learn* — the static-comparison half is already a faithful, tested, torch-free clean-room port. The actionable work is (a) port `calcSyncAdjustment` as the corrective controller for live coaching + practice-deck auto-sync, and (b) write the orphan-engine's missing live producer in `src/vibemix/learn/` that runs `MiniDeck → grade_beatmatch → BEATMATCH_GRADED event + citation`, lighting up the already-wired `skill_recognizer` credit gate and closing g14.
