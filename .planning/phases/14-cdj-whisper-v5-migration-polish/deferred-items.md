# Phase 14 — Deferred Items

Issues discovered during execution that are out-of-scope for the current task. Wave 5 (Plan 14-06) or a phase-close pass should address them.

## DEF-14-01: REQUIREMENTS.md POLISH-04 still references "Geist + Fraunces"

**Discovered:** Task 14-01-03 (typeface reconciliation)

**Issue:** `.planning/REQUIREMENTS.md` POLISH-04 row + traceability table both still read `Geist for chrome + Fraunces for headlines` and `Geist + Fraunces only`. The plan explicitly scoped REQUIREMENTS edits OUT of Task 14-01-03 ("Do NOT alter REQUIREMENTS.md POLISH-04"). Verified by grep:

```
.planning/REQUIREMENTS.md — line 1: POLISH-04 row contains "Geist for chrome + Fraunces for headlines"
.planning/REQUIREMENTS.md — line 2: traceability row contains "Geist + Fraunces only"
```

**Why deferred:** Plan author's instruction was explicit; out-of-task-scope per task_commit_protocol (only fix issues directly caused by current task's changes). The stale REQUIREMENTS text doesn't block any Wave 1-5 gate (those gates check fonts, not doc text), so it's not a Wave-0 blocker.

**Risk if left:** Pitfall 6 propagation — a future agent reading POLISH-04 will follow stale guidance ("Geist + Fraunces") and waste a critique-loop cycle. Rule-2-adjacent: the reconciliation is incomplete until BOTH doc surfaces (ROADMAP + REQUIREMENTS) agree.

**Recommended fix in Wave 5 (Plan 14-06):** Same surgical text edit pattern Task 14-01-03 applied to ROADMAP — swap `Geist for chrome + Fraunces for headlines` → `Saira variable wdth + wght axes for chrome + JetBrains Mono for numerics` and `Geist + Fraunces only` → `Saira + JetBrains Mono only`. Two-line edit, zero risk.
