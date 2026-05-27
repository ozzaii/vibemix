# Phase 37 — Research

**Date:** 2026-05-15
**Mode:** gsd-autonomous fully

This phase is INTEGRATION audit, not feature work. Research is light — the surface to extend already exists.

## Existing audit infrastructure

| Surface | Path | Source phase |
|---------|------|--------------|
| Audit script skeleton | `scripts/integration_audit.py` | v2.0 Phase 26 (shipped) |
| Concerns/orphan inventory | `.planning/codebase/CONCERNS.md` | maintained across milestones |
| POC immutability gate | `tests/repo/test_g5_poc_files_untouched.py` | v2.0 (shipped) |
| Per-phase Kaan-action surfaces | `KAAN-ACTION-LEGAL.md` (root) + `*/KAAN-ACTION-*.md` (phase dirs) | every phase that defers |
| v2.0 milestone audit (reference) | `.planning/milestones/v2.0-MILESTONE-AUDIT.md` (archive) | v2.0 close |

## 5 critical seams — surface anchors

| # | Seam | Source surface | Sink surface |
|---|------|----------------|--------------|
| 1 | P18 → P20 | `src/vibemix/evidence/registry.py` (EvidenceRegistry) | `src/vibemix/agent/citation_linter.py` (live-mode enforce gate) |
| 2 | P19 → agent | `src/vibemix/agent/gemini_context_cache.py` (cached content) | `src/vibemix/agent/dj_cohost_agent.py` (per-turn run) |
| 3 | P25 → P28 | `src/vibemix/library/pyrekordbox_xml.py` (parser) | `src/vibemix/library/library_intel.py` (register_library final-mile — P48) |
| 4 | P27 → eval-gate | `scripts/eval/replay_harness.py` (2-judge cross-check) | `.github/workflows/eval.yml` (CI gate) |
| 5 | P31 → ws_bus | `tauri/ui/src/mascot/priority-stack.ts` (4-layer) | `src/vibemix/ws_bus.py` (IPC frame format) |

Seam test under `tests/e2e/test_seam_<source>__<sink>.py`. Each must call REAL surfaces (no mocking the seam — only mock external IO like Gemini API + signing keys).

## v2.1-MILESTONE-AUDIT.md template

Sections (fixed order):

1. **Summary** — total seams, verdict counts (WIRED / PARTIAL / MISSING), pass/fail.
2. **Per-Seam Verdicts** — table: seam, source `file:line`, sink `file:line`, test result, verdict.
3. **Orphan Inventory** — table: symbol, file, last touched phase, hypothesis (orphan / used-internally / planned).
4. **Kaan-Action Roll-Up** — table: ID, type (legal-capacity / proxy / deferred), owner, blocking?, target phase.
5. **Grey-Area Decisions** — table: phase, decision, rationale, reversible?.
6. **POC Files Untouched** — git diff verdict against v2.0 baseline allowlist.
7. **Conclusion** — pass / partial / fail + next-step recommendation.

## CI workflow

`.github/workflows/orphan-inventory.yml`:
- Runs `python scripts/integration_audit.py --orphan-inventory --diff`.
- Diffs current scan against committed `.planning/codebase/CONCERNS.md`.
- Fails on new orphans not in inventory.

## P87 grey-area decision capture

Walk every phase SUMMARY.md + VERIFICATION.md for markers like:
- `recommended:` / `proposed:` / `accepted per gsd-autonomous fully`
- `deferred:` (per autonomous mode rules)

Aggregate. Each entry needs `phase`, `decision`, `rationale`, `reversible` columns.

## Plan slice (preview for 37-PLAN.md)

6 plans:
1. `37-01` — 5 seam e2e tests (AUDIT-01)
2. `37-02` — `integration_audit.py` extension + `v2.1-MILESTONE-AUDIT.md` template + writer (AUDIT-02, AUDIT-07)
3. `37-03` — Orphan inventory CI gate (AUDIT-03)
4. `37-04` — Kaan-action roll-up generator (AUDIT-04)
5. `37-05` — Grey-Area Decisions log generator (AUDIT-05)
6. `37-06` — POC files allowlist refresh (AUDIT-06)
