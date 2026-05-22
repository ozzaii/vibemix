---
phase: 63
slug: memory-store
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-22
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `63-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-mock (already dev deps) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers`; `parity` marker registered |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |
| **Estimated runtime** | ~sub-second for `tests/memory`; full suite as baseline |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=src python3 -m pytest -q tests/memory` (new package tests; sub-second)
- **After every plan wave:** Run `pytest -m parity` + `tests/repo/test_model_literal_gate.py` (parity + literal gate)
- **Before `/gsd:verify-work`:** Full suite must be green (at the 7-WIP `live-tuning-or-brain` baseline — zero NEW failures)
- **Max feedback latency:** < 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 63-W0 | W0 | 0 | STORE-01..04 | — | N/A (test fences) | unit | `pytest -q tests/memory` | ❌ W0 | ⬜ pending |
| STORE-01a | — | 1 | STORE-01 | — | sqlite-vec↔numpy bit-identical top-k | parity | `pytest -m parity tests/memory/test_store_parity.py -x` | ❌ W0 | ⬜ pending |
| STORE-01b | — | 1 | STORE-01 | — | numpy fallback engaged when ext unavailable | unit | `pytest tests/memory/test_store.py::test_numpy_fallback -x` | ❌ W0 | ⬜ pending |
| STORE-02a | — | 1 | STORE-02 | — | add/query round-trip; raw signature verbatim | unit | `pytest tests/memory/test_store.py::test_add_query_roundtrip -x` | ❌ W0 | ⬜ pending |
| STORE-02b | — | 1 | STORE-02 | T-no-extraction | no live-path import; only embed_content | unit (static+subproc) | `pytest tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py -x` | ❌ W0 | ⬜ pending |
| STORE-03a | — | 1 | STORE-03 | T-orphan | delete_session removes vectors+rows atomically | unit | `pytest tests/memory/test_store.py::test_delete_cascade -x` | ❌ W0 | ⬜ pending |
| STORE-03b | — | 1 | STORE-03 | — | retention evicts oldest-session-first whole-session | unit | `pytest tests/memory/test_retention.py -x` | ❌ W0 | ⬜ pending |
| STORE-03c | — | 1 | STORE-03 | T-path-traversal | crafted session_id rejected | unit (security) | `pytest tests/memory/test_store.py::test_session_id_path_traversal -x` | ❌ W0 | ⬜ pending |
| STORE-04 | — | 1 | STORE-04 | T-confab | embedding via resolve("embedding"); no model literal | unit (static) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/memory/__init__.py` — package marker
- [ ] `tests/memory/test_store.py` — round-trip, numpy-fallback, delete-cascade, path-traversal (STORE-01/02/03)
- [ ] `tests/memory/test_store_parity.py` — `@pytest.mark.parity` Mac↔Win bit-identity (STORE-01)
- [ ] `tests/memory/test_no_live_path_import.py` — static + subprocess import-boundary gate (no-live-path invariant)
- [ ] `tests/memory/test_no_extraction.py` — tokenize-stripped scan: only `embed_content`, never generation (STORE-02 raw-in/raw-out)
- [ ] `tests/memory/test_retention.py` — oldest-session-first whole-session eviction (STORE-03)
- Parity fixture: in-test rng synthetic 768-dim vectors (no new fixture file — keeps repo lean)
- Framework install: none — pytest + parity marker already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Clean-VM (Mac + Win incl. ARM64) `memory.db` write→read round-trip in e2e install matrix | STORE-01 | Requires signed/notarized clean VMs on the external Apple/SignPath clock | **KAAN-ACTION** — rides the in-flight notarization approvals; data-file only, zero new signing surface. NOT a Phase 63 engineering blocker. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-22 (autonomous `fully` — Nyquist map derived from research; clean-VM round-trip parked as KAAN-ACTION)
