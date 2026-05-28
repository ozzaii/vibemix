# Phase 103: Live "Mastered" Grounding - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — design locked in ROADMAP + REQUIREMENTS (MAST-01..04); grey-area recommendations auto-accepted per `gsd-autonomous` default-YES. Builds directly on Phase 102's shipped `skill_tree.py` + `LearnProgress.skills` live-portion block.

<domain>
## Phase Boundary

The Competent→Mastered segment of each skill bar — the anti-slop heart of v11.0. Once a skill is Competent (Phase 102), its Mastered fill advances ONLY from REAL, cited live events: a thin pure-logic recognizer maps EXISTING `EvidenceRegistry` event types → skill credit, and grants credit ONLY when the event resolves a valid citation. After N grounded demonstrations a skill flips to "Mastered" with a persisted count + `first_mastered_at`. NO new detectors are invented; the live event taxonomy + `EvidenceRegistry` are consumed UNCHANGED and READ-ONLY.

DELIVERS: MAST-01 (locked-until-Competent), MAST-02 (recognizer maps existing event types, no new detectors), MAST-03 (every credit requires a resolvable citation; un-cited/fabricated → zero credit — test-pinned, Invariants #2+#3), MAST-04 (N grounded demos → Mastered + persisted count + first_mastered_at).

NOT IN THIS PHASE: the `skills` schema fields (shipped in 102), any UI / panel / animation / co-host vocal / IPC envelope (Phase 104), any NEW event detector, any change to `state/` or `agent/` or `__main__.py`.
</domain>

<decisions>
## Implementation Decisions

### Recognizer architecture (GA1)
- A new pure-logic module `src/vibemix/learn/skill_recognizer.py` (sibling to `skill_tree.py`) maps a detected live event → the skill(s) it demonstrates, gated on citation validity. Keeps `skill_tree.py` focused on fill/stage math; the recognizer owns event→skill translation.
- `skill_tree.py` gains `record_live_demo(progress, skill_id, *, now) -> LearnProgress` (the deferred-from-102 mutator): increments that skill's `live_proof_count` and, on reaching the skill's `mastered_threshold`, sets `mastered=True` + `first_mastered_at=now` (injected timestamp, deterministic). Pure transform over the `skills` block; persisted via the existing 102 atomic-write helper.
- The recognizer takes an event + an `EvidenceRegistry`-citation check (injected as a predicate/callable so the engine is testable with synthetic events and never hard-depends on live `state/` internals).

### Event→skill mapping + citation requirement (GA2)
- Reverse map (declared in `SKILL_MANIFEST` or the recognizer, single source): `MIX_MOVE`/EQ-band MIDI → `eq_mixing`; harmonic-compatible transition → `harmonic_mixing`; beatmatch/on-beat-blend → `beatmatching`; `LAYER_ARRIVAL`/completed-transition → `transitions`; phrase-locked / count-in hit → `phrasing_performance`; hot-cue/loop usage (MIDI) → `deck_control`. (Exact event-type constants confirmed against `state/event_detector.py` in research.)
- MAST-03 (the spine): a live event grants credit ONLY when it resolves a valid citation in `EvidenceRegistry`. The recognizer requires the citation check to return true; an un-cited or fabricated event yields ZERO credit. Test-pinned with synthetic cited vs un-cited streams (Invariants #2 + #3). No event → no fill, ever.

### N threshold + Mastered flip (GA3)
- Each skill declares a `mastered_threshold` (N grounded demos) in `SKILL_MANIFEST` (default-YES recommended N≈3, tunable — Claude's discretion in plan-phase, defended by tests). `live_proof_count` increments once per DISTINCT grounded demonstration; the same event must not double-count (dedup by event identity within the credit call). On `live_proof_count >= mastered_threshold` the skill flips to `mastered=True` + `first_mastered_at` is stamped once (idempotent — never overwritten on later demos).
- Mastered is monotonic: once flipped it stays mastered; `first_mastered_at` is set exactly once.

### Locked-until-Competent + integration seam (GA4)
- MAST-01: `record_live_demo` / the recognizer is a NO-OP for a skill that is not yet Competent — you cannot master what you have not learned. Locked skills ignore live events entirely (no buffered backfill).
- Integration seam stays INSIDE the learn island: the existing learn-side play-mode observation point (`learn/runtime.py` / `learn/teaching_loop.py`, which already observe the live co-host for the proactive tutor in v9.0) is where the recognizer is invoked on relevant events. P103 wires the recognizer to THIS learn-side seam ONLY.
- **Hard concurrency rule:** P103 must NOT modify `state/evidence_registry.py`, `state/event_detector.py`, `agent/`, or `__main__.py` — those are read-only imports owned by other concurrent sessions (One Mind = src/vibemix/** minus learn). If the only honest live-path wiring would require touching a non-learn file, STOP and flag it as a deferred wiring KAAN-ACTION rather than violate the island. The engine + recognizer + learn-side seam remain fully offline-unit-testable with synthetic events regardless.

### Claude's Discretion
- Exact `mastered_threshold` value per skill (uniform N vs per-skill) — plan-phase decides, defended by tests.
- Whether the recognizer is invoked via a method on the existing learn runtime or a small observer registered at the learn-side seam — whichever minimizes the cross-module surface while staying in `learn/`.
- Event-identity dedup mechanism (event id vs (type, timestamp) tuple).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/learn/skill_tree.py` (Phase 102) — `SkillTree.compute`, `SKILL_MANIFEST`, `SkillProgress`, the Competent stage. P103 adds `record_live_demo` here and the reverse event→skill map.
- `src/vibemix/learn/progress.py` (Phase 102) — the `skills` live-portion block (`live_proof_count`/`mastered`/`first_mastered_at` already exist with safe defaults) + atomic write. P103 fills these fields; NO new migration needed (schema v2 already carries them).
- `src/vibemix/state/evidence_registry.py` (READ-ONLY) — the citation-resolution source; the recognizer's citation predicate wraps its public interface. Import types only; do NOT modify.
- `src/vibemix/state/event_detector.py` (READ-ONLY) — the existing event taxonomy (event-type constants). Confirm exact names in research; do NOT add detectors.
- `src/vibemix/learn/runtime.py` / `learn/teaching_loop.py` — the existing learn-side play-mode observation seam (my island) where the recognizer plugs in.
- `tests/learn/test_skill_tree.py` + `test_runtime_invariants.py` — the test idioms to extend (synthetic event streams + invariant pins).

### Established Patterns
- Pure-logic learn-engine modules, offline-unit-testable, injected timestamps for determinism (102 precedent).
- Citation grounding (#2/#3): live evidence is authoritative; un-cited claims strip. P103's "no citation → no credit" is the same invariant applied to skill credit.
- Single-writer (#1): only the learn runtime writes learn state; skill_recognizer is pure, record_live_demo mutates only the `skills` block via the existing helper.

### Integration Points
- Reads `EvidenceRegistry` citation resolution (read-only, via injected predicate).
- Reads existing `event_detector` event types (read-only).
- Persists `live_proof_count`/`mastered`/`first_mastered_at` into the SAME `learn-progress.json` `skills` block (no new file/path/migration).
- Phase 104 consumes the now-fillable Mastered state for the panel + the grounded "Mastered" vocal.
</code_context>

<specifics>
## Specific Ideas

- "Every notch is earned" extends to Mastered: the headline P103 test is `test_uncited_event_grants_zero_mastery_credit` (a fabricated/un-cited event must NOT advance Mastered) — the anti-slop spine of this phase, a named must_have.
- Locked-until-Competent is non-negotiable: `test_live_demo_noop_when_not_competent`.
- `first_mastered_at` stamped exactly once: `test_first_mastered_at_idempotent`.
</specifics>

<deferred>
## Deferred Ideas

- The skill-tree panel + the rare earned grounded "Mastered" co-host vocal → Phase 104.
- Any live-path wiring that would require touching `state/`, `agent/`, or `__main__.py` → flagged as KAAN-ACTION wiring if it arises (island discipline; those files are owned by concurrent sessions).
- Skill-state feeding the live persona/lens prior → Future (v11.x) per REQUIREMENTS.
</deferred>
