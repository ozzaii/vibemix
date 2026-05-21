---
phase: 59
slug: full-deck-awareness-grounding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 59-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python 3.12) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q tests/state tests/agent -x` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60–120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched area.
- **After every plan wave:** Run the full suite.
- **Before `/gsd:verify-work`:** Full suite must be green.
- **Max feedback latency:** ~120 seconds.

---

## Anti-Slop / Grounding Guarantees (must be observably tested)

| Guarantee | Requirement | How it is proven |
|-----------|-------------|------------------|
| Honest `unknown` — never a false-confident key/track | DECK-02 | Unit test: when no source resolves a deck, snapshot field is `unknown`, not a guess. |
| Citable `key:` — fabricated harmonic atoms are stripped | DECK-03 | Linter test: a response citing `[key:A:12B]` with no registered `key:` evidence is stripped by `CitationLinter._validate_atom` (existence-only). |
| Strictly read-only — no DJ-DB write | DECK-05 | Subprocess/grep test mirroring the existing SQLCipher-dormancy idiom: assert no DJ-software DB opened in write mode anywhere in the deck path. |
| Single-writer preserved | DECK-04 | Test: only `_tick_once` copies deck-state into `MusicState`; snapshot golden-equivalence holds (additive-only). |
| `to_camelot` correctness (Rekordbox `Am`/`F#m` → Camelot) | DECK-01/02 | Unit table test over the 24 musical-notation → Camelot mappings against the Rekordbox fixture. |
| Cross-deck claim suppression when 2nd deck unresolved | DECK-05 | Test: with only one deck resolvable, no cross-deck assertion is emitted. |
| Gemini-vision deck-read accuracy (gated re-enable) | DECK-02 | Eval task on real screenshots; vision path stays gated until the eval passes a defined accuracy floor. |

---

## Per-Task Verification Map

> Populated by the planner — each task maps to a requirement + an automated command above.

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| _TBD by planner_ | | | | | | | |
