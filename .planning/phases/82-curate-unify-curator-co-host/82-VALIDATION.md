---
phase: 82
slug: curate-unify-curator-co-host
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 82 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "curate or toolset or genre_prototypes or profile or curator or no_live_path"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## What's already shared (DO NOT re-do) vs the genuine new work

- **ALREADY SHARED (Phase 77/79 — regression-pin only):** persona/lens (`build_lens_instruction` + `ConfigStore.extra["lens"]` read by both curator backends + Telegram); the perception MECHANISM (`library/genre_prototypes.py`) already consumed by the co-host (`refresh.py`).
- **GENUINE NEW WORK (two thin additive seams):** (CURATE-01) the curator's `get_track_features` resolves genre via `genre_prototypes.classify` (today returns `genre: None`) → both surfaces derive genre from ONE mechanism; (CURATE-02 taste half) the curator lazy-reads the co-host-only `profile/` to curate "for this DJ".

---

## Per-Task Verification Map

> Populated by the planner. No API key. Both seams are pure reads testable on cached `library.db` + a fixture profile.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | CURATE-01/02 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for CURATE-01: the curator's `get_track_features` resolves genre via `genre_prototypes.classify` — the SAME mechanism the co-host reads (`refresh.py`); assert both surfaces derive genre from one source (no parallel genre notion); `genre` is no longer `None` for a library track.
- [ ] Test for CURATE-02 (taste): the curator lazy-reads `load_profile()` and biases curation "for this DJ"; the read is GUARDED (absent/empty profile → graceful default) and LAZY (does not regress `tests/memory/test_no_live_path_import.py`).
- [ ] Test for CURATE-02 (persona — regression pin only, already shared Phase 79): both curator backends + Telegram still read the shared `extra["lens"]`.
- [ ] Test that the curator reads the LIBRARY representation, NOT `MusicState` (invariant #1 — grep/assert no curator import of the live state object).
- [ ] Regression pins: existing `library curate` / Telegram / `next_suggestion` (pill) / codex `mcp_server` surfaces still work; both seams reach BOTH backends (shared `toolset.py`/`ViberAgent` core); no new ws port (invariant #4), no new IPC envelope.

*Existing pytest infrastructure covers all phase requirements — extend `tests/library/test_toolset.py`. No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Curating "for this DJ" / the co-host leaning on the library actually FEELS personal | CURATE-01/02 | Subjective — needs a real library + a real session | KAAN-ACTION: curate with a populated profile + library, judge whether it reflects the DJ's taste |

*All unit-level phase behaviors have automated verification (no API, cached vectors + fixture profile); the felt "does it know me" judgment is parked KAAN-ACTION (never blocks).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
