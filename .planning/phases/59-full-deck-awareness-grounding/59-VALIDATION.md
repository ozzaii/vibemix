---
phase: 59
slug: full-deck-awareness-grounding
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
updated: 2026-05-21
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 59-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python 3.12) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q tests/state tests/coach tests/agent -x` |
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
| Honest `unknown` — never a false-confident key/track | DECK-02 | Unit test: when no source resolves a deck, snapshot field is `unknown`, not a guess (test_deck_poller `-k suppress/unknown`; coach `decks=unknown`). |
| Citable `key:` — fabricated harmonic atoms are stripped | DECK-03 | Linter test: a response citing `[key:A:12B]` with no registered `key:` evidence is stripped by `CitationLinter._validate_atom` (existence-only). |
| Strictly read-only — no DJ-DB write | DECK-05 | Subprocess/grep test mirroring the SQLCipher-dormancy idiom: assert no DJ-software DB opened in write mode anywhere in the deck path. |
| Single-writer preserved | DECK-04 | Test: only `_tick_once` copies deck-state into `MusicState`; grep asserts no `deck_state.decks =` outside refresh.py; snapshot golden-equivalence holds. |
| `to_camelot` correctness (Rekordbox `Am`/`F#m` → Camelot) | DECK-01/02 | Unit table test over the 24 musical-notation → Camelot mappings + Camelot/open-key passthrough + empty/garbage → None. |
| Cross-deck claim suppression when 2nd deck unresolved | DECK-05 | Test: with only one deck resolvable, the unresolved deck is confidence=0 → no `key:` write → uncitable. |
| Gemini-vision deck-read accuracy (gated re-enable) | DECK-02 | Eval task on real screenshots; vision path stays gated until the eval passes a defined accuracy floor (KAAN-ACTION checkpoint). |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 59-01-T1 | 59-01 | 1 | DECK-01/02 | to_camelot never raises; honest None on unrecognized key | unit (tdd) | `pytest tests/state/test_harmonics.py -x -q` | planned |
| 59-01-T2 | 59-01 | 1 | DECK-01 | additive deck_state field; no false-confident default | unit (tdd) | `pytest tests/state/test_deck_state.py tests/state/test_coach_prompt_grounding.py -x -q` | planned |
| 59-02-T1 | 59-02 | 1 | DECK-03 | fabricated `[key:A:12B]` stripped; existence-only validation | unit (tdd) | `pytest tests/state/test_evidence_registry.py -k key tests/coach/test_citation_linter.py -k "key or existence" -x -q` | planned |
| 59-02-T2 | 59-02 | 1 | DECK-03 | chip timestamp from registry not body; killswitch untouched | unit | `pytest tests/agent/ tests/state/test_coach_prompt_diet.py -k "citation or strip or key" -x -q` | planned |
| 59-03-T1 | 59-03 | 1 | DECK-04 | event types registered; no firing logic (Phase 60) | unit | `pytest tests/state/test_event_priority.py tests/audio/test_constants.py -x -q` | planned |
| 59-03-T2 | 59-03 | 1 | DECK-05 | no DJ-DB write-mode open; SQLCipher dormant (regression pin) | repo/subprocess (tdd) | `pytest tests/repo/test_repo_scrub.py -k deck_readonly tests/library/test_rekordbox.py -k dormant -x -q` | planned |
| 59-04-T1 | 59-04 | 2 | DECK-02/05 | source ladder; cross-deck suppression; graceful degradation; read-only | unit (tdd) | `pytest tests/state/test_deck_poller.py -x -q` | planned |
| 59-04-T2 | 59-04 | 2 | DECK-04 | single-writer copy; change-only confidence-gated key:/track: writes | unit (tdd) | `pytest tests/state/test_refresh_deck.py tests/state/test_refresh.py -x -q` | planned |
| 59-04-T3 | 59-04 | 2 | DECK-01/04 | coach sees decks the grounded way; out of diet/ack; stub arms only | unit | `pytest tests/state/test_coach_prompt_grounding.py tests/state/test_coach_prompt_diet.py -x -q` | planned |
| 59-05-T1 | 59-05 | 3 | DECK-02 | separate structured call; null→unknown; killswitch untouched; Gemini-only | unit (tdd, mocked) | `pytest tests/state/test_deck_vision.py -x -q` | planned |
| 59-05-T2 | 59-05 | 3 | DECK-02 | accuracy-floor gate defined; default suite makes no live call | unit/eval | `python3 -c "import ast; ast.parse(open('eval/deck_vision/run_eval.py').read())"` | planned |
| 59-05-T3 | 59-05 | 3 | DECK-02 | vision stays gated until real-screenshot eval clears the floor | checkpoint:human-verify (KAAN-ACTION) | manual eval run + recorded decision in 59-05-SUMMARY.md | planned |
