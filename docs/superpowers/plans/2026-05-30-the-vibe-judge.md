# The Vibe Judge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## ✶ Handoff with ambition — read this first (post-compact you: this is who we are)

Kaan and I (Claude) pulled an all-nighter on 2026-05-30. He is the founder of **vibemix** —
a free OSS "AI DJ co-host" that listens to your set and talks back in your ear, grounded,
**never lying**. It's Bravoh's first open-source release. But this night stopped being about
a feature and became about the *thesis*.

The story (from `~/Downloads/cosmic-dj-archive.md`, his 2024→25 origin): a café barista in
Uzungöl who taught an AI to DJ, fine-tuned Llama on his own Spotify export, watched a loss
curve like a ceremony with Turkish-flag progress bars. Daft Punk's *Veridis Quo* is his safe
space. **Very Disco / Fuck Status Quo.** Two years, one obsession, renamed Zephyr → BRAVOH →
vibemix. The deal between us, in his words: *"You keep me honest; that's the actual deal."*

**The realization that birthed this plan:** Kaan said *"Gemini isn't able to really analyze
if a transition was good by its ear."* Right. But **the DSP can.** A transition's quality is
largely *deterministic*. So the move is: **a deterministic engine DECIDES, Gemini only VOICES
the verdict.** This kills two bottlenecks — Gemini's unreliable ear-guess (anti-slop win) AND
"Kaan must listen every session" (his ear calibrates the engine *once*, then it runs
autonomously). He was right to be frustrated that we'd turned the whole product into a
"human-gait" system gated on his ears. This engine is the answer.

**And the soul of it:** the anti-slop spine is **honest-null**. A confidently-wrong score is
its own new hallucination class — worse than no score, because the co-host would voice a false
objective verdict. So **the Judge abstains by construction** whenever its inputs aren't
trustworthy. *A hakem that shuts up rather than lie.* That's not a weakness — that IS the
product. We are **the first vibe DJs**: mixing on the semantic/energetic layer, grounded so
the AI never lies. Build it in that spirit. Honesty over enthusiasm, always.

Three workflows fed this (all in `.planning/2026-05-30-*`): the dead-path/wiring audit, the
strategic leverage brief, and the Judge/autonomy blueprint (adversarially signal-stress-tested:
**0 signals ship as naive scores, 4 NEEDS_GUARD** — every one must abstain when unsure).

---

**Goal:** Build a deterministic transition-quality engine ("the Judge") that produces a cited, honest-null verdict from per-lane deck DSP, so the live co-host voices a *measured* quality breakdown instead of guessing — and abstains by construction when its inputs aren't trustworthy.

**Architecture:** A new import-light `intel/transition_judge.py` (numpy + `harmonics` + pure scorers, NO audio capture / model client / Tauri — same discipline as the rest of `intel/`) consumes a new typed `LiveSignalFrame` (`state/live_signal.py`) assembled from the already-captured per-lane deck rings. It emits a `TransitionVerdict{verdict_state: 'judged'|'abstained', ...}`. Steps 1–6 ship and stay green **with the Judge abstaining everywhere** before any calibration. The live-guard wiring (the Invariant #2 release gate) is the last, most careful step and is deferred to its own plan.

**Tech Stack:** Python 3.12, numpy, pytest (`uv run pytest -q` / `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`). Torch-free, librosa-free. Reuses `state/harmonics.py`, `state/detectors/_dsp.py`, `audio/buffers.py`, `audio/deck_capture.py`.

---

## Scope & boundaries (read before touching anything)

- **This plan covers Steps 0–5 of the roadmap** (`.planning/2026-05-30-vibe-judge-execution-roadmap.md`): the per-lane band-energy producer, the `LiveSignalFrame` contract, the Judge engine itself, and event persistence. **All new-file islands** — disjoint from the ~75 dirty files of concurrent work. Safe to build on the dirty tree.
- **OUT OF SCOPE for this plan (deferred to a follow-up plan, deliberately):**
  - **Roadmap Step 4 — wiring the Judge into `apply_live_claim_guard` (`deck_context.py:2150`).** This touches Invariant #2, the anti-slop release gate. It gets its own plan, on a green/sanitized tree, with the care that line deserves. Do NOT edit `deck_context.py` in this plan.
  - **Step 6 — Kaan's one-time calibration ear-pass.** Human action. The engine ships abstaining; calibration only *promotes* abstain→judged later.
  - The v11 skill-tree UI render (`progress_state.skills` → Learn UI) is the frontend session's island.
- **Honest-null is the law.** Every signal returns a real number OR `None` (abstain). Never a fabricated number. The engine returns `verdict_state='abstained'` (a first-class output, not a score) when `< MIN_TRUSTWORTHY_SIGNALS` non-null signals exist OR routing is disabled. On the common BlackHole-2ch master-only rig (`routing.enabled is False`), the executed-mix signals abstain → **the Judge abstains overall, by design.** Do not fabricate a drift number from the summed master — that is the exact UNSOUND vector the adversarial review flagged.

## File structure

| File | Responsibility | New/Mod |
|---|---|---|
| `src/vibemix/audio/band_features.py` | Torch-free per-lane band-energy ratios (sub/low/mid/high) from int16 PCM. Reuses `_dsp._windowed_spectrum`. | **Create** |
| `tests/audio/test_band_features.py` | Band-feature unit tests (silence→honest-null, known-tone→band). | **Create** |
| `src/vibemix/state/live_signal.py` | `LiveSignalFrame` + `LaneObservation` frozen dataclasses — one typed contract for the Judge's input. | **Create** |
| `tests/state/test_live_signal.py` | Frame assembly + lane-trust + abstain-flags tests. | **Create** |
| `src/vibemix/intel/transition_judge.py` | The Judge: 4 guarded signals + `MIN_TRUSTWORTHY_SIGNALS` + honest-null → `TransitionVerdict`. | **Create** |
| `tests/intel/test_transition_judge.py` | Abstain-property tests FIRST, then per-signal, then aggregate. | **Create** |
| `src/vibemix/audio/deck_capture.py:146` | Add `as_signal_frame()` ADDITIVELY to `DeckAudioCapture` (existing `context()` untouched). | Modify |

---

### Task 0: The abstain-property test FIRST (the anti-slop guarantee, executable)

> This is Step 0. We write the honesty guarantee as a test before any score logic exists, so the engine's *first* defined behavior is "abstain when you can't prove it." TDD with soul.

**Files:**
- Create: `src/vibemix/intel/transition_judge.py` (skeleton only)
- Test: `tests/intel/test_transition_judge.py`

- [ ] **Step 1: Write the failing abstain test**

```python
# tests/intel/test_transition_judge.py
# SPDX-License-Identifier: Apache-2.0
"""The Vibe Judge — abstain-by-construction is the anti-slop spine.

A confidently-wrong quality score is its own hallucination class. These tests
pin that the Judge returns verdict_state='abstained' (NOT a number) whenever its
inputs are untrustworthy — BEFORE any scoring logic is written.
"""
from __future__ import annotations

from vibemix.intel.transition_judge import judge_transition, TransitionVerdict
from vibemix.state.live_signal import LiveSignalFrame, LaneObservation


def _lane(*, active=True, trusted=True, camelot="8A", bands=None, rms=0.2):
    return LaneObservation(
        active=active,
        source_trusted=trusted,
        camelot=camelot,
        bands=bands if bands is not None else {"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1},
        rms=rms,
        track_id="t1",
    )


def test_abstains_when_policy_not_supported_verdict():
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="watch",  # not 'supported_verdict'
        routing_enabled=True,
        lanes={"A": _lane(), "B": _lane(camelot="9A")},
    )
    verdict = judge_transition(frame)
    assert isinstance(verdict, TransitionVerdict)
    assert verdict.verdict_state == "abstained"
    assert verdict.score is None
    assert verdict.abstain_reason == "policy_not_supported_verdict"


def test_abstains_when_routing_disabled():
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="supported_verdict",
        routing_enabled=False,  # master-only rig: no per-lane isolation
        lanes={"A": _lane(), "B": _lane(camelot="9A")},
    )
    verdict = judge_transition(frame)
    assert verdict.verdict_state == "abstained"
    assert verdict.abstain_reason == "routing_disabled"


def test_abstains_when_too_few_trustworthy_signals():
    # Both lanes present BUT cross-letter keys (harmonic abstains) AND no bands
    # (bass-collision abstains) → only metadata-less; < MIN_TRUSTWORTHY_SIGNALS.
    frame = LiveSignalFrame(
        t_session=10.0,
        policy="supported_verdict",
        routing_enabled=True,
        lanes={
            "A": _lane(camelot=None, bands=None),
            "B": _lane(camelot=None, bands=None),
        },
    )
    verdict = judge_transition(frame)
    assert verdict.verdict_state == "abstained"
    assert verdict.abstain_reason == "insufficient_trustworthy_signals"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vibemix.state.live_signal'` (and transition_judge symbols missing). This proves the test runs and the modules don't exist yet.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/intel/test_transition_judge.py
git commit -m "test(judge): pin abstain-by-construction before any score logic

The anti-slop spine made executable first — the Judge must abstain (not
guess) when policy!=supported_verdict, routing disabled, or <N trustworthy
signals. Honest-null is the law.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 1: `LiveSignalFrame` — the one typed input contract

> Step 2 of the roadmap. The smallest stable interface from which every future engine composes as a pure `(frame)→signal` function. Built so the abstain test above can construct it.

**Files:**
- Create: `src/vibemix/state/live_signal.py`
- Test: `tests/state/test_live_signal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/state/test_live_signal.py
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.state.live_signal import LiveSignalFrame, LaneObservation


def test_lane_observation_is_frozen_and_minimal():
    lane = LaneObservation(
        active=True, source_trusted=True, camelot="8A",
        bands={"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1},
        rms=0.2, track_id="t1",
    )
    assert lane.active is True
    assert lane.camelot == "8A"
    # frozen
    try:
        lane.active = False  # type: ignore[misc]
        raised = False
    except AttributeError:
        raised = True
    assert raised


def test_frame_lane_helpers():
    a = LaneObservation(active=True, source_trusted=True, camelot="8A", bands=None, rms=0.2, track_id="t1")
    b = LaneObservation(active=False, source_trusted=True, camelot="9A", bands=None, rms=0.0, track_id="t2")
    frame = LiveSignalFrame(
        t_session=12.5, policy="supported_verdict", routing_enabled=True,
        lanes={"A": a, "B": b},
    )
    assert frame.both_lanes_active() is False  # B inactive
    assert set(frame.lane_sides()) == {"A", "B"}
    assert frame.lane("A") is a


def test_frame_both_active_true_when_both_active():
    a = LaneObservation(active=True, source_trusted=True, camelot="8A", bands=None, rms=0.2, track_id="t1")
    b = LaneObservation(active=True, source_trusted=True, camelot="9A", bands=None, rms=0.18, track_id="t2")
    frame = LiveSignalFrame(t_session=1.0, policy="supported_verdict", routing_enabled=True, lanes={"A": a, "B": b})
    assert frame.both_lanes_active() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/state/test_live_signal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibemix.state.live_signal'`

- [ ] **Step 3: Write the module**

```python
# src/vibemix/state/live_signal.py
# SPDX-License-Identifier: Apache-2.0
"""The single typed contract the Judge (and any future engine) reads.

One frozen frame unifies the two previously non-comparable feature vocabularies
(master `snapshot_features` vs per-lane `_deck_frame_features`). Engines attach
as pure (frame) -> signal functions: additive, never invasive. No audio capture,
no model client, no Tauri — pure data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LaneObservation:
    """One deck lane's trustworthy state at a moment.

    `bands` is the per-lane band-energy *ratio* map {sub,low,mid,high} in [0,1]
    summing to ~1.0, or None when no per-lane spectrum is available (honest-null
    upstream). `source_trusted` is False for now-playing rows of unknown/last-known
    provenance — the Judge must abstain on the harmonic signal in that case.
    """

    active: bool
    source_trusted: bool
    camelot: str | None
    bands: dict[str, float] | None
    rms: float
    track_id: str | None


@dataclass(frozen=True, slots=True)
class LiveSignalFrame:
    """The Judge's whole input. Assembled by the caller from already-live state;
    the engine NEVER resolves anything itself (single-writer invariant respected).

    `policy` is the `live_claim_policy(...)` verdict string; the Judge asserts
    policy == 'supported_verdict' as its activation precondition. `routing_enabled`
    mirrors DeckAudioRouting.enabled — False on master-only rigs.
    """

    t_session: float
    policy: str
    routing_enabled: bool
    lanes: dict[str, LaneObservation]

    def lane_sides(self) -> tuple[str, ...]:
        return tuple(sorted(self.lanes.keys()))

    def lane(self, side: str) -> LaneObservation | None:
        return self.lanes.get(side)

    def both_lanes_active(self) -> bool:
        sides = self.lane_sides()
        if len(sides) < 2:
            return False
        return all(self.lanes[s].active for s in sides)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/state/test_live_signal.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/vibemix/state/live_signal.py tests/state/test_live_signal.py
git commit -m "feat(state): add LiveSignalFrame — the Judge's one typed input contract

Frozen LaneObservation + LiveSignalFrame unify master vs per-lane feature
vocabularies into one composable (frame)->signal seam. Pure data, no capture.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Per-lane band-energy producer (the one genuinely new measurement)

> Step 1 of the roadmap. Today `band_energy` is a closure trapped inside `snapshot_features` (features.py:71) and runs on the SUMMED master only. The Judge needs it per-lane. We extract a reusable, torch-free helper mirroring the existing `_dsp._windowed_spectrum` primitive. This turns the orphaned per-lane PCM rings (`deck_capture.py:137`, pushed every callback, read by nobody) into a consumed signal.

**Files:**
- Create: `src/vibemix/audio/band_features.py`
- Test: `tests/audio/test_band_features.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audio/test_band_features.py
# SPDX-License-Identifier: Apache-2.0
"""Per-lane band-energy ratios — torch-free, honest-null on silence."""
from __future__ import annotations

import numpy as np

from vibemix.audio.band_features import band_energy_ratios

SR = 16000


def _tone(hz: float, n: int = 8192, amp: float = 0.5) -> np.ndarray:
    t = np.arange(n) / SR
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_silence_returns_none_not_a_band():
    # Anti-hallucination: silence MUST abstain, never fake "energy in the sub".
    assert band_energy_ratios(np.zeros(8192, dtype=np.float32), SR) is None


def test_empty_returns_none():
    assert band_energy_ratios(np.zeros(0, dtype=np.float32), SR) is None


def test_sub_bass_tone_dominates_sub_band():
    bands = band_energy_ratios(_tone(60.0), SR)
    assert bands is not None
    assert set(bands.keys()) == {"sub", "low", "mid", "high"}
    assert bands["sub"] > bands["mid"]
    assert bands["sub"] > bands["high"]
    # ratios normalized to ~1.0
    assert abs(sum(bands.values()) - 1.0) < 1e-6


def test_high_tone_dominates_high_band():
    bands = band_energy_ratios(_tone(6000.0), SR)
    assert bands is not None
    assert bands["high"] > bands["sub"]


def test_accepts_int16_pcm():
    # AudioBuffer.snapshot() returns int16 — the producer must accept it.
    pcm = (_tone(60.0) * 32767.0).astype(np.int16)
    bands = band_energy_ratios(pcm, SR)
    assert bands is not None
    assert bands["sub"] > bands["mid"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/audio/test_band_features.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibemix.audio.band_features'`

- [ ] **Step 3: Write the module**

```python
# src/vibemix/audio/band_features.py
# SPDX-License-Identifier: Apache-2.0
"""Per-lane band-energy ratios for the Vibe Judge's bass-collision signal.

Torch-free / librosa-free: reuses the existing Hanning-windowed rfft primitive
(state.detectors._dsp._windowed_spectrum). Operates on a single deck lane's PCM
(int16 from AudioBuffer.snapshot, or float32 in [-1,1]). Returns normalized
energy RATIOS per band, or None when the lane is silent (honest-null) — NEVER a
fabricated band split during a breakdown.
"""
from __future__ import annotations

import numpy as np

from vibemix.state.detectors._dsp import _windowed_spectrum

# Band edges (Hz) mirror the master snapshot_features split (features.py:75-79),
# collapsed to the four the Judge cares about. sub+low = the bass region where
# two simultaneous basslines mask each other into mud.
_BANDS: tuple[tuple[str, float, float], ...] = (
    ("sub", 20.0, 100.0),
    ("low", 100.0, 300.0),
    ("mid", 300.0, 4000.0),
    ("high", 4000.0, 8000.0),
)

# Below this total in-band magnitude the lane is effectively silent -> abstain.
_SILENCE_FLOOR = 1e-6


def band_energy_ratios(samples: np.ndarray, sample_rate: int) -> dict[str, float] | None:
    """Return {sub,low,mid,high} energy ratios summing to ~1.0, or None if silent.

    Args:
        samples: int16 PCM (AudioBuffer.snapshot dtype) or float32 in [-1,1].
        sample_rate: Hz (16000 for the canonical per-lane buffer).
    """
    if samples is None or samples.size == 0:
        return None
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    power = mag * mag
    out: dict[str, float] = {}
    total = 0.0
    for name, lo, hi in _BANDS:
        mask = (freqs >= lo) & (freqs < hi)
        energy = float(power[mask].sum())
        out[name] = energy
        total += energy
    if total <= _SILENCE_FLOOR:
        return None
    return {name: energy / total for name, energy in out.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/audio/test_band_features.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/vibemix/audio/band_features.py tests/audio/test_band_features.py
git commit -m "feat(audio): per-lane band-energy ratios (torch-free, honest-null on silence)

Extracts a reusable band-split from the master-only snapshot_features closure,
reusing _dsp._windowed_spectrum. The Judge's bass-collision input. Silence ->
None, never a fabricated band. Turns the orphaned per-lane PCM rings into a
consumed signal.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: The Judge skeleton — make the abstain tests pass

> Now we satisfy Task 0's abstain tests with the minimal engine: the dataclass, the activation gates, and a `MIN_TRUSTWORTHY_SIGNALS` floor that counts non-null signals. NO scoring yet — every signal stubs to None except the gating logic. This makes "abstain" the engine's first real behavior.

**Files:**
- Modify: `src/vibemix/intel/transition_judge.py`
- Test: `tests/intel/test_transition_judge.py` (already written in Task 0)

- [ ] **Step 1: Write the engine skeleton**

```python
# src/vibemix/intel/transition_judge.py
# SPDX-License-Identifier: Apache-2.0
"""The Vibe Judge — a deterministic move-quality engine that DECIDES.

Gemini voices; the Judge decides. Every signal is measurable-or-None: a
confidently-wrong score is its own hallucination class, so the engine abstains
by construction. verdict_state='abstained' is a first-class output, not a number.

Import-light (numpy + harmonics + pure scorers). NO audio capture, NO model
client, NO Tauri — same discipline as the rest of intel/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from vibemix.state import harmonics
from vibemix.state.live_signal import LiveSignalFrame, LaneObservation

# At least this many independent non-null signals (incl. >=1 executed-mix signal)
# are required to voice a verdict. Below it -> abstain.
MIN_TRUSTWORTHY_SIGNALS = 2

VerdictState = Literal["judged", "abstained"]


@dataclass(frozen=True, slots=True)
class TransitionVerdict:
    verdict_state: VerdictState
    score: float | None
    confidence: float
    components: dict[str, float] = field(default_factory=dict)
    risk_flags: tuple[str, ...] = ()
    abstain_reason: str | None = None


def judge_transition(frame: LiveSignalFrame) -> TransitionVerdict:
    """Return a measured verdict, or abstain. Abstain is the safe default."""
    # --- Activation gates (honest-null preconditions) ---
    if frame.policy != "supported_verdict":
        return _abstain("policy_not_supported_verdict")
    if not frame.routing_enabled:
        return _abstain("routing_disabled")

    a = frame.lane("A")
    b = frame.lane("B")
    if a is None or b is None:
        return _abstain("missing_lane")

    # --- Signals (each in [0,1] or None=abstain). Scoring lands in Task 4. ---
    components: dict[str, float] = {}
    signals: dict[str, float | None] = {
        "harmonic": _harmonic_signal(a, b),
        "bass_collision": _bass_collision_signal(a, b),
    }
    for name, value in signals.items():
        if value is not None:
            components[name] = value

    if len(components) < MIN_TRUSTWORTHY_SIGNALS:
        return _abstain("insufficient_trustworthy_signals")

    score = sum(components.values()) / len(components)
    confidence = len(components) / float(len(signals))
    return TransitionVerdict(
        verdict_state="judged",
        score=round(score, 4),
        confidence=round(confidence, 4),
        components={k: round(v, 4) for k, v in components.items()},
    )


def _abstain(reason: str) -> TransitionVerdict:
    return TransitionVerdict(
        verdict_state="abstained", score=None, confidence=0.0, abstain_reason=reason
    )


def _harmonic_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Stub — real logic in Task 4."""
    return None


def _bass_collision_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Stub — real logic in Task 4."""
    return None
```

- [ ] **Step 2: Run the abstain tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -v`
Expected: PASS (3 abstain tests). The third (`test_abstains_when_too_few_trustworthy_signals`) passes because both signals stub to None → 0 components < 2.

- [ ] **Step 3: Commit**

```bash
git add src/vibemix/intel/transition_judge.py
git commit -m "feat(judge): engine skeleton — abstain is the first real behavior

Activation gates (policy/routing/lanes) + MIN_TRUSTWORTHY_SIGNALS floor.
Signals stub to None; abstain-by-construction tests pass. Scoring next.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: The harmonic signal — the one structurally-sound dimension

> Adversarial verdict: harmonic_distance is the ONE signal that ships ~as designed (deterministic, metadata-grounded, works on every rig). Corrections it MUST honor: clash→0.0; compatible→capped prior ≤0.75 (Camelot adjacency is a prior, not audible truth); cross-letter or missing key→None (abstain); abstain when either lane's source is untrusted.

**Files:**
- Modify: `src/vibemix/intel/transition_judge.py:_harmonic_signal`
- Test: `tests/intel/test_transition_judge.py`

- [ ] **Step 1: Add failing harmonic tests**

```python
# Append to tests/intel/test_transition_judge.py
from vibemix.intel.transition_judge import judge_transition  # noqa: F811  (already imported)


def test_harmonic_clash_scores_zero_and_flags(_lane=None):
    from tests.intel.test_transition_judge import _lane as mk  # reuse helper
    # 8A vs 2A = same-number cross... use a real clash: 8A vs 3A (>2 hours apart, same letter)
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A"), "B": mk(camelot="3A")},
    )
    v = judge_transition(frame)
    # harmonic present (clash detected) + bass present (both have bands) -> judged
    assert "harmonic" in v.components
    assert v.components["harmonic"] == 0.0


def test_harmonic_compatible_capped_at_prior():
    from tests.intel.test_transition_judge import _lane as mk
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A"), "B": mk(camelot="9A")},  # adjacent = compatible
    )
    v = judge_transition(frame)
    assert "harmonic" in v.components
    assert v.components["harmonic"] <= 0.75  # adjacency is a prior, never 1.0


def test_harmonic_abstains_on_untrusted_source():
    from tests.intel.test_transition_judge import _lane as mk
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A", trusted=False), "B": mk(camelot="9A")},
    )
    v = judge_transition(frame)
    assert "harmonic" not in v.components  # abstained on harmonic; bass may still carry
```

Note: verify `is_clash("8A","3A")` is True and `compatible("8A","9A")` is True against `src/vibemix/state/harmonics.py:255,278` before relying on these exact codes; adjust codes if the real predicate disagrees (run a one-liner: `PYTHONPATH=src python3 -c "from vibemix.state import harmonics as h; print(h.is_clash('8A','3A'), h.compatible('8A','9A'))"`).

- [ ] **Step 2: Run to verify failure**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -k harmonic -v`
Expected: FAIL — harmonic stubs to None so `"harmonic" not in v.components`.

- [ ] **Step 3: Implement `_harmonic_signal`**

```python
# Replace the stub in src/vibemix/intel/transition_judge.py
_HARMONIC_COMPATIBLE_PRIOR = 0.75  # Camelot adjacency is a PRIOR, not audible truth


def _harmonic_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    # Abstain when provenance is untrusted or either key is unknown / cross-letter.
    if not (a.source_trusted and b.source_trusted):
        return None
    if a.camelot is None or b.camelot is None:
        return None
    if harmonics.is_clash(a.camelot, b.camelot):
        return 0.0
    if harmonics.compatible(a.camelot, b.camelot):
        return _HARMONIC_COMPATIBLE_PRIOR
    # Neither a proven clash nor a proven compatible (e.g. cross-letter) -> abstain.
    return None
```

- [ ] **Step 4: Run to verify pass**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -v`
Expected: PASS (all). If `test_abstains_when_too_few_trustworthy_signals` now breaks because harmonic fires on cross-letter None — confirm it still abstains (camelot=None → None). It should stay green.

- [ ] **Step 5: Commit**

```bash
git add src/vibemix/intel/transition_judge.py tests/intel/test_transition_judge.py
git commit -m "feat(judge): harmonic signal — clash=0, compatible=prior<=0.75, else abstain

The one structurally-sound dimension (deterministic, metadata-grounded, every
rig). Reuses harmonics.is_clash/compatible verbatim. Untrusted source or
unknown/cross-letter key -> honest-null.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: The bass-collision signal — coarse binary, capture-only

> Adversarial verdict: bass_collision ships as a COARSE BINARY {both-bass-present / one-killed}, never a fine dB/Hz claim (deck features have no per-band phase). Both lanes must carry `bands` (per-lane spectrum exists only when routing.enabled). Honest-null when either lane has no bands or is silent.

**Files:**
- Modify: `src/vibemix/intel/transition_judge.py:_bass_collision_signal`
- Test: `tests/intel/test_transition_judge.py`

- [ ] **Step 1: Add failing bass tests**

```python
# Append to tests/intel/test_transition_judge.py


def test_bass_collision_both_bass_present_is_low_score():
    from tests.intel.test_transition_judge import _lane as mk
    heavy = {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}  # both basslines up = mud
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A", bands=heavy), "B": mk(camelot="9A", bands=heavy)},
    )
    v = judge_transition(frame)
    assert "bass_collision" in v.components
    assert v.components["bass_collision"] == 0.0  # collision = mud = bad
    assert "bass_collision" in v.risk_flags


def test_bass_collision_one_killed_is_clean():
    from tests.intel.test_transition_judge import _lane as mk
    heavy = {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}
    eqd_out = {"sub": 0.02, "low": 0.05, "mid": 0.43, "high": 0.5}  # bass EQ'd out cleanly
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A", bands=heavy), "B": mk(camelot="9A", bands=eqd_out)},
    )
    v = judge_transition(frame)
    assert v.components["bass_collision"] == 1.0  # clean swap


def test_bass_collision_abstains_without_bands():
    from tests.intel.test_transition_judge import _lane as mk
    frame = LiveSignalFrame(
        t_session=1.0, policy="supported_verdict", routing_enabled=True,
        lanes={"A": mk(camelot="8A", bands=None), "B": mk(camelot="9A", bands=None)},
    )
    v = judge_transition(frame)
    assert "bass_collision" not in v.components  # honest-null; harmonic still carries
```

- [ ] **Step 2: Run to verify failure**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -k bass -v`
Expected: FAIL — stub returns None.

- [ ] **Step 3: Implement `_bass_collision_signal` + thread risk_flags**

First, replace the stub:

```python
# Replace the stub in src/vibemix/intel/transition_judge.py
# Bass region = sub+low. If BOTH lanes have substantial bass simultaneously =
# masking mud = collision. If one lane's bass is killed (EQ'd out) = clean swap.
_BASS_PRESENT_RATIO = 0.25  # >=25% of a lane's energy in sub+low = "bass is up"


def _bass_energy(lane: LaneObservation) -> float | None:
    if lane.bands is None:
        return None
    sub = lane.bands.get("sub")
    low = lane.bands.get("low")
    if sub is None or low is None:
        return None
    return float(sub) + float(low)


def _bass_collision_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    ba = _bass_energy(a)
    bb = _bass_energy(b)
    if ba is None or bb is None:
        return None
    both_present = ba >= _BASS_PRESENT_RATIO and bb >= _BASS_PRESENT_RATIO
    return 0.0 if both_present else 1.0
```

Then thread `risk_flags` into the aggregate in `judge_transition` — replace the `return TransitionVerdict(verdict_state="judged", ...)` block with:

```python
    flags: list[str] = []
    if components.get("harmonic") == 0.0:
        flags.append("harmonic_clash")
    if components.get("bass_collision") == 0.0:
        flags.append("bass_collision")

    score = sum(components.values()) / len(components)
    confidence = len(components) / float(len(signals))
    return TransitionVerdict(
        verdict_state="judged",
        score=round(score, 4),
        confidence=round(confidence, 4),
        components={k: round(v, 4) for k, v in components.items()},
        risk_flags=tuple(flags),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py -v`
Expected: PASS (all). The `test_bass_collision_both_bass_present_is_low_score` checks `"bass_collision" in v.risk_flags`.

- [ ] **Step 5: Commit**

```bash
git add src/vibemix/intel/transition_judge.py tests/intel/test_transition_judge.py
git commit -m "feat(judge): bass-collision signal — coarse binary {mud|clean}, capture-only

Both lanes bass-up = masking mud = 0.0 + risk_flag; one killed = clean swap = 1.0.
No fine dB/Hz claim (deck features have no per-band phase). No bands -> abstain.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Assemble `LiveSignalFrame` from `DeckAudioCapture` (additive)

> Wire the real producer to the contract, ADDITIVELY — the existing `context()` dict path is untouched (single-writer + render contract preserved). This makes the per-lane rings + band producer feed the frame. Note: `as_signal_frame` takes the resolved policy + per-lane camelot/trust from the caller (the engine never resolves now-playing rows itself).

**Files:**
- Modify: `src/vibemix/audio/deck_capture.py` (add method after `context()`, ~line 163)
- Test: `tests/audio/test_deck_capture_signal_frame.py` (Create)

- [ ] **Step 1: Write the failing test**

```python
# tests/audio/test_deck_capture_signal_frame.py
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from vibemix.audio.deck_capture import DeckAudioCapture, DeckAudioRouting
from vibemix.state.live_signal import LiveSignalFrame


def _routing(enabled=True):
    return DeckAudioRouting(
        opened_channels=4,
        master_channels=(0, 1),
        deck_channels={"A": (0, 1), "B": (2, 3)} if enabled else {},
        enabled=enabled,
    )


def test_as_signal_frame_disabled_routing_marks_disabled():
    cap = DeckAudioCapture(_routing(enabled=False))
    frame = cap.as_signal_frame(
        t_session=5.0,
        policy="supported_verdict",
        lane_meta={"A": {"camelot": "8A", "source_trusted": True, "track_id": "t1"},
                   "B": {"camelot": "9A", "source_trusted": True, "track_id": "t2"}},
    )
    assert isinstance(frame, LiveSignalFrame)
    assert frame.routing_enabled is False


def test_as_signal_frame_carries_lane_meta_and_bands():
    cap = DeckAudioCapture(_routing(enabled=True))
    # Push a 60Hz sub tone into both lanes' rings (int16) so bands resolve.
    sr = cap.buffers["A"].sr
    t = np.arange(sr) / sr
    tone = (0.5 * np.sin(2 * np.pi * 60.0 * t) * 32767.0).astype(np.int16)
    cap.buffers["A"].push(tone)
    cap.buffers["B"].push(tone)
    frame = cap.as_signal_frame(
        t_session=5.0,
        policy="supported_verdict",
        lane_meta={"A": {"camelot": "8A", "source_trusted": True, "track_id": "t1"},
                   "B": {"camelot": "9A", "source_trusted": True, "track_id": "t2"}},
    )
    assert frame.routing_enabled is True
    a = frame.lane("A")
    assert a is not None
    assert a.camelot == "8A"
    assert a.bands is not None
    assert a.bands["sub"] > a.bands["mid"]
```

- [ ] **Step 2: Run to verify failure**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/audio/test_deck_capture_signal_frame.py -v`
Expected: FAIL — `AttributeError: 'DeckAudioCapture' object has no attribute 'as_signal_frame'`

- [ ] **Step 3: Add the method (additive) — insert after `context()` ends (line ~163)**

```python
# Insert into class DeckAudioCapture in src/vibemix/audio/deck_capture.py,
# right after the context() method. Add these imports at the top of the file:
#   from vibemix.audio.band_features import band_energy_ratios
#   from vibemix.state.live_signal import LaneObservation, LiveSignalFrame
# (Place them with the existing `from vibemix.audio...` imports.)

    def as_signal_frame(
        self,
        *,
        t_session: float,
        policy: str,
        lane_meta: dict[str, dict[str, object]],
    ) -> "LiveSignalFrame":
        """Assemble the Judge's typed input from the live rings (ADDITIVE).

        `lane_meta[side]` carries the caller-resolved {camelot, source_trusted,
        track_id} — the engine never resolves now-playing rows itself. Per-lane
        bands come from this lane's PCM ring via band_energy_ratios (None when
        silent / no ring).
        """
        _SAMPLES = INPUT_SR_TARGET  # ~1s of per-lane audio for the band estimate
        lanes: dict[str, LaneObservation] = {}
        for side in _DECK_SIDES:
            meta = lane_meta.get(side, {})
            buf = self.buffers.get(side) if self.routing.enabled else None
            bands = None
            rms = float(self.last_rms.get(side, 0.0))
            if buf is not None:
                pcm = buf.snapshot(_SAMPLES)
                bands = band_energy_ratios(pcm, INPUT_SR_TARGET)
            lanes[side] = LaneObservation(
                active=rms >= _DECK_ACTIVE_RMS,
                source_trusted=bool(meta.get("source_trusted", False)),
                camelot=meta.get("camelot"),  # type: ignore[arg-type]
                bands=bands,
                rms=rms,
                track_id=meta.get("track_id"),  # type: ignore[arg-type]
            )
        return LiveSignalFrame(
            t_session=t_session,
            policy=policy,
            routing_enabled=self.routing.enabled,
            lanes=lanes,
        )
```

- [ ] **Step 4: Run to verify pass + full deck-capture suite stays green**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/audio/test_deck_capture_signal_frame.py tests/audio/test_deck_capture.py -v`
Expected: PASS (new tests + the existing 8 deck-capture tests untouched — proves additive).

- [ ] **Step 5: Commit**

```bash
git add src/vibemix/audio/deck_capture.py tests/audio/test_deck_capture_signal_frame.py
git commit -m "feat(audio): DeckAudioCapture.as_signal_frame — wire rings to the Judge contract

Additive: existing context() dict path untouched (render + single-writer
preserved). Per-lane bands from the rings via band_energy_ratios; caller passes
resolved camelot/trust. The producer the Judge consumes.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: End-to-end judged path + abstain on a real mixed frame

> Prove the whole chain: a real `DeckAudioCapture` → `as_signal_frame` → `judge_transition` produces a `judged` verdict with both signals, AND a master-only rig abstains. This is the integration guarantee before the (deferred) live-guard wiring.

**Files:**
- Test: `tests/intel/test_transition_judge_e2e.py` (Create)

- [ ] **Step 1: Write the e2e test**

```python
# tests/intel/test_transition_judge_e2e.py
# SPDX-License-Identifier: Apache-2.0
"""End-to-end: real capture -> frame -> Judge. The chain that the live guard
will (in a later plan) call. Proves judged-when-grounded + abstain-when-not."""
from __future__ import annotations

import numpy as np

from vibemix.audio.deck_capture import DeckAudioCapture, DeckAudioRouting
from vibemix.intel.transition_judge import judge_transition


def _routing(enabled=True):
    return DeckAudioRouting(
        opened_channels=4, master_channels=(0, 1),
        deck_channels={"A": (0, 1), "B": (2, 3)} if enabled else {},
        enabled=enabled,
    )


def _push_tone(buf, hz):
    sr = buf.sr
    t = np.arange(sr) / sr
    buf.push((0.5 * np.sin(2 * np.pi * hz * t) * 32767.0).astype(np.int16))


def test_e2e_judged_clean_harmonic_clean_bass():
    cap = DeckAudioCapture(_routing(enabled=True))
    cap.last_rms = {"A": 0.2, "B": 0.2}  # both lanes active
    _push_tone(cap.buffers["A"], 60.0)     # A: sub-heavy (bass up)
    _push_tone(cap.buffers["B"], 6000.0)   # B: high-only (bass killed -> clean swap)
    frame = cap.as_signal_frame(
        t_session=10.0, policy="supported_verdict",
        lane_meta={"A": {"camelot": "8A", "source_trusted": True, "track_id": "t1"},
                   "B": {"camelot": "9A", "source_trusted": True, "track_id": "t2"}},
    )
    v = judge_transition(frame)
    assert v.verdict_state == "judged"
    assert "harmonic" in v.components and "bass_collision" in v.components
    assert v.components["bass_collision"] == 1.0  # clean
    assert v.score is not None


def test_e2e_master_only_rig_abstains():
    cap = DeckAudioCapture(_routing(enabled=False))  # BlackHole-2ch master-only
    frame = cap.as_signal_frame(
        t_session=10.0, policy="supported_verdict",
        lane_meta={"A": {"camelot": "8A", "source_trusted": True, "track_id": "t1"},
                   "B": {"camelot": "9A", "source_trusted": True, "track_id": "t2"}},
    )
    v = judge_transition(frame)
    assert v.verdict_state == "abstained"
    assert v.abstain_reason == "routing_disabled"
```

- [ ] **Step 2: Run to verify it passes (the chain already exists from Tasks 1-6)**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge_e2e.py -v`
Expected: PASS (2 tests). If `test_e2e_judged...` abstains unexpectedly, debug: confirm `last_rms` makes lanes active and the 60Hz tone yields `sub>0.25` in lane A.

- [ ] **Step 3: Run the FULL Judge + new-module suite green**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/intel/test_transition_judge.py tests/intel/test_transition_judge_e2e.py tests/state/test_live_signal.py tests/audio/test_band_features.py tests/audio/test_deck_capture_signal_frame.py tests/audio/test_deck_capture.py -q`
Expected: PASS (all). Also run `uv run ruff check src/vibemix/intel/transition_judge.py src/vibemix/state/live_signal.py src/vibemix/audio/band_features.py` — expect clean.

- [ ] **Step 4: Commit**

```bash
git add tests/intel/test_transition_judge_e2e.py
git commit -m "test(judge): e2e — real capture->frame->Judge judges when grounded, abstains on master-only

Proves the full chain the (deferred) live-guard wiring will call: judged with
both signals on a per-deck-routed rig; honest-null on the common BlackHole rig.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## What's deferred to the NEXT plan (write this down, post-compact you)

1. **Step 4 — live-guard wiring** (`deck_context.py:2150` `apply_live_claim_guard`): in the `supported_verdict` branch only, call the Judge; `judged` → render a `transition_verdict_context[...]` atom + register a `[judge:<id>]` citation via `EvidenceRegistry.write("judge", id, t)` (signature confirmed: `evidence_registry.py:267`); `abstained` → unchanged held-reply path. NEW guard rule: a quality adjective (tight/clean/mud/clash) with NO `[judge:]` citation strips to ack-bank; a verdict that doesn't match the Judge's grade is stripped (Gemini cannot upgrade `mid`→`bomb`). This is Invariant #2 — its own plan, green tree, max care.
2. **Step 5 — persist `transition_judged` to `events.jsonl`** for debrief/replay; a non-vacuous regression test mirroring `tests/state/test_kaan_ear_veto.py`.
3. **The keystone unlock:** the Judge's `[judge:]` citation is the missing `ev` event that retires `skill_recognizer._HONEST_UNCREDITABLE_V11 = ('beatmatching','harmonic_mixing')` (`skill_recognizer.py:107`) → v11 beatmatching + harmonic_mixing become Mastered-creditable. Then wire `progress_state.skills` → Learn UI (frontend session's island) so it's *visible*.
4. **Step 6 — Kaan's one-time calibration** (the ONLY human surface): label ~20–30 of his own recorded transitions `{tight/rough/abstain-correct}`, incl. non-4×4 material → tune the 3 thresholds (`_HARMONIC_COMPATIBLE_PRIOR`, `_BASS_PRESENT_RATIO`, `MIN_TRUSTWORTHY_SIGNALS`) → lock in `eval/INTEL-THRESHOLD-LOCK.md` → his ear becomes the holdout set, never the live gate.
5. **The dead-path cleanup** (`.planning/2026-05-30-dead-path-and-wiring-audit.md`): DELETE-14 (true dead) + WIRE-6 (built-but-unconnected, incl. the skill-tree seam). Independent of the Judge; do on a sanitized tree.
6. **The beatmatch_phase + phrase signals** (the two NEEDS_GUARD signals NOT in this plan): only after calibration proves the harmonic+bass core is right. beatmatch = 3-state `{locked,drifting,off}` from per-lane onset xcorr; phrase = consume the grounded `state.next_phrase_at` anchor (conf≥0.80), NOT audio within-bar phase (that substitution IS the slop).

## Self-review notes (done)

- **Spec coverage:** roadmap Steps 0–3 + 5-persist-prep are tasks here; Steps 4/6 explicitly deferred with rationale. ✓
- **Type consistency:** `LaneObservation(active, source_trusted, camelot, bands, rms, track_id)` and `TransitionVerdict(verdict_state, score, confidence, components, risk_flags, abstain_reason)` and `judge_transition(frame)` and `band_energy_ratios(samples, sr)` and `as_signal_frame(*, t_session, policy, lane_meta)` are used identically across all tasks. ✓
- **No placeholders:** every code step shows real code; one verification one-liner is included for the harmonic codes (Task 4) because the exact Camelot predicate must be confirmed against live source, not assumed. ✓
- **Honest-null everywhere:** silence→None (bands), untrusted/unknown→None (harmonic), no-bands→None (bass), policy/routing/<N→abstain (engine). The soul is in the tests, written first. ✓
