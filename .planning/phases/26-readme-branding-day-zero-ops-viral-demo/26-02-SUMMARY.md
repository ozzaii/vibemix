---
phase: 26
plan: "02"
subsystem: docs / community
tags: [issue-templates, contributing, anti-slop, ai-misbehavior, dco]
requires: []
provides: [ai_misbehavior issue template, CONTRIBUTING sniff tool invocation, CONTRIBUTING AI-misbehavior reporting section]
affects: [GitHub community triage workflow]
tech_stack_added: []
tech_stack_patterns: [GitHub issue forms YAML]
key_files_created:
  - .github/ISSUE_TEMPLATE/ai_misbehavior.yml
key_files_modified:
  - CONTRIBUTING.md
decisions:
  - "ai_misbehavior.yml is the dedicated channel for hallucination / generic-AI-slop / late-reaction / wrong-vocabulary reports. The two highest-leverage fields are 'what did the AI say?' and 'what actually happened?' — that pair is the grounding-chain replay key."
  - "Labels ai-quality + triage (not bug + triage) so AI quality issues route to a separate review queue."
  - "CONTRIBUTING surfaces the sniff_controller.py invocation literally — copy-paste-ready — instead of leaving it implicit."
metrics:
  duration_minutes: ~10
  completed_date: "2026-05-14"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 26 Plan 02: ai_misbehavior Issue Template + CONTRIBUTING Refinement

One-liner: **New `.github/ISSUE_TEMPLATE/ai_misbehavior.yml` opens the dedicated AI-quality report channel; CONTRIBUTING.md gains the literal sniff_controller.py invocation + a new "Reporting AI misbehavior" section.**

## What Was Done

### Task 1 — ai_misbehavior issue template

Created `.github/ISSUE_TEMPLATE/ai_misbehavior.yml`:

- Title prefix `[ai-slop]`, labels `["ai-quality", "triage"]`
- Markdown intro frames anti-slop as the central product thesis and this template as the fastest path to a fix
- Required inputs: vibemix version, OS, skill level (Beginner/Intermediate/Pro), mode (Hype-man/Coach)
- Required textareas: "what did the AI say?" + "what actually happened?" (the grounding-chain replay pair)
- Required dropdown: misbehavior class (Hallucinated event / Late reaction / Generic AI slop / Repeated itself / Wrong vocabulary for skill level / Talked over mic / Other)
- Optional: events.jsonl excerpt (rendered as jsonl), track context (genre + BPM helps debug unusual musical context), free-form extras

YAML validated with `python3 -c "import yaml; yaml.safe_load(open('.github/ISSUE_TEMPLATE/ai_misbehavior.yml'))"` — exits 0.

### Task 2 — CONTRIBUTING refinement

Edited `CONTRIBUTING.md` in three places:

1. Above the bug-fix path: callout directing AI-slop / hallucination reports to the new ai_misbehavior template instead of a generic bug report.
2. Inside the "New controller mapping" path: added a literal `python3 scripts/sniff_controller.py --device "Your Controller Name"` invocation example with a one-line note about the JSON output shape and how it feeds into the profile file.
3. New top-level "Reporting AI misbehavior" section between "What we don't accept" and "License", explaining why this channel matters more than feature requests (anti-slop = central thesis), naming the two highest-leverage fields, and tagging it P0 in triage.

DCO sign-off section unchanged. Section count: 6 → 7.

## Deviations from Plan

None. Plan executed exactly as written.

## Verification

- `[ -f .github/ISSUE_TEMPLATE/ai_misbehavior.yml ]` exits 0 ✅
- YAML parses without error ✅
- `grep "ai-quality" .github/ISSUE_TEMPLATE/ai_misbehavior.yml` returns hit ✅
- `grep "sniff_controller.py" CONTRIBUTING.md` returns hit ✅
- `grep -ci "ai misbehavior\|hallucin" CONTRIBUTING.md` returns 5 ✅
- `grep -c "^## " CONTRIBUTING.md` returns 7 (was 6 before) ✅
- DCO section intact ✅
- No regression: `pytest -q` baseline unchanged

## Commits

- `a43f95f` — feat(26-02): ai_misbehavior issue template + CONTRIBUTING refinement

## Self-Check: PASSED
