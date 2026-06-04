# OVERNIGHT STATUS — autonomous QA loop (maintained by the driver)

> Kaan wakes to THIS board. The driver appends each pass; lanes commit with `QA-LANE:` trailers.
> Audit: `git log --all --grep '^QA-LANE:'` + read each lane's `qa-verdict.json`.

## Baselines (the bar to beat — never regress below)
- **Backend (Sven prose, 2026-06-02 fixture, MIDI-flattered):** friend 0.09 · earned 0.06 · move 0.10 · voice 0.20 · grounded 2.08 · should-NOT-spoken 137/137. Targets: friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0.
- **UX (vitest):** ~886 green at HEAD `364c55ba`. Target: never reduce; voice badge resolves; surfaces eye-pass-ready.

## Lane: backend (`qa/backend`)
| pass | last SHA | gate | dim_means (f/e/m/v/g) | should-not-spoke | items done | notes |
|---|---|---|---|---|---|---|
| _seed_ | 364c55ba | — | 0.09/0.06/0.10/0.20/2.08 | 137 | — | baseline (pre-lane) |

## Lane: ux (`qa/ux`)
| pass | last SHA | gate | vitest green | items done | screens for eye-pass | notes |
|---|---|---|---|---|---|---|
| _seed_ | 364c55ba | — | ~886 | — | — | baseline (pre-lane) |

## Blockers
- (none yet)

## Morning merge order
1. `qa/ux` then `qa/backend` (near-disjoint islands; resolve any `library_cmds.rs` overlap once, awake).
2. Eye-pass the UX-flagged screens before merge-to-main.
