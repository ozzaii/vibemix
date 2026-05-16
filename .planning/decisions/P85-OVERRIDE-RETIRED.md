# P85 Override Retired — v2.1 → v3.0 Transition

**REQ-IDs:** GATE-08
**Plan:** Phase 42 / Plan 42-05
**Date retired:** 2026-05-16

## Status

**RETIRED** (replaced by v3.0 hybrid gate).

The v2.1 P85 autonomous-only override is no longer in force. v3.0 ships with the
hybrid gate scaffolded across Phase 42 (Plans 42-01 → 42-06). All scripts, tests,
and reminder lines tied to the override expiry clock are removed in this plan.

## History

The v2.1 milestone shipped under an autonomous-only proxy gate (Phase 27) because
the Phase 16 ear-test memory override was accepted as a one-milestone carveout per
`gsd-autonomous fully` mode. Kaan's ear was deferred — the autonomous Phase 27
proxy gate (F1 / substance / cited-cosine / bypass thresholds) stood in for it
through the v2.1 RC bake.

The override's expiry was tracked via three distinct mechanisms:

1. **Pitfall P85** — flagged the carveout in `.planning/research/PITFALLS.md`.
2. **`tests/repo/test_phase_16_override_expiry.py`** (Phase 39-08) — load-bearing
   repo-level test asserting STATE.md still carried the override line + that
   `cut_release.sh` printed a `Phase 16 override cleanup reminder` on every RC
   cut so Kaan was prodded each ship.
3. **`scripts/launch/cut_release.sh` reminder lines** — `[P85] Phase 16 override
   cleanup reminder` plus the STATE.md cross-reference, both emitted on the
   success path so the reminder was visible every cut.

This worked: v2.1 shipped without the ear-test, the override was scoped to one
milestone, and the audit trail is in git history + the audit doc.

## Replacement

v3.0 Phase 42 introduces the **hybrid gate**: Phase 27's autonomous proxy stays
as the fast lane (PR + nightly canary), and Kaan's ear-test is added back as the
slow lane (release-cut Gate-2b veto). Both must be green before a release tag
can be cut.

The wiring lives in:

- `scripts/release/check_gate.sh` — combines 7-nightly proxy reads + ear-test
  invocation (Plan 42-04 / GATE-06).
- `scripts/release/check_ear_test.sh` — ear-test status gate (Plan 42-03 /
  GATE-05).
- `eval/EAR-TEST-PROTOCOL.md` — the ear-test runbook itself (Plan 42-03 /
  GATE-07).
- `scripts/launch/cut_release.sh` — Gate-2b slot invokes `check_gate.sh`
  (Plan 42-04 / GATE-06).

The hybrid design is locked: CONTEXT D-GATE-08 + memory
`project_phase_16_kaan_dj_testing` both pin "Kaan's DJ ear, not a formal suite"
as the v3.0 reaction-quality gate. No further iteration on the gate design is
sanctioned by this milestone.

## Audit Trail

- **v2.1 lock:** `eval/THRESHOLD-LOCK.md` signed `kaan_signed: autonomous_phase27`
  (2026-05-15). Locks the autonomous proxy thresholds at the moment of v2.1 cut.
- **v2.1 reminder enforcement:** `tests/repo/test_phase_16_override_expiry.py`
  (Phase 39-08) — asserted the expiry clock was live every time `pytest
  tests/repo/` ran.
- **v2.1 milestone close:** `.planning/v2.1-MILESTONE-AUDIT.md` (overall_verdict:
  WIRED) — captures the moment the override-bypass shipped.
- **v3.0 retirement:** Phase 42 / Plan 42-05 (this entry) + the positive-assertion
  replacement test `tests/repo/test_gate_42_hybrid_in_force.py`.

## What Changes

- **DELETED:** `tests/repo/test_phase_16_override_expiry.py` (its four assertions
  were tied to expiry-clock state that no longer exists).
- **DELETED:** P85 reminder lines in `scripts/launch/cut_release.sh` (Plan 42-04
  removes them in the same wave that wires `check_gate.sh` in).
- **ADDED:** hybrid-gate enforcement at Gate 2b in `cut_release.sh` (Plan 42-04).
- **ADDED:** `tests/repo/test_gate_42_hybrid_in_force.py` — positive-assertion
  replacement that pins the new contract (Plan 42-05 Task 2).
- **ANNOTATED:** `.planning/STATE.md` "Phase 16 ear-test memory override"
  decision line marked `[RETIRED post-v2.1]` with a cross-reference to this
  Decision Log entry. The original line is preserved (not deleted) — the audit
  trail must remain visible per STATE.md conventions.

## Anti-Feature Carveout

Do **NOT** build a more aggressive autonomous judge (LLM-as-judge, calibrated
classifier, replay-harness scorer, etc.) intended to replace or supersede the
ear-test. CONTEXT D-GATE-08 + memory `project_phase_16_kaan_dj_testing` together
lock the hybrid design as **final for v3.0**.

The autonomous proxy is the fast lane; Kaan's ear is the slow lane. Future
milestones may revisit this, but anyone reading this entry inside the v3.0
window should treat the hybrid design as load-bearing IP and not refactor it
under cover of routine cleanup.
