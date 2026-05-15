# Phase 37: Cross-Phase Integration Audit Gate - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning (Phase 33 in flight; Phase 37 plans need all v2.1 phases shipped before final e2e seam pass)
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

Penultimate gate — every cross-phase seam is end-to-end verified + fresh-VM smoke-tested + zero orphan-but-shipped surfaces remain + every grey-area autonomous decision is logged.

**Mapped REQ-IDs (7):** AUDIT-01 (≥ 5 seam e2e tests), AUDIT-02 (`scripts/integration_audit.py` produces `v2.1-MILESTONE-AUDIT.md`), AUDIT-03 (orphan inventory current + CI gate), AUDIT-04 (Kaan-action surface roll-up = only legal-capacity), AUDIT-05 (grey-area decision log — P87), AUDIT-06 (POC files untouched verified ONCE MORE), AUDIT-07 (`v2.1-MILESTONE-AUDIT.md` includes Grey-Area Decisions section).

**In scope (autonomous):**
- 5 e2e seam tests: P18→P20 (evidence→linter), P19→agent (cached content → DJCoHostAgent), P25→P28 (pyrekordbox XML → library intel), P27→eval-gate (replay harness → eval workflow), P31→ws_bus (4-layer mascot → IPC).
- Extend v2.0's `gsd-integration-checker` to `scripts/integration_audit.py` — emits `v2.1-MILESTONE-AUDIT.md` with WIRED / PARTIAL / MISSING verdicts per seam, anchored to real source lines.
- `.planning/codebase/CONCERNS.md` orphan inventory refresh + CI gate that fails on any new orphaned-but-shipped surface.
- Kaan-action surface roll-up — walk `KAAN-ACTION-LEGAL.md` + every phase's `KAAN-ACTION-PROXY.md` and assert only the 2 legal-capacity items (Apple Dev Agreement, SignPath OSS) remain; everything else autonomously discharged.
- Grey-Area Decisions section in audit — every `gsd-autonomous fully` recommended answer logged with rationale (P87).
- `test_g5_poc_files_untouched.py` v2.1 modified-files allowlist refresh.

**Out of scope (autonomous; deferred to Kaan-action):**
- ACTUAL fresh-VM smoke run (Phase 33 INSTALL-08 dep + macOS license).
- ACTUAL signed-binary verification on fresh VM (Phase 38 secrets dep).

**Pure out of scope:**
- Linux smoke (Linux excluded).
- Bravoh proxy load test (Phase 36 already shipped).
- Re-running unit tests for every phase (each phase has its own gate).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 37 verbatim
- REQUIREMENTS.md AUDIT-01..07
- Pitfalls P48 (register_library final-mile), P66 (false-confidence seam), P87 (grey-area drift)
- v2.0 Phase 26 day-zero scaffold + Phase 21 CI (shipped)
- Memory `feedback_autonomous_no_grey_area_pause`

### 5 critical seams (AUDIT-01)
1. **P18 → P20:** EvidenceRegistry citation grammar → citation linter enforce gate.
2. **P19 → agent:** GeminiContextCache cached content → DJCoHostAgent.run() per-turn.
3. **P25 → P28:** pyrekordbox XML output → library intelligence (`register_library` final-mile).
4. **P27 → eval-gate:** replay harness corpus + 2-judge cross-check → eval.yml CI gate.
5. **P31 → ws_bus:** 4-layer mascot priority-stack → ws_bus IPC frame format.

Each test must call the real surface (no mocking the seam itself), assert the integration contract, and live under `tests/e2e/test_seam_*.py`.

### Integration audit script (AUDIT-02)
- Extends v2.0 `scripts/integration_audit.py` (already shipped).
- For each seam, emit verdict + source line `file:line` + per-test pass/fail.
- Writes `.planning/v2.1-MILESTONE-AUDIT.md` with sections: Summary, Per-Seam Verdicts, Orphan Inventory, Kaan-Action Roll-Up, Grey-Area Decisions.

### Orphan inventory + CI gate (AUDIT-03)
- Read `.planning/codebase/CONCERNS.md`'s orphan section.
- Scan repo for newly-shipped symbols (post-v2.0) that have no test + no production caller — emit as candidates.
- CI: `.github/workflows/orphan-inventory.yml` runs the scan + diff'd against committed inventory; fails on new entries.

### Kaan-action roll-up (AUDIT-04)
- Walk every phase dir under `.planning/phases/` + repo root for `KAAN-ACTION-*.md`.
- Aggregate items into a single roll-up table in `v2.1-MILESTONE-AUDIT.md`.
- Assert ONLY two legal-capacity items remain (Apple + SignPath).
- Fail if any non-legal-capacity Kaan-action surface persists (would mean autonomous skipped work it shouldn't).

### Grey-Area Decisions log (AUDIT-05 / AUDIT-07 / P87)
- Walk all phase SUMMARY + VERIFICATION files for "recommended answer" markers.
- Aggregate into `Grey-Area Decisions` section of `v2.1-MILESTONE-AUDIT.md`.
- Per entry: phase, decision, rationale, reversible?.
- P87 satisfied if every grey-area decision has rationale + reversible flag.

### POC files untouched (AUDIT-06)
- Extend `tests/repo/test_g5_poc_files_untouched.py` with v2.1 modified-files allowlist.
- Allowlist = explicit list of v2.1 paths permitted to differ from v2.0 baseline.
- Allowlist NEVER contains `cohost*.py`, `mascot.html`.

### Plan slice
6 plans, mapping 1:1 to AUDIT-01..06 (AUDIT-07 is a section within AUDIT-02 output):
1. `37-01` — 5 seam e2e tests (AUDIT-01)
2. `37-02` — `integration_audit.py` extension + `v2.1-MILESTONE-AUDIT.md` template (AUDIT-02, AUDIT-07)
3. `37-03` — Orphan inventory CI gate (AUDIT-03)
4. `37-04` — Kaan-action roll-up (AUDIT-04)
5. `37-05` — Grey-Area Decisions log (AUDIT-05)
6. `37-06` — POC files allowlist refresh (AUDIT-06)

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 26 (shipped)** — day-zero scaffold including `scripts/integration_audit.py` skeleton.
- **`.planning/codebase/CONCERNS.md`** — existing orphan inventory + concerns log.
- **`tests/repo/test_g5_poc_files_untouched.py`** — existing POC immutability gate (v2.0).
- **Phase 33** (in flight) — INSTALL-08 fresh-VM scaffold (real VM = Kaan-action).
- **Memory `project_v2_open_candidates`** — confirmed v2.1 deliverables list (no surprises here).

</code_context>

<specifics>
## Specific Ideas

- **No re-running of per-phase unit suites** — each phase has its own gate; 37 is INTEGRATION only.
- **Seam tests call real surfaces** — no mocking the seam under test. Mocking external IO is fine (Gemini, signing keys).
- **`v2.1-MILESTONE-AUDIT.md` is the artifact** — Phase 37's primary deliverable. Sections fixed.
- **Grey-Area Decisions = P87 enforcement** — must list every recommended autonomous answer with rationale.
- **Fresh-VM smoke is Kaan-action** — Phase 37 stages the test surface; real run is gated on Phase 33 INSTALL-08 real VM execution (which is Kaan-action).

</specifics>

<deferred>
## Deferred Ideas

- **Cross-platform behavioural diff matrix** — too broad; v2.2 stretch.
- **AI-generated audit narrative** — humans write the v2.1-MILESTONE-AUDIT.md narrative section.
- **Performance regression bench across phases** — v2.0 already has perf gates per phase.

</deferred>

<kaan_action_required>
## Critical: Kaan-Action Required (KAAN-ACTION-LEGAL.md)

Phase 37 autonomous deliverables: 5 seam e2e tests + audit script + orphan inventory + Kaan-action roll-up + grey-area log + POC allowlist.

Kaan-action items (rolled up by AUDIT-04):
1. **AUDIT-VM:** Run `integration_audit.py` ON A FRESH VM after Phase 33 INSTALL-08 real VM matrix lands (post-Phase-38 signed binary).
2. **AUDIT-SIGN-VERIFY:** Run signed-binary verifier on the real signed artifacts (Phase 38 secrets dep).

Both stay in `KAAN-ACTION-LEGAL.md` — Phase 37 produces the script; Kaan runs it on the real VM.
</kaan_action_required>
