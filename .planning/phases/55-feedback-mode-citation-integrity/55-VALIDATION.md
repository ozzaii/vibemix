---
phase: 55
slug: feedback-mode-citation-integrity
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Verified against HEAD `20466bb`. The coach + evidence + linter machinery
> (`AICoach`, `EvidenceRegistry`, `CitationLinter`, `StrippedRateTracker`,
> COACH_* matrix cells, `coach_loop`, the debrief stripper) is ALREADY
> SHIPPED and load-bearing-tested — this phase EXTENDS Phase 54's anti-slop
> spine to COACH prompts (LIVE-02) and CLOSES two telemetry-surface leaks so
> the `ipc.session.citation` strip reflects real stripped/verified counts +
> the real stripped text (LIVE-04). The GROUNDING contract (linter strips
> orphans before they reach the ear) is already airtight; the leak is in the
> diagnostics TELEMETRY (`_citation_telemetry()` placeholders), not in the
> emission gate.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`[tool.pytest.ini_options]`, `--strict-markers`) + vitest (`tauri/ui/`) for the diagnostics strip |
| **Config file** | `pyproject.toml` (Python); `tauri/ui/package.json` + `vitest.config` (frontend) |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <file>` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60-120 seconds (default suite); frontend `npm test` ~10-20s; +real-hw live drive is `macos_audio`, Kaan-action |

---

## Sampling Rate

- **After every task commit:** Run the task's quick command (single test file).
- **After every plan wave:** Run the full default suite.
- **Before `/gsd:verify-work`:** Full default suite must be green. The `macos_audio` live drive (≥2-genre coach-usefulness Kaan-ear sign-off + watch-the-strip) is Kaan-action and recorded as deferred — not a default-suite gate.
- **Max feedback latency:** ~120 seconds (full suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | LIVE-02 | T-18-01-05 | Coach anti-slop spine: a COACH reaction citing an event NOT in an empty `EvidenceRegistry` snapshot → `CitationLinter.check(...).valid is False` (strip → no voice); the grounded one passes — REAL primitives, no network | unit | `pytest -q tests/state/test_coach_anti_slop.py` | ❌ W0 | ⬜ pending |
| 55-01-02 | 01 | 1 | LIVE-02 | — | Coach-prompt grounding: `build_system_instruction("intermediate","coach")` selects a COACH_* cell carrying citation grammar + anti-slop footer; `AICoach.build_prompt(coach_ev, registry_snapshot=...)` emits the grounded evidence line + coach task tail | unit | `pytest -q tests/agent/test_coach_prompt_grounding.py` | ❌ W0 | ⬜ pending |
| 55-01-03 | 01 | 1 | LIVE-02 | — | ≥2 genres in the automated suite: genre-1 (real `hype_trace_genre1.jsonl` fixture, REUSED) + genre-2 (synthetic build→drop BPM ~128) both fire coach-relevant Events through the REAL detector + ground a coach reaction; empty evidence → no fire | unit (clock-patched) | `pytest -q tests/state/test_coach_anti_slop.py` | ❌ W0 (extends 55-01-01) | ⬜ pending |
| 55-02-01 | 02 | 1 | LIVE-04 | T-18-01-05 | Zero-orphan replay: build a registry from the real fixture's events; every `[track:<id>]`/`[ev:...]`/evidence citation the grammar produces resolves to a real registry entry → orphan count == 0 | unit | `pytest -q tests/coach/test_citation_zero_orphan_replay.py` | ❌ W0 | ⬜ pending |
| 55-02-02 | 02 | 1 | LIVE-04 | T-20-01-02 | Hallucination-strip: a response citing a non-existent evidence id → `CitationLinter.check` strips it (`valid=False`, `reason="invalid_atoms"`, orphan in `.missing`) | unit | `pytest -q tests/coach/test_citation_zero_orphan_replay.py` | ❌ W0 (extends 55-02-01) | ⬜ pending |
| 55-02-03 | 02 | 1 | LIVE-04 | — | Live/debrief consistency: the SAME orphan citation is stripped in BOTH `mode="live"` (±1.0s) and `mode="debrief"` (±2.0s) — one grammar, one registry, two tolerance bands | unit | `pytest -q tests/coach/test_citation_live_debrief_consistency.py` | ❌ W0 | ⬜ pending |
| 55-03-01 | 03 | 1 | LIVE-04 | — | Real slop counter: a cumulative `(stripped, total)` source exposes `slop_ratio = stripped/total`; rises when a strip is recorded, stays 0.0 cold-start (never NaN) | unit | `pytest -q tests/coach/test_slop_ratio_source.py` | ❌ W0 | ⬜ pending |
| 55-03-02 | 03 | 1 | LIVE-04 | — | Last-unverified source: the strip/bypass path's `raw_text` reaches a last-unverified holder; `None` until a strip occurs, then the stripped text | unit | `pytest -q tests/coach/test_last_unverified_source.py` | ❌ W0 | ⬜ pending |
| 55-03-03 | 03 | 1 | LIVE-04 | T-20-05-03 | `_citation_telemetry()` returns the REAL `slop_ratio` (stripped/total) + REAL `last_unverified_response` (not the `1/(1+mean)` placeholder, not hardcoded `None`); `bypass_active` + `stripped_rate_15s` stay real reads; callable never raises | unit (AST/source-grep + behavior) | `pytest -q tests/coach/test_main_anti_slop_wiring.py` | ✅ (extends existing) | ⬜ pending |
| 55-04-01 | 04 | 2 | LIVE-04 | — | IPC payload end-to-end: `coach_loop`'s publish gate emits a `SessionCitation` whose `slop_ratio`/`last_unverified_response` carry the REAL telemetry values (not mock zeros) when wired | unit (async harness) | `pytest -q tests/runtime/test_coach_citation_publish.py` | ✅ (extends existing) | ⬜ pending |
| 55-04-02 | 04 | 2 | LIVE-04 (SC2/SC3) | — | Diagnostics strip renders real values: the existing Settings → Diagnostics citation component consumes a real-valued `SessionCitationPayload` (slop_ratio shown, last-unverified text shown when present); citation deep-link path (Phase 24 overlay-highlight) reuses real session data | unit (vitest) | `cd tauri/ui && npm test -- citation` | ❌ W0 (extends existing component spec) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/state/test_coach_anti_slop.py` — new, LIVE-02 coach anti-slop spine (linter strips unbacked coach citation; grounded passes) + ≥2-genre grounded fire (REUSES `tests/fixtures/hype_trace_genre1.jsonl`, no second fixture copy)
- [ ] `tests/agent/test_coach_prompt_grounding.py` — new, LIVE-02 COACH persona cell + grounded `evidence_line`/`build_prompt`
- [ ] `tests/coach/test_citation_zero_orphan_replay.py` — new, LIVE-04 zero-orphan replay + hallucination-strip
- [ ] `tests/coach/test_citation_live_debrief_consistency.py` — new, LIVE-04 live/debrief one-grammar-two-tolerance consistency
- [ ] `tests/coach/test_slop_ratio_source.py` — new, LIVE-04 real cumulative slop_ratio source
- [ ] `tests/coach/test_last_unverified_source.py` — new, LIVE-04 last-unverified holder fed from the strip path
- [ ] `src/vibemix/coach/stripped_rate.py` (or a new small `coach/slop_metrics.py`) — add cumulative `(stripped,total)` + `slop_ratio()` accessor (source, append-only; single-threaded contract preserved)
- [ ] `src/vibemix/agent/dj_cohost.py` — wire the strip/bypass `raw_text` into the last-unverified holder (additive; the `raw_text` is already captured at the strip log)
- [ ] `src/vibemix/__main__.py` — rewrite `_citation_telemetry()` to read the real slop_ratio + last-unverified (replace the `1/(1+mean)` placeholder + the hardcoded `None`)
- [ ] `tauri/ui/src/.../citation*.spec.ts` — extend the existing diagnostics-strip spec to assert real-valued payload render (no new component)

*Existing infrastructure (`tests/state/test_event_detector.py` clock-patch pattern, `tests/state/test_hype_anti_slop.py` FLOOR/SPINE pattern, REAL `EvidenceRegistry`+`CitationLinter` primitives, `tests/runtime/test_coach_citation_publish.py` async harness, `tests/coach/test_main_anti_slop_wiring.py` source-grep harness, `tauri/ui` vitest harness, the Phase 24 `ipc.session.overlay_highlight` deep-link) covers fixtures — no new framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coach (feedback) mode coaches USEFULLY across ≥2 genres, in-bar, no slop — observations tie to things that actually happened in the set, like a real mentor not a script | LIVE-02 (SC1) | needs his library + his ear (hard quality gate per CLAUDE.md + `project_phase_16_kaan_dj_testing`) | `VIBEMIX_MODE=coach uv run python -m vibemix`; play ≥2 genres into BlackHole 2ch; listen — coaching lands grounded + useful, across genres, no scripted/late/fake/hallucinated lines. |
| The diagnostics citation strip reflects real session events live — slop_ratio stays low, no orphan citations, `last_unverified_response` populates on a real strip, clicking a live citation deep-links to the real event | LIVE-04 (SC2/SC3) | needs a live full-set run + eyes on the Settings → Diagnostics drawer | Run coach mode through a full set; open Settings → Diagnostics; confirm slop_ratio stays low, no orphan citations appear, and a deliberately-stripped turn shows its text under last-unverified; click a citation → real event highlight. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-21
