---
phase: 58
slug: ship-readiness
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python 3.12) + shell assertions for `cut_release.sh` gate behavior |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <paths>` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` + a scripted `cut_release.sh --dry-run v0.1.0-rc1` green exit |
| **Estimated runtime** | ~210s |

---

## Sampling Rate

- **After every task commit:** Run the quick command scoped to touched paths
- **After every plan wave:** Run the repo + release gate tests
- **Before `/gsd:verify-work`:** the `--dry-run` SHIP-CUT exits green (signature stubbed)
- **Max feedback latency:** ~220s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 01-1 sidecar + unsigned .dmg | 58-01 | 1 | REL-01 | build | `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec` then `test -x tauri/src-tauri/binaries/.../vibemix-core-aarch64-apple-darwin` | ⬜ pending |
| 01-2 v4.0 milestone audit | 58-01 | 1 | REL-01 | unit | `pytest tests/repo/test_v4_milestone_audit_present.py -q` | ⬜ pending |
| 02-1 record_50a path fix | 58-02 | 1 | REL-02 | unit | `pytest tests/repo/test_record_50a_walk_paths.py -q` | ⬜ pending |
| 02-2 real Gate-6b report | 58-02 | 1 | REL-02 | integration | `pytest tests/e2e/macbook/test_report_render.py -q` | ⬜ pending |
| 03-1 SHIP-V4 cookbook surface | 58-03 | 1 | REL-03 | static | `grep -q SHIP-V4 KAAN-ACTION-LEGAL.md && python3 scripts/launch/check_no_ai_slop.py KAAN-ACTION-LEGAL.md` | ⬜ pending |
| 03-2 cookbook completeness pin | 58-03 | 1 | REL-03 | unit | `pytest tests/repo/test_kaan_action_v4_surface.py -q` | ⬜ pending |
| 04-1 Gate 1+4 re-point | 58-04 | 2 | REL-01 | unit | `pytest tests/repo/test_cut_release_tag_regex.py -q` | ⬜ pending |
| 04-2 --dry-run + hard guard | 58-04 | 2 | REL-01/03 | unit | `pytest tests/repo/test_cut_release_no_autonomous_publish.py -q` | ⬜ pending |
| 04-3 green dry-run | 58-04 | 2 | REL-01/03 | integration | `pytest tests/repo/test_cut_release_dry_run.py -q && bash scripts/launch/cut_release.sh --dry-run v0.1.0-rc1` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing release machinery covers the phase — the gaps are: re-point Gates 1+4 to v0.1.0-rc1/v4.0 (test-pinned), a `--dry-run`/`--no-sign` signature stub (+ hard-guard regression that `gh release create` never auto-runs), the `record_50a_walk.sh` OUT_DIR path-bug fix, the v4.0 milestone audit generation, the real Gate-6b report, and the consolidated v4.0 KAAN-ACTION cookbook. No new framework.*

New test files created during the phase (all standard pytest, no scaffold needed):
- [ ] `tests/repo/test_v4_milestone_audit_present.py` (Plan 01)
- [ ] `tests/repo/test_record_50a_walk_paths.py` (Plan 02)
- [ ] `tests/e2e/macbook/test_report_render.py` (Plan 02 — extend if it exists)
- [ ] `tests/repo/test_kaan_action_v4_surface.py` (Plan 03)
- [ ] `tests/repo/test_cut_release_tag_regex.py` (Plan 04)
- [ ] `tests/repo/test_cut_release_no_autonomous_publish.py` (Plan 04)
- [ ] `tests/repo/test_cut_release_dry_run.py` (Plan 04)
- [ ] `.planning/v4.0-MILESTONE-AUDIT.md` — generated artifact (Gate 4 input), not a test but a Wave-1 deliverable

---

## Manual-Only Verifications (KAAN-ACTION / external clock)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| §E2E-50A-WALK recorded on the real Mac with real DJ-set audio → `docs/e2e/2026-05-walk.webm` (feeds Gate 6b) | REL-02 | Needs real hardware + real audio + screen recording | Run `scripts/e2e/record_50a_walk.sh`; drive the app end-to-end; confirm the .webm |
| Gate 2b hallucination sign-off — Kaan's live hype (54) + coach (55) ear-pass ≥2 genres | REL-01 | Felt-quality on real hardware (the 54/55 HUMAN-UAT items) | Discharge `54-HUMAN-UAT.md` + `55-HUMAN-UAT.md` |
| External signatures: Apple Dev Agreement (Francesco) + SignPath OSS cert (Kaan) | REL-03 | Legal-capacity / external clock | The SHIP-CUT is one-button-after-these |
| Unsigned `.dmg` headless build (if `cargo tauri build` blocks on signing config) | REL-01 | May require CI/real signed-Mac | If blocked, documented in 58-01-SUMMARY; dry-run falls back to the whl for the Gate-2 path proof |

*Automated coverage proves the gates run green on real artifacts + the dry-run is green-minus-signature + the cookbook is complete; the recorded walk, ear-pass, and signatures are the KAAN-ACTION/external-clock carveouts.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 1 deliverable dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 1 covers all new-file references (no MISSING placeholders)
- [x] No watch-mode flags
- [x] Feedback latency < 220s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
