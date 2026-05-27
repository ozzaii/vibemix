# Phase 37 — Cross-Phase Integration Audit Gate — PLAN

**Status:** Ready to execute (after Phase 33 lands)
**Plans:** 6 (37-01 → 37-06)
**Mode:** `gsd-autonomous fully` — scaffold + tests + audit script in scope; real fresh-VM smoke = Kaan-action

---

## Cross-cutting rules

1. **POC files (`cohost*.py`, `mascot.html`) UNTOUCHED — verified ONCE MORE by 37-06.**
2. **Seam tests call REAL surfaces — only external IO is mocked** (Gemini API, signing keys).
3. **Atomic commits per plan.**
4. **`scripts/integration_audit.py` EXTENDS v2.0's surface; does not rewrite.**
5. **`v2.1-MILESTONE-AUDIT.md` lives at `.planning/v2.1-MILESTONE-AUDIT.md` per v2.0 archive convention.**

---

## Plan 37-01 — 5 seam e2e tests (AUDIT-01)

**REQ-IDs:** AUDIT-01

**Edits:**
- NEW `tests/e2e/test_seam_p18__p20.py` — EvidenceRegistry → CitationLinter live-mode.
  - Build a real EvidenceRegistry with 1 real evidence packet.
  - Construct a real LLM response citing the packet.
  - Pass through the live citation linter; assert PASS.
  - Then construct a fake-citation response; assert linter blocks.
- NEW `tests/e2e/test_seam_p19__agent.py` — GeminiContextCache → DJCoHostAgent.
  - Build a real GeminiContextCache instance (no Gemini network).
  - Initialize DJCoHostAgent with cache (mock the Gemini transport).
  - Call `.run()` for one turn; assert cache was hit (assert via mock spy).
- NEW `tests/e2e/test_seam_p25__p28.py` — pyrekordbox XML → library_intel register_library.
  - Parse a fixture Rekordbox XML.
  - Pass result to `register_library` (real surface — P48 final-mile).
  - Assert library entries indexed + searchable via the vibe-search interface.
- NEW `tests/e2e/test_seam_p27__eval_gate.py` — replay_harness → eval.yml.
  - Run `scripts/eval/replay_harness.py --dry-run` against synthetic corpus.
  - Parse outputs.
  - Assert `.github/workflows/eval.yml` job names match what the harness produces (contract).
- NEW `tests/e2e/test_seam_p31__ws_bus.py` — 4-layer mascot → ws_bus IPC.
  - Import `priority-stack.ts` exports via a vitest test (NOT Python — ws_bus.py is Python sink).
  - OR: Python test that asserts ws_bus.py's frame schema matches the contract priority-stack.ts emits.
  - Use schema fixture as the contract anchor.

**Acceptance:** all 5 seam tests pass.

---

## Plan 37-02 — `integration_audit.py` extension + audit template (AUDIT-02, AUDIT-07)

**REQ-IDs:** AUDIT-02, AUDIT-07

**Edits:**
- `scripts/integration_audit.py`:
  - Add `--write-milestone-audit OUTPUT_PATH` mode.
  - For each seam, look up source + sink `file:line` via static grep + write WIRED / PARTIAL / MISSING verdict.
  - Run pytest on `tests/e2e/test_seam_*.py` and capture pass/fail per test.
  - Compose `.planning/v2.1-MILESTONE-AUDIT.md` from a template with 7 sections (Summary / Per-Seam Verdicts / Orphan Inventory / Kaan-Action Roll-Up / Grey-Area Decisions / POC Files Untouched / Conclusion).
- NEW `scripts/integration_audit_templates/v2_1_milestone_audit.md.jinja` — fixed-order section template.
- NEW `tests/scripts/test_integration_audit_v2_1.py`:
  - `test_audit_emits_all_seven_sections`.
  - `test_audit_writes_to_planning_v2_1_path`.
  - `test_audit_records_seam_test_pass_fail`.
  - `test_audit_does_not_overwrite_existing_without_force`.

**Acceptance:** all new tests pass; `python scripts/integration_audit.py --write-milestone-audit .planning/v2.1-MILESTONE-AUDIT.md` produces a valid file.

---

## Plan 37-03 — Orphan inventory CI gate (AUDIT-03)

**REQ-IDs:** AUDIT-03

**Edits:**
- `scripts/integration_audit.py`:
  - Add `--orphan-inventory` mode — walks `src/vibemix/`, `runtime/`, `tauri/`, builds symbol→file index, checks each top-level symbol for: any test import + any production caller. Emits CSV.
- NEW `.github/workflows/orphan-inventory.yml`:
  - On every PR + push to main, runs orphan scan + diffs against committed list under `.planning/codebase/orphans.csv`.
  - Fails on new orphans not in the list.
- NEW `.planning/codebase/orphans.csv` — committed baseline (initially empty or matching current state).
- NEW `tests/scripts/test_orphan_inventory.py`:
  - `test_orphan_scan_finds_synthetic_orphan` — plant a test fixture orphan, assert detected.
  - `test_orphan_scan_excludes_known_callers` — symbol with real caller is not flagged.

**Acceptance:** new tests pass; orphan inventory mode runs clean on current repo (zero new orphans).

---

## Plan 37-04 — Kaan-action roll-up (AUDIT-04)

**REQ-IDs:** AUDIT-04

**Edits:**
- `scripts/integration_audit.py`:
  - Add `--kaan-action-rollup` mode — walks `KAAN-ACTION-LEGAL.md` (repo root) + every `.planning/phases/*/KAAN-ACTION-*.md`. Aggregates entries with type / owner / blocking flag.
  - Emits markdown table for `v2.1-MILESTONE-AUDIT.md`'s Kaan-Action Roll-Up section.
  - HARD assertion: only entries of type `legal-capacity` should be present at milestone close — anything else → error exit code (means autonomous skipped real work).
- NEW `tests/scripts/test_kaan_action_rollup.py`:
  - `test_rollup_finds_dist_09_dist_11_legal_capacity`.
  - `test_rollup_fails_on_non_legal_capacity_entry` — synthesize a proxy entry, assert error.
  - `test_rollup_excludes_strikethrough_completed_entries`.

**Acceptance:** new tests pass; current real rollup contains DIST-09 + DIST-11 + Phase 33 / 35 / 39 deferred items.

---

## Plan 37-05 — Grey-Area Decisions log (AUDIT-05)

**REQ-IDs:** AUDIT-05

**Edits:**
- `scripts/integration_audit.py`:
  - Add `--grey-area-log` mode — greps every phase SUMMARY.md + VERIFICATION.md for markers (`recommended:`, `proposed:`, `accepted per gsd-autonomous fully`, `deferred per autonomous mode`).
  - Emits markdown table for `v2.1-MILESTONE-AUDIT.md`'s Grey-Area Decisions section.
  - Each row: phase, decision, rationale, reversible? (yes/no).
- NEW `tests/scripts/test_grey_area_log.py`:
  - `test_grey_area_scan_finds_recommended_marker`.
  - `test_grey_area_scan_finds_deferred_per_autonomous`.
  - `test_grey_area_scan_emits_required_columns`.

**Acceptance:** new tests pass; real scan produces a list of every v2.1 phase's grey-area decisions.

---

## Plan 37-06 — POC files allowlist refresh (AUDIT-06)

**REQ-IDs:** AUDIT-06

**Edits:**
- `tests/repo/test_g5_poc_files_untouched.py`:
  - Extend the `MODIFIED_FILES_ALLOWLIST` constant with v2.1 paths that intentionally diverge from v2.0 (e.g., new wizard components from Phase 33, new mascot layers from Phase 31, etc.).
  - The allowlist NEVER contains `cohost*.py` or `mascot.html`.
  - Test asserts every modified-since-v2.0 file is either in the allowlist OR matches one of the protected POC patterns (which fails).
- NEW test cases:
  - `test_cohost_py_untouched_since_v2_0` — git diff against v2.0 tag's `cohost.py` blob; assert identical.
  - `test_mascot_html_untouched_since_v2_0`.
  - `test_allowlist_does_not_contain_poc_patterns` — assert no `cohost*.py` / `mascot.html` in allowlist.

**Acceptance:** all POC files match v2.0 byte-for-byte; allowlist excludes them.

---

## Hard gates (collected from CONTEXT)

| Gate | Plan |
|------|------|
| 5 seam e2e tests pass on real surfaces | 37-01 |
| `integration_audit.py --write-milestone-audit` produces 7-section file | 37-02 |
| Orphan inventory CI gate fails on new orphans | 37-03 |
| Kaan-action rollup fails if non-legal-capacity entries remain | 37-04 |
| Grey-Area Decisions log captures every recommended/deferred mark | 37-05 |
| POC files untouched since v2.0 | 37-06 |

Each plan = one atomic commit. Final verification runs `python scripts/integration_audit.py --write-milestone-audit .planning/v2.1-MILESTONE-AUDIT.md` and inspects the output.
