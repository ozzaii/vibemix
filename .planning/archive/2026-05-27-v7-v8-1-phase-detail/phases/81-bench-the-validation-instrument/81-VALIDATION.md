---
phase: 81
slug: bench-the-validation-instrument
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-26
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q tests/bench/` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite); `tests/bench/` < 5s |

---

## Sampling Rate

- **After every task commit:** Run quick run command (`pytest -q tests/bench/`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## The offline / parked split (READ FIRST)

- **OFFLINE-TESTABLE (the phase test gate):** BENCH-01 harness logic (dimension sweep, per-cell prompt assembly from the real seams, results recording) with a FAKE genai client → zero API; BENCH-02 eval scorers (groundedness via `CitationLinter`, specificity, lens/mode-fidelity) on FIXTURE cells → deterministic, zero API; the BENCH-03 review-surface GENERATION (from fixture cells + scores).
- **PARKED (KAAN-ACTION, never auto-judged, never faked):** the bounded real-cell RUN on the funded key (the produce step — fail-safe parks on API error, never fabricates); the BENCH-03 VERDICT (Kaan's ear picks the winning architecture + model); the final taste-rubric wording (Kaan's IP).

---

## Per-Task Verification Map

> Every BENCH requirement's CODE is offline-provable (fake client + fixture cells); the live run + Kaan's verdict + the rubric wording are parked KAAN-ACTION (manual rows below, NOT auto-verified).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 81-01-T1 | 01 | 1 | BENCH-01/02/03 (fixtures + .mp3 data + _FakeClient) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/conftest.py --collect-only` + `ls tests/bench/data/*.mp3` | ⬜ pending |
| 81-01-T2 | 01 | 1 | BENCH-01/02/03 (xfail-strict scaffolds + bench literal-guard) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/` | ⬜ pending |
| 81-02-T1 | 02 | 2 | BENCH-01 (cell/matrix/fixtures/assemble — the composer; no-audio cell; no literal) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/test_assemble.py tests/bench/test_no_model_literal.py -x` | ⬜ pending |
| 81-02-T2 | 02 | 2 | BENCH-01 (run_study fake-client sweep + 429 fail-safe + recorder + SessionMeter + `vibemix bench` CLI) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/test_run_fake.py -x` | ⬜ pending |
| 81-03-T1 | 03 | 3 | BENCH-02 (groundedness via reused CitationLinter + specificity + lens-fidelity; rank-only) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/test_eval.py -x` | ⬜ pending |
| 81-04-T1 | 04 | 4 | BENCH-03 (review-surface render — ranked, grouped, EMPTY verdict, errored→parked) | unit | `PYTHONPATH=src python3 -m pytest -q tests/bench/test_review.py -x` | ⬜ pending |
| 81-04-T2 | 04 | 4 | BENCH-03 (docs/bench.md — produce step + KAAN-ACTION parking) | doc-check | `test -f docs/bench.md && grep -c KAAN-ACTION docs/bench.md` | ⬜ pending |
| — (parked) | 02 | manual | BENCH-01 (the bounded real two-study RUN on the funded key) | manual / produce | `uv run python -m vibemix bench run --study A` | ⬛ KAAN-ACTION |
| — (parked) | 04 | manual | BENCH-03 (Kaan's-ear VERDICT — did it click / which wins) | manual / human gate | (Kaan reads the review surface, picks the winner) | ⬛ KAAN-ACTION |
| — (parked) | 02 | manual | BENCH-01 taste axis (final TASTE_RUBRIC wording — Kaan's IP) | manual | (Kaan replaces the placeholder rubric) | ⬛ KAAN-ACTION |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬛ parked KAAN-ACTION (never auto-verified, never faked)*

**Sampling continuity check:** every code-producing task carries an `<automated>` verify; no 3 consecutive tasks lack one. The three parked rows are the hard human gate / Kaan's IP — they are NOT auto-verified by design (the offline gate is the honest-green proof; the live run + verdict ride forward).

---

## Wave 0 Requirements (Plan 01)

- [ ] Test for BENCH-01: the harness sweeps the 6 dimensions and assembles a per-cell prompt from the REAL seams (model_router/evidence/build_system_instruction flags/MusicState trajectory/build_lens_instruction/taste-rubric); a fake genai client records each cell — zero API. Includes the `no-audio`/`dsp_only` cell. → `tests/bench/test_assemble.py`, `tests/bench/test_run_fake.py` (xfail-strict, flip in Plan 02)
- [ ] Test for BENCH-01 fail-safe: a per-cell API error (e.g. 429) parks the cell as `{"error": ...}` — never fabricated, never aborts the sweep. → `tests/bench/test_run_fake.py` (xfail-strict, flip in Plan 02)
- [ ] Test for BENCH-02: groundedness via `CitationLinter.check(output, cell_snapshot)` (a cell citing an event absent from its snapshot scores ungrounded); specificity + lens/mode-fidelity heuristics deterministic on fixture cells — zero API. → `tests/bench/test_eval.py` (xfail-strict, flip in Plan 03)
- [ ] Test for BENCH-03: the review-surface generator produces a ranked, human-readable KAAN-ACTION artifact from fixture cells + scores; it RANKS but records NO verdict (the verdict field is empty/"pending Kaan"). → `tests/bench/test_review.py` (xfail-strict, flip in Plan 04)
- [ ] Model-axis uses `model_router.resolve(alias)` only — `tests/bench/test_no_model_literal.py` + the existing `tests/repo/test_model_literal_gate.py` rglob gate stay green (no literal in `bench/`; `bench/` NOT in the gate allowlist). → real-green now (Plan 01).

*Existing pytest infrastructure covers all offline phase requirements — no framework install needed. The `.mp3` excerpts live under `tests/bench/data/` (outside `src/`, not in the wheel — verified `[tool.hatch.build.targets.wheel] packages = ["src/vibemix"]`).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The bounded real-cell RUN produces honest cells on the funded key | BENCH-01 | Needs the funded key + real Gemini calls (cost) | KAAN-ACTION: run `uv run python -m vibemix bench run --study A`; cost-bounded + fail-safe (parks on API error, never fabricates) |
| Kaan's-ear verdict — "did it click / is it slop / which architecture + model wins" | BENCH-03 | THE HARD HUMAN GATE — subjective, Phase-16 rule | KAAN-ACTION: read the review surface, judge the cells, pick the winner. Autonomous NEVER fills this in. |
| Final taste-rubric wording ("what 'clicked' means") | BENCH-01 (taste axis) | Kaan's authored IP (like HYPE_INTERMEDIATE) | KAAN-ACTION: replace the placeholder `TASTE_RUBRIC` with Kaan's own wording |

*All BENCH code is offline-verified (fake client + fixture cells); the real run, Kaan's verdict, and the taste-rubric wording are parked KAAN-ACTION — never faked, never block the autonomous run.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (the 3 parked rows are the hard human gate / Kaan's IP — manual by design)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 scaffolds all of BENCH-01/02/03)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-approved 2026-05-26
