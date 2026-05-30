# vibemix — The Vibe Judge & The Autonomy Loop · Execution Roadmap (2026-05-30)

> Consolidates three back-to-back investigation workflows into one ordered plan:
> the **dead-path/wiring audit** (94 agents), the **strategic leverage brief** (32 agents),
> and the **Judge/autonomy blueprint** (9 agents, adversarially signal-stress-tested).
> Companion docs: `2026-05-30-dead-path-and-wiring-audit.md`,
> `2026-05-30-state-of-the-tree-inventory.md`.

## The thesis (Kaan's, sharpened)

We are the **first vibe DJs** — mixing on the semantic/energetic layer, not the
commoditized technical layer, grounded so the AI never lies. The engine for that:
**the Judge decides, Gemini voices.** Gemini cannot reliably judge "was that transition
good?" by ear; the DSP can. So a deterministic move-quality engine produces the verdict;
the co-host only voices the measured breakdown. **And the anti-slop spine is honest-null:
a confidently-wrong score is its own new hallucination class, so the engine ABSTAINS by
construction whenever its inputs aren't trustworthy.** A hakem that shuts up when it can't
prove it.

## What the Judge can honestly decide (the adversarial reality)

The 4 proposed signals were adversarially stress-tested: **0 ship as naive scores, 4
NEEDS_GUARD, 0 unsound.** None ship in continuous form. Honest verdict per signal:

| Signal | Ships as | Reality |
|---|---|---|
| **harmonic_distance** | **~as designed — the one structurally sound dimension** | Deterministic, built (`harmonics.is_clash` `:278`), already live-wired (`coach.py` compute_relation). Works **universally** (metadata-grounded). Correction: clash→0.0; compatible→prior ≤0.75 (adjacency is a prior, not audible truth); cross-letter→None. |
| **beatmatch_phase** | **3-state `{locked, drifting, off}`, middle abstains** | `estimate_bpm` is ±2.7 BPM autocorr ("is there a beat?", not a meter). Cross-correlate per-lane onset envelopes for phase offset; only the extreme buckets voice a verdict. **Per-lane audio only.** |
| **bass_collision** | **Coarse binary `{both-bass / one-killed}`, capture-only** | No per-lane band producer exists today (`_deck_frame_features` is broadband). Needs a new per-lane band-energy producer. Never voice fine dB/Hz. |
| **phrase_alignment** | **SPLIT** — consume the grounded `state.next_phrase_at` anchor (conf ≥ 0.80); the audio-derived part renamed to "within-bar offset". | Audio alone cannot supply absolute bar count; substituting within-bar phase for phrase boundary **is the slop**. Abstain when the anchor is cold. |

**The blunt limit, stated honestly:** on the common BlackHole-2ch master-only rig
(`routing.enabled is False`), both executed-mix signals abstain → **the Judge abstains
overall.** "Was that blend tight" only fires for per-deck-routed setups (rekordbox external
mixer). **harmonic_distance is the universal floor; executed-mix quality is the
per-routing bonus.** We do NOT fabricate a drift number from the summed master.

## The keystone closes itself

The Judge's cited `[judge:...]` verdict is the **missing `ev` event** that unlocks the two
v11.0 skills currently hard-flagged uncreditable (`skill_recognizer._HONEST_UNCREDITABLE_V11
= ('beatmatching','harmonic_mixing')`, `skill_recognizer.py:107`) — they're capped at
Competent because no cited live event ever fires for them. The Judge supplies that event.
So: **build the Judge → v11 beatmatching + harmonic_mixing become Mastered-creditable
autonomously**, and the skill-tree seam (`progress_state.skills` → Learn UI render) is the
last hop to make it visible. The dead-path hunt, the strategic brief, and the Judge
blueprint all converged on this one spine.

## Gate → autonomy (the answer to "you made it a human-gait system")

vibemix **already shipped the calibration machine**: `intel/gold_labels.py` +
`gold_sampling.py` + `gold_validation.py` (labeled corpus), `eval/INTEL-THRESHOLD-LOCK.md`
(locked thresholds), `tests/state/test_kaan_ear_veto.py` (the regression-template).
**Pattern: Kaan's ear → small labeled split ONCE → tuned thresholds locked → his ear
becomes the holdout set, never the live gate.**

| Runtime ear-gate | → Autonomy |
|---|---|
| §EARNED-LIVE-MASTERED-VERIFY | **Already autonomous in code** (credit is citation-gated). Reduce to ONE recorded FLX4 session replayed through `skill_recognizer` (trace.jsonl captures it) → assert cited-credits/uncited-zero. |
| Harmonic-clash gate (default off) | Run `eval/harmonic/run_veto.py` against Kaan's disagreed pairs ONCE → lock thresholds → flip `harmonic_clash_enabled` → autonomous. |
| "tight transition" Gemini ear-guess | Build the Judge → calibrate 3 thresholds ONCE (label ~20-30 own blends `{tight/rough/abstain-correct}`, incl. non-4×4) → locked → autonomous. |
| Mastered-vocal / tone passes | Genuinely irreducible (felt tone of prose) but **bounded**: autonomous `negative_dict` + bench specificity pre-filter catches slop pre-Kaan; his pass = one yes/no on a frozen rendered set, not per-session. |

## The simplicity loop (the modular core)

One **accidental complexity** to cut: `snapshot_features` (master vocab) and
`_deck_frame_features` (per-lane vocab) are two non-comparable feature vocabularies. The
fix and the modular spine in one move:

1. **`LiveSignalFrame`** (new, `state/live_signal.py`) — one frozen typed contract
   `{t_session, master, lanes, lane_pcm}` unifying both vocabularies. Added ADDITIVELY
   via `DeckAudioCapture.context().as_signal_frame()` — existing renderers keep reading
   the dict view (zero breakage, single-writer untouched).
2. **The Judge** (new, `intel/transition_judge.py`) — pure `(LiveSignalFrame, history) →
   TransitionVerdict{verdict_state: judged|abstained, score|None, components, risk_flags,
   abstain_reason}`. Import-light (numpy + harmonics + transition_scorer pure fns). Writes
   `EvidenceRegistry.write("judge", id, t)` → citable under Invariant #2.
3. **Reuse, don't fork** — `harmonics.is_clash` verbatim; PREP-time `transition_scorer`
   stays the candidate scorer; borrow `move_grade` slug vocab so Judge output rides the
   **same pill wire** (zero new UI contract).

Why it's the loop: one `LiveSignalFrame` + one `EvidenceRegistry` source lets **any future
engine attach as a pure `(frame)→signal` function** — additive, never invasive. DSP →
quality → AI → library → format-RE engines feed each other without a framework.

## Build sequence — [agent-autonomous] vs [kaan-once]

| # | Step | Owner |
|---|---|---|
| 0 | **Abstain-property test FIRST (TDD):** Judge returns `abstained` when `policy != supported_verdict`, when `routing.enabled is False`, when `< N` non-null signals. The anti-slop guarantee made executable before any score logic. | agent |
| 1 | **Per-lane band-energy producer** in `audio/` — run existing `_windowed_spectrum`+`band_energy` on `buffers['A'/'B']`, behind `routing.enabled`. Torch-free. *(turns the orphaned per-lane PCM rings into a consumed signal)* | agent |
| 2 | `state/live_signal.py` — `LiveSignalFrame` + additive `.as_signal_frame()`. | agent |
| 3 | `intel/transition_judge.py` — 4 guarded signals + `MIN_TRUSTWORTHY_SIGNALS=2` + honest-null. | agent |
| 4 | Wire into `apply_live_claim_guard` (`deck_context.py:2150`) **supported_verdict branch only**: `judged` → verdict atom + `[judge:]` citation; `abstained` → unchanged held-reply; a quality adjective without a `[judge:]` citation strips to ack-bank (Gemini cannot upgrade `mid`→`bomb`). | agent |
| 5 | Persist `transition_judged` to `events.jsonl`; regression test mirroring `test_kaan_ear_veto`. | agent |
| 6 | **Calibration ear-pass:** label ~20-30 own recorded transitions `{tight/rough/abstain-correct}` (incl. non-4×4) ONCE → sets 3 thresholds → locks in `INTEL-THRESHOLD-LOCK.md`. Thereafter autonomous. | **kaan-once** |

Steps 0–5 ship and stay green **with the Judge abstaining everywhere** (honest-null
default) before calibration. Step 6 only *promotes* abstain→judged on calibrated cases.

## Parallel cleanup (from the dead-path audit — independent of the Judge)

- **DELETE the 14** (true dead — shims, superseded setters, dead icons/aliases). Surgical commits per island (Python/TS/Rust separately).
- **WIRE the 6** (built-but-unconnected). Order: (1) skill-tree seam `progress_state.skills` → Learn UI *(frontend session's island — coordinate)*, (2) `emote_parser` → mascot reaction, (3) overlay-highlight listener, (4) wizard install steps into `STEP_ORDER`, (5) `NonDjConfirm`, (6) telemetry consent.
- **KEEP the 36** intentional deferred orphans — document, don't churn.

## Universal library interop (SEPARATE milestone — biggest reach unlock)

The pluggable seam **already exists**: `_Source` Protocol + `ingest_source` orchestrator +
`TrackEntry` universal currency + CLAP as the source-blind semantic layer. So
Serato/Traktor/Engine DJ/VirtualDJ are **parser-writing jobs, not architecture jobs** —
each a deterministic test, zero Gemini, zero ear-pass. **Serato = the largest single DJ
base = the biggest install-base unlock.** Scope guard: a separate milestone, NOT part of
the Judge build.

## The one first move

**Step 0 + Step 1 together: the per-lane band-energy producer over `DeckAudioCapture.
buffers['A'/'B']`, guarded by the abstain-property test.** It turns the orphaned per-lane
PCM rings (pushed every callback, read by nobody) into the first consumed executed-mix
signal, forces the honest-null gate to exist before any score, and starts the simplicity
loop at its lowest-risk entry — flipping the live path from "describe the shape, don't
score it" toward "voice this measured breakdown."

## Execution discipline (leader note)

The tree is currently ~75 files dirty across 2+ concurrent sessions with 14 pre-existing
suite failures. Per the hard rule Kaan documented (concurrent-session commit-absorb; the
161k-line near-disaster), the Judge chain executes as a **focused, sequenced TDD build on
disjoint new-file islands** (`transition_judge.py`, `live_signal.py`, the band producer,
the tests are all new files) — not scattered onto the dirty tree. Surgical `git add` per
island, verify `git diff --cached --name-only` before each commit, suite green per step.
