<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Plan 42-06 — Public-facing documentation for the vibemix hallucination gate. -->

# vibemix Hallucination Gate

Public-facing documentation of the v3.0 hybrid hallucination gate — the
guardrail that keeps vibemix's spoken reactions tied to real events in the
actual DJ mix.

## Why this exists

vibemix's value is not the AI talking — it's the AI talking **in ground
truth**. Every reaction must be tied to a real event in the actual mix.
This gate is how we keep that contract honest. The north-star statement —
"A real DJ friend in your ear — no AI slop" — lives in the
[project README](../README.md#what-it-does) and is the load-bearing
anti-slop manifesto for everything below.

If a reaction feels scripted, late, hallucinated, or generic, the product
fails. The gate exists so that bar can be measured and enforced before
every release cut, not just inferred after the fact.

## Hybrid Gate at a glance

The gate has two lanes — a fast autonomous one that runs continuously,
and a slow human one that runs before release cuts.

| Lane | What it checks | Cadence | Bypass-able? |
|------|----------------|---------|--------------|
| Fast (autonomous proxy) | 2-judge cross-check (Gemini 3 Pro + Gemini 3 Flash) against the real-corpus replay harness | Every PR + nightly canary | No — required for merge |
| Slow (Kaan ear-test)    | Real DJ session ear-pass via debrief window toggle                                          | ≥ 2 sessions ≥ 2 genres in 14-day window | No — required for release cut |

Both lanes must be green before `scripts/release/check_gate.sh` (Gate-2 of
`scripts/launch/cut_release.sh`) exits 0. The fast lane catches drift
mechanically; the slow lane catches the qualitative slop modes (felt
scripted, felt late, felt generic) that no judge prompt currently catches.

## Threshold Values

The fast-lane gate consumes five locked numeric thresholds from
[`eval/THRESHOLD-LOCK.md`](THRESHOLD-LOCK.md). The values below are
mirrored from that file exactly — if the lock changes, this table must
change (the test suite pins the equality).

| Metric              | Locked value | What it means                                                                                       |
|---------------------|--------------|-----------------------------------------------------------------------------------------------------|
| `f1_min`            | ≥ 0.80       | At least 80% of ground-truth events get a substantive, on-time response (min of pro_f1, flash_f1).  |
| `substance_min`     | ≥ 0.65       | At least 65% of responses are genuinely useful — not boilerplate, not filler grunts with citations. |
| `cited_cosine_min`  | ≥ 0.40       | Cited evidence in each response is semantically related to the event (Gemini Embedding 2 cosine).   |
| `bypass_max`        | ≤ 0.15       | At most 15% of detected events go unspoken — the cascade isn't dropping reactions on the floor.     |
| `per_genre_f1_min`  | ≥ 0.70       | No single (detector × genre) cell falls below F1 = 0.70 — anti-overfit floor (Pitfall P43).         |

Audit trail for any movement in these values lives in
[`eval/THRESHOLD-RECALIBRATION-LOG.md`](THRESHOLD-RECALIBRATION-LOG.md).
Re-tuning without re-running both judges is forbidden per the lock file's
self-described retuning protocol.

## 2-Judge Architecture (high level)

The fast lane runs two judges over each session's reactions:

- **`judge_pro`** (Gemini 3 Pro) — the careful 6-axis judge. Scores
  groundedness, timing, substance, tone, relevance, brevity; emits a
  structured verdict.
- **`judge_flash`** (Gemini 3 Flash) — the broad-coverage binary judge.
  Asks one orthogonal question: does this sentence semantically anchor to
  its cited event?

The gate aggregates by `min(pro_f1, flash_f1)`. A single judge inflating a
score cannot drag the gate above 0.80 — that's the Pitfall P42 collusion
mitigation. The two rubrics are intentionally divergent so cross-checking
catches single-judge drift.

The full rubric bodies are public under [`eval/rubrics/`](rubrics/)
(`judge_pro.md`, `judge_flash.md`). Prompts are not inlined here so the
README stays scannable and the rubrics stay the single source of truth.

## Ear-Test Protocol (shape only)

The slow lane is captured by an opt-in toggle inside the Phase 29 debrief
window. After a DJ session ≥ 30 minutes, Kaan can sign off on the session
for the release-gate. The structured payload (genre, slop-flag booleans,
free-form notes, timestamps, signing identity) lands at
`eval/ear-test-logs/<session-id>.json` against the schema at
`eval/ear-test-logs/schema.json`.

Acceptance window math: **≥ 2 sessions** across **≥ 2 distinct genres**
within the last **14 days**, with **every** captured slop-flag
(`felt_slop`, `felt_scripted`, `felt_late`, `felt_generic`) reported as
`false`. A single `true` blocks the gate. Full protocol — including the
30 min minimum, the genre enum, the capture-surface UX, and the privacy
rationale — lives in [`eval/EAR-TEST-PROTOCOL.md`](EAR-TEST-PROTOCOL.md).

The textual content of individual ear-test sessions is **REDACTED** from
this public doc per the project's narrow privacy boundary. Only the
protocol shape is documented publicly; the structured log files live in
the repo as audit trail so reviewers can verify the gate fired on real
signed sessions, but their `free_form` text, session ids, and signed_at
timestamps are not republished here.

## Reproducing the proxy gate locally

OSS contributors can re-run the fast lane against the synthetic fixtures
in a fresh clone without any Gemini API spend:

```bash
# 1. Install deps (Python toolchain pinned in pyproject.toml + uv.lock)
uv sync --group dev

# 2. Run the eval test suite (uses VCR cassettes — $0)
uv run pytest tests/eval/

# 3. Run the replay harness with the noop judge against the synthetic fixtures
uv run python -m scripts.eval.replay_harness \
  --corpus tests/eval/fixtures \
  --judges noop \
  --threshold-lock eval/THRESHOLD-LOCK.md \
  --output /tmp/eval-out
```

Real-corpus runs against `eval/corpus/sessions/` (six ~30 min DJ sessions
tracked via git-LFS — see [`eval/corpus/MANIFEST.md`](corpus/MANIFEST.md)
+ [`eval/corpus/LICENSES.md`](corpus/LICENSES.md)) require a populated
corpus + `GEMINI_API_KEY` and incur cost (~$1–2 per full nightly canary).
The nightly CI workflow `.github/workflows/eval.yml` is the canonical
real-corpus runner.

## History — why v3.0 is hybrid

The v2.1 milestone shipped under an autonomous-only proxy gate (the
Phase 27 architecture above) because the Phase 16 ear-test memory override
was accepted as a one-milestone carveout per `gsd-autonomous fully` mode.
That override (informally tracked as "P85") was time-limited by design.
v3.0 retires it formally and reinstates Kaan's ear as the slow-lane veto.
Full transition rationale and audit trail in
[`.planning/decisions/P85-OVERRIDE-RETIRED.md`](../.planning/decisions/P85-OVERRIDE-RETIRED.md).

## Anti-feature carveouts

The hybrid gate is the locked design. The following are explicitly NOT in
scope for v3.0:

- We are **NOT building a more aggressive autonomous judge** to replace
  the ear-test. The 2-judge cross-check already meets the locked
  thresholds; the qualitative slop modes need a human ear.
- We are **NOT cross-DJ ear-testing** in v3.0 — single-DJ (Kaan) signed
  only. Cross-DJ sign-off is deferred to v3.x.
- We are **NOT gamifying the ear-test** (no streaks, no badges). The
  debrief toggle is a low-friction signal-capture surface, not a UX
  pattern to optimize for engagement.

## Cross-references

- [`eval/THRESHOLD-LOCK.md`](THRESHOLD-LOCK.md) — locked numeric thresholds (signed).
- [`eval/THRESHOLD-RECALIBRATION-LOG.md`](THRESHOLD-RECALIBRATION-LOG.md) — audit trail for threshold movement.
- [`eval/EAR-TEST-PROTOCOL.md`](EAR-TEST-PROTOCOL.md) — full ear-test protocol document.
- [`eval/corpus/MANIFEST.md`](corpus/MANIFEST.md) — real-corpus session manifest.
- [`eval/corpus/LICENSES.md`](corpus/LICENSES.md) — corpus attribution + licenses.
- [`eval/rubrics/`](rubrics/) — judge rubric bodies (`judge_pro.md`, `judge_flash.md`).
- [`scripts/eval/replay_harness.py`](../scripts/eval/replay_harness.py) — deterministic replay CLI.
- [`scripts/release/check_gate.sh`](../scripts/release/check_gate.sh) — Gate-2 umbrella that combines both lanes.
- [`scripts/release/check_ear_test.sh`](../scripts/release/check_ear_test.sh) — slow-lane ear-test gate.
- [`.planning/decisions/P85-OVERRIDE-RETIRED.md`](../.planning/decisions/P85-OVERRIDE-RETIRED.md) — v2.1→v3.0 override retirement.
