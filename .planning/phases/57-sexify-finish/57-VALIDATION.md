---
phase: 57
slug: sexify-finish
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python) + vitest (Tauri UI) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `tauri/ui/vitest.config.ts` |
| **Quick run command** | `cd tauri/ui && npm test -- <file>`  /  `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <paths>` |
| **Full suite command** | `cd tauri/ui && npm test` (711 baseline) + `PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~210s (Python) + ~10s (vitest) |

---

## Sampling Rate

- **After every task commit:** Run the quick command scoped to touched paths
- **After every plan wave:** Run the full UI vitest + scoped Python
- **Before `/gsd:verify-work`:** Full suite green
- **Max feedback latency:** ~220s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 57-01 T1 | 57-01 | 1 | POLISH-02 | static/unit | `pytest -q tests/security/test_drag_capability_present.py` + `npm test -- mascot.chrome.test.ts drag.spec.ts` | ⬜ pending |
| 57-01 T2 | 57-01 | 1 | POLISH-02 | static | `pytest -q tests/security/test_tcc_prime_path_wired.py` | ⬜ pending |
| 57-02 T1 | 57-02 | 1 | POLISH-03 | static/audit | `python3 scripts/audit/check_no_slop_install.py` + `npm test -- wizard` | ⬜ pending |
| 57-02 T2 | 57-02 | 1 | POLISH-03 | unit | `npm test -- first-run-continuity.spec.ts` + `npm test` | ⬜ pending |
| 57-03 T1 | 57-03 | 2 | POLISH-01 | unit (regression) | `npm test` (session component contracts hold) | ⬜ pending |
| 57-03 T2 | 57-03 | 2 | POLISH-01 | unit (regression) | `npm test -- mascot.chrome.test.ts` + `npm test` | ⬜ pending |
| 57-03 T3 | 57-03 | 2 | POLISH-01 | agent gate | paired ui-checker + ui-auditor → zero HIGH; `npm test` | ⬜ pending |
| 57-03 T4 | 57-03 | 2 | POLISH-01 | KAAN-ACTION | felt visual sign-off (human-verify checkpoint) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infra covers all phase requirements — the gaps are missing REGRESSION ASSERTIONS (the 3 carryover bugs were already fixed in commit `fac4c4a`; pin them so they can't regress) + a first-run continuity smoke. No new framework, no new feature code.*

---

## Manual-Only Verifications (KAAN-ACTION)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tier-1 surfaces look peak / "sexy" — felt visual quality | POLISH-01 | Beauty is Kaan's eye; engineering only proves zero-HIGH ui-checker/ui-auditor | Review the impeccable before/after on session view + mascot overlay |
| 3 carryover bugs confirmed on the real app: window drags, no mascot chrome strip, TCC list populates | POLISH-02 | Needs the real Mac + a fresh-ish account | Drag the window; inspect mascot overlay edges; open first-run → watch the Privacy list |
| Fresh macOS account first-run → first-session has no friction | POLISH-03 | Felt "no dead-ends" needs a real fresh-account walk | Create a fresh account; walk first-run to audio-live; note any confusing step |

*Automated coverage proves the fixes exist + are regression-pinned + the wizard flow is continuous; the felt/real-app confirmations are the Kaan-action live-drive carveout.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 220s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-filled 2026-05-21
