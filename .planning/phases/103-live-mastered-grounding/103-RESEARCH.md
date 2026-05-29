# Phase 103: Live "Mastered" Grounding - Research

**Researched:** 2026-05-29
**Domain:** Pure-logic skill-credit recognizer over the existing live event taxonomy + EvidenceRegistry citation grounding (vibemix learn island)
**Confidence:** HIGH (every interface below was read from source this session; no training-data assumptions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **GA1 — Recognizer architecture:** New pure-logic module `src/vibemix/learn/skill_recognizer.py` (sibling to `skill_tree.py`) maps a detected live event → the skill(s) it demonstrates, gated on citation validity. `skill_tree.py` gains `record_live_demo(progress, skill_id, *, now) -> LearnProgress` (the deferred-from-102 mutator): increments `live_proof_count`, and on reaching `mastered_threshold` sets `mastered=True` + `first_mastered_at=now` (injected timestamp). Persisted via the existing 102 atomic-write helper. The recognizer takes an event + an `EvidenceRegistry`-citation check injected as a predicate/callable (testable with synthetic events, never hard-depends on live `state/` internals).
- **GA2 — Event→skill mapping + citation requirement:** Reverse map (single source — `SKILL_MANIFEST` or the recognizer): `MIX_MOVE`/EQ-band MIDI → `eq_mixing`; harmonic-compatible transition → `harmonic_mixing`; beatmatch/on-beat-blend → `beatmatching`; `LAYER_ARRIVAL`/completed-transition → `transitions`; phrase-locked / count-in hit → `phrasing_performance`; hot-cue/loop usage (MIDI) → `deck_control`. MAST-03 spine: a live event grants credit ONLY when it resolves a valid citation in `EvidenceRegistry`; un-cited/fabricated → ZERO credit. Test-pinned with synthetic cited vs un-cited streams (Invariants #2 + #3). No event → no fill, ever.
- **GA3 — N threshold + Mastered flip:** Each skill declares a `mastered_threshold` (N grounded demos) in `SKILL_MANIFEST` (default-YES N≈3, tunable — Claude's discretion in plan-phase). `live_proof_count` increments once per DISTINCT grounded demo; the same event must not double-count (dedup by event identity within the credit call). On `live_proof_count >= mastered_threshold` the skill flips `mastered=True` + `first_mastered_at` stamped once (idempotent — never overwritten). Mastered is monotonic.
- **GA4 — Locked-until-Competent + integration seam:** MAST-01: `record_live_demo`/the recognizer is a NO-OP for a skill that is not yet Competent (no buffered backfill). Integration seam stays INSIDE the learn island. **Hard concurrency rule:** P103 must NOT modify `state/evidence_registry.py`, `state/event_detector.py`, `agent/`, or `__main__.py` (read-only imports owned by concurrent sessions). If the only honest live-path wiring requires touching a non-learn file, STOP and flag it as a deferred wiring KAAN-ACTION. The engine + recognizer + learn-side seam remain fully offline-unit-testable regardless.

### Claude's Discretion
- Exact `mastered_threshold` per skill (uniform N vs per-skill) — defended by tests.
- Whether the recognizer is invoked via a method on the existing learn runtime or a small observer registered at the learn-side seam — whichever minimizes the cross-module surface while staying in `learn/`.
- Event-identity dedup mechanism (event id vs (type, timestamp) tuple).

### Deferred Ideas (OUT OF SCOPE)
- Skill-tree panel + rare earned grounded "Mastered" co-host vocal → Phase 104.
- Any live-path wiring that would require touching `state/`, `agent/`, or `__main__.py` → KAAN-ACTION wiring if it arises.
- Skill-state feeding the live persona/lens prior → Future (v11.x).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAST-01 | Competent→Mastered segment stays locked until the skill reaches Competent | `record_live_demo` reads the skill's derived Competent state via `SkillTree.compute(progress)[skill_id].competent` and is a no-op when False. Confirmed `compute` already returns `competent: bool` per skill (skill_tree.py:211, :281). |
| MAST-02 | Once Competent, Mastered fill advances only from existing EvidenceRegistry event types (MIX_MOVE / LAYER_ARRIVAL / harmonic / EQ-band MIDI / beatmatch) — no new detectors | Verified the EXACT event-type string literals (below). The reverse map references real `Event.type` strings. **LOAD-BEARING GAP:** `beatmatching` and `harmonic_mixing` have NO clean dedicated event signal — see Deliverable 1. |
| MAST-03 | Every live mastery credit must resolve a valid citation in `EvidenceRegistry`; un-cited/fabricated → zero credit (Invariants #2+#3, test-pinned) | The recognizer's injected predicate wraps `EvidenceRegistry.has(source, key, t_target, tol)` (existence check) or the `snapshot().get(source,{}).get(key)` pattern that `agent/dj_cohost.py::_build_citation_strip` already uses. Exercisable offline with a synthetic registry. |
| MAST-04 | Skill flips to "Mastered" after N grounded live demos; count + `first_mastered_at` persist | `record_live_demo` writes the `skills` block (`live_proof_count`/`mastered`/`first_mastered_at`) shipped in 102-01; persists via `save_progress` (atomic tmp+os.replace). `SkillTree.compute` already reads + promotes stage to `"mastered"` (test-pinned 102: `test_mastered_live_portion_promotes_stage`). |
</phase_requirements>

## Summary

Phase 103 is a **pure-logic, learn-island-only** phase. Two new artifacts: a `skill_recognizer.py` module (event→skill translation, citation-gated) and a `record_live_demo` mutator added to `skill_tree.py`. Both are offline-unit-testable with synthetic events + a synthetic registry — no live `state/` or `agent/` dependency at test time, by design (the citation check is injected as a callable). The `skills` block on `learn-progress.json` already carries `live_proof_count`/`mastered`/`first_mastered_at` with safe defaults (102-01), and `SkillTree.compute` already reads + promotes them to `stage="mastered"` (102-02, test-pinned). So no schema change and no migration — Phase 103 only *writes* the live-portion that 102 left as the forward seam.

**The single most load-bearing finding:** there is **NO existing learn-side seam that observes the live co-host's `EventDetector` fires.** `learn/runtime.py::LessonRuntime` is the *lesson* FSM — it reads MIDI for *lesson actions* and *writes* its own lesson observations into the shared `EvidenceRegistry`; it never reads `EventDetector.detect()` output from a real DJ set. The live event→reaction loop is `runtime/coach.py::coach_loop` (the `runtime/` island, NOT learn), wired in `__main__.py:2051`. `coach_loop` does not touch learn at all. Therefore the recognizer's **engine, the `record_live_demo` mutator, the reverse map, and all four MAST tests are fully deliverable offline this phase** — but the *live wiring* (feeding real `EventDetector` fires into the recognizer during an actual set) requires touching `runtime/coach.py` or `__main__.py`, both outside the learn island. **That wiring is a deferred KAAN-ACTION** (`§EARNED-LIVE-MASTERED-VERIFY` already on the queue covers the real-FLX4 verify). This matches CONTEXT GA4's explicit escape hatch.

**The second load-bearing finding:** of the 6 skills, only 4 have a clean existing event signal. `eq_mixing`, `transitions`, `phrasing_performance`, and `deck_control` map to real events/MIDI-move labels. **`beatmatching` and `harmonic_mixing` do NOT have a distinct, citable detected event** — there is no `BEATMATCH`/`SYNC_ENGAGED` event type, and the only harmonic event (`KEY_CLASH`/`TRANSITION_OPPORTUNITY`) is **default-OFF** (`harmonic_clash_enabled=False`, never flipped — gated behind the unshipped Plan 60-03 Kaan-ear veto). The plan must decide per-skill: either map these two to the best available proxy (documented + tested as a proxy, not as ground truth) or declare them un-creditable-in-v11.0 and gate their Mastered fill behind the future detector work. Recommendation below.

**Primary recommendation:** Build `skill_recognizer.py` + `record_live_demo` as pure logic with an injected citation predicate. Map the 4 clean skills to real event signals; map `beatmatching` and `harmonic_mixing` to **documented proxies tagged as such, OR leave them recognizer-recognized-but-uncreditable** (planner's call, defended by a test that pins the decision). Ship all MAST-01..04 tests offline. Flag the live-loop wiring + the two weak-signal skills as the two KAAN-ACTION items (one is already queued).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Event→skill translation (the reverse map) | learn-engine (`skill_recognizer.py`) | — | Pure logic; no clock, no I/O; sibling to `skill_tree.py` per GA1 |
| Citation grounding check | learn-engine (injected predicate) wraps `state/evidence_registry.py` (read-only) | — | The predicate is a callable; the engine never imports `EvidenceRegistry` types except optionally for typing. Keeps the engine offline-testable |
| Mastered-flip persistence (`record_live_demo`) | learn-engine (`skill_tree.py`) → `learn/progress.py` atomic write | — | Mutates only the `skills` live-portion block; persists via shipped `save_progress` |
| Live event observation (feeding real fires in) | **`runtime/coach.py::coach_loop` (NON-learn island)** | `__main__.py` (NON-learn) | **No learn-side seam exists.** This is the deferred KAAN-ACTION wiring per GA4 |
| Stage derivation (locked/competent/mastered) | learn-engine (`skill_tree.py::SkillTree.compute`) — SHIPPED in 102 | — | Already reads the live-portion + promotes `stage="mastered"`; P103 only fills it |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib only | 3.12 | `dataclasses`, `datetime` (UTC ISO stamp), pure logic | Project rule: engine is pure-Python on existing primitives (REQUIREMENTS "no new heavy dependency") |

No new dependency. The phase adds only first-party modules. `pyproject.toml` is untouched.

## Package Legitimacy Audit

> Not applicable — Phase 103 installs **zero** external packages. The engine + recognizer are first-party pure-Python modules on existing primitives (REQUIREMENTS.md "Out of Scope: New heavy dependency"). No `npm install` / `pip install` / `cargo add`. slopcheck/registry verification is moot.

## Architecture Patterns

### System Architecture Diagram

```
                           OFFLINE-DELIVERABLE THIS PHASE (learn island)
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                            │
  │   Event(type, state, extra)                                                │
  │   (synthetic in tests; real EventDetector fire in live wiring)             │
  │         │                                                                  │
  │         ▼                                                                  │
  │   skill_recognizer.recognize(event, *, citation_check, progress)           │
  │         │                                                                  │
  │         ├──(1) reverse map: event.type / MIX_MOVE move-labels → skill_id(s)│
  │         │      no match → return [] (no fill, ever)                        │
  │         │                                                                  │
  │         ├──(2) MAST-01 gate: SkillTree.compute(progress)[skill].competent? │
  │         │      not Competent → SKIP that skill (no buffered backfill)      │
  │         │                                                                  │
  │         ├──(3) MAST-03 spine: citation_check(source, key, t) → bool        │
  │         │      ┌─────────────────────────────────────────────────┐        │
  │         │      │ injected predicate wraps EvidenceRegistry.has(   │        │
  │         │      │   source, key, t_target, tol) OR snapshot lookup │        │
  │         │      └─────────────────────────────────────────────────┘        │
  │         │      returns False (un-cited / fabricated) → ZERO credit         │
  │         │                                                                  │
  │         ├──(4) dedup: (event-identity) seen this call? → skip double-count │
  │         │                                                                  │
  │         ▼                                                                  │
  │   for each credited skill_id:                                             │
  │     skill_tree.record_live_demo(progress, skill_id, now=<injected>)        │
  │         │   increment live_proof_count                                     │
  │         │   if live_proof_count >= mastered_threshold and not mastered:    │
  │         │       mastered = True;  first_mastered_at = now  (once)          │
  │         ▼                                                                  │
  │   learn/progress.save_progress(progress)  ── atomic tmp + os.replace ──────┼──► learn-progress.json
  │         │                                            (skills block only)   │
  │         ▼                                                                  │
  │   SkillTree.compute(progress) reads it → stage="mastered"  (SHIPPED 102)   │
  └──────────────────────────────────────────────────────────────────────────┘

         DEFERRED KAAN-ACTION WIRING (NON-learn island — not this phase)
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  state/refresh.py (10Hz) → EventDetector.detect() → Event → coach_loop      │
  │  (runtime/coach.py, wired __main__.py:2051) ── would need to call the      │
  │  recognizer here. coach_loop touches NO learn module today.                │
  └──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities
| File | New / Changed | Responsibility |
|------|---------------|----------------|
| `src/vibemix/learn/skill_recognizer.py` | **NEW** | `recognize(event, *, citation_check, progress, now)` — reverse map + Competent gate + citation gate + dedup; returns the skills to credit (or applies credit directly via `record_live_demo`). Pure logic. Imports `EVENT→skill` map; imports `SkillTree`/`SKILL_MANIFEST` from `skill_tree`; takes the citation check as a callable. |
| `src/vibemix/learn/skill_tree.py` | **CHANGED (additive)** | Add `mastered_threshold` to `SkillSpec` (or a parallel constant); add `record_live_demo(progress, skill_id, *, now) -> LearnProgress`. The reverse `EVENT_SKILL_MAP` may live here (single source per GA2) or in the recognizer — recommend here, next to `SKILL_MANIFEST`. |
| `src/vibemix/learn/progress.py` | UNCHANGED | `save_progress` / `_fresh_skills_block` already shipped. `record_live_demo` mutates `progress.skills[...]` in place; the runtime calls `save_progress`. |
| `tests/learn/test_skill_recognizer.py` | **NEW** | MAST-01/02/03 + headline `test_uncited_event_grants_zero_mastery_credit`, `test_live_demo_noop_when_not_competent`. |
| `tests/learn/test_skill_tree.py` | **EXTEND** | `record_live_demo` unit tests + `test_first_mastered_at_idempotent` + threshold-flip + dedup. |

### Pattern 1: Injected citation predicate (keeps the engine offline + island-clean)
**What:** The recognizer never imports `EvidenceRegistry`; it takes a `citation_check: Callable[[str, str, float], bool]`. Live wiring passes a thin lambda wrapping `registry.has(...)`; tests pass a fake.
**When to use:** Always — this is the GA1/GA4 contract that keeps the engine pure and the import graph one-way (learn → no state/ runtime dependency).
**Example:**
```python
# Source: pattern mirrors learn/exemplar.py:356 (registry injected, Optional) +
# the agent/dj_cohost.py:240 grounding check (.has / snapshot lookup).

# In the recognizer (pure):
def recognize(
    event: Any,
    *,
    citation_check: Callable[[str, str, float], bool],
    progress: Any,
    now: str,
) -> list[str]: ...

# Live wiring (deferred, NON-learn) would pass:
citation_check = lambda source, key, t: registry.has(source, key, t, tol=1.0)

# Tests pass a synthetic predicate — no real registry needed:
cited   = lambda s, k, t: True
uncited = lambda s, k, t: False
```

### Pattern 2: The real EvidenceRegistry grounding contract (what the live predicate wraps)
**What:** `EvidenceRegistry.has(source, key, t_target, tol=1.0) -> bool` returns True iff some observation at `(source, key)` lies within `±tol` seconds (evidence_registry.py:386-409). Missing source/key returns False (no KeyError). For existence-only sources the agent uses `snapshot().get(source,{}).get(body)` truthiness (dj_cohost.py:285-288). Either is a valid grounding check; `has()` is the cleaner predicate.
**Source key shape for `ev` events:** the EventDetector writes `registry.write("ev", ev_type, t_session)` (event_detector.py:509) — so the key is the bare event type string (e.g. `"MIX_MOVE"`), and `t_session = now - state.set_start_at`. The recognizer's citation key for an `ev` credit is therefore `(source="ev", key=event.type, t_target=<event t_session>)`.

### Anti-Patterns to Avoid
- **Importing `EvidenceRegistry`/`EventDetector` into the recognizer for runtime use:** breaks the island + the offline-test contract. Type-only `TYPE_CHECKING` import is acceptable (exemplar.py:40 precedent); a runtime hard-dependency is not.
- **Storing `learn_fill`/`competent` in the `skills` block:** the live-portion stores ONLY `live_proof_count`/`mastered`/`first_mastered_at` (progress.py:105-112). `competent` is DERIVED every `compute()` call — re-storing it reintroduces dual-write drift.
- **Reading One-Mind-in-flux `state/` modules at runtime:** `state/event_detector.py`, `state/refresh.py`, `state/coach.py` are owned by concurrent sessions. Read the `Event.type` string contract only; never call into live state objects from the recognizer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Citation resolution | A new citation parser / registry walk | Inject a predicate wrapping `EvidenceRegistry.has()` | `has()` + `parse_citations` are the locked grounding contract (Invariant #2). Re-implementing risks divergence from the linter |
| Atomic persistence | A bespoke JSON writer | `learn/progress.save_progress()` | Already crash-safe (tmp + `os.replace`), DATA-01 contract |
| Stage promotion | New mastered-stage logic | `SkillTree.compute` (SHIPPED 102) | It already reads the live-portion + sets `stage="mastered"` (test-pinned `test_mastered_live_portion_promotes_stage`) — P103 only fills the fields |
| Schema migration | A v2→v3 migration | None — schema v2 already carries the `skills` block | 102-01 shipped v1→v2 with the live-portion; P103 needs **no** migration (CONTEXT code_context confirms) |

**Key insight:** Phase 102 deliberately left `record_live_demo` and the live-portion fields as the forward seam. P103 is mostly *filling a pre-built slot*, not building new persistence/derivation machinery.

## Runtime State Inventory

> Not a rename/refactor/migration phase — this is additive new logic. Section omitted per template guidance. (No stored data renames, no live-service config, no OS-registered state, no secret renames, no stale build artifacts.)

## Deliverable 1 — EXACT event-type constants + verified reverse event→skill map

**Event types are PLAIN STRING LITERALS, not an enum** (state/event.py docstring line 4-6: "string literals, not enum members, matching v4"). `Event.type: str`. The recognizer matches on these strings + (for `MIX_MOVE`) on the move-label substrings inside `event.extra["moves"]`.

### Every event-type string fired in `state/` (verified by grep this session)
Baseline (event_detector.py): `KAAN_SPOKE`, `MANUAL`, `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, `KEY_CLASH`, `TRANSITION_OPPORTUNITY`.
Genre-chain detectors: `DROP`, `DISTORTION_CLIMB`, `ACID_LINE_ENTRY`, `KICK_SWAP`, `KICK_DENSITY_SHIFT`, `BREAKDOWN_KICK_KILL`, `SUB_LAYER_ARRIVAL`, `PHRASE_BOUNDARY`, `REENTRY_KICK_LAND`.

### `MIX_MOVE` significance move-labels (the EQ/hotcue/loop discriminators)
`MIX_MOVE` fires on `state.recent_moves` labels matching: `killed`, `_low:`, `_mid:`, `_hi:`, `_filter:`, `xfader`, `big`, `_play→` (event_detector.py:325-334). The raw move-label vocabulary (midi/state.py `_record_move`):
- EQ-band twist: `"{deck}_low: <a>→<b> (<mag> twist)"`, `"{deck}_mid: ..."`, `"{deck}_hi: ..."` (from fields `eq_low`/`eq_mid`/`eq_hi`), plus `"{deck}_filter: ..."`.
- `"{deck}_cue_hit"`, `"{deck}_sync_hit"`, `"{deck}_loop_in_hit (play=ON)"`, `"{deck}_loop_out_hit"`, `"{deck}_jog nudge <dir>"`, `"{deck}_vol <dir> (<mag>)"`, `"{deck}_tempo <dir> (<mag>)"`.
- **NOTE:** hot-cue/loop hits are recorded as moves but are NOT in the `MIX_MOVE` significance set — so a bare hot-cue press does NOT fire a `MIX_MOVE`. See the deck_control gap below.

### Verified reverse map (which REAL signal credits which of the 6 skills)

| Skill | Cleanest existing signal | Citation source/key | Confidence | Notes |
|-------|--------------------------|---------------------|------------|-------|
| `eq_mixing` | `MIX_MOVE` whose `extra["moves"]` contains `_low:`/`_mid:`/`_hi:`/`killed` | `("ev", "MIX_MOVE", t)` | **HIGH** | EQ-band twists + kills are the literal significance keys. Clean. |
| `transitions` | `LAYER_ARRIVAL`, OR `TRANSITION_OPPORTUNITY` (retrospective completed-transition) | `("ev", "LAYER_ARRIVAL", t)` | **MEDIUM-HIGH** | `LAYER_ARRIVAL` is a layer/element arrival, a reasonable transition proxy. `TRANSITION_OPPORTUNITY` is the truer signal but is **default-OFF** (see below). |
| `phrasing_performance` | `PHASE` transition, OR `PHRASE_BOUNDARY` (genre-chain) | `("ev", "PHASE", t)` / `("ev", "PHRASE_BOUNDARY", t)` | **MEDIUM** | `PHASE` always fires; `PHRASE_BOUNDARY` only on the genre chain when active. Count-in is a *coach lens* (coach.py `_count_in_eligible`), NOT an event — cannot cite it. Use `PHASE`/`PHRASE_BOUNDARY`. |
| `deck_control` | `MIX_MOVE` whose moves contain `_play→`/`xfader`, OR `MANUAL` | `("ev", "MIX_MOVE", t)` | **MEDIUM** | **GAP:** hot-cue/loop hits (the CONTEXT-named deck_control signal) do NOT fire `MIX_MOVE` (not in the significance set). The citable deck signals are play-toggle + xfader. Hot-cue/loop are only present as `midi`-source moves, never surfaced as a fired `ev`. |
| `beatmatching` | **NONE (clean)** | — | **LOW / NO SIGNAL** | **LOAD-BEARING GAP.** There is no `BEATMATCH`/`SYNC_ENGAGED` event type. `"{deck}_sync_hit"` exists as a MIDI move but is NOT in the `MIX_MOVE` significance set, so no `ev` ever fires for it. On-beat-blend is not a detected/citable event. |
| `harmonic_mixing` | `KEY_CLASH` / `TRANSITION_OPPORTUNITY` — both **default-OFF** | `("ev", "KEY_CLASH", t)` | **LOW / DISABLED** | **LOAD-BEARING GAP.** The only harmonic events are gated behind `EventDetector(harmonic_clash_enabled=...)` which defaults False and is never flipped in `__main__.py` (gated behind the unshipped Plan 60-03 Kaan-ear veto). In a real session today these events NEVER fire. |

### LOAD-BEARING FINDING (MAST-02)
**Two of the six skills — `beatmatching` and `harmonic_mixing` — have no clean, citable, currently-firing event signal.** `beatmatching` has no event at all (sync is a MIDI move below the `MIX_MOVE` significance threshold). `harmonic_mixing` has events (`KEY_CLASH`/`TRANSITION_OPPORTUNITY`) but they are default-OFF and never enabled in production. MAST-02 forbids inventing new detectors, so these two cannot earn honest Mastered credit in v11.0 without either (a) enabling the dormant harmonic path (touches `state/`/`__main__.py` — outside the island, KAAN-ACTION) or (b) accepting a documented proxy. **Recommendation:** the recognizer should *recognize* all six skills (the map is complete), but the plan should mark `beatmatching` + `harmonic_mixing` as **proxy-credited or uncreditable-in-v11.0**, defended by an explicit test that pins whichever decision is made, and surface this as a KAAN-ACTION note (it directly informs `§EARNED-MASTERY-THRESHOLD-TUNE` and `§EARNED-LIVE-MASTERED-VERIFY`). Do NOT silently map them to a wrong signal as if it were ground truth — that is the exact false-expertise anti-slop class this product guards.

## Deliverable 2 — EXACT EvidenceRegistry citation-resolution interface

The recognizer's predicate wraps one of these (both verified in source):

1. **`EvidenceRegistry.has(source: str, key: str, t_target: float, tol: float = 1.0) -> bool`** (evidence_registry.py:386-409). Returns True iff an observation at `(source, key)` lies within `±tol` of `t_target`. Missing source/key → False (no raise). Live tolerance is `tol=1.0`; debrief `tol=2.0` (GROUND-07). **This is the recommended predicate** — it's the same call the Phase 20 linter uses.
2. **Snapshot existence check** — `registry.snapshot().get(source, {}).get(key)` truthiness (dj_cohost.py:285-288). Used for existence-only sources (`key`/`track`/`recall`/`exemplar`/`cue`). For `ev` events the time-keyed `has()` is more precise.

For an `ev`-sourced credit the lookup is `has("ev", event.type, t_target=<event's t_session>, tol=1.0)`. The EventDetector wrote that exact tuple at fire time (`registry.write("ev", ev_type, t_session)`, event_detector.py:509).

**Offline-exercisable? YES.** `EvidenceRegistry()` constructs with no required args (evidence_registry.py:227 — all kwargs optional). A test can do `reg = EvidenceRegistry(); reg.write("ev", "MIX_MOVE", 12.3)` and then `reg.has("ev", "MIX_MOVE", 12.3)` returns True; `reg.has("ev", "FABRICATED", 12.3)` returns False. The `on_mutation` scheduler silently no-ops without a running loop (evidence_registry.py:476-480), so sync test code is safe. **But for engine purity, prefer injecting a synthetic `Callable` predicate** rather than a real registry in the recognizer unit tests — keeps the recognizer import-graph-clean and the test fast. Use a real `EvidenceRegistry` only in one integration-flavored test that proves the live predicate shape resolves correctly.

## Deliverable 3 — The precise learn-side integration seam

**FINDING: there is NO in-island seam that observes live co-host events.** Verified:
- `learn/runtime.py::LessonRuntime` receives `evidence_registry` (runtime.py:389, wired `__main__.py:1853`) but only *writes* lesson-action observations (`_record_evidence` → `registry.write`, runtime.py:1214-1232). It reads MIDI for *lesson* actions via `MidiMirror`/`ControllerState`, never `EventDetector.detect()` output. It has no callback for live co-host event fires.
- `learn/teaching_loop.py` is pure planning logic (no event observation).
- The live event→reaction loop is `runtime/coach.py::coach_loop` (the `runtime/` island), wired in `__main__.py:2051`. Grep confirms `coach_loop` references **zero** learn/skill/lesson_runtime symbols.
- `event_detector` (`__main__.py:925`) and `lesson_runtime` (`__main__.py:1847`) are separate objects; the only shared object is the `EvidenceRegistry`, which is a write/read store, not an event bus.

**Honest conclusion (per CONTEXT GA4's explicit escape hatch):** The recognizer + `record_live_demo` + the reverse map + all MAST tests are **fully deliverable offline this phase**. The *live wiring* — calling the recognizer when a real `EventDetector` fire happens during an actual set — requires touching `runtime/coach.py` (add a recognizer-notify call after `event_detector.detect()`) or `__main__.py` (register an observer), **both outside the learn island.** Per the hard concurrency rule, **STOP and flag this as a deferred KAAN-ACTION wiring item** rather than touch a non-learn file. `§EARNED-LIVE-MASTERED-VERIFY` (already on the v11.0 KAAN-ACTION queue) is the natural home; the plan should expand its scope note to include "wire `coach_loop`/`__main__` to feed live fires into `skill_recognizer`."

**Minimal-surface option for WHEN the wiring is greenlit (document, do not build):** add a single optional `on_live_event: Callable[[Event], None] | None` hook the live loop calls, with the learn side supplying a closure that calls `skill_recognizer.recognize(...)`. This is one call site in `coach_loop` and one closure construction in `__main__`. Both are NON-learn files → KAAN-ACTION. (Alternatively a learn-side `LiveDemoObserver` object registered onto the loop — same cross-island requirement.)

## Deliverable 4 — Recommended `mastered_threshold` + dedup mechanism

### Threshold
**Recommend uniform `mastered_threshold = 3`** (matches CONTEXT GA3 "N≈3"), declared as a per-skill field on `SkillSpec` so it is *tunable per skill* without code change (mirrors how 102 made weights tunable constants). Defend with a test that pins the *flip-at-N behavior*, not the literal N (mirror 102's "the ordering is the contract, not the numbers" precedent — `test_quality_weighted_fill_ordering`). Per-skill override is cheap and future-proofs `§EARNED-MASTERY-THRESHOLD-TUNE` (the queued Kaan tuning item). Put the field on `SkillSpec` with a default of `3` so the existing 6 manifest entries don't all need editing if uniform.

### Dedup (event-identity)
**Recommend `(event.type, t_session)` tuple** as the identity key, deduped *within a single `recognize()` call* and *not double-credited across rapid re-calls of the same fire*. Rationale: `Event` has no stable id field (event.py — fields are `type`, `state`, `extra`, `priority`; no uuid). The `(type, t_session)` pair is what the EventDetector itself uses as the registry key+timestamp, so it is the natural identity. Since `EventDetector` already enforces per-type cooldowns (`MIN_EVENT_GAP_PER_TYPE`, event_detector.py:164-167), the same logical event won't fire twice within the cooldown window — so the dedup only needs to guard against the *same fire* being handed to the recognizer twice (e.g. a retry). Keep a small recent-seen set of `(type, round(t_session, 1))` on the recognizer call or the observer; do NOT persist it (transient, per-session). A single `MIX_MOVE` mapping to multiple skills (e.g. EQ + deck_control) is NOT a double-count — it is one event crediting multiple distinct skills, which is correct and intended.

## Common Pitfalls

### Pitfall 1: Treating `beatmatching`/`harmonic_mixing` proxies as ground truth
**What goes wrong:** Mapping `beatmatching` to e.g. `TRACK_CHANGE` or `harmonic_mixing` to any audible event, then crediting Mastered as if the skill was truly demonstrated.
**Why it happens:** The 6-skill symmetry tempts a "complete the map" instinct; the gaps are easy to paper over.
**How to avoid:** Either (a) leave these two recognizer-recognized but uncreditable in v11.0 (flag KAAN-ACTION), or (b) credit a documented proxy with an explicit `# PROXY:` comment + a test asserting it is a proxy. Never present a proxy credit as a real demonstration.
**Warning signs:** A test that asserts `beatmatching` reaches Mastered from a `sync_hit` or `TRACK_CHANGE` without a comment explaining it is a proxy.

### Pitfall 2: `first_mastered_at` overwrite on later demos
**What goes wrong:** A 4th, 5th grounded demo re-stamps `first_mastered_at`, losing the true first-mastery moment.
**Why it happens:** Naive `record_live_demo` sets the timestamp every time the threshold is met-or-exceeded.
**How to avoid:** Set `first_mastered_at` ONLY on the transition `not mastered → mastered` (guard `if not mastered and count >= threshold:`). Once `mastered=True`, only `live_proof_count` may keep incrementing. Pinned by `test_first_mastered_at_idempotent`.
**Warning signs:** `first_mastered_at` changes between two `compute()` calls after mastery.

### Pitfall 3: Citation-interface coupling to live `state/`
**What goes wrong:** Importing `EvidenceRegistry` into the recognizer for runtime use, hard-coupling the engine to a One-Mind-in-flux module + breaking offline testability.
**Why it happens:** It seems simpler to pass the registry directly than to inject a predicate.
**How to avoid:** Inject `citation_check: Callable[[str, str, float], bool]`. Type-only `TYPE_CHECKING` import is fine (exemplar.py:40 precedent). The live wiring (KAAN-ACTION) supplies the lambda.
**Warning signs:** `from vibemix.state.evidence_registry import EvidenceRegistry` outside a `TYPE_CHECKING` block in `skill_recognizer.py`.

### Pitfall 4: Double-counting one event across rapid re-delivery
**What goes wrong:** The same `(type, t_session)` fire credits a skill twice → inflated `live_proof_count` → premature Mastered.
**How to avoid:** Dedup by `(type, round(t_session,1))` within the credit path. Note one event crediting *multiple distinct skills* is NOT a double-count.
**Warning signs:** `live_proof_count` jumps by 2 on a single fire.

### Pitfall 5: MAST-01 ordering — reading Competent from stored fields
**What goes wrong:** Checking `progress.skills[skill]["competent"]` — but `competent` is NOT stored (it's derived). The stored block has only `live_proof_count`/`mastered`/`first_mastered_at`.
**How to avoid:** Compute Competent via `SkillTree().compute(progress)[skill_id].competent` inside the MAST-01 gate. This is a pure call, cheap. Pinned by `test_live_demo_noop_when_not_competent`.
**Warning signs:** A `KeyError`/`AttributeError` on `competent`, or a no-op gate that never triggers.

### Pitfall 6: Reading One-Mind-in-flux `state/` modules
**What goes wrong:** Importing/calling `state/refresh.py`, `state/coach.py`, or `state/event_detector.py` live objects from learn — those are owned by concurrent sessions and may change under you.
**How to avoid:** Depend ONLY on the stable `Event.type` string contract and the `EvidenceRegistry.has()` signature. Both verified stable this session. The recognizer consumes a synthetic event shape in tests.

## Code Examples

### `record_live_demo` skeleton (the deferred-from-102 mutator)
```python
# Source: shape derived from skill_tree.py SkillProgress fields + progress.py
# _fresh_skills_block live-portion contract (verified this session).
def record_live_demo(progress, skill_id, *, now: str):
    """Increment live_proof_count for one skill; flip to Mastered at threshold.

    PURE-ish transform: mutates progress.skills[skill_id] in place and returns
    progress. Idempotent first_mastered_at. NO-OP if the skill is not Competent
    (MAST-01) — caller checks via SkillTree.compute(progress)[skill_id].competent.
    """
    block = progress.skills.setdefault(skill_id, {
        "live_proof_count": 0, "mastered": False, "first_mastered_at": None,
    })
    if block.get("mastered"):
        # already mastered — count may still increment, ts NEVER re-stamped
        block["live_proof_count"] = int(block.get("live_proof_count", 0) or 0) + 1
        return progress
    block["live_proof_count"] = int(block.get("live_proof_count", 0) or 0) + 1
    threshold = _threshold_for(skill_id)  # SkillSpec.mastered_threshold, default 3
    if block["live_proof_count"] >= threshold:
        block["mastered"] = True
        block["first_mastered_at"] = now   # stamped exactly once
    return progress
```

### Synthetic cited-vs-uncited event stream (the test construction)
```python
# Source: EvidenceRegistry() no-arg construct (evidence_registry.py:227) +
# Event(type, state, extra) (event.py). Use a synthetic predicate to stay
# island-clean; a real registry only in one integration test.
def _cited(_s, _k, _t):   return True
def _uncited(_s, _k, _t): return False

def _event(ev_type, t=10.0, moves=None):
    extra = {"moves": moves} if moves else {}
    return Event(ev_type, _stub_state(), extra=extra)   # _stub_state: minimal MusicState

# Cited MIX_MOVE with an EQ move → credits eq_mixing.
ev = _event("MIX_MOVE", moves=["A_low: open→killed (big twist)"])
recognize(ev, citation_check=_cited, progress=competent_progress, now=NOW)
# Uncited (fabricated) identical event → ZERO credit (headline test).
recognize(ev, citation_check=_uncited, progress=competent_progress, now=NOW)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| (102) Mastered fill was a forward seam — fields stored, never written | (103) `record_live_demo` writes them; recognizer gates on citation | This phase | P103 fills a pre-built slot; no schema/migration work |
| Event taxonomy | Plain string `Event.type`, no enum | Since v4 port | The reverse map keys on string literals, not enum members |

**Deprecated/outdated:** none relevant. The `KEY_CLASH`/`TRANSITION_OPPORTUNITY` harmonic events exist but are *dormant* (default-OFF), not deprecated.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `LayerArrival`/`PHASE` are acceptable proxies for `transitions`/`phrasing_performance` Mastered credit | Deliverable 1 | If Kaan deems them too coarse, those skills also become weak-signal — widens the KAAN-ACTION. Low risk (both are real, citable, fire in production). |
| A2 | Uniform `mastered_threshold=3` is the right default | Deliverable 4 | Pure tunable; `§EARNED-MASTERY-THRESHOLD-TUNE` already owns the post-verify tune. Near-zero risk. |
| A3 | The live-loop wiring belongs under `§EARNED-LIVE-MASTERED-VERIFY` rather than a new KAAN-ACTION | Deliverable 3 | Organizational only; the plan can split it out. No correctness impact. |

**Everything else in this research was VERIFIED by reading source this session** (event types, registry signature, learn seam absence, schema fields, atomic-write helper).

## Open Questions

1. **`beatmatching` + `harmonic_mixing` — proxy-credit or declare uncreditable-in-v11.0?**
   - What we know: neither has a clean citable production event (sync is sub-significance MIDI; harmonic events are default-OFF).
   - What's unclear: whether Kaan wants a documented proxy (so all 6 bars *can* reach Mastered) or honest "these unlock in v11.x when the detector lands."
   - Recommendation: plan-phase decides; pin the decision with a test either way. Surface to Kaan via the KAAN-ACTION note. Do not silently proxy.

2. **`deck_control` hot-cue/loop signal gap.**
   - What we know: hot-cue/loop hits are MIDI moves but never fire a `MIX_MOVE` (`_play→`/`xfader` do).
   - Recommendation: credit `deck_control` from the play-toggle/xfader `MIX_MOVE` + `MANUAL`; document that hot-cue/loop specifically aren't citable as `ev`. Acceptable — deck control is broader than hot-cues.

## Environment Availability

> Skipped — Phase 103 is pure-logic, code-only, offline-unit-testable. No external tools, services, runtimes, or CLI utilities beyond the Python 3.12 venv already required to run `tests/learn`. (Standalone-verifiable per the phase spine: "Engine-level verifiable on synthetic event streams.")

## Validation Architecture

> nyquist_validation enabled (no `workflow.nyquist_validation: false` in config). This section drives VALIDATION.md.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard; `[tool.pytest.ini_options]` in `pyproject.toml`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/learn/test_skill_recognizer.py tests/learn/test_skill_tree.py -q` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/learn -q` |

**Critical runner note (102 precedent):** bare `python3` is 3.14 and CANNOT import the learn package (`__init__` pulls `sqlite_vec`). ALL verification MUST run under `source .venv/bin/activate && PYTHONPATH=src python3` (3.12). Baseline before this phase: `tests/learn` = 479 passed / 1 skipped.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAST-01 | Locked-until-Competent: `record_live_demo` is a no-op for a non-Competent skill | unit | `pytest tests/learn/test_skill_recognizer.py::test_live_demo_noop_when_not_competent -x` | ❌ Wave 0 |
| MAST-02 | Reverse map credits each clean skill from its REAL event type; unmapped event → no credit | unit | `pytest tests/learn/test_skill_recognizer.py::test_event_skill_map_credits_real_events -x` | ❌ Wave 0 |
| MAST-02 | `beatmatching`/`harmonic_mixing` weak-signal decision is pinned (proxy-tagged OR uncreditable) | unit | `pytest tests/learn/test_skill_recognizer.py::test_weak_signal_skills_decision_pinned -x` | ❌ Wave 0 |
| MAST-03 | **HEADLINE:** a fabricated/un-cited event grants ZERO mastery credit | unit | `pytest tests/learn/test_skill_recognizer.py::test_uncited_event_grants_zero_mastery_credit -x` | ❌ Wave 0 |
| MAST-03 | A cited event DOES credit (the positive control for the headline) | unit | `pytest tests/learn/test_skill_recognizer.py::test_cited_event_grants_credit -x` | ❌ Wave 0 |
| MAST-04 | N grounded demos flip `mastered=True` + stamp `first_mastered_at`; persists | unit | `pytest tests/learn/test_skill_tree.py::test_record_live_demo_flips_mastered_at_threshold -x` | ❌ Wave 0 (extends existing file) |
| MAST-04 | `first_mastered_at` stamped exactly once (idempotent on later demos) | unit | `pytest tests/learn/test_skill_tree.py::test_first_mastered_at_idempotent -x` | ❌ Wave 0 |
| MAST-04 | The same event identity does not double-count `live_proof_count` | unit | `pytest tests/learn/test_skill_recognizer.py::test_event_identity_dedup_no_double_count -x` | ❌ Wave 0 |
| MAST-04 | Mastered persists across reload (save→load round-trip; engine reads stage="mastered") | unit | `pytest tests/learn/test_skill_tree.py::test_mastered_persists_across_reload -x` | ❌ Wave 0 (extends; complements existing `test_mastered_live_portion_promotes_stage`) |
| Invariant | Recognizer does NOT import `EvidenceRegistry`/`EventDetector` for runtime use (TYPE_CHECKING only) + no MusicState write | unit | `pytest tests/learn/test_skill_tree_invariants.py -x` (extend with a recognizer-import gate) | ⚠️ EXTEND existing |

### Synthetic cited-vs-uncited event stream construction (the headline test machinery)
The headline `test_uncited_event_grants_zero_mastery_credit` is built WITHOUT a live registry: inject two predicates — `cited = lambda s,k,t: True` and `uncited = lambda s,k,t: False` — and feed the SAME `Event("MIX_MOVE", stub_state, extra={"moves":[...]})` to `recognize()` with each. Assert the cited call increments `live_proof_count` for `eq_mixing`, the uncited call leaves it at 0. One additional integration-flavored test uses a real `EvidenceRegistry()` (no-arg construct) with `reg.write("ev","MIX_MOVE",t)` then `reg.has("ev","MIX_MOVE",t)` to prove the live predicate shape resolves — keeping the rest of the suite registry-free for purity.

### Sampling Rate
- **Per task commit:** `pytest tests/learn/test_skill_recognizer.py tests/learn/test_skill_tree.py -q` (~ms, pure logic)
- **Per wave merge:** `pytest tests/learn -q` (full learn island; baseline 479 passed / 1 skipped)
- **Phase gate:** full `tests/learn` green before `/gsd:verify-work`; the live-FLX4 verify is the KAAN-ACTION (`§EARNED-LIVE-MASTERED-VERIFY`), not an automatable gate.

### Wave 0 Gaps
- [ ] `tests/learn/test_skill_recognizer.py` — covers MAST-01/02/03 + headline + dedup (NEW file)
- [ ] `tests/learn/test_skill_tree.py` — EXTEND with `record_live_demo` flip/idempotent/reload tests (existing file, additive)
- [ ] `tests/learn/test_skill_tree_invariants.py` — EXTEND with a recognizer no-runtime-import gate (existing file, additive)
- [ ] No framework install needed — pytest + the 3.12 venv already drive `tests/learn`.

## Security Domain

> `security_enforcement` defaults enabled. This phase is pure local in-memory logic + a local JSON write; no network, no auth, no external input beyond a local synthetic/real event and a local registry. ASVS surface is minimal.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app; no auth surface |
| V3 Session Management | no | No sessions/tokens |
| V4 Access Control | no | No multi-user/privilege boundary |
| V5 Input Validation | yes | `record_live_demo`/`compute` already degrade non-numeric `live_proof_count` to a safe default (skill_tree.py:294-297); the recognizer must mirror this never-raises posture for hand-edited/garbage `skills` blocks |
| V6 Cryptography | no | No crypto; `first_mastered_at` is a plain ISO timestamp |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hand-edited `learn-progress.json` inflates `live_proof_count` to fake Mastered | Tampering | Out of v11.0 threat scope (local single-user file the user owns); but the recognizer must NOT crash on garbage values — degrade to safe default (mirror skill_tree.py guard). Anti-slop integrity is the citation gate, not file tamper-proofing. |
| Fabricated/un-cited event grants credit | Spoofing (of evidence) | **The MAST-03 spine** — citation gate via `EvidenceRegistry.has()`; un-cited → zero credit. Test-pinned (`test_uncited_event_grants_zero_mastery_credit`). This IS the security-relevant control of the phase. |
| Corrupt `skills` block wedges the engine | DoS | `from_dict` seeds defaults on missing/non-dict `skills` (progress.py:360-363); `compute` never raises on inner garbage (skill_tree.py:294-297). `record_live_demo` must `setdefault` the block + guard `int()` the same way. |

## Project Constraints (from CLAUDE.md)
- **GSD-only edits:** start through a GSD command; no direct edits outside the workflow.
- **Island discipline (`feedback_concurrent_sessions_one_tree`):** surgical commits, named `--files`, never `git add -A`. P103's island is `src/vibemix/learn/` + `tests/learn/`. Do NOT touch `state/`, `agent/`, `__main__.py` (concurrent-session owned).
- **Conventions:** `snake_case`/`PascalCase`/`UPPER_SNAKE_CASE`; `from __future__ import annotations`; PEP 604 unions; comments explain *why*; injected timestamps for determinism (102 precedent).
- **No hardcoded model literals:** N/A — this phase resolves no model (pure logic, no LLM call).
- **Cardinal invariants** (all hold by ADDITIVE design): #1 single-writer (recognizer is pure; only `record_live_demo` mutates, only the `skills` block); #2 citation grounding (the MAST-03 spine); #3 trust-the-audio (un-cited/fabricated → zero credit); #4 one socket (no new port — no IPC in this phase, that's P104).
- **Privacy:** never write `profile.json` (5-field `additionalProperties:false`); skill data lives in `learn-progress.json` only — already enforced + test-pinned in 102.

## Sources

### Primary (HIGH confidence — read from source this session)
- `src/vibemix/learn/skill_tree.py` — `SKILL_MANIFEST`, `SkillSpec(lesson_ids, gate)`, `SkillProgress` (fields incl. `live_proof_count`/`mastered`/`first_mastered_at`), `SkillTree.compute` (already promotes `stage="mastered"`).
- `src/vibemix/learn/progress.py` — `_fresh_skills_block` live-portion shape, `save_progress` (atomic tmp+os.replace), `from_dict` v1→v2 routing + garbage-degradation, schema v2 (no new migration needed).
- `src/vibemix/state/event_detector.py` — exact event-type literals + `MIX_MOVE` significance keys + `_fire` registry write (`write("ev", ev_type, t_session)`) + `harmonic_clash_enabled=False` default-OFF.
- `src/vibemix/state/event.py` — `Event.type: str` (plain string, no enum); `EVENT_PRIORITY` full set.
- `src/vibemix/state/evidence_registry.py` — `has(source, key, t_target, tol=1.0)`, `write`, `snapshot`, `EVIDENCE_SOURCES`, no-arg constructibility.
- `src/vibemix/learn/runtime.py` — `LessonRuntime` only WRITES lesson observations to the registry; no live-event observation seam.
- `src/vibemix/learn/teaching_loop.py` — pure planning, no event observation.
- `src/vibemix/agent/dj_cohost.py:181-290` — the live citation-grounding pattern (`parse_citations` + `snapshot.get(...).get(body)`) the predicate mirrors.
- `src/vibemix/midi/state.py` — `_record_move` label vocabulary (EQ-band, sync_hit, loop/cue hits).
- `tests/learn/test_skill_tree.py`, `tests/learn/test_runtime_invariants.py` — test idioms to extend; the existing `test_mastered_live_portion_promotes_stage` forward seam.
- `.planning/phases/102-.../102-02-SUMMARY.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, CONTEXT.md.

### Secondary / Tertiary
- None — no WebSearch/Context7 needed (pure first-party implementation-readiness; all facts verifiable in-repo).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; all primitives shipped + read this session.
- Architecture / seam: HIGH — the no-learn-seam finding is grep+read-verified (coach_loop references zero learn symbols; LessonRuntime only writes the registry).
- Event→skill map: HIGH for the 4 clean skills (exact literals verified); the `beatmatching`/`harmonic_mixing` GAP is a HIGH-confidence *negative* finding (no event exists / events are default-OFF, verified in source).
- Pitfalls: HIGH — derived from the actual shipped guards + invariant gates.

**Research date:** 2026-05-29
**Valid until:** ~2026-06-28 (stable — pure-logic, first-party; the only churn risk is concurrent edits to `state/event_detector.py` event types, which would only ADD literals, not remove the ones mapped).
