---
phase: 79
slug: lens-three-grounded-modes
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-26
---

# Phase 79 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "lens or matrix or curator or persona or citation or linter or apply_lens"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Every LENS-0x acceptance criterion maps to an automated proof — no API key. Lens→(mode,mood) mapping + shared-selection + per-lens citation-gate are all pure prompt-shape / strip-decision assertions. The "does each lens FEEL right / did the tutor teach" judgment is Phase-81 BENCH (lens dimension) + Kaan's-ear (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 79-01-T1 | 79-01 | 1 | LENS-01/02 | unit (scaffold) | `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py` | ⬜ pending |
| 79-01-T2 | 79-01 | 1 | LENS-01/02 | unit (scaffold) | `PYTHONPATH=src python3 -m pytest -q tests/runtime/test_settings_apply.py tests/library/test_curator_persona_seam.py tests/agent/test_dj_cohost.py` | ⬜ pending |
| 79-02-T1 | 79-02 | 2 | LENS-01 | unit | `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py tests/prompts/test_matrix.py` | ⬜ pending |
| 79-03-T1 | 79-03 | 3 | LENS-02 | unit | `PYTHONPATH=src python3 -m pytest -q tests/runtime/test_settings_apply.py -k "lens or skill or mood"` | ⬜ pending |
| 79-03-T2 | 79-03 | 3 | LENS-02 | unit | `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_lens.py tests/library/test_curator_persona_seam.py tests/agent/test_dj_cohost.py tests/memory/test_no_live_path_import.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → proof coverage

| Req | Proof | Plan/Task |
|-----|-------|-----------|
| LENS-01 — three grounded lenses over the same state | `test_lens_map_covers_three_canonical_lenses`, `test_lens_prompt_shape_per_lens`, `test_unknown_lens_raises_value_error`, `test_default_lens_byte_identical_to_cohost_default`, `test_three_lenses_pass_the_same_gate` | 79-02-T1 (flips 79-01 scaffolds) |
| LENS-01 — v4 byte-identity preserved | `tests/prompts/test_matrix.py` v4 golden stays green (builder untouched) | 79-02-T1 |
| LENS-02 — shared selection flows to both | `test_shared_selection_flows_to_both_builders`, curator-seam lens-read, `_resolve_prompt_cell_uses_shared_lens` | 79-03-T2 |
| LENS-02 — `_apply_lens` validates + persists + reloads | `test_apply_lens_happy_path` / `_invalid_value_rejected` / `_non_string_rejected` | 79-03-T1 |
| LENS-02 — both cold paths byte-identical | `test_resolve_prompt_cell_cold_path_byte_identical` + curator default-when-unset | 79-03-T2 |
| Invariant #2 — lens-blind gate | `test_three_lenses_pass_the_same_gate` (strip decision depends only on EvidenceRegistry membership) | 79-02-T1 |
| No new IPC envelope | `grep -rn "lens" tauri/ui/src/ipc/messages.schema.json src/vibemix/runtime/messages.py` returns empty | 79-03-T2 |

---

## Wave 0 Requirements

- [x] Test for LENS-01: hype/critique/tutor each map to a distinct grounded prompt over the SAME evidence; switching lens changes voice/intent, not the facts; `critique`→coach-substrate alias; `tutor` is a real new grounded voice. → `tests/prompts/test_lens.py` (Plan 79-01 T1)
- [x] Test for default-lens byte-identity: the default (`hype`) lens prompt is byte-identical to today's co-host default; the v4 `test_matrix.py` golden stays green (matrix builder/_CELLS/MOOD_PERSONAS untouched). → `test_default_lens_byte_identical_to_cohost_default` + real-green `test_v4_golden_anchor_present` (Plan 79-01 T1)
- [x] Test for LENS-02: a single shared lens-selection source (`ConfigStore.extra["lens"]` + `_apply_lens`) flows to BOTH `build_system_instruction` and `build_curator_instruction` — choose "tutor" once → both surfaces read it. → `test_shared_selection_flows_to_both_builders` + apply_lens trio (Plan 79-01 T1/T2)
- [x] Test for per-lens citation grounding: all three lenses go through the same gate; un-cited output strips to `<silence/>` (ack-bank retired) regardless of lens — strip decision depends only on `EvidenceRegistry` membership, not the lens. → `test_three_lenses_pass_the_same_gate` (Plan 79-01 T1)

*Existing pytest infrastructure covers all phase requirements — no framework install needed. All scaffolds are `xfail(strict=True)` in Plan 79-01; a silent early-pass becomes a HARD failure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Each lens FEELS right in a real set (hype rides / critique coaches / tutor teaches through who you are) | LENS-01 | Subjective voice-fidelity — Phase-16 rule | Phase-81 BENCH lens dimension + KAAN-ACTION ear verdict; never auto-judged, never blocks under `gsd-autonomous fully` |

*All unit-level phase behaviors have automated verification (no API); the felt voice-fidelity is the Phase-81 BENCH lens dimension + Kaan's ear (parked, never blocks).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
