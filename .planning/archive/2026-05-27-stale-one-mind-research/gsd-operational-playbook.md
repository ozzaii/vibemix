# GSD Operational Playbook

> Read-only research artifact. How to open and autonomously run a rich, multi-phase milestone with the GSD ("Get Shit Done") system installed on this machine. Written for the main agent to wield directly.

**Engine root:** `~/.claude/get-shit-done/` (`workflows/`, `references/`, `templates/`, `bin/`)
**CLI/SDK binary:** `/opt/homebrew/bin/gsd-sdk` (Node). Skills live at `~/.claude/skills/gsd-*/SKILL.md`.
**Project planning home:** `/Users/ozai/projects/dj-set-ai/.planning/`
**Current state:** v8.0 "Proof & Polish" SHIPPED (phases 71–76, all complete/archived). `roadmap.analyze` returns an EMPTY phase list because no milestone is active — this is expected; opening a new milestone repopulates it.

---

## 0. The two ways to drive GSD

1. **Skill-driven (in-session, what the main agent normally uses).** Invoke skills with the `Skill` tool: `gsd-new-milestone`, `gsd-autonomous`, `gsd-discuss-phase`, `gsd-plan-phase`, `gsd-execute-phase`, etc. Each skill's `SKILL.md` is a thin wrapper that reads the corresponding `~/.claude/get-shit-done/workflows/<name>.md` and executes it. The workflow markdown is the authoritative behavior spec.
2. **SDK-driven (headless / non-Claude runtimes).** `gsd-sdk run "<prompt>"` (full milestone from a text prompt), `gsd-sdk auto` (full autonomous lifecycle: discover → execute → advance), `gsd-sdk init [@prd.md|"desc"]` (bootstrap a project from a PRD). The skills themselves call `gsd-sdk query <handler>` for all state I/O.

The skills and the SDK share one state substrate (`.planning/`), so you can mix them: open the milestone via the `gsd-new-milestone` skill (interactive, good for the questioning gates), then hand off to the `gsd-autonomous` skill (or `gsd-sdk auto`) to grind phases.

The `gsd-sdk query <handler>` layer is the data plane every workflow uses for reads/writes instead of raw `ls`/`grep`/`sed`. Longest-prefix argv match; dotted (`state.json`) and spaced (`state json`) aliases both work. `--pick <field>` extracts one JSON field. Full handler catalog: `~/.npm/_npx/4db0de1f85c3165e/node_modules/get-shit-done-cc/sdk/src/query/QUERY-HANDLERS.md`.

---

## 1. Milestone lifecycle (end-to-end)

```
new-milestone  → (requirements + roadmap written, STATE reset)
   └─ per phase, in numeric order:
        discuss-phase   → <NN>-CONTEXT.md         (decisions, boundary)
        [ui-phase]      → <NN>-UI-SPEC.md          (frontend phases only)
        plan-phase      → <NN>P<NN>-PLAN.md ...    (one or more, wave-grouped)
        execute-phase   → <NN>P<NN>-SUMMARY.md ... + production commits
        [code-review]   → <NN>-REVIEW.md           (+ auto --fix in autonomous)
        verify (inside execute) → <NN>-VERIFICATION.md  (status: passed|human_needed|gaps_found)
        [ui-review]     → <NN>-UI-REVIEW.md         (frontend, advisory)
   └─ after all phases:
        audit-milestone     → v<X.Y>-MILESTONE-AUDIT.md (status: passed|gaps_found|tech_debt)
        complete-milestone  → archives ROADMAP/phases to .planning/milestones/v<X.Y>-*
        cleanup             → archives stale phase dirs (asks before deleting)
```

| Step | Skill (Skill tool) | Workflow file | Primary artifact written |
|------|--------------------|---------------|--------------------------|
| Open milestone | `gsd-new-milestone` | `new-milestone.md` | PROJECT.md (Current Milestone block), REQUIREMENTS.md, ROADMAP.md, STATE.md (reset) |
| Discuss a phase | `gsd-discuss-phase` | `discuss-phase.md` | `<NN>-CONTEXT.md` |
| UI contract | `gsd-ui-phase` | `ui-phase.md` | `<NN>-UI-SPEC.md` |
| Plan a phase | `gsd-plan-phase` | `plan-phase.md` | `<NN>P<NN>-PLAN.md` (+ `-PLAN-CHECK.md`, `-RESEARCH.md`) |
| Execute a phase | `gsd-execute-phase` | `execute-phase.md` | `<NN>P<NN>-SUMMARY.md` + code commits + `<NN>-VERIFICATION.md` |
| Code review | `gsd-code-review` | `code-review.md` / `code-review-fix.md` | `<NN>-REVIEW.md` |
| Audit milestone | `gsd-audit-milestone` | `audit-milestone.md` | `v<X.Y>-MILESTONE-AUDIT.md` |
| Complete milestone | `gsd-complete-milestone` | `complete-milestone.md` | `.planning/milestones/v<X.Y>-ROADMAP.md` (archive) |
| Cleanup | `gsd-cleanup` | `cleanup.md` | moves old phase dirs to archive |
| Run all phases | `gsd-autonomous` | `autonomous.md` | orchestrates discuss→plan→execute→verify per phase, then lifecycle |

The whole per-phase + lifecycle loop is what `gsd-autonomous` automates. `gsd-new-milestone` is NOT part of `gsd-autonomous` — you open the milestone first, then run autonomous.

---

## 2. `gsd-new-milestone` specifics

Workflow: `~/.claude/get-shit-done/workflows/new-milestone.md`. Spawns subagents `gsd-project-researcher` (×4), `gsd-research-synthesizer`, `gsd-roadmapper`.

**Step sequence:**
1. **Load context** — parse `$ARGUMENTS` (`--reset-phase-numbers` flag opts into restarting phase numbering at 1; default CONTINUES numbering, e.g. v8.0 ended at 76 → next milestone starts at 77). Remaining text = milestone name. Reads PROJECT.md, MILESTONES.md, STATE.md, optional `MILESTONE-CONTEXT.md`.
2. **Gather goals** — from MILESTONE-CONTEXT.md if present, else asks "What do you want to build next?" (inline freeform), then probes with AskUserQuestion.
2.5. **Scan seeds** — `ls .planning/seeds/SEED-*.md`; matching seeds become requirement input. (None present here.)
3. **Determine version** — parses last version, suggests next (vX.Y → vX.(Y+1) or v(X+1).0).
3.5. **Confirm understanding** — presents milestone summary, AskUserQuestion "Looks good / Adjust" gate.
4. **Update PROJECT.md** — adds `## Current Milestone: vX.Y [Name]` (Goal + Target features) and ensures `## Evolution` section.
5. **Reset STATE.md** — `gsd-sdk query state.milestone-switch --milestone "vX.Y" --name "[Name]"` (writes frontmatter + body atomically; preserves accumulated context; do NOT hand-edit — bug #2630).
6. **Cleanup + commit** — deletes consumed MILESTONE-CONTEXT.md; `gsd-sdk query phases.clear --confirm`; commits PROJECT.md + STATE.md via `gsd-sdk query commit "..." --files ...`.
7. **Load init JSON** — `INIT=$(gsd-sdk query init.new-milestone)`. Returns: `researcher_model`, `synthesizer_model`, `roadmapper_model`, `research_enabled`, `current_milestone`, `phase_dir_count`, `phase_archive_path`, `agents_installed`, `missing_agents`, `project_title`, etc.
7.5. **Reset-phase safety** — only when `--reset-phase-numbers`: archive old phase dirs before roadmapping so `01-*` can't collide.
8. **Research decision** — AskUserQuestion "Research first / Skip". If research: `mkdir -p .planning/research`, spawn 4 parallel `gsd-project-researcher` agents (Stack/Features/Architecture/Pitfalls) writing `STACK.md`/`FEATURES.md`/`ARCHITECTURE.md`/`PITFALLS.md`, then `gsd-research-synthesizer` writes `SUMMARY.md`. **This is the step to short-circuit when you have pre-written research (see §5).**
9. **Define requirements** — reads PROJECT.md + (if present) `FEATURES.md`; scopes features per category via AskUserQuestion (multiSelect); writes **REQUIREMENTS.md** with REQ-IDs (`[CATEGORY]-[NN]`, continuing numbering), v1/future/out-of-scope/traceability sections. Commits.
10. **Create roadmap** — spawns `gsd-roadmapper` which reads PROJECT.md + REQUIREMENTS.md + `research/SUMMARY.md` (if exists) + config.json + MILESTONES.md, then derives phases (every REQ mapped to exactly one phase, 2–5 observable success criteria each, 100% coverage), and writes **ROADMAP.md + STATE.md + REQUIREMENTS.md traceability** directly. AskUserQuestion "Approve / Adjust / Review" gate; commits on approval.
10.5. **Link todos** — tags matching pending todos with `resolves_phase: N`.
11. **Done** — prints artifact map + next step (`/gsd:discuss-phase N` or `/gsd:plan-phase N`).

**Driving it in AUTONOMOUS / no-block mode:**
- The workflow has AskUserQuestion gates at 2, 3.5, 8, 9, 10. There is no first-class `--auto` flag for `new-milestone` itself (it expects a human at the questioning gates), so the cleanest fully-autonomous open is one of:
  - **Pre-seed `MILESTONE-CONTEXT.md`** (from `gsd-discuss-milestone`/`gsd-explore`) so step 2 consumes scope without asking, then answer the remaining confirm gates with the recommended option.
  - **Seed REQUIREMENTS.md + ROADMAP.md directly** (see §5) and skip new-milestone almost entirely — only run steps 4–6 (PROJECT.md + STATE reset) manually via the SDK, then go straight to `gsd-autonomous`.
  - **`gsd-sdk run "<milestone prompt>"`** — headless full-milestone driver that does requirements→roadmap→execute from a single prompt (good for non-interactive runtimes; uses `text_mode` instead of AskUserQuestion).
- Per `gsd-autonomous fully` mode in this repo: answer grey-area gates with the recommended option, never pause; defer true blockers to a `KAAN-ACTION-*.md` surface rather than stopping. Only the privacy rule + destructive risk + legal-capacity carveouts (Apple Dev / SignPath) pause.
- `text_mode` (config `workflow.text_mode: true` or `--text`) replaces every AskUserQuestion with a numbered plain-text list — the mechanism for non-Claude runtimes.

---

## 3. `gsd-autonomous` specifics

Workflow: `~/.claude/get-shit-done/workflows/autonomous.md`. Requires ROADMAP.md + STATE.md to exist (errors otherwise — "run new-milestone first").

**Flags** (parsed from `$ARGUMENTS`):
- `--from N` — start at phase N (skip < N).
- `--to N` — stop after phase N (skip > N); compatible with `--from`.
- `--only N` — run exactly phase N; skips the milestone lifecycle (no audit/complete/cleanup).
- `--interactive` — discuss runs INLINE (asks questions, waits), while plan + execute dispatch as **background agents**; enables pipeline parallelism (discuss phase N+1 while phase N builds). Default (non-interactive) runs everything inline with **smart discuss** (auto-answered grey-area tables).

**Phase discovery:**
1. `INIT=$(gsd-sdk query init.milestone-op)` → `milestone_version`, `milestone_name`, `phase_count`, `completed_phases`, `roadmap_exists`, `state_exists`.
2. `ROADMAP=$(gsd-sdk query roadmap.analyze)` → `phases[]` array. Keep phases where `disk_status !== "complete"` OR `roadmap_complete === false`. Apply `--from`/`--to`/`--only` numeric filters. Sort ascending (handles decimals like 5.1).
3. Per phase: `gsd-sdk query roadmap.get-phase N` → `phase_name`, `goal`, `success_criteria`.

**Per-phase run (step 3 in workflow):**
- **3a Smart discuss** — `gsd-sdk query init.phase-op N` → `has_context`. If true, skip. If `workflow.skip_discuss=true`, write a minimal CONTEXT.md from the ROADMAP goal. Else run smart-discuss (reference: `references/autonomous-smart-discuss.md`) — proposes grey-area answers in batch tables, single-pass, never loops. `--interactive` runs the real `gsd-discuss-phase` skill inline instead.
- **3a.5 UI contract** — if frontend indicators in the phase AND no UI-SPEC AND `workflow.ui_phase != false`: `Skill(gsd-ui-phase, N)`.
- **3b Plan** — `Skill(gsd-plan-phase, N)` (or background Agent in `--interactive`). Verify `has_plans` via `init.phase-op`.
- **3c Execute** — `Skill(gsd-execute-phase, "N --no-transition")` (autonomous manages transitions itself). Background Agent in `--interactive`.
- **3c.5 Code review** — if `workflow.code_review != false`: `Skill(gsd-code-review, N)`; if findings, auto `Skill(gsd-code-review, "N --fix --auto")`. (Autonomous CHAINS the fix; plain execute only suggests it.)
- **3d Post-execution routing** — read `<NN>-VERIFICATION.md` `status`:
  - `passed` → continue.
  - `human_needed` → AskUserQuestion validate-now / continue (in fully mode, log to KAAN-ACTION and continue).
  - `gaps_found` → offer gap closure (`gsd-plan-phase N --gaps` then re-execute, **limited to 1 retry**), continue, or stop.
  - empty/missing → `handle_blocker`.
- **3d.5 UI review** — if UI-SPEC exists AND `workflow.ui_review != false`: `Skill(gsd-ui-review, N)` (advisory, non-blocking).

**Iterate (step 4):** after each phase, RE-READ `roadmap.analyze` (catches phases inserted mid-run as decimals) + `cat STATE.md` (checks `## Blockers/Concerns`). Loop to next incomplete phase.

**Lifecycle (step 5):** after all phases — `gsd-audit-milestone` → route on `passed`/`gaps_found`/`tech_debt` → `gsd-complete-milestone vX.Y` → `gsd-cleanup`. Skipped entirely when `--only`/partial `--to`.

**Blockers vs pauses (step 6 `handle_blocker`):** any step failure or STATE blocker presents AskUserQuestion: **Fix and retry / Skip this phase / Stop autonomous mode**. Stop prints a resume command (`/gsd:autonomous --from <next>`). In `fully` mode, prefer recommended option + defer; genuine external blockers route to KAAN-ACTION, don't halt.

**Sub-agents/waves:** autonomous delegates plan + execute to the same machinery `gsd-plan-phase`/`gsd-execute-phase` use. Execute-phase itself spawns `gsd-executor` agents per wave (parallel within a wave when `parallelization: true` + `use_worktrees`). `--interactive` adds an outer layer of background agents for plan/execute so the main context stays lean.

---

## 4. Phase & requirements model

- **REQ-IDs:** `[CATEGORY]-[NUMBER]` (e.g. `LOG-01`, `SIM-03`, `DESIGN-04`). Live in REQUIREMENTS.md grouped by category; v1 = checkboxes, future/out-of-scope tracked separately. Numbering CONTINUES across milestones.
- **Traceability:** REQUIREMENTS.md has a `## Traceability` table (`Requirement | Phase | Status`). The roadmapper maps **every** REQ to **exactly one** phase (100% coverage; unmapped = roadmap gap). ROADMAP phase headers list `**Requirements**: [LOG-01, LOG-03]`. Plans carry `requirements: [GH-04]` in frontmatter. `gsd-sdk query requirements.extract-from-plans N` dedupes them.
- **Phase numbering:** integers (71, 72, …) for planned work; decimals (72.1) for urgent INSERTED phases (added via `gsd-phase`/`insert-phase`, appear between integers in numeric order). New milestone continues from last phase number unless `--reset-phase-numbers`.
- **Phase dir:** `.planning/phases/<NN>-<slug>/`. Artifacts (observed in real phases): `<NN>-CONTEXT.md`, `<NN>-RESEARCH.md`, `<NN>-UI-SPEC.md` (frontend), `<NN>P<NN>-PLAN.md` (one per plan; older phases use `<NN>-<plan>-PLAN.md`), `<NN>P<NN>-SUMMARY.md`, `<NN>-PLAN-CHECK.md`/`-PLAN-INDEX.md`, `<NN>-REVIEW.md`, `<NN>-VERIFICATION.md`, `<NN>-UI-REVIEW.md`.
- **Plans within a phase = waves.** PLAN.md frontmatter carries `wave: 0|1|2…`, `depends_on: [...]`, `files_modified: [...]`, `autonomous: true`, `requirements:`, and a structured `must_haves:` block (`truths`, `artifacts` with `path/provides/contains`, `key_links`). Execute groups plans by wave; within a wave, plans run in PARALLEL when `parallelization: true` (else sequential); waves run in sequence. Later-wave plans `@`-include earlier-wave SUMMARY.md files. Wave safety: a higher wave never runs while a prerequisite lower-wave plan is incomplete.
- **Commit discipline:** atomic per-plan commits (`gsd-sdk query commit "..." --files ...`); planning-doc commits are separate from code commits. Each plan creates its SUMMARY.md on completion. The phase manifest of commits backs `gsd-undo`. MVP+TDD gate can require a RED commit before each implementation step. Verification reads the diff (e.g. `git diff --stat HEAD -- src/...`) to enforce "zero-touch" constraints.
- **Success criteria:** 2–5 observable behaviors per phase in ROADMAP → flow into plan `must_haves.truths` → verified by the verifier into VERIFICATION.md per-SC verdict table.

---

## 5. Manipulating GSD to consume pre-written research and run a custom 6–10 phase vision

We already have research under `.planning/research/`: `oss-launch-2026-05-25/SUMMARY.md`,
`clap-spike-2026-05-25/` (spike data), and archived historical Viber direction
reports under `.planning/archive/2026-05-27-stale-viber-direction-research/`.
Goal: make new-milestone CONSUME current summaries instead of re-running the
4-researcher spawn, then hand to autonomous.

**The key seam:** the roadmapper (step 10) reads `.planning/research/SUMMARY.md`. The 4-researcher spawn (step 8) exists ONLY to produce that SUMMARY.md (+ STACK/FEATURES/ARCHITECTURE/PITFALLS). So:

**Option A — Skip research, point at existing SUMMARY (lightest):**
1. At step 8's research gate, choose **"Skip research for this milestone."**
2. Ensure `.planning/research/SUMMARY.md` reflects the new vision. Either keep the canonical `research/SUMMARY.md` current, or synthesize a fresh `SUMMARY.md` from the current report dirs first. The old Viber direction reports are archived; use them only for historical context. The roadmapper will read whatever `SUMMARY.md` is at `.planning/research/SUMMARY.md`.
3. Optionally place a `FEATURES.md` at `.planning/research/FEATURES.md` so step 9 auto-presents feature categories (it explicitly reads `FEATURES.md` if it exists). Without it, step 9 gathers requirements conversationally.

**Option B — Seed REQUIREMENTS.md + ROADMAP.md directly, skip most of new-milestone (most control, most "manipulation"):**
1. Run only new-milestone steps 4–6 by hand via SDK: update PROJECT.md Current Milestone block, then `gsd-sdk query state.milestone-switch --milestone "vX.Y" --name "..."`, then `gsd-sdk query phases.clear --confirm`, then commit.
2. Hand-write `.planning/REQUIREMENTS.md` against the requirements template (`~/.claude/get-shit-done/templates/requirements.md`): categories + REQ-IDs continuing from the last used ID, v1 checkboxes, out-of-scope, and a Traceability table.
3. Hand-write `.planning/ROADMAP.md` against the roadmap template (`templates/roadmap.md`): the milestone-grouped form (collapse prior milestones in `<details>`), 6–10 phase headers each with `**Goal**`, `**Depends on**`, `**Requirements**: [IDs]`, `**Success Criteria**` (2–5), and a `Plans:` checklist + Progress table. Map every REQ to exactly one phase. Cite the pre-written research inline in goals so plan-phase `@`-includes the right report files.
4. Verify the SDK can parse it: `gsd-sdk query roadmap.analyze` (phases populate), `gsd-sdk query roadmap.get-phase <first>` (goal+SCs resolve), `gsd-sdk query validate.consistency`, `gsd-sdk query check.completion milestone vX.Y`.
5. Commit, then run `gsd-autonomous` (or `--from <first> --to <last>`). With `workflow.skip_discuss=true` (config), autonomous turns each ROADMAP goal directly into a minimal CONTEXT.md and goes straight to planning — the leanest fully-autonomous grind. To force plan-phase to ground in pre-written reports, reference the current report files in each phase's ROADMAP goal/SC text and/or in the seeded CONTEXT.md.

**Important:** even in Option B, plan-phase still runs its own per-phase RESEARCH step (config `workflow.research: true`) unless you set it off. The pre-written reports are best surfaced by (a) keeping `research/SUMMARY.md` authoritative for the roadmapper and (b) naming the relevant report files in each phase's CONTEXT/goal so the planner reads them as context rather than re-researching.

---

## 6. Gotchas (things that break or surprise an autonomous run)

- **`roadmap.analyze` returns empty when no milestone is active** (current state — v8.0 archived). `gsd-autonomous` will say "All phases complete / nothing to do" until `gsd-new-milestone` (or a hand-seeded ROADMAP) repopulates it. This is the #1 confusion: green/empty ≠ ready.
- **STATE.md frontmatter is load-bearing.** Every downstream reader (`state.json`, progress bars, `init.milestone-op`) keys off the YAML frontmatter `milestone`/`status`/`progress`. Reset it ONLY via `gsd-sdk query state.milestone-switch` — hand-editing the body while leaving frontmatter stale reproduces bug #2630 (stale milestone reported everywhere). If a `protect-files.sh` PreToolUse hook is active, raw Edit/Write of STATE.md is blocked — use SDK handlers (`state.update`, `state.add-roadmap-evolution`).
- **ROADMAP.md must be SDK-parseable.** Phase headers need `### Phase N: Name`, `**Goal**`, `**Success Criteria**`, `**Requirements**`. The milestone-grouped form must keep the ACTIVE milestone's phases OUTSIDE `<details>` (collapsed `<details>` = treated as shipped/complete). Decimal phases must sort numerically. Verify with `roadmap.analyze` + `roadmap.get-phase` before launching autonomous.
- **Every REQ maps to exactly one phase or the roadmapper blocks** (`## ROADMAP BLOCKED`). Unmapped REQ = coverage gap; duplicated REQ across phases = ambiguity.
- **`--only` skips the lifecycle** (no audit/complete/cleanup) — do a final flagless `gsd-autonomous` pass to close the milestone.
- **`--to N` skips lifecycle** when not all milestone phases are done — partial completion is intentional, milestone stays open.
- **Discuss is single-pass in autonomous mode.** Once `has_context` is true it will NOT re-discuss, even if the CONTEXT looks thin. Get discuss right the first pass (or pre-seed CONTEXT.md).
- **Gap closure is capped at 1 automatic retry** to avoid infinite loops; persistent `gaps_found` forces a user decision (continue / stop).
- **`agents_installed: false` degrades silently** — new-milestone falls back to inline roadmap generation (no parallel researchers). Check `init.new-milestone` `agents_installed`/`missing_agents`. Here it's `true`.
- **Worktree isolation + parallel waves:** `config.workflow.use_worktrees` is currently `false`, so executor agents run sequentially on the main tree even within a wave. Parallel waves require `use_worktrees: true` AND `parallelization: true`; plans touching submodule paths drop isolation per-plan.
- **`commit --files` re-stages whole files by default** (use `--respect-staged` to commit only already-staged hunks within the pathspec). Surprising when you have unrelated unstaged edits.
- **Config gates change behavior.** This project: `model_profile: quality` (all agents Opus), `ui_phase`/`ui_review`/`code_review`/`plan_check`/`verifier`/`nyquist_validation` all ON, `mode: yolo`, `granularity: fine`, `auto_advance: true`, `research: true`, `skip_discuss: false`. To make autonomous leaner, flip `skip_discuss: true` and/or `research: false` via `gsd-config`/`gsd-settings` — but `research: true` is a persistent preference; new-milestone explicitly will NOT persist a per-milestone "skip" choice (only `/gsd:settings` changes the default).
- **`new-milestone` has no `--auto` flag.** It expects a human at AskUserQuestion gates. For no-block: pre-seed MILESTONE-CONTEXT.md or REQUIREMENTS+ROADMAP (§5), use `text_mode`, or use `gsd-sdk run`.
- **`gsd-autonomous fully` (this repo's mode) is a project convention, not a CLI flag.** It means: answer grey areas with the recommended option, defer blockers to KAAN-ACTION surfaces instead of pausing; only privacy/destructive/legal carveouts pause. The mechanical flags are still `--from/--to/--only/--interactive`.
- **CLI-only SDK commands:** `graphify` and `from-gsd2` have no native query handler — they shell out to `gsd-tools.cjs`. Don't rely on them in `strictSdk` contexts.

---

## Reference index (read these for depth)

- Milestone open: `~/.claude/get-shit-done/workflows/new-milestone.md`
- Autonomous: `~/.claude/get-shit-done/workflows/autonomous.md` + `references/autonomous-smart-discuss.md`
- Per-phase: `workflows/discuss-phase.md`, `plan-phase.md` (81k — the planning bible), `execute-phase.md` (87k), `verify-phase.md`, `ui-phase.md`
- Lifecycle: `audit-milestone.md`, `complete-milestone.md`, `cleanup.md`, `transition.md`
- Templates: `templates/{requirements,roadmap,project,state,context,summary,phase-prompt}.md`
- SDK handler catalog: `~/.npm/_npx/4db0de1f85c3165e/node_modules/get-shit-done-cc/sdk/src/query/QUERY-HANDLERS.md`
- Questioning style: `references/questioning.md`; brand/UI: `references/ui-brand.md`
- Real-phase exemplars in this repo: `.planning/phases/70-github-sexified-generated-tested/` (full CONTEXT/UI-SPEC/PLAN/SUMMARY/VERIFICATION/REVIEW set), `67-all-tests-pass/` (5-wave plan set).
```
