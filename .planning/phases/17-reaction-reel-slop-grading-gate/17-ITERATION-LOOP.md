# Phase 17 — Iteration Loop (Gate-Fail Recovery)

**Status:** Locked spec — governs what happens if `scripts/reaction_reel/analyze.py` returns a FAIL verdict against the rubric in `17-RUBRIC.md`.
**Source-of-truth for:** ROADMAP Phase 17 Success Criterion #3 (the "if gate fails" clause).
**Audience:** Kaan (operator) + future Phase 10 author who re-enters prompt-template work.

---

## 1. Trigger Condition

The gate **fails** iff at least one of these holds against the rubric in `17-RUBRIC.md` §5:

- Average score across all (reactions × raters) is **< 4.0**, OR
- **Any** rater scored **any** reaction with a **1 or 2**.

Both conditions are evaluated by `scripts/reaction_reel/analyze.py` (Plan 17-03). When the script writes `report.md` with `verdict: FAIL`, Phase 10 (prompt-template matrix) re-enters with the **3-cycle budget** defined in Section 2. The `verdict` field in `report.md` is the single source of truth — do not eyeball the numbers and decide "close enough"; the gate is mechanical.

If the verdict is `TIE_BREAKER` (avg ∈ [3.95, 4.05] AND >25% of reactions scored 3 — see `17-RUBRIC.md` §5), Kaan decides ship-vs-cycle. That decision sits outside this loop. The loop in this document handles only the unambiguous FAIL case.

---

## 2. Cycle Protocol — the 4-Step Loop

Run up to **three cycles**. Each cycle follows these four steps in order.

### Step 1 — Identify the worst cells
Read `report.md` from the most recent grading run. Pull the three lowest-scoring (persona × genre × mode) cells from the per-cell breakdown. These are the surgical targets — not the entire matrix. The script surfaces them at the top of `report.md` under the "Bottom-3 cells" section; do not re-aggregate by hand.

### Step 2 — Revise Phase 10 prompt templates surgically
Open `src/vibemix/prompts/matrix.py` and edit **only** the failing cells from Step 1. Phase 10's prompt-template matrix is a 6-cell grid (3 skills × 2 modes); each cell is a prompt template. The temptation is to rewrite globally — resist it. Global rewrites un-do unrelated cells that already pass. Surgical edits: change phrasing, add a negative-dictionary ban, tighten the persona voice in the failing cell alone. Run the existing Phase 10 unit tests after each edit to confirm no regressions.

### Step 3 — Re-record a focused reel
Re-record a **~10-minute focused reel** covering only the regressed cells, not the full 30-min reel. The `17-CAPTURE-PROTOCOL.md` segment-table scales down proportionally: if cells A, B, C failed, record one 3-min segment per failed cell, in Hype-man + Coach split if both modes failed. This keeps cycle time short — a full 30-min reel takes a day to capture + grade and the loop budget would burn out before convergence.

### Step 4 — Re-grade with Kaan + 1 friend only
Re-grade the focused reel with **Kaan + one DJ friend (dj1)** only. The other two raters (Francesco and dj2) are **preserved untouched** for the eventual full 30-min re-grade at cycle exit — they do not see the focused reels, so their blindness is intact when the loop converges and the full reel is re-rated. This preserves the blind invariant that the rubric depends on.

Run `scripts/reaction_reel/analyze.py` against the focused reel's grades. If `verdict: PASS` against the rubric criteria applied to the focused subset, treat the cell as fixed and exit the cycle. If still FAIL, increment the cycle counter and return to Step 1.

---

## 3. Escalation — After 3 Failed Cycles

If three full cycles complete without converging to PASS, escalate per ROADMAP Phase 17 Success Criterion #3: consider **scope-cut to Hype-man-only** — drop the Coach persona from v1 entirely. This is Kaan's decision, not the script's. The rationale: if three rounds of targeted prompt revision cannot lift Coach above the 4.0 floor, the persona may be fundamentally harder to ground than Hype-man (observations require more context than hype reactions). Shipping with **Hype-man-only** preserves the product's core value and defers Coach to v2 with the data from the failed cycles informing the redesign.

Alternative escalation paths Kaan may also consider:

- Push back the launch date and run a longer Phase 10 pass (not just 3 cycles, but a deep prompt-engineering sprint).
- Drop one skill level (e.g. Pro-only or Beginner-dropped) if the failure clusters on a skill axis rather than a mode axis.
- Re-evaluate the rubric — if multiple raters consistently land 3.x averages, the rubric may be calibrated too strict for the product's actual demographic. This is the path of last resort and requires Kaan's explicit override.

None of the alternatives are automatic. The default escalation after 3 failed cycles is **Hype-man-only scope-cut**.

---

## 4. Cycle Budget Accounting

Each cycle's `report.md` gets copied into the phase directory for audit:

```
.planning/phases/17-reaction-reel-slop-grading-gate/
├── 17-CYCLE-1-REPORT.md    — first failed cycle's analyze.py output
├── 17-CYCLE-2-REPORT.md    — second cycle's output (if needed)
└── 17-CYCLE-3-REPORT.md    — third cycle's output (if needed)
```

This preserves the iteration history alongside the final `17-GATE-RESULT.md` so the 3-cycle budget is **auditable post-hoc**. The threat-model concern is verdict-shopping (claiming a passing run without artefact); archiving every cycle's report makes that impossible. If `17-GATE-RESULT.md` lands on disk without the matching cycle reports, the gate verification is incomplete and Phase 17 cannot close.

The Phase 10 cell-by-cell diff between cycles also tells the team **what changed and why**, which feeds v2 prompt-template work directly. Do not delete the cycle reports after the gate passes — they are the most honest record of which phrasings worked on which (genre × mode × skill) combinations.
