---
phase: 77
slug: wire-connect-the-islands
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 77 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "wire or grounding or ingest or dotenv or curator"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite, 4449 tests) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Populated by the planner. Each WIRE-0x requirement maps to an automated proof (no API key needed — honest green). Live e2e on the funded key is a KAAN-ACTION (produce-and-park), never blocks.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | WIRE-01/04/05/06 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test file(s) for WIRE-01 (grounding kwarg + `[track:<id>]` citation survives the EvidenceRegistry gate, off-loop seam test mirroring `test_ingest_wiring.py`)
- [ ] Test for WIRE-04 (curator reads shared persona seam; `_SYSTEM_INSTRUCTION` no longer hardcoded)
- [ ] Test for WIRE-05 (`_fire_ingest` fires on the live `main()` path when `VIBEMIX_RECALL_ENABLED`; no double-retention)
- [ ] Test for WIRE-06 (decoy `GEMINI_API_KEY` shell env var set → `.env` value wins under `override=True`)
- [ ] Regression pins for WIRE-02 / WIRE-03 (detectors + `detected_genre` still surface — no new work, just lock)

*Existing pytest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live co-host cites the actually-playing track in a real DJ session | WIRE-01 | Needs funded Gemini key + live audio (BlackHole) | KAAN-ACTION: run `uv run python -m vibemix`, play a known track, confirm `[track:<id>]` citation in a real reaction |

*All unit-level phase behaviors have automated verification; only the live-audio end-to-end is manual (parked for Kaan).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
