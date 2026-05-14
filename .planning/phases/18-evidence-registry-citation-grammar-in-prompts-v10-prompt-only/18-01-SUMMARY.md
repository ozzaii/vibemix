---
phase: 18-evidence-registry-citation-grammar-in-prompts-v10-prompt-only
plan: 01
subsystem: state
tags: [evidence, citations, grammar, regex, threading, anti-hallucination]
requires:
  - vibemix.state.MusicState (writer pattern reference)
  - threading.Lock pattern (Phase 6 / P17 precedent)
provides:
  - vibemix.state.EvidenceRegistry
  - vibemix.state.EVIDENCE_CITATION_RE
  - vibemix.state.EVIDENCE_SOURCES
  - vibemix.state.parse_citations
affects:
  - Plan 18-02 (refresh + EventDetector wiring) — imports against this stable surface
  - Plan 18-03 (AICoach grammar bake) — reads snapshot() into prompt
  - Plan 18-04 (telemetry) — uses parse_citations for citation-count
  - Phase 20 (linter + ack-bank) — consumes EvidenceRegistry.has() + parse_citations
tech_stack:
  added: []
  patterns:
    - "threading.Lock single-writer (mirrors MusicState in src/vibemix/state/music_state.py)"
    - "deep-copy + tuple-frozen snapshot for lock-free reader iteration"
    - "compiled re.Pattern with verbose-free EBNF grammar"
key_files:
  created:
    - src/vibemix/state/evidence_registry.py
    - tests/state/test_evidence_registry.py
  modified:
    - src/vibemix/state/__init__.py
decisions:
  - "v1.0 registry is permissive (any string source/key writable); regex enforces shape only at prompt + Phase 20 linter boundary — keeps future P17 detectors landing without cross-plan code change"
  - "single-Lock writer pattern (NOT asyncio.Lock) — both writers (state_refresh_loop tick body + EventDetector._fire) run synchronously; matches MusicState"
  - "snapshot() returns deep copy with tuple-frozen inner — closes T-18-01-03 (information disclosure of live dict reference)"
  - "has() boundary INCLUSIVE at exactly tol — matches Phase 20 §per-mode tolerance bands semantics"
  - "EBNF body excludes `[`, `]`, whitespace, comma — single regex handles single + multi-citation in one pass"
  - "parse_citations splits each atom on the FIRST `:` only; inner-body (key@t) shape NOT parsed further in v1.0 (locking it would force v2 when Phase 20 tightens per-source body grammar)"
metrics:
  duration: ~12 min
  completed: 2026-05-14
---

# Phase 18 Plan 01: EvidenceRegistry + Citation Grammar Skeleton — Summary

**One-liner:** Built the `EvidenceRegistry` skeleton + EBNF citation-grammar regex (`[ev:.../@t]` form) + `parse_citations` helper as a stable, fully-decoupled API surface for Plans 18-02/03/04 and the Phase 20 linter to consume — runtime anchor of cohost_v4's "trust the audio" anti-hallucination rule.

## What Shipped

### EvidenceRegistry public API (`src/vibemix/state/evidence_registry.py`)

```python
class EvidenceRegistry:
    def __init__(self) -> None: ...
    def write(self, source: str, key: str, t_session: float) -> None: ...
    def snapshot(self) -> dict[str, dict[str, tuple[float, ...]]]: ...
    def has(self, source: str, key: str, t_target: float, tol: float = 1.0) -> bool: ...
    def clear(self) -> None: ...
    def __len__(self) -> int: ...
```

- **Storage:** `dict[source, dict[key, list[t_session]]]`, append-only, insertion-ordered.
- **Thread-safety:** every read AND write goes through `threading.Lock` (closes Pitfall P12 — registry race). Test 3 (8 threads × 100 writes = 800 entries, no torn writes) is the gate.
- **Snapshot semantics:** deep copy + inner lists frozen as tuples. Mutating the returned dict cannot leak back into registry state (Test 4).
- **Tolerance semantics:** `has()` boundary INCLUSIVE at exactly `±tol` per Phase 20 §"per-mode tolerance bands". Phase 20 will pass `tol=1.0` for live mode, `tol=2.0` for debrief mode (GROUND-07) — API is mode-agnostic.
- **Permissive validation:** v1.0 accepts any string source/key (no enforcement at write-time). Grammar enforcement is at the prompt + Phase 20 linter boundary, NOT at the registry — keeps future P17 detectors landing without a cross-plan code change.

### EVIDENCE_SOURCES (frozenset)

```python
EVIDENCE_SOURCES = frozenset({"ev", "aud", "midi", "track", "screen", "mix", "tend"})
```

The 7 LOCKED EBNF source identifiers from `18-CONTEXT.md §EBNF Grammar`.

### EVIDENCE_CITATION_RE (compiled regex)

Final pattern shape:

```regex
\[(?:ev|aud|midi|track|screen|mix|tend):[^\s,\]]+(?:,(?:ev|aud|midi|track|screen|mix|tend):[^\s,\]]+)*\]
```

EBNF expressed:

```
citation := '[' atom ( ',' atom )* ']'
atom     := source ':' body
source   := 'ev' | 'aud' | 'midi' | 'track' | 'screen' | 'mix' | 'tend'
body     := one-or-more chars excluding whitespace, ']', ','
```

Matches all 7 single-citation forms (`[ev:KICK_SWAP@45.2]`, `[aud:bpm@45.2]`, `[midi:cue_a@12.7]`, `[track:abc-123]`, `[screen:waveform_deck_a]`, `[mix:audible_deck=A]`, `[tend:user_likes_acid]`) AND the comma-joined multi-citation form (`[ev:KICK_SWAP@45.2,aud:bpm@45.0]`) in a single pass. Whitespace inside brackets is rejected (Test 9). Empty `[]` is rejected because the body requires at least one char (Test 10).

### parse_citations(text) -> list[tuple[source, body]]

```python
def parse_citations(text: str) -> list[tuple[str, str]]: ...
```

Walks `EVIDENCE_CITATION_RE.finditer` and partitions each atom on the FIRST `:`. Returns `[]` on no-match (never raises — closes T-18-01-04). Plan 18-04 (telemetry) and Phase 20 (linter) both consume this. Inner-body shape (e.g., splitting `KICK_SWAP@45.2` further into key + timestamp) is intentionally NOT parsed in v1.0 — locking it would force a v2 API change when Phase 20 tightens per-source body grammar.

## Test Count Delta

| Scope            | Before | After | Δ   |
| ---------------- | ------ | ----- | --- |
| `tests/state/`   | 375    | 394   | +19 |
| Full repo        | 1549   | 1568  | +19 |
| Pre-existing failures | 9 | 9 | 0 (unchanged, all out of scope) |

13 logical tests written; pytest reports 19 because Test 7 (parametrize over the 7 EBNF source forms) fans out to 7 cases. All 19 pass.

## Decoupling Confirmation (Plan 18-02 contract surface)

Plan 18-02's job is to wire this registry into:
1. `src/vibemix/state/refresh.py` — `state_refresh_loop._tick_once` writes per-tick aud / mix observations.
2. `src/vibemix/state/event_detector.py` — `EventDetector._fire` writes per-event-fire `ev` observations.
3. `src/vibemix/audio/recorder.py` — `VoiceRecorder.close()` calls `registry.clear()` for per-session lifecycle.

**This plan touched ZERO of those files** — wiring is exclusively Plan 18-02's responsibility per the Wave 1 split. Plans 18-02/03/04 + the Phase 20 linter import against this stable surface:

```python
from vibemix.state import (
    EvidenceRegistry,
    EVIDENCE_CITATION_RE,
    EVIDENCE_SOURCES,
    parse_citations,
)
```

## Threat Register Status

| Threat ID | Disposition | Status |
| --------- | ----------- | ------ |
| T-18-01-01 (concurrent-write tampering) | mitigate | **Closed** — Test 3 (8-thread torn-write) passes. |
| T-18-01-02 (unbounded growth) | accept | Documented; `clear()` exposed for Plan 18-02 per-session reset wiring. |
| T-18-01-03 (snapshot live-dict leak) | mitigate | **Closed** — Test 4 (snapshot frozen) passes. |
| T-18-01-04 (parse_citations crash on malformed) | mitigate | **Closed** — `parse_citations` returns `[]` on no-match; Tests 9 + 10 cover whitespace + empty rejection at the regex level; Test 13 covers the no-citation-input → `[]` case. |
| T-18-01-05 (LLM emits fake `[ev:fake@99]`) | accept | v1.0 prompt-only seeding by design; Phase 20 linter (GROUND-04..08) closes via `EvidenceRegistry.has(tol=...)` lookup. |

## POC Files Untouched

`git diff --stat cohost.py cohost_v2.py cohost_lk.py cohost_v4.py` → empty. Confirmed clean.

## Deviations from Plan

None — the plan executed exactly as written. Three commits, three tasks, RED-then-GREEN per task per `tdd="true"` annotation. No Rule 1/2/3/4 fires, no auth gates.

## Commits

| Task | SHA       | Message                                                              |
| ---- | --------- | -------------------------------------------------------------------- |
| 1    | a799a43   | `test(18-01): add failing tests for EvidenceRegistry + citation grammar` |
| 2    | 0bd933f   | `feat(18-01): implement EvidenceRegistry + EBNF citation grammar`    |
| 3    | f73888e   | `feat(18-01): add parse_citations + registry-grammar coherence tests` |

## Self-Check: PASSED

- `src/vibemix/state/evidence_registry.py` — FOUND (198 lines).
- `src/vibemix/state/__init__.py` — FOUND (re-exports added).
- `tests/state/test_evidence_registry.py` — FOUND (13 logical / 19 parametrize-expanded tests).
- Commit `a799a43` — FOUND.
- Commit `0bd933f` — FOUND.
- Commit `f73888e` — FOUND.
- Smoke import `from vibemix.state import EvidenceRegistry, EVIDENCE_CITATION_RE, EVIDENCE_SOURCES, parse_citations` → "imports ok".
- POC files untouched.
- tests/state/ regression: 375 → 394 (+19, no losses).
- Full repo: 1549 → 1568 passed (+19), 9 failed unchanged (all pre-existing, all outside `tests/state/`).
