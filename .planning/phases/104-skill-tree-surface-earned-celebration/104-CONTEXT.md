# Phase 104: Skill-Tree Surface + Earned Celebration - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning
**Mode:** `gsd-autonomous fully` — smart-discuss, default-YES on grey area, KAAN-ACTION items parked (only privacy hard-rule + destructive risk pause).

<domain>
## Phase Boundary

The Learn-module **skill-tree panel** — the user views all ~6 skills, each bar's
stage (Locked / Competent / Mastered), current fill, and a plain "what remains to
advance" line. Competent-stage fills render with a **quiet, satisfying** cue (no
slop, no spam, no constant celebration). A live "Mastered" unlock triggers a
**single, rare, earned grounded co-host vocal** acknowledgment, tone-gated against
the anti-slop blocklist. The surface honors v9.0 accessibility (dual color+shape,
keyboard-nav, no time-pressure). **The UI phase** — final treatment is a Kaan
decision-gate (deferred: "later on when design is done, within this gsd it will be
done"), discharged here with a frontend-enforcement-compliant default + parked
ear/eye pass.

Requirements: **SURF-01 / SURF-02 / SURF-03 / SURF-04**. Rides existing `learn.*`
envelopes on `127.0.0.1:8765` through `IpcRouterBus` (Invariant #4 — no new port,
no new envelope family); any `messages.schema.json` edit requires
`cd tauri/ui && npm run codegen:ipc`.
</domain>

<code_context>
## Existing Code Insights — the surface is ALREADY ~70% built

A sibling non-GSD workstream (the "constellation" star-chart, which independently
converged on **the v11 skill-tree live→UI render as the only DRAW_NOW**) already
shipped the **Earned Wall**:

- **Backend** (`6d87c632`): `skill_tree.skill_wall_payload(progress)` folds
  `SkillTree.compute` into a JSON-safe, manifest-ordered list on the
  `ipc.learn.progress_state` envelope; `progress.py:397` emits `"skills"`/skill_wall;
  `messages.schema.json` extended + `npm run codegen:ipc` done; tests
  `test_progress_snapshot_skill_wall.py` + `test_skill_wall_payload.py`.
- **Frontend** (`aa04e8e8`): `tauri/ui/src/learn/SkillWall.ts` (205L) renders the
  six skills (label · stage · proportional fill bar · cited-proof line for
  Mastered), honest-null empty state, live `mountSkillWall` subscription;
  `styles/skill-wall.css` (gold=Mastered / brand-pink=Competent / muted=Locked);
  mounted in `shell/app.ts:72` (`learn-earned-wall` host); test
  `test_skill_wall.spec.ts`.
- **Live credit call-site** (quick task `260530-3lh`, `6dc07ab3`): `runtime/coach.py`
  `_credit_live_skill_demo` wires `skill_recognizer.recognize` into the event loop —
  a CITED live event advances Mastered; un-cited/fabricated → zero (Inv #2/#3).

**So SURF-01's panel is substantially delivered.** The Earned Wall is by design a
**read-only render** — "nothing enters the co-host voice." That leaves the gaps.

### Gap analysis vs SURF-01..04

| REQ | State | Gap to close in P104 |
|-----|-------|----------------------|
| **SURF-01** panel + stage + fill + **what-remains line** | panel ✓; what-remains ✗ | Add a deterministic, single-source-in-Python `what_remains` string to the payload (schema+codegen), render it. |
| **SURF-02** quiet Competent cue, no vocal/modal | fill animates (`transition: width 200ms`) ✓; **pin test ✗** | Add `skill-tree-quiet-fill.spec.ts` (Competent fill → no `cohost-reaction`, no modal). |
| **SURF-03** rare grounded **Mastered vocal**, fires once, tone-gated | **entirely absent** (wall is voiceless) | New `learn/mastered_vocal.py` (pure fire-once selection) + hand-authored slop-gated fixture + thread a `speak` hook into `_credit_live_skill_demo` on the not-mastered→mastered flip; `test_mastered_vocal_fires_once.py`. |
| **SURF-04** dual color+shape, keyboard-nav, no time-pressure | color+text-label ✓; **shape glyph ✗; only Mastered rows focusable ✗** | Add a per-stage shape glyph; make every row keyboard-focusable (browsable) while only Mastered rows are activatable buttons; `skill-tree-a11y.spec.ts`. |

### Ground truth pinned during discuss

- **Live-creditable skills** (can reach Mastered): `deck_control`, `eq_mixing`,
  `transitions`, `phrasing_performance`, `harmonic_mixing` (via the Judge
  `transition_judged` keystone, `cd645c73`). **Honest-uncreditable in v11.0:**
  `beatmatching` only (`skill_recognizer._HONEST_UNCREDITABLE_V11 = ("beatmatching",)`).
  → `what_remains` must be honest for `beatmatching` at Competent: no false "soon".
- **The slop gate** (`check_no_tutor_slop`) scans `src/vibemix/learn/transcripts/**.json`
  recursively (`test_no_tutor_slop_blocklist.py`). Putting the Mastered vocal copy in
  a fixture there gates it automatically — the v9.0 hand-authored precedent.
- **Co-host speech** is via the LiveKit `AgentSession` (`session.generate_reply` for
  LLM reactions; the ack-bank was retired). The Mastered vocal must NOT be free LLM
  generation (slop risk) → it is a **fixed hand-authored string** spoken via the
  session's fixed-text path (`session.say`-style), routed through the existing
  co-host (no new AI provider — Invariant-respecting).
- **Single-source-in-Python:** stage + what_remains derive in Python
  (`skill_wall_payload`); the frontend never re-derives `COMPETENT_THRESHOLD`/weights
  (no manifest-drift). UI micro-copy (what_remains, glyphs) is affordance labelling,
  not co-host speech — only the spoken Mastered vocal rides the tutor-slop fixture gate.
</code_context>

<decisions>
## Implementation Decisions (default-YES, Kaan ratifies via parked ear/eye pass)

### Claude's Discretion (grey areas resolved default-YES)
1. **Surface = the existing Earned Wall, extended** (not a from-scratch redesign).
   It is frontend-enforcement-compliant and already the ratified DRAW_NOW. Discharges
   `§EARNED-SURFACE-DESIGN-GATE` with a strong default; Kaan ratifies the final
   treatment (parked, NON-BLOCKING).
2. **`what_remains` is computed in Python** and added to the payload (schema edit +
   `npm run codegen:ipc`), staying single-source. Deterministic, factual labels:
   - locked & fill < threshold → "Finish the lessons to reach Competent"
   - locked & fill ≥ threshold (recital is the gate, COMP-02) → "Pass the recital to reach Competent"
   - competent & creditable → "{N − count} more cited live demo(s) to Master"
   - competent & **uncreditable (beatmatching)** → honest non-promise (no "soon")
   - mastered → "" (the cited-proof line carries it)
3. **Mastered vocal copy** = one hand-authored line (per-skill or shared default) in a
   slop-gated JSON fixture under `learn/transcripts/earned/`. Fires exactly once on the
   not-mastered→mastered flip, via a pure selection fn + an injected `speak` hook at
   the credit site. **Final tone parks as `§EARNED-MASTERED-VOCAL-EAR` (BLOCKING ear-pass).**
4. **Dual-cue = color + shape glyph + text label.** Every row keyboard-focusable
   (browsable) with an `aria-label`; only Mastered rows are `role=button` activatable.
   No time-pressure (structural — there is none).
5. **Live-creditability becomes a manifest fact** (`SkillSpec.live_creditable`) with a
   drift pin against `_HONEST_UNCREDITABLE_V11` — keeps the readable manifest the single
   source (SKILL-01/03 spirit) and lets `what_remains` stay honest without importing the
   recognizer into the import-light engine.

### Anti-creep guardrails (locked, encoded)
ZERO new AI provider / ws port / IPC envelope family beyond `learn.*` / heavy dep /
live event detector. NO streaks / leaderboards / social. Single-user local. NEVER
write skill data to `profile.json` (5-field `additionalProperties:false` privacy
contract). All 4 cardinal invariants hold by ADDITIVE design. Honest green: engine
offline-unit-testable; live-app gate for the surface per
`feedback_verify_live_app_not_just_tests`.
</decisions>

<specifics>
## Specific Ideas

- Extend, don't rewrite, `SkillWall.ts` / `skill-wall.css` / `skill_wall_payload`.
- Surgical `--files` commits ONLY — the branch `live-tuning-or-brain` is 439 ahead of
  main with concurrent-session dirt; never `git add -A` (`feedback_concurrent_sessions_one_tree`).
- After `messages.schema.json` edit: `cd tauri/ui && npm run codegen:ipc` (the ajv
  validator is pre-compiled — `feedback_schema_edit_needs_codegen_ipc`).
- Gate: `tests/learn` green (pytest) + `cd tauri/ui && npm run build && npm test` (vitest).
- The one existing-test evolution: `test_skill_wall.spec.ts` non-mastered `tabindex`
  assertion changes (rows become browsable for SURF-04) — a legitimate requirement-driven
  update on the learn island, called out in the SUMMARY.
</specifics>

<deferred>
## Deferred Ideas (parked KAAN-ACTION — never faked)

- 🔴 `§EARNED-MASTERED-VOCAL-EAR` (BLOCKING) — ear-pass on the Mastered unlock vocal:
  real friend earning a moment vs gamification slop. Final tone is Kaan's gate.
- 🔴 `§EARNED-LIVE-MASTERED-VERIFY` (BLOCKING, carried from P103) — real-FLX4 live verify
  that a cited event advances Mastered and an un-cited moment does not.
- 🟡 `§EARNED-SURFACE-DESIGN-GATE` (NON-BLOCKING) — Kaan ratifies the final panel +
  celebration treatment (default ships frontend-enforcement-compliant).
- 🟡 `§EARNED-MASTERY-THRESHOLD-TUNE` (NON-BLOCKING, carried from P103) — per-skill `N`.
</deferred>
