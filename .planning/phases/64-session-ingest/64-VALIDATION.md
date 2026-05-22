---
phase: 64
slug: session-ingest
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-22
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `64-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (already dev dep) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |
| **Estimated runtime** | ~sub-second for `tests/memory`; full suite as baseline |

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src python3 -m pytest -q tests/memory` (sub-second)
- **After every plan wave:** `tests/memory/` + `tests/repo/test_model_literal_gate.py` + the two shipped memory gates (no-extraction, no-live-path)
- **Before `/gsd:verify-work`:** full suite green at the 8-failure `live-tuning-or-brain` baseline (zero NEW failures)
- **Max feedback latency:** < 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 64-W0 | W0 | 0 | INGEST-01..03 | — | N/A (test fences) | unit | `pytest -q tests/memory/test_ingest.py` | ❌ W0 | ⬜ pending |
| INGEST-01a | — | 1 | INGEST-01 | — | `build_coach_line_signature` deterministic (same fields → same bytes) | unit | `pytest tests/memory/test_ingest.py::test_signature_deterministic -x` | ❌ W0 | ⬜ pending |
| INGEST-01b | — | 1 | INGEST-01 | — | reads events.jsonl → one coach_line per emitted ai_text; skips citation_strip | unit | `pytest tests/memory/test_ingest.py::test_ingest_emits_coach_lines -x` | ❌ W0 | ⬜ pending |
| INGEST-01c | — | 1 | INGEST-01 | T-confab | ingest references NO generation surface (only embed_content/embed_query) | unit (static, auto) | `pytest tests/memory/test_no_extraction.py -x` | ✅ globs memory/*.py | ⬜ pending |
| INGEST-02a | — | 1 | INGEST-02 | T-livepath | ingest imports no live-reaction-path module | unit (static+subproc) | `pytest tests/memory/test_no_live_path_import.py -x` | ✅ globs memory/*.py | ⬜ pending |
| INGEST-02b | — | 1 | INGEST-02 | — | session-close + boot sweep dispatch through run_in_executor (not inline) | unit | `pytest tests/memory/test_ingest.py::test_sweep_uses_executor -x` | ❌ W0 | ⬜ pending |
| INGEST-03a | — | 1 | INGEST-03 | — | re-ingest of marked session = 0 embed calls, 0 new records (idempotent) | unit | `pytest tests/memory/test_ingest.py::test_reingest_is_noop -x` | ❌ W0 | ⬜ pending |
| INGEST-03b | — | 1 | INGEST-03 | — | every record carries session_id + ts + kind=="coach_line" | unit | `pytest tests/memory/test_ingest.py::test_records_tagged -x` | ❌ W0 | ⬜ pending |
| INGEST-03c | — | 1 | INGEST-03 | — | signature-keyed embed cache hit → 0 API calls | unit | `pytest tests/memory/test_ingest.py::test_embed_cache_hit -x` | ❌ W0 | ⬜ pending |
| INGEST-x | — | 1 | (cross) | T-confab | no hardcoded model literal in ingest.py | unit (static, shipped) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ scans src/vibemix/ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/memory/test_ingest.py` — signature determinism, coach_line emission, skip-citation_strip, idempotent re-ingest, tagging, embed-cache hit, executor dispatch
- [ ] Synthetic `events.jsonl` fixture (mirror real on-disk shapes: `event` lines with `type/track/phase/deck`; `ai_text` lines with `[emotion]`-prefixed text + optional `[aud:rms@…]` citation; a `citation_strip` line to assert it is skipped) — generated in-test to keep repo lean
- [ ] Verify shipped `test_no_extraction.py` / `test_no_live_path_import.py` actively cover the new `ingest.py` (both glob `memory/*.py`)
- Framework install: none

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-session round-trip: a finished session's `coach_line`s appear in `memory.db` and re-ingest is a 0-cost no-op | INGEST-01/03 | Requires a real recorded DJ session + live FLEX embed call | **KAAN-ACTION** (rides the live-ear pass) — not an engineering blocker; unit tests cover the logic with synthetic fixtures. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-22 (autonomous `fully` — Nyquist map from research; real-session round-trip parked as KAAN-ACTION)
