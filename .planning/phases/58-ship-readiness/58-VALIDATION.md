---
phase: 58
slug: ship-readiness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + bats/shell assertions for `cut_release.sh` gate behavior |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <paths>` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` + a scripted `cut_release.sh --dry-run` green exit |
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
| (planner fills) | — | — | REL-01/02/03 | unit/integration | (planner fills) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing release machinery covers the phase — the gaps are: re-point Gates 1+4 to v0.1.0-rc1/v4.0 (test-pinned), a `--dry-run`/`--no-sign` signature stub (+ hard-guard regression that `gh release create` never auto-runs), the `record_50a_walk.sh` OUT_DIR path-bug fix, and the consolidated v4.0 KAAN-ACTION cookbook. No new framework.*

---

## Manual-Only Verifications (KAAN-ACTION / external clock)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| §E2E-50A-WALK recorded on the real Mac with real DJ-set audio → `docs/e2e/2026-05-walk.webm` (feeds Gate 6b) | REL-02 | Needs real hardware + real audio + screen recording | Run `scripts/e2e/record_50a_walk.sh`; drive the app end-to-end; confirm the .webm |
| Gate 2b hallucination sign-off — Kaan's live hype (54) + coach (55) ear-pass ≥2 genres | REL-01 | Felt-quality on real hardware (the 54/55 HUMAN-UAT items) | Discharge `54-HUMAN-UAT.md` + `55-HUMAN-UAT.md` |
| External signatures: Apple Dev Agreement (Francesco) + SignPath OSS cert (Kaan) | REL-03 | Legal-capacity / external clock | The SHIP-CUT is one-button-after-these |

*Automated coverage proves the gates run green on real artifacts + the dry-run is green-minus-signature + the cookbook is complete; the recorded walk, ear-pass, and signatures are the KAAN-ACTION/external-clock carveouts.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 220s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
