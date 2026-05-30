---
quick_id: 260530-3lh
slug: land-backend-live-tuning-brain
status: complete
date: 2026-05-30
milestone: v11.0
subsystem: learn + runtime
commits: [6dc07ab3, 41ccd726]
requirements-touched: [MAST-02, MAST-03, "§EARNED-LIVE-MASTERED-VERIFY (backend call-site)"]
---

# Quick Task 260530-3lh Summary — backend wiring of the v11.0 mastery spine

**The until-now-ORPHANED `learn/skill_recognizer.recognize()` finally has a live
call-site: `coach_loop` now credits the v11.0 skill(s) a CITED detected event
demonstrates, gated on the live `EvidenceRegistry` (un-cited/fabricated → ZERO
credit). This lands the backend code path that `§EARNED-LIVE-MASTERED-VERIFY`
(the real-FLX4 ear-pass, still KAAN-ACTION) verifies.**

## What shipped

| Commit | Type | What |
|--------|------|------|
| `6dc07ab3` | feat(103) | `_credit_live_skill_demo` glue in `runtime/coach.py` + 2 threaded kwargs in `__main__.py` coach_loop call + 5 RED→GREEN tests |
| `41ccd726` | test(103) | +3 coverage tests from cross-verify (MIX_MOVE dual-skill, unset-clock, raising-registry) + one-loop SAFETY comment |

- **The wire:** inside `coach_loop`'s `if ev is not None:` block, the new
  never-raises helper closes `EvidenceRegistry.has(s,k,t,tol=1.0)` over the
  recognizer's citation predicate, recomputes the session-relative `t_session`
  the EventDetector wrote (`event_detector.py:508`, wall clock), passes it as
  the explicit `event_t`, and persists the live-portion via `save_progress` only
  on a real credit. Learn imports are function-local (no top-level
  runtime→learn dep). **None-path is byte-identical** for every existing caller.
- **Anti-slop preserved/strengthened (Invariants #2/#3):** credit moves only on
  a resolvable citation; the MAST-03 positive-vs-negative control is the SAME
  event differing only in whether its citation resolves.
- **Competent floor + threshold (MAST-01/04):** only Competent skills accrue;
  Mastered flips at the per-skill threshold; `first_mastered_at` stamped once.

## Verification

- `tests/runtime/test_coach_skill_credit.py` — **8/8** (cited→credit+persist,
  un-cited→zero, gate-off no-op, broken-progress + raising-registry never-raises,
  MIX_MOVE→eq_mixing+deck_control, unset set_start_at self-cancel, unmapped→none).
- Slice green: `tests/runtime tests/learn tests/agent tests/test_main_smoke.py`
  → **1412 passed, 1 skipped** (opt-in live FLX4 jog). Import smoke (`__main__` +
  coach) OK. Clean-checkout gate green. The 12 prior ship-gate failures all
  GREEN on the current tree.
- **Cross-verify (2 independent adversarial agents):** correctness → CORRECT
  (contract honored on all 6 axes, no over-credit, None-path byte-identical);
  safety → SAFE (shared `_learn_progress` clobber-free on the one asyncio loop;
  reads MusicState only; never-raises). Actionable feedback folded into `41ccd726`.
- **Final full-suite:** `6736 passed, 27 skipped, 1 xfailed, 4 xpassed` (was
  `12 failed / 6718 passed` at the start-of-session baseline — all 12 ship-gates
  resolved). 2 transient `tests/launch/test_readme_hero_lock.py` failures
  appeared mid-run (a concurrent session was rewriting README/launch files
  during the 7-min run) and pass 11/11 on a clean re-run — concurrent-edit
  noise, not from this backend work (which touches only coach/__main__/tests).

## Context that shaped this (concurrent-session reality)

The SHIP-READY directive's "package orphaned work" step completed itself
mid-run: a sibling session committed the deck-context brain (`7347cff4`),
Course-2 harmonic lesson (`14431357`), and inventory doc (`250db877`) as
clean-checkout-safe islands — with the untracked `deck_capture.py` /
`harmonic_practice.py` modules landed alongside their importers. The 2 inventory
"logic regressions" were already fixed; the 12 ship-gates went green. So the one
true remaining backend deliverable was the skill_recognizer call-site — done here.

## Flagged for Kaan / other sessions (NOT done here — out of backend lane)

- 🔴 `§EARNED-LIVE-MASTERED-VERIFY` — real two-deck DDJ-FLX4 verify: a CITED
  event advances Mastered, an un-cited moment does not. The code path now exists;
  the hardware ear-pass is Kaan's.
- 🟡 **No env kill-switch for skill-credit.** It accrues in every live session by
  design (Competent + citation floor limits blast radius). If the live ear-pass
  ever shows over-crediting, disabling needs a code change today — Kaan may want
  a default-ON `VIBEMIX_*` gate. Cross-verify advisory; left as a conscious decision.
- 🟡 `tauri/ui/` dirty (pill polish, library UI, learn UI) + `library_cmds.rs` +
  the pill Playwright dir + `package.json` — frontend/Tauri session's lane.
- 🟡 github-meta `altidus`-vs-`bravoh.ai` domain gate — Kaan's flagged domain
  decision (per memory); never auto-edited.
- 🟡 P104 skill-tree UI panel + the rare grounded "Mastered" vocal — frontend phase + ear-pass.
