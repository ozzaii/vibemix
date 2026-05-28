# Phase 102: Skill-Tree Engine + Data Model + Competent Stage - Research

**Researched:** 2026-05-29
**Domain:** Pure-logic Python skill-tree engine + JSON schema migration on an existing local-cache file (no external deps, no network, no UI)
**Confidence:** HIGH (everything verified against the actual shipped source on this branch; zero external-library risk — phase adds no packages)

## Summary

Phase 102 is a self-contained, offline-unit-testable engine phase. It adds one new pure-logic module (`src/vibemix/learn/skill_tree.py`) plus a `skills` block on the existing `learn-progress.json`, mapping the shipped 36 real lessons (C1×16 + C2×14 + C3×6; `course_0` is a hello-world demo that feeds no skill) onto 6 named DJ skills, each with a quality-weighted "Competent" fill that is gated behind a real recital pass. There is no new dependency, no new port, no new IPC envelope, no new AI provider — the entire phase is plain Python on `dataclasses` + `json` + the existing atomic-write idiom in `progress.py`. The headline product assertion ("100% click-through, no recital → NOT Competent") is a unit test on a pure function.

Two load-bearing facts surfaced that the planner MUST design around (both verified in-source, not assumed):
1. **The existing `LearnProgress.from_dict` short-circuits to a fresh-empty object on ANY `schema_version != SCHEMA_VERSION`, and an existing test (`test_schema_version_mismatch_returns_fresh_empty`) writes `schema_version: 2` and asserts fresh-empty.** Bumping `SCHEMA_VERSION` to 2 to carry the `skills` block will break that test — it must be rewritten into a real v1→v2 migration test, not left as a "future schema = wipe" seam.
2. **There is NO Course-3 completion flag.** `course_2_unlocked` and `course_3_unlocked` are *unlock* gates (C1-recital → unlock C2; C2-recital → unlock C3). Course 3 has no recital and no completion bit, and the `courses` dict in `LearnProgress` is **only ever cleared to `{}`, never populated** — so `phrasing_performance`'s gating "recital" must be defined as a derived check, not a stored flag. Recommended below: gate `phrasing_performance` on `course_3_unlocked` (the honest C2 recital pass that *earns entry* to play mode) — the only honest-score gate that touches the C3 boundary today.

**Primary recommendation:** Mirror `progress.py` exactly — derive the learn-portion (fill + competent bool) by recomputing from `LearnProgress` on every load; store ONLY the live-portion (`live_proof_count`/`mastered`/`first_mastered_at`) in a new `skills` block; bump `SCHEMA_VERSION` 1→2 with an explicit `_migrate_v1_to_v2` upgrader inside `from_dict` (NOT the wipe seam); keep `skill_tree.py` I/O-free and `MusicState`-free. Put the live-ledger atomic-write helper in `progress.py` (not a new module) so the single `learn-progress.json` round-trip stays one file, one writer.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill→lesson manifest (SKILL_MANIFEST) | Pure logic (`learn/skill_tree.py` module constant) | — | Static declaration; readable by a contributor without running anything (SKILL-03) |
| Compute skill stage + fill (`SkillTree.compute`) | Pure logic (`learn/skill_tree.py`) | reads `LearnProgress` | Deterministic pure function over an in-memory dataclass; no I/O, no clock, no `MusicState` (Invariant #1) |
| Quality-weighted fill math (COMP-01) | Pure logic (`learn/skill_tree.py`) | — | Weights are module constants; fill is a normalized fraction in [0,1] |
| Competent recital gate (COMP-02) | Pure logic (`learn/skill_tree.py`) | reads `LearnProgress.course_N_unlocked` | Honest-score gate read from the persisted unlock flags written by `RecitalRuntime` |
| Persist live-portion `skills` block (DATA-01) | Persistence (`learn/progress.py` extension) | — | Same `~/.cache/vibemix/learn-progress.json`, same atomic `tmp.write_text`→`os.replace` |
| v1→v2 migration + corrupt recovery (DATA-02) | Persistence (`learn/progress.py::from_dict`/`load_progress`) | — | Migration seam already lives in `from_dict`; corrupt recovery already in `load_progress` |
| Reset path (DATA-03) | Persistence (`learn/progress.py` + `__main__.py` `learn reset` + `ipc_handlers.py` reset) | — | Mirrors the existing lesson-progress reset; clears the live-portion ledger |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.12 | `SkillProgress` / engine model | `LearnProgress` precedent; no pydantic (project D-Area-4.4) `[VERIFIED: src/vibemix/learn/progress.py]` |
| Python stdlib `json` | 3.12 | persist `skills` block in `learn-progress.json` | Existing file is already plain JSON via `json.dumps(..., indent=2, sort_keys=True)` `[VERIFIED: progress.py:283]` |
| Python stdlib `os`/`pathlib` | 3.12 | atomic `os.replace(tmp, target)` | Existing `save_progress` idiom `[VERIFIED: progress.py:265-286]` |
| `jsonschema` | `>=4.23,<5` (already pinned) | OPTIONAL: validate the `skills` block shape on read | Same Draft-07 idiom as `profile/schema.py`; pydantic banned `[VERIFIED: pyproject.toml:97]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `ast` | 3.12 | Invariant-pin static gates | Mirror `tests/learn/test_runtime_invariants.py` (currently regex-based, not `ast`) `[VERIFIED]` |
| stdlib `re` | 3.12 | static-grep gates (no-new-port, no-MusicState-write) | The shipped invariant gate uses line-oriented `re`, not `ast` — match that idiom `[VERIFIED: test_runtime_invariants.py:38-41]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Storing live-portion in `learn-progress.json` | A new `skill-ledger.json` file | Rejected by CONTEXT — second file = second corrupt-recovery path + second reset path; one file is simpler and matches the locked decision |
| `jsonschema` validation of the `skills` block | Inline `isinstance`/`.get(..., default)` guards | Inline guards are lighter and match `from_dict`'s existing style; jsonschema is optional belt-and-suspenders. Recommend inline guards (the rest of `progress.py` uses them) — reserve jsonschema for `profile.json` where the privacy contract demands it |

**Installation:** None. This phase adds zero packages — `[VERIFIED: pyproject.toml]` already pins everything used (stdlib + the existing `jsonschema`).

## Package Legitimacy Audit

> Not applicable — Phase 102 installs **no external packages**. The engine is pure-Python on the standard library plus the already-pinned `jsonschema>=4.23,<5` (verified present in `pyproject.toml:97`, used today by `profile/schema.py` and the IPC validator). slopcheck N/A.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌─────────────────────────────────────┐
   learn-progress.json    │  load_progress()  (progress.py)      │
   (~/.cache/vibemix/)────►│  - read + json.loads                │
        │                 │  - corrupt? → fresh-empty v2 + flag  │
        │                 │  - from_dict() → MIGRATE v1→v2:      │
        │                 │      seed 6-skill live-portion block │
        │                 │      (count 0 / mastered false /     │
        │                 │       first_mastered_at null)        │
        │                 └───────────────┬─────────────────────┘
        │                                 │ LearnProgress (has .skills live block)
        │                                 ▼
        │                 ┌─────────────────────────────────────┐
        │                 │  SkillTree.compute(progress)         │
        │                 │  (skill_tree.py — PURE, no I/O)      │
        │                 │                                      │
        │   SKILL_MANIFEST│  for each of 6 skills:               │
        │   (module const)│   1. DERIVE learn_fill from          │
        │   skill→{lessons}──► progress.lessons (quality-weighted)│
        │   skill→recital │   2. READ recital gate from          │
        │                 │      progress.course_N_unlocked      │
        │                 │   3. READ live-portion from          │
        │                 │      progress.skills[skill]          │
        │                 │   4. stage = Locked|Competent|Master │
        │                 └───────────────┬─────────────────────┘
        │                                 │ dict[str, SkillProgress]
        │                                 ▼
        │                        (P104 reads for display;
        │                         P103 calls record_live_demo)
        │
        └──◄── save_skills_block() / save_progress()  (atomic tmp→os.replace)
               writes ONLY the live-portion back; learn-portion is never stored
```

Data flow: the file is the only persistent state; `compute()` is a pure projection that joins the DERIVED learn-portion with the STORED live-portion. Nothing flows *into* `MusicState` — the diagram has no edge to the live deck (that is the Invariant #1 pin).

### Recommended Project Structure
```
src/vibemix/learn/
├── progress.py        # EXTEND: SCHEMA_VERSION 1→2, skills block in dataclass + to_dict/from_dict,
│                      #         _migrate_v1_to_v2(), save_skills helper (the live-ledger atomic write)
├── skill_tree.py      # NEW: SKILL_MANIFEST + SkillProgress dataclass + SkillTree.compute (pure)
├── recital.py         # UNCHANGED (read its course_N_unlocked output only)
└── curriculum.py      # UNCHANGED (SKILL_MANIFEST references its lesson IDs; import-time assert)

tests/learn/
├── test_skill_tree.py            # NEW: fill math, manifest↔curriculum drift, Competent gate, click-through case
├── test_skill_tree_invariants.py # NEW: 3 invariant pins (no MusicState write, no new port, no profile.json)
└── test_progress_persistence.py  # MODIFY: rewrite test_schema_version_mismatch + add v1→v2 migration tests
```

### Pattern 1: Derived learn-portion / stored live-portion split
**What:** `learn_fill` and `competent` are recomputed from `LearnProgress.lessons` + `course_N_unlocked` on every `compute()`; only `live_proof_count`/`mastered`/`first_mastered_at` are stored in the JSON `skills` block.
**When to use:** Always — this is the locked GA3 decision and the single-source-of-truth guarantee (zero dual-write drift).
**Example:**
```python
# Source: pattern mirrors src/vibemix/learn/progress.py::from_dict (verified idiom)
@dataclass
class SkillProgress:
    skill_id: str
    stage: str            # "locked" | "competent" | "mastered"
    learn_fill: float     # DERIVED [0.0, 1.0]
    competent: bool       # DERIVED (fill >= threshold AND recital passed)
    live_proof_count: int        # STORED (P103 writes; P102 default 0)
    mastered: bool               # STORED (P103; P102 default False)
    first_mastered_at: str | None  # STORED (P103; P102 default None)
```

### Pattern 2: Import-time manifest↔curriculum drift assertion (SKILL-03 anti-drift)
**What:** A module-level loop asserts every lesson ID referenced in `SKILL_MANIFEST` exists in `CURRICULUM`, so a typo or a pruned lesson is caught at import (and in a dedicated test), never at runtime.
**When to use:** Module load of `skill_tree.py` + a paranoid test.
**Example:**
```python
# Source: lazy-import idiom mirrors progress.py::dots_for_course (verified; avoids circular import)
from vibemix.learn.curriculum import CURRICULUM
for skill_id, spec in SKILL_MANIFEST.items():
    for lesson_id in spec.lesson_ids:
        assert lesson_id in CURRICULUM, (
            f"SKILL_MANIFEST[{skill_id!r}] references unknown lesson {lesson_id!r} "
            f"— curriculum drift"
        )
```

### Pattern 3: Explicit v1→v2 migration inside `from_dict` (NOT the wipe seam)
**What:** When `raw["schema_version"] == 1`, run `_migrate_v1_to_v2(raw)` (seed the `skills` live-portion with safe defaults, keep `lessons`/`courses`/`course_N_unlocked`), then load as v2. The existing "any other version → fresh `cls()`" wipe behavior is preserved for `schema_version` > 2 / garbage.
**When to use:** This is DATA-02. The current `from_dict` does `if raw.get("schema_version") != SCHEMA_VERSION: return cls()` — that exact line must change to route v1 through the upgrader.

### Anti-Patterns to Avoid
- **Storing `learn_fill` in the JSON:** creates dual-write drift the moment a lesson is replayed first-try after a strike-laden completion. Derive it. (Locked decision; the test suite should pin "no `learn_fill` key in the persisted skills block".)
- **Bumping `SCHEMA_VERSION` without rewriting `test_schema_version_mismatch_returns_fresh_empty`:** that test writes `schema_version: 2` and asserts fresh-empty — it will FAIL the moment v2 is a real migrated schema. The planner must replace it (v3/garbage → fresh-empty; v1 → migrate; v2 → load).
- **Gating `phrasing_performance` on a non-existent `course_3` completion flag:** no such flag exists and `courses` is never populated. Use `course_3_unlocked` (the honest C2-recital gate) — see Open Question #1.
- **Letting `compute()` read the clock or write the file:** keep it pure; inject any timestamp via a `now: Callable[[], str]` param (mirrors `RecitalRuntime`'s injected seed/save_fn). Persistence lives in `progress.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic JSON write | A custom write-then-fsync dance | `progress.py::save_progress` pattern (`tmp.write_text`→`os.replace`) | POSIX rename + Windows `ReplaceFileW` are atomic; precedent is test-pinned `[VERIFIED]` |
| Corrupt-read recovery | A new try/except + toast scheme | Extend `progress.py::load_progress`'s existing `OSError|JSONDecodeError`→unlink→fresh path | Already returns `(progress, was_corrupt)`; just seed an empty v2 skills block on the fresh path `[VERIFIED]` |
| Reset path | A new CLI subcommand + IPC handler | Extend the existing `learn reset` (`__main__.py:3760`) + `ipc_handlers.py:465` reset | Reset already clears `lessons`/`courses`/`course_N_unlocked`; add the live-portion ledger clear there `[VERIFIED]` |
| Recital honest-score gate | Re-implement scoring | Read `LearnProgress.course_2_unlocked` / `course_3_unlocked` (written by `RecitalRuntime` on a real 5/5 pass) | The honest gate already exists and is the only path that flips those bits `[VERIFIED: recital.py:497]` |
| Schema validation | pydantic | Inline `.get(..., default)` guards (or `jsonschema` Draft-07 like `profile/schema.py`) | pydantic is banned project-wide (D-Area-4.4) `[VERIFIED: profile/schema.py:11]` |

**Key insight:** Nearly every "hard" part of this phase (atomic write, corrupt recovery, reset, honest-score gate) is already shipped and test-pinned in `progress.py`/`recital.py`. The genuinely new code is one pure module (`skill_tree.py`) and a careful `from_dict` migration edit. The risk is not novelty; it's silently breaking an existing test or mis-deriving a gate.

## Runtime State Inventory

> Phase 102 is additive (new module + new JSON block), not a rename/refactor. But because it migrates an on-disk file shape, the migration-state questions apply:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `~/.cache/vibemix/learn-progress.json` — real users on this branch have `schema_version: 1` files with `lessons`/`courses`/`course_2_unlocked`/`course_3_unlocked`. A v1→v2 bump must migrate these in place, not wipe them. | Data migration (`_migrate_v1_to_v2` seeds live-portion, preserves lesson history) — this IS DATA-02 |
| Live service config | None — no external service stores skill state. Skill state is single-user local only (REQUIREMENTS Out-of-Scope: no sync, no cloud). | None — verified by REQUIREMENTS.md:50-59 |
| OS-registered state | None — no Task Scheduler / launchd / pm2 entry references skills. | None — verified (engine has no daemon, no port) |
| Secrets/env vars | None — engine needs no `GEMINI_API_KEY`, no env var. Offline-unit-testable by design. | None — verified (CONTEXT "no API key, no audio capture") |
| Build artifacts | None new — pure Python module under existing `src/vibemix/learn/`; hatchling already packages the package. No egg-info churn (no `pyproject.toml` change). | None |

**The canonical question** ("after every file is updated, what runtime systems still have the old shape cached?"): only the on-disk `learn-progress.json` — handled by the v1→v2 migration. In-memory `LearnProgress` instances held by a live runtime are recreated from disk on next `load_progress`; the runtime never caches skill state separately in P102 (P104 wires display).

## Common Pitfalls

### Pitfall 1: Bumping SCHEMA_VERSION silently breaks an existing passing test
**What goes wrong:** `test_schema_version_mismatch_returns_fresh_empty` (test_progress_persistence.py:91) writes `{"schema_version": 2, ...}` and asserts fresh-empty. Bumping `SCHEMA_VERSION` to 2 makes v2 the *current* schema → that JSON now loads as a real (empty-but-valid) v2 → the "fresh empty because mismatch" assertion semantics change.
**Why it happens:** The v9.0 migration seam was "any non-1 version → wipe". v11.0 makes 2 a real version.
**How to avoid:** In the plan, the migration task MUST include rewriting this test: v1 → migrated (lessons preserved, skills seeded), v2 → loaded as-is, v3/garbage/`schema_version` absent on a non-empty dict → fresh-empty. Treat it as a known test edit, not a regression.
**Warning signs:** A green `skill_tree` suite but a red `test_progress_persistence` — the migration touched the seam without updating its guard test.

### Pitfall 2: `phrasing_performance` gated on a non-existent Course-3 completion flag
**What goes wrong:** A naive manifest writes `phrasing_performance → gating_recital="course_3_complete"` or reads `progress.courses["course_3_play_mode"]["completed"]`. Neither exists — `courses` is **only ever set to `{}`** (`ipc_handlers.py:465`), never populated, and Course 3 has no recital and no completion bit.
**Why it happens:** CONTEXT says "phrasing_performance→Course 3 completion gate", but v9.0 never shipped a C3 completion flag (C3 ends at L3.06 "dj profile graduation" with no persistent flag).
**How to avoid:** Gate `phrasing_performance` on `course_3_unlocked` — the honest C2-recital pass that *earns entry to* play mode (the only honest-score boundary touching C3). This is defensible: you cannot reach Course 3 lessons at all without the C2 recital pass, so `course_3_unlocked == True` is a genuine earned gate. Flag for the planner as Open Question #1 (Claude's discretion). Alternatively, the plan could add a `course_3_complete` derived check ("all 6 C3 lessons completed") — but that is NOT an honest-score gate (lessons can be click-through), so it would weaken COMP-02. Prefer the `course_3_unlocked` gate.
**Warning signs:** A manifest test that references a curriculum/flag key that does not resolve.

### Pitfall 3: Lesson-ID drift between manifest and curriculum
**What goes wrong:** The manifest hard-codes `"L2.4"` (curriculum uses zero-padded `"L2.04"`), or references `"L3.07"` (curriculum stops at `"L3.06"` — the docstring comment at curriculum.py:457 wrongly says "L3.01..L3.07"; the actual table is L3.01..L3.06).
**Why it happens:** The curriculum's own comment is stale. The lesson count is also commonly mis-stated: actual is **37 entries** (`course_0` ×1 + C1 ×16 + C2 ×14 + C3 ×6); "36 lessons" = the 36 real lessons excluding the `course_0` hello-world demo.
**How to avoid:** Author the manifest against the verified IDs below (Code Examples section). Land the import-time + test-time drift assertion (Pattern 2). The `course_0` lesson `L0.00-press-play` feeds NO skill — it is a valid no-op (CONTEXT GA1).
**Warning signs:** `assert lesson_id in CURRICULUM` fails at import.

### Pitfall 4: Derived-state non-determinism / non-monotonic display fill
**What goes wrong:** Fill jiggles between reloads, or decreases when a user replays a lesson with more strikes than their first pass.
**Why it happens:** If quality weight is read from the *latest* completion and a replay overwrites a clean first-try with a strike-laden one, fill drops. `mark_completed` overwrites the lesson row each time (progress.py:121).
**How to avoid:** CONTEXT GA2 says "fill is monotonic for display (never decreases on reload) but recomputed deterministically from source". Reconcile this: recompute deterministically from the *stored* lesson rows (deterministic), and either (a) define weight so a recorded completion never counts as *less* than a prior click-through (floor semantics: a lesson that is `completed=True` always contributes ≥ the floor regardless of strikes), or (b) treat the lesson row's `strikes_used` as the authoritative quality input and accept that monotonicity holds because a *completion* never reverts to *incomplete*. Recommend (b): once `completed=True`, the lesson's contribution is fixed by its stored `strikes_used`; replays that lower strikes only *raise* fill. Document the chosen semantics in a fill-math docstring + pin with a unit test.
**Warning signs:** A "fill decreased on reload" test the planner forgot to write.

### Pitfall 5: Migration not idempotent
**What goes wrong:** Loading a v2 file re-runs the v1→v2 seeding and clobbers a non-zero `live_proof_count` (P103 data) back to 0.
**Why it happens:** Migration keyed on "skills block absent" rather than "schema_version == 1".
**How to avoid:** Gate migration strictly on `schema_version == 1`. A v2 file (skills block present, possibly with P103 live data) loads through the v2 path untouched. Pin with a test: migrate v1 → save → load → save → load, assert the live-portion is stable and the file is byte-identical on the second round-trip.
**Warning signs:** A round-trip test where `first_mastered_at` / `live_proof_count` resets.

## Code Examples

### Verified lesson IDs per course (the SKILL_MANIFEST source of truth)
`[VERIFIED: src/vibemix/learn/curriculum.py — grep of CURRICULUM keys, 2026-05-29]`

```
course_0  (hello-world demo — feeds NO skill, valid no-op):
  L0.00-press-play

course_1_anatomy (16 lessons; recital = L1.16; honest-pass flips course_2_unlocked):
  L1.01 opening dialog            L1.09 master · booth · headphones
  L1.02 meet your controller      L1.10 anatomy of a song
  L1.03 channel strip             L1.11 counting bars
  L1.04 crossfader                L1.12 spot breakdown by ear
  L1.05 pitch fader               L1.13 spot breakdown by eye
  L1.06 transport buttons         L1.14 eq as tutor
  L1.07 jog wheel                 L1.15 load two tracks
  L1.08 headphone cueing          L1.16 course 1 recital   ← gating recital

course_2_transitions (14 lessons; recital = L2.14; honest-pass + ≥3 distinct types flips course_3_unlocked):
  L2.01 beatmatching by ear       L2.08 drop swap
  L2.02 beatmatching with sync    L2.09 loop transition
  L2.03 long blend                L2.10 hot cues and memory cues
  L2.04 eq swap                   L2.11 camelot wheel
  L2.05 bassline swap             L2.12 phrase matching
  L2.06 filter fade               L2.13 diagnosing a train wreck
  L2.07 echo-out                  L2.14 course 2 recital   ← gating recital

course_3_play_mode (6 lessons L3.01..L3.06 — NO recital, NO completion flag):
  L3.01 first 5-minute mix        L3.04 first 30-minute set capstone
  L3.02 first 15-minute set       L3.05 recovery drills
  L3.03 reading the room          L3.06 dj profile graduation
```

### Recommended SKILL_MANIFEST (skill → lessons + gating gate)
`[VERIFIED: mapping derived from curriculum lesson titles + CONTEXT GA1 skill set]`

The 6 locked skills and a defensible lesson assignment (a lesson may feed ≥1 skill per CONTEXT). This is a *recommended* mapping — exact lesson→skill assignment is implementation detail the plan finalizes, but the gating recitals are pinned by CONTEXT:

| Skill | Course | Feeds from lessons (recommended) | Gating gate (honest-score) |
|-------|--------|----------------------------------|----------------------------|
| `deck_control` | C1 | L1.02, L1.03, L1.04, L1.05, L1.06, L1.07, L1.08, L1.09 (the hardware/transport anatomy) | `course_2_unlocked` (L1.16 recital pass) |
| `beatmatching` | C2 | L2.01, L2.02 (ear + sync) | `course_3_unlocked` (L2.14 recital pass) |
| `eq_mixing` | C1+C2 | L1.14 (eq as tutor), L2.04 (eq swap), L2.05 (bassline swap) | `course_3_unlocked` (L2.14 recital pass) |
| `harmonic_mixing` | C2 | L2.11 (camelot wheel) | `course_3_unlocked` (L2.14 recital pass) |
| `transitions` | C2 | L2.03, L2.06, L2.07, L2.08, L2.09 (the canonical transitions) | `course_3_unlocked` (L2.14 recital pass) |
| `phrasing_performance` | C1+C2+C3 | L1.10, L1.11, L1.12, L1.13 (song anatomy/bars/breakdown), L2.10, L2.12, L2.13 (hot cues/phrase/wreck), L3.01–L3.06 (play mode) | `course_3_unlocked` (the honest C2-recital gate that earns play-mode entry — see Open Q#1) |

Notes: `L0.00-press-play` and `L1.01 opening dialog` (pure dialog, no competency) feed no skill — valid no-ops. The four C2 skills all gate on the SAME flag (`course_3_unlocked`) per CONTEXT ("the four C2 skills → Course 2 recital L2.14"); `deck_control` gates on `course_2_unlocked` per CONTEXT ("deck_control → Course 1 recital L1.16").

### Recommended Competent fill math (COMP-01) + threshold
`[ASSUMED — concrete numbers are Claude's discretion per CONTEXT GA2; rationale below, pinned by unit tests]`

```python
# Quality weights — a completed lesson's contribution to its skill's fill.
WEIGHT_FIRST_TRY: float = 1.0    # completed with 0 strikes
WEIGHT_WITH_STRIKES: float = 0.6 # completed using 1+ hint strikes
WEIGHT_FLOOR: float = 0.0        # not completed (click-through / never reached)

# A skill's learn_fill = sum(weight(lesson) for lesson in skill.lessons) / len(skill.lessons)
# (denominator = full-weight if every lesson were first-try → normalizes to [0,1])

COMPETENT_THRESHOLD: float = 0.6  # fill must reach this AND the recital must pass
```

**Rationale:**
- **`0.0` floor for click-through is the anti-slop spine.** CONTEXT: "click-through with no demonstrated outcome contributes the floor." A lesson the user never completed contributes nothing. Note: in v9.0, `mark_completed` is only called on a *real* completion, so "completed=True" already means a demonstrated outcome — the true floor case is "lesson absent from `lessons` dict". If the plan wants a small non-zero floor for *completed-but-clicked-through* lessons, that contradicts CONTEXT's "no demonstrated outcome → floor"; recommend floor = absent-lesson = 0.0.
- **`0.6` for with-strikes vs `1.0` first-try** gives a meaningful but not punitive gap — a user who needed hints still progresses, but a clean run is visibly worth more. The 0.6 figure is a starting point the fill-math tests defend; Kaan can tune.
- **`COMPETENT_THRESHOLD = 0.6`** means: a user must have first-try-completed ~60% of a skill's lessons (or completed all of them with strikes) AND passed the gating recital. This is high enough that pure-with-strikes barely-clears, low enough that a competent user isn't blocked on one perfectionist lesson. The decisive gate is COMP-02 (the recital), not the threshold — the threshold is the secondary "you actually did the lessons" floor. **Crucially: because the recital pass (`course_N_unlocked`) is AND-ed in, 100% click-through with no recital is mathematically incapable of reaching Competent regardless of threshold.**

### v1→v2 migration sketch (DATA-02)
`[VERIFIED: edits the real from_dict at progress.py:201-228]`

```python
SCHEMA_VERSION = 2  # bumped from 1

_SKILL_IDS = (
    "deck_control", "beatmatching", "eq_mixing",
    "harmonic_mixing", "transitions", "phrasing_performance",
)

def _fresh_skills_block() -> dict[str, dict[str, Any]]:
    """Live-portion defaults for all 6 skills (P103 fills these)."""
    return {
        sid: {"live_proof_count": 0, "mastered": False, "first_mastered_at": None}
        for sid in _SKILL_IDS
    }

def _migrate_v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Seed the live-portion skills block; preserve all v1 lesson history.
    Learn-portion is NOT stored — it is recomputed by SkillTree.compute."""
    raw = dict(raw)
    raw["schema_version"] = 2
    raw["skills"] = _fresh_skills_block()  # safe defaults only
    return raw

@classmethod
def from_dict(cls, raw: dict[str, Any]) -> LearnProgress:
    if not isinstance(raw, dict):
        return cls()
    version = raw.get("schema_version")
    if version == 1:
        raw = _migrate_v1_to_v2(raw)           # NEW: migrate, don't wipe
    elif version != SCHEMA_VERSION:
        return cls()                            # v3+/garbage → fresh empty (wipe seam preserved)
    skills = raw.get("skills")
    if not isinstance(skills, dict):
        skills = _fresh_skills_block()          # corrupt/missing block → defaults (idempotent on v2)
    return cls(
        schema_version=SCHEMA_VERSION,
        courses=raw.get("courses", {}) or {},
        lessons=raw.get("lessons", {}) or {},
        course_2_unlocked=bool(raw.get("course_2_unlocked", False)),
        course_3_unlocked=bool(raw.get("course_3_unlocked", False)),
        skills=skills,
    )
```
The fresh-empty corrupt path in `load_progress` returns `LearnProgress()` whose dataclass default for `skills` is `field(default_factory=_fresh_skills_block)` — so corrupt recovery seeds an empty v2 skills block automatically (DATA-02).

## State of the Art

| Old Approach (v9.0) | Current Approach (P102) | When Changed | Impact |
|--------------------|------------------------|--------------|--------|
| `schema_version` 1; any non-1 → wipe | `schema_version` 2; v1 → migrate, v3+/garbage → wipe | P102 | The wipe seam becomes a real upgrader; the guard test must be rewritten |
| `LearnProgress` carries lessons + unlock flags only | + a `skills` live-portion block (6 skills, defaults) | P102 | Forward-compat shape so P103 writes without a second migration |
| Course completion implicit (unlock flags only) | Skill stage derived from lessons + unlock flags | P102 | No new completion flag added; gates reuse `course_N_unlocked` |

**Deprecated/outdated:**
- The curriculum.py:457 docstring comment "L3.01..L3.07" is **wrong** — Course 3 ships 6 lessons (L3.01..L3.06). Do not author the manifest against an L3.07 that does not exist. (This is a doc-comment bug, not a code bug — out of scope to fix here, but do not trust it.)
- The "36 lessons" figure (STATE.md, CONTEXT) counts the 36 *real* lessons (C1+C2+C3) and excludes the `course_0` hello-world demo. Actual `CURRICULUM` has **37 entries**.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `WEIGHT_FIRST_TRY=1.0 / WEIGHT_WITH_STRIKES=0.6 / WEIGHT_FLOOR=0.0` | Fill math | Low — explicitly Claude's discretion (CONTEXT GA2); fill-math unit tests defend whatever the plan picks; Kaan can tune |
| A2 | `COMPETENT_THRESHOLD=0.6` | Fill math | Low — Claude's discretion; the decisive gate is the recital (COMP-02), threshold is secondary |
| A3 | Recommended skill→lesson assignment (which lessons feed which skill) | SKILL_MANIFEST | Medium — the *gating recitals* are CONTEXT-locked, but the per-lesson assignment is a judgment call; plan finalizes. Drift assert + tests catch typos, not semantic mis-assignment |
| A4 | `phrasing_performance` gates on `course_3_unlocked` (not a C3 completion flag) | Open Q#1 | Medium — CONTEXT says "Course 3 completion gate" but no such flag exists; this is the only honest-score gate touching C3. If Kaan wants a true C3-completion gate, a new honest-score mechanism would be needed (out of P102 scope) |
| A5 | Live-ledger atomic-write helper lives in `progress.py` (not a new `skill_store.py`) | Project structure | Low — explicitly Claude's discretion (CONTEXT); one file = one corrupt-recovery + one reset path |
| A6 | Inline `.get(default)` guards over `jsonschema` for the skills block | Standard Stack | Low — matches `from_dict`'s existing style; jsonschema reserved for `profile.json` privacy contract |

## Open Questions

1. **`phrasing_performance` gating recital** (the one genuine design gap)
   - What we know: CONTEXT says "phrasing_performance → Course 3 completion gate". `course_2_unlocked` and `course_3_unlocked` exist; there is NO Course-3 completion flag, no C3 recital, and `courses` is never populated.
   - What's unclear: Whether "Course 3 completion gate" means (a) `course_3_unlocked` (the honest C2-recital pass that *earns entry* to C3), or (b) a new "all C3 lessons done" derived check.
   - Recommendation: Gate on `course_3_unlocked` (option a). It is a real honest-score gate (you cannot reach C3 lessons without it), preserves COMP-02 ("pure click-through can never reach Competent"), and adds no new flag. Option (b) is NOT honest-score (C3 lessons can be clicked through) and would weaken the anti-slop gate. Plan-phase decides; this research recommends (a).

2. **Floor semantics for completed-but-strike-heavy lessons**
   - What we know: CONTEXT GA2 says fill is monotonic for display but recomputed from source; `mark_completed` overwrites the lesson row on replay.
   - What's unclear: Whether a replay with more strikes can lower a skill's fill.
   - Recommendation: Once `completed=True`, contribution is fixed by stored `strikes_used`; a replay only ever raises fill (lower strikes). Pin with a "fill never decreases across reload" test. (Pitfall 4.)

## Environment Availability

> SKIPPED — Phase 102 has no external dependencies. It is pure-Python on the standard library plus the already-installed `jsonschema`. No tool, service, runtime, database, or network access is required. The engine is offline-unit-testable by design (CONTEXT: "no API key, no audio capture"). Verified: the test command `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (CLAUDE.md) needs only the existing `.venv` (Python 3.12.x) — `[VERIFIED: pyproject.toml requires-python >=3.12,<3.13]`.

## Validation Architecture

> `workflow.nyquist_validation` not explicitly disabled — treat as enabled. This section enumerates the test surface that proves each REQ-ID, the 3 invariant pins, and the headline anti-slop assertion.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (the authoritative dev workflow per CONTRIBUTING.md / CLAUDE.md) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (verified present) |
| Quick run command | `PYTHONPATH=src python3 -m pytest tests/learn/test_skill_tree.py -q` (single-file, ~sub-second — pure logic, no I/O beyond tmp) |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |

All P102 tests are default-run (no opt-in marker) — pure logic + tmp-file persistence, no `network`/`macos_audio`/`slow`/`integration` markers needed. The reset-CLI test is the only one that may carry the existing `cli` subprocess marker (mirror `test_reset_cli` in test_progress_persistence.py).

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 | 6 skills, two-stage bar (Locked→Competent→Mastered); each skill resolves a stage | unit | `pytest tests/learn/test_skill_tree.py::test_six_skills_present_with_stage -x` | ❌ Wave 0 |
| SKILL-02 | `SkillTree.compute(progress)` is a pure function returning `dict[str, SkillProgress]`; sole writer of skill state | unit | `pytest tests/learn/test_skill_tree.py::test_compute_is_pure_no_side_effects -x` | ❌ Wave 0 |
| SKILL-02 (Inv #1 pin) | `skill_tree.py` never imports/writes `MusicState` | static-grep | `pytest tests/learn/test_skill_tree_invariants.py::test_skill_tree_never_mutates_musicstate -x` | ❌ Wave 0 |
| SKILL-03 | `SKILL_MANIFEST` is a readable constant; every referenced lesson ID exists in `CURRICULUM` (no drift) | unit | `pytest tests/learn/test_skill_tree.py::test_manifest_lesson_ids_exist_in_curriculum -x` | ❌ Wave 0 |
| COMP-01 | First-try > with-strikes > click-through fill weighting; fill ∈ [0,1] | unit | `pytest tests/learn/test_skill_tree.py::test_quality_weighted_fill_ordering -x` | ❌ Wave 0 |
| COMP-01 | Fill never decreases across reload (monotonic display) | unit | `pytest tests/learn/test_skill_tree.py::test_fill_monotonic_on_reload -x` | ❌ Wave 0 |
| COMP-02 | **HEADLINE: 100% lesson fill, no recital pass → NOT Competent** | unit | `pytest tests/learn/test_skill_tree.py::test_full_clickthrough_without_recital_not_competent -x` | ❌ Wave 0 |
| COMP-02 | Competent requires `fill >= THRESHOLD` AND gating `course_N_unlocked` True | unit | `pytest tests/learn/test_skill_tree.py::test_competent_requires_threshold_and_recital -x` | ❌ Wave 0 |
| DATA-01 | `skills` block persists in `learn-progress.json` via atomic write; round-trips | unit | `pytest tests/learn/test_skill_tree.py::test_skills_block_round_trips -x` | ❌ Wave 0 |
| DATA-01 (Inv: privacy) | Skill data NEVER appears in `profile.json` (5-field `additionalProperties:false` intact) | unit | `pytest tests/learn/test_skill_tree_invariants.py::test_skills_never_in_profile_json -x` | ❌ Wave 0 |
| DATA-02 | v1 file → migrated to v2 with skills seeded, lesson history preserved | unit | `pytest tests/learn/test_progress_persistence.py::test_migrate_v1_to_v2_seeds_skills -x` | ⚠️ MODIFY existing file |
| DATA-02 | Migration idempotent — v2 file with P103 live data not clobbered | unit | `pytest tests/learn/test_progress_persistence.py::test_migration_idempotent_preserves_live_portion -x` | ❌ Wave 0 |
| DATA-02 | Corrupt read → fresh-empty v2 with seeded skills block + `was_corrupt=True` | unit | `pytest tests/learn/test_progress_persistence.py::test_corrupt_recovers_with_empty_skills_block -x` | ❌ Wave 0 |
| DATA-02 | v3/garbage `schema_version` → fresh empty (wipe seam preserved); REWRITES existing test | unit | `pytest tests/learn/test_progress_persistence.py::test_future_schema_version_returns_fresh_empty -x` | ⚠️ REWRITE `test_schema_version_mismatch_returns_fresh_empty` |
| DATA-03 | Reset clears the live-portion ledger (mirrors lesson-progress reset) | unit + cli | `pytest tests/learn/test_skill_tree.py::test_reset_clears_live_portion -x` | ❌ Wave 0 |
| (Inv #4 pin) | No new ws port — zero `websockets.serve` / `8765`/`8766` literal in `skill_tree.py` | static-grep | `pytest tests/learn/test_skill_tree_invariants.py::test_no_new_ws_port -x` | ❌ Wave 0 |

### The 3 Invariant Pins (mirror v9.0 `tests/learn/test_runtime_invariants.py`)
The shipped gate uses **line-oriented `re`** (not `ast`) walking `src/vibemix/learn/**/*.py` — match that idiom:
1. **`test_skill_tree_never_mutates_musicstate`** (Invariant #1): grep `skill_tree.py` for `MusicState`/`music_state` field writes AND for any `import` of `state.music_state`. The new module must read `LearnProgress` only. (The existing `test_learn_package_never_writes_music_state_or_controller_state` already covers the whole `learn/` dir — the new module is automatically swept; add a *focused* assertion that `skill_tree.py` does not even import `MusicState`.)
2. **`test_no_new_ws_port`** (Invariant #4): static-grep `skill_tree.py` for `websockets.serve`, `WS_PORT`, literal `8765`/`8766` — assert zero. The engine is pure logic; it touches no socket.
3. **`test_skills_never_in_profile_json`** (privacy contract): assert (a) `skill_tree.py` and the `skills` block code never import/write `profile.schema` / `profile.json` / `serialize_profile`; and (b) the `PROFILE_SCHEMA` still has exactly its 5 required fields with `additionalProperties: false` and no `skills`/`live_proof_count`/`mastered` keys. A grep + a structural assertion on `PROFILE_SCHEMA["properties"].keys()`.

### Headline Anti-Slop Assertion (the product spine)
`test_full_clickthrough_without_recital_not_competent`: construct a `LearnProgress` where EVERY lesson for a skill is `completed=True` with `strikes_used=0` (max fill = 1.0) but `course_N_unlocked` is `False` (no recital pass). Assert `compute(progress)[skill].competent is False` and `.stage == "locked"`. This is the "nothing is given; every notch is earned" gate in executable form (CONTEXT specifics).

### Sampling Rate
- **Per task commit:** `pytest tests/learn/test_skill_tree.py tests/learn/test_skill_tree_invariants.py -q` (pure logic, sub-second)
- **Per wave merge:** `pytest tests/learn/ -q` (whole learn suite — catches migration regressions in `test_progress_persistence.py` and the existing invariant gate)
- **Phase gate:** full suite green (`pytest -q`) before `/gsd:verify-work` — confirms the `SCHEMA_VERSION` bump did not red any cross-tree test that reads `learn-progress.json`.

### Wave 0 Gaps
- [ ] `tests/learn/test_skill_tree.py` — covers SKILL-01/02/03, COMP-01/02, DATA-01/03 + the headline click-through case
- [ ] `tests/learn/test_skill_tree_invariants.py` — covers the 3 invariant pins (Inv #1, Inv #4, privacy)
- [ ] `tests/learn/test_progress_persistence.py` — MODIFY: rewrite `test_schema_version_mismatch_returns_fresh_empty` (v2 is now a real version), ADD v1→v2 migration + idempotency + corrupt-with-skills tests
- [ ] No framework install needed — `pytest` + `.venv` already present.

## Project Constraints (from CLAUDE.md)

- **No pydantic** — `jsonschema` only (D-Area-4.4). `[VERIFIED: profile/schema.py:11, pyproject.toml:97]`
- **Python 3.12, `snake_case` modules/functions, `PascalCase` classes, `UPPER_SNAKE_CASE` module constants**; `from __future__ import annotations` + PEP 604 unions. `[VERIFIED: CLAUDE.md Conventions]`
- **No hardcoded model literals** — N/A here (engine touches no LLM), but do not introduce any.
- **Anti-slop discipline** applies to any user-facing string — P102 expects NONE (no UI, no co-host vocal; that is P104). If a docstring/comment is written, mind the `stop-slop` phrase list.
- **Type hints are documentation** (no enforced mypy/pyright) — write them anyway, mirror `progress.py`.
- **`git commit` is shared across concurrent sessions** — stage surgically (`git diff --cached --name-only`), never `git add -A`. The P102 island is `src/vibemix/learn/skill_tree.py` + `progress.py` + the new test files; disjoint from One Mind (`src/vibemix/**` minus learn), LiveKit-upgrade (`__main__.py`/`agent/`), frontend-wiring (`tauri/ui/*`). **Caution:** P102 edits `__main__.py:3760` (reset CLI) and `ipc_handlers.py:465` (reset handler) for DATA-03 — these are NOT pure-learn-island files; the LiveKit-upgrade session also touches `__main__.py`. Coordinate / stage only the reset lines.
- **The 4 cardinal invariants hold by ADDITIVE design** — verified the phase is additive (new module + new JSON block + migration), regressing nothing.

## Sources

### Primary (HIGH confidence)
- `src/vibemix/learn/progress.py` — `LearnProgress` dataclass, `SCHEMA_VERSION`, `from_dict` migration seam (lines 201-228), `load_progress` corrupt recovery (231-262), `save_progress` atomic write (265-286), `reset_progress` (289-303), `dots_for_course` lazy-import idiom (133-189)
- `src/vibemix/learn/recital.py` — `RecitalRuntime` honest-score gate; flips `course_2_unlocked`/`course_3_unlocked` on real 5/5 pass (line 497); C1/C2 only — NO C3 handling (verified grep count = 0)
- `src/vibemix/learn/curriculum.py` — `CURRICULUM` 37 entries verified (course_0 ×1, C1 ×16, C2 ×14, C3 ×6); docstring comment "L3.01..L3.07" is wrong (actual L3.01..L3.06)
- `tests/learn/test_runtime_invariants.py` — the regex-based AST/static-gate idiom for Invariant #1
- `tests/learn/test_progress_persistence.py` — `progress_path_in_tmp` monkeypatch fixture; `test_schema_version_mismatch_returns_fresh_empty` (the test the v2 bump breaks)
- `src/vibemix/profile/schema.py` — the 5-field `additionalProperties:false` privacy contract (`test_skills_never_in_profile_json` protects it)
- `src/vibemix/learn/ipc_handlers.py:465` + `src/vibemix/__main__.py:3760` — verified `courses` is only ever cleared to `{}`, never populated; reset path to mirror
- `.planning/phases/102-skill-tree-engine-data-model-competent-stage/102-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `CLAUDE.md`

### Secondary (MEDIUM confidence)
- None — this phase touched no external sources; everything is in-repo and verified.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; every primitive is shipped + test-pinned in `progress.py`
- Architecture: HIGH — derived/stored split + migration verified directly against the real `from_dict`
- Pitfalls: HIGH — the two load-bearing pitfalls (SCHEMA_VERSION test break; missing C3 completion flag) are confirmed by reading the actual source/tests, not inferred
- Fill math numbers: MEDIUM — explicitly Claude's discretion; the *mechanism* is HIGH, the *constants* are tunable

**Research date:** 2026-05-29
**Valid until:** 2026-06-28 (30 days — stable; pure stdlib + in-repo, no fast-moving external surface). Re-verify only if `progress.py`/`curriculum.py`/`recital.py` change under a concurrent session before P102 executes.
