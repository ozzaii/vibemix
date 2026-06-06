# SPDX-License-Identifier: Apache-2.0
"""Skill-tree engine — the pure-logic Competent stage + fill math.

Phase 102 (v11.0 "Earned"), Plan 02. This is the engine: the sole DERIVER of
skill state and the "nothing is given; every notch is earned" gate in
executable form. It joins two halves of each skill's state:

  * the DERIVED learn-portion — a quality-weighted fill ``[0.0, 1.0]`` computed
    from the persisted lesson rows (``LearnProgress.lessons``) plus the recital
    honest-score unlock flags (``LearnProgress.course_N_unlocked``); and
  * the STORED live-portion — ``live_proof_count`` / ``mastered`` /
    ``first_mastered_at``, read read-only from ``LearnProgress.skills`` (Phase
    103 writes it; Plan 102-01 seeds it with safe defaults).

The decisive lock is COMP-02: a recital pass is AND-ed into Competent, so a 100%
lesson click-through can NEVER reach Competent regardless of the fill threshold.
The recital is the earned gate; the fill threshold is only the secondary "you
actually did the lessons" floor.

PURITY (Invariant #1 / SKILL-02): this module is I/O-free, clock-free, and never
imports or writes ``MusicState`` / ``ControllerState``. ``compute`` is a pure
function of its ``LearnProgress`` argument — twice on the same input returns
equal results and mutates nothing. It opens no ws port and never touches
``profile.json`` (the privacy contract). These properties are pinned by
``tests/learn/test_skill_tree_invariants.py``.

NOT in this plan: ``record_live_demo`` (Phase 103 writes the live-portion) and
any UI / IPC envelope (Phase 104 reads the computed dict for display).

REQ-IDs: SKILL-01 (6 skills resolve a stage), SKILL-02 (pure compute),
SKILL-03 (manifest<->curriculum anti-drift), COMP-01 (quality-weighted fill),
COMP-02 (HEADLINE recital AND-gate).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Fill-math constants (COMP-01)
# ---------------------------------------------------------------------------
# A completed lesson's contribution to its skill's fill is quality-weighted:
# a first-try (0-strike) completion is worth MORE than a with-strikes
# completion, which is worth more than a click-through (never completed). This
# is what makes the fill mean "how well did you actually learn this", not "did
# you click Next enough times".
#
# Monotonicity (CONTEXT GA2 / RESEARCH Pitfall 4(b)): fill is recomputed
# deterministically from the STORED lesson rows. Once a lesson is
# ``completed=True`` its contribution is fixed by its stored ``strikes_used``;
# a replay that LOWERS the strike count only RAISES fill, and a completion never
# reverts to incomplete — so display fill never decreases across a reload.
#
# The exact numbers are Claude's discretion per CONTEXT GA2 — the load-bearing
# invariant is the strict ordering (first-try > with-strikes > click-through),
# defended by ``test_quality_weighted_fill_ordering``. The threshold is the
# secondary floor; the DECISIVE Competent gate is the recital (COMP-02).
WEIGHT_FIRST_TRY: float = 1.0  # completed with 0 hint strikes
WEIGHT_WITH_STRIKES: float = 0.6  # completed using 1+ hint strikes
WEIGHT_FLOOR: float = 0.0  # never completed (click-through / never reached)

# A skill is "you did the lessons" eligible once its quality-weighted fill
# crosses this floor — the SECONDARY gate. Competent still requires the recital
# (COMP-02), so this threshold can never, on its own, promote a click-through.
COMPETENT_THRESHOLD: float = 0.6


@dataclass(frozen=True)
class SkillSpec:
    """A skill's static definition: which lessons fill it + its recital gate.

    Immutable (``frozen=True``) — the manifest is a constant declaration, not a
    runtime-mutated object.

    Attributes:
        lesson_ids: The curriculum lesson ids whose completion fills this skill.
            Every id MUST exist in ``CURRICULUM`` (asserted at import time and
            re-pinned by ``test_manifest_lesson_ids_exist_in_curriculum``).
        gate: The name of the ``LearnProgress`` recital-unlock attribute that
            must be True for this skill to reach Competent — one of
            ``"course_2_unlocked"`` / ``"course_3_unlocked"``. The honest-score
            flag is written by ``RecitalRuntime`` on a 5/5 recital pass.
        mastered_threshold: Number of distinct grounded live demos
            (``live_proof_count``) needed to flip the Competent→Mastered segment
            (MAST-04). Uniform default ``3`` per RESEARCH Deliverable 4 — the
            flip-AT-N behaviour is the contract, not the literal N (mirrors the
            COMP-01 "ordering is the contract, not the numbers" precedent). It is
            a per-skill field (not a module constant) so the future
            ``§EARNED-MASTERY-THRESHOLD-TUNE`` Kaan-action can tune any one skill
            without a code change; the 6 manifest entries stay valid unchanged
            because the default is supplied here.
        live_creditable: Whether this skill has a production live Mastered path
            in v11.0, meaning the app can actually emit a cited live event for
            it. Defaults ``True``; set ``False`` when only a future-ready grader
            or recognizer branch exists but no production emitter can fire.
            Read by ``_what_remains`` (SURF-01) so the wall never promises a demo
            path a skill does not have. The drift between this field and the
            recognizer's uncreditable list is pinned by ``test_creditability_drift``.
    """

    lesson_ids: tuple[str, ...]
    gate: str
    mastered_threshold: int = 3
    live_creditable: bool = True


# ---------------------------------------------------------------------------
# SKILL_MANIFEST (SKILL-03) — the 6 REQ-locked DJ skills
# ---------------------------------------------------------------------------
# Lesson assignment per RESEARCH § Code Examples; gating recitals are
# CONTEXT-locked. The lesson ids are the human-readable contract for "what fills
# this skill"; the gate is the earned recital that AND-gates Competent.
#
# phrasing_performance (Open-Q#1): its lessons span the C1 musicality block,
# the C2 phrasing lessons, and all of C3 play-mode. C3 has NO recital and NO
# completion flag, so it is gated on ``course_3_unlocked`` — the honest C2
# recital pass that EARNS play-mode entry.
#
# FIVE curriculum lessons feed no skill (deliberately, not by oversight):
#   * ``L0.00-press-play`` / ``L1.01`` (opening dialog) — intro stubs.
#   * ``L1.16`` (course 1 recital) / ``L2.14`` (course 2 recital) — the
#     recitals are the GATE for their skills, never fill (counting them would
#     double-count the AND-gate as fill).
#   * ``L1.15`` (load two tracks) — an orphaned teaching lesson that fills no
#     skill. Whether it SHOULD map to deck_control is a product-design call
#     (deck_control covers L1.02-L1.09 contiguously, then jumps to course 2);
#     it is left a deliberate non-fill until that call is made. Do NOT read
#     this gap as accidental coverage.
SKILL_MANIFEST: dict[str, SkillSpec] = {
    "deck_control": SkillSpec(
        lesson_ids=(
            "L1.02",
            "L1.03",
            "L1.04",
            "L1.05",
            "L1.06",
            "L1.07",
            "L1.08",
            "L1.09",
        ),
        gate="course_2_unlocked",
    ),
    "beatmatching": SkillSpec(
        lesson_ids=("L2.01", "L2.02"),
        gate="course_3_unlocked",
        # ``learn.practice_loop`` emits cited ``BEATMATCH_GRADED`` events from
        # the owned-deck Judge, so Mastered credit is now a measured practice
        # signal instead of proxy-slop.
    ),
    "eq_mixing": SkillSpec(
        lesson_ids=("L1.14", "L2.04", "L2.05"),
        gate="course_3_unlocked",
    ),
    "harmonic_mixing": SkillSpec(
        lesson_ids=("L2.11",),
        gate="course_3_unlocked",
    ),
    "transitions": SkillSpec(
        lesson_ids=("L2.03", "L2.06", "L2.07", "L2.08", "L2.09"),
        gate="course_3_unlocked",
    ),
    "phrasing_performance": SkillSpec(
        lesson_ids=(
            "L1.10",
            "L1.11",
            "L1.12",
            "L1.13",
            "L2.10",
            "L2.12",
            "L2.13",
            "L3.01",
            "L3.02",
            "L3.03",
            "L3.04",
            "L3.05",
            "L3.06",
        ),
        gate="course_3_unlocked",
    ),
}


# Import-time manifest<->curriculum drift assertion (SKILL-03 anti-drift). A
# typo or a pruned lesson is caught at module load, never at runtime. Lazy
# import mirrors ``progress.dots_for_course`` — keeps the import graph one-way
# (curriculum does not import this module today; the lazy import keeps it that
# way regardless of future refactors).
def _assert_manifest_matches_curriculum() -> None:
    from dataclasses import fields

    from vibemix.learn.curriculum import CURRICULUM
    from vibemix.learn.progress import LearnProgress

    # Every manifest GATE name must be a real boolean field on LearnProgress.
    # ``compute`` reads the gate via ``getattr(progress, spec.gate, False)``
    # with a False fallback, so a typo'd gate (e.g. ``course_99_unlocked``)
    # would silently pin its skill to "locked" forever — a far quieter failure
    # than the lesson-id drift below. Fail loud at import instead, matching the
    # lesson-id anti-drift posture (a gate typo is no different from a lesson
    # typo; both must fail at module load, not silently at runtime).
    progress_fields = {f.name for f in fields(LearnProgress)}
    for skill_id, spec in SKILL_MANIFEST.items():
        assert spec.gate in progress_fields, (
            f"SKILL_MANIFEST drift: {skill_id} gate {spec.gate!r} is not a "
            "LearnProgress field (typo'd gates pin the skill locked forever)"
        )

    for skill_id, spec in SKILL_MANIFEST.items():
        for lesson_id in spec.lesson_ids:
            assert lesson_id in CURRICULUM, (
                f"SKILL_MANIFEST drift: {skill_id} references {lesson_id!r} "
                "which is not a CURRICULUM lesson id"
            )


_assert_manifest_matches_curriculum()


@dataclass
class SkillProgress:
    """The computed state of one skill — DERIVED learn-portion + STORED live.

    The learn-portion (``learn_fill`` / ``competent`` / ``stage``) is recomputed
    by :meth:`SkillTree.compute` on every call and never persisted. The
    live-portion (``live_proof_count`` / ``mastered`` / ``first_mastered_at``)
    is read read-only from ``LearnProgress.skills`` (Phase 103 writes it).
    """

    skill_id: str
    stage: str  # "locked" | "competent" | "mastered"
    learn_fill: float  # DERIVED [0.0, 1.0]
    competent: bool  # DERIVED (fill >= threshold AND recital passed)
    live_proof_count: int  # STORED (Phase 103 writes; Plan 102 default 0)
    mastered: bool  # STORED (Phase 103; Plan 102 default False)
    first_mastered_at: str | None  # STORED (Phase 103; Plan 102 default None)

    def as_payload(self) -> dict[str, Any]:
        """JSON-safe dict for the ``ipc.learn.progress_state`` skill-wall block.

        IPC-only — never persisted (the derived learn-portion is recomputed on
        every load). ``learn_fill`` is rounded to keep the wire stable.
        """
        return {
            "skill_id": self.skill_id,
            "stage": self.stage,
            "learn_fill": round(self.learn_fill, 4),
            "competent": self.competent,
            "live_proof_count": self.live_proof_count,
            "mastered": self.mastered,
            "first_mastered_at": self.first_mastered_at,
        }


def _weight_for(row: dict[str, Any] | None) -> float:
    """Quality weight of a single lesson row's contribution to fill.

    * absent / ``None`` / not a dict → ``WEIGHT_FLOOR`` (never reached).
    * ``completed=True`` but ``demonstrated=False`` → ``WEIGHT_FLOOR``.
    * ``completed=True`` with 0 strikes → ``WEIGHT_FIRST_TRY``.
    * ``completed=True`` with >= 1 strikes → ``WEIGHT_WITH_STRIKES``.
    * present but not completed (in-progress) → ``WEIGHT_FLOOR``.

    Monotonic by construction: once a row is ``completed=True`` its weight is a
    fixed function of the stored ``strikes_used``; lowering strikes only raises
    the weight, and a completion never becomes incomplete.
    """
    if not isinstance(row, dict):
        return WEIGHT_FLOOR
    if row.get("completed") is not True:
        return WEIGHT_FLOOR
    if row.get("demonstrated", True) is not True:
        return WEIGHT_FLOOR
    try:
        strikes = int(row.get("strikes_used", 0))
    except (TypeError, ValueError):
        strikes = 0
    return WEIGHT_FIRST_TRY if strikes <= 0 else WEIGHT_WITH_STRIKES


class SkillTree:
    """Pure engine: holds the manifest and DERIVES skill state from progress.

    Stateless apart from the (immutable) manifest. The whole point is that
    :meth:`compute` is a pure function — no I/O, no clock, no MusicState — so
    the UI can recompute display state on every progress reload with zero
    dual-write drift.
    """

    def __init__(self, manifest: dict[str, SkillSpec] | None = None) -> None:
        self._manifest = manifest if manifest is not None else SKILL_MANIFEST

    def compute(self, progress: Any) -> dict[str, SkillProgress]:
        """Compute the per-skill :class:`SkillProgress` from a ``LearnProgress``.

        Single-arg and PURE — the live-portion is read from
        ``progress.skills`` (the shape Plan 102-01 shipped), NOT a separate
        ledger argument. Reads only; mutates nothing; calls no clock and no I/O.

        For each skill:

          1. ``learn_fill`` = mean quality-weight of its lessons (``[0, 1]``).
          2. ``gate_passed`` = ``getattr(progress, spec.gate)`` — the recital
             honest-score flag.
          3. ``competent`` = ``learn_fill >= COMPETENT_THRESHOLD AND gate_passed``
             (COMP-02: the recital is AND-ed in, so 100% click-through with the
             gate False can never be Competent).
          4. live-portion read from ``progress.skills.get(skill_id, {})`` with
             safe defaults (count 0, not mastered, ts None).
          5. ``stage`` = ``"mastered"`` if the live-portion says so and the skill
             is production-live-creditable, else ``"competent"`` if competent,
             else ``"locked"``.
        """
        results: dict[str, SkillProgress] = {}
        live_block = getattr(progress, "skills", {}) or {}
        lessons = getattr(progress, "lessons", {}) or {}

        for skill_id, spec in self._manifest.items():
            total = sum(_weight_for(lessons.get(lid)) for lid in spec.lesson_ids)
            learn_fill = total / len(spec.lesson_ids) if spec.lesson_ids else 0.0

            gate_passed = bool(getattr(progress, spec.gate, False))
            competent = learn_fill >= COMPETENT_THRESHOLD and gate_passed

            live = live_block.get(skill_id, {})
            if not isinstance(live, dict):
                live = {}
            mastered = bool(live.get("mastered", False)) and spec.live_creditable
            # Mirror ``_weight_for``'s guard: ``from_dict`` only isinstance-checks
            # the top-level ``skills`` dict, never the inner value types, so a
            # parseable v2 JSON carrying a non-numeric ``live_proof_count``
            # (hand-edit, partial Phase-103 write, future drift) reaches here
            # untouched. A bare ``int()`` would raise an uncaught ``ValueError``
            # and wedge the engine on every load — contradicting the module's
            # never-raises contract. Degrade garbage to the safe default instead.
            try:
                live_proof_count = int(live.get("live_proof_count", 0) or 0)
            except (TypeError, ValueError):
                live_proof_count = 0
            first_mastered_at = live.get("first_mastered_at", None) if mastered else None

            if mastered:
                stage = "mastered"
            elif competent:
                stage = "competent"
            else:
                stage = "locked"

            results[skill_id] = SkillProgress(
                skill_id=skill_id,
                stage=stage,
                learn_fill=learn_fill,
                competent=competent,
                live_proof_count=live_proof_count,
                mastered=mastered,
                first_mastered_at=first_mastered_at,
            )
        return results


def _safe_nonnegative_int(value: Any) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, raw)


def _practice_bank_count_for_spec(progress: Any, spec: SkillSpec) -> int:
    lessons = getattr(progress, "lessons", {}) or {}
    if not isinstance(lessons, dict):
        return 0
    total = 0
    for lesson_id in spec.lesson_ids:
        row = lessons.get(lesson_id)
        if not isinstance(row, dict) or row.get("completed") is True:
            continue
        sources = row.get("practice_sources")
        if not isinstance(sources, dict):
            continue
        total += _safe_nonnegative_int(sources.get("hardware"))
        total += _safe_nonnegative_int(sources.get("screen"))
    return min(3, total)


def _practice_bank_remains_line(count: int) -> str:
    unit = "rep" if count == 1 else "reps"
    pronoun = "it" if count == 1 else "them"
    return f"{count} banked practice {unit}; finish the matching lesson to keep {pronoun}"


def _what_remains(
    sp: SkillProgress,
    spec: SkillSpec,
    *,
    banked_practice_reps: int = 0,
) -> str:
    """The plain "what remains to advance" line for one skill (SURF-01).

    Deterministic, never-raises UI affordance copy — single-sourced in Python so
    the frontend never re-derives the stage rule. Honest at every stage; the
    uncreditable branch states the current limit without hinting at a hidden path:

      * ``mastered``  → ``""`` (the cited-proof line carries it; nothing remains).
      * ``competent`` + creditable → ``"{N-count} more cited proof(s) to Master"``.
      * ``competent`` + uncreditable → states the limit, NO false "soon"/"coming".
      * ``locked`` + lessons done (fill ≥ threshold) → the recital is the gate (COMP-02).
      * ``locked`` + lessons unfinished → finish the lessons first.
    """
    if sp.stage == "mastered":
        return ""
    if sp.stage == "competent":
        if not spec.live_creditable:
            # No event grounds this skill, so it caps at Competent. State the fact
            # without promising a path that does not exist (anti-slop).
            return "Mastered isn't live-graded for this skill"
        remaining = max(1, spec.mastered_threshold - sp.live_proof_count)
        unit = "proof" if remaining == 1 else "proofs"
        return f"{remaining} more cited {unit} to Master"
    # locked: distinguish "needs the recital" (lessons done) from "needs lessons".
    if sp.learn_fill >= COMPETENT_THRESHOLD:
        return "Pass the recital to reach Competent"
    if banked_practice_reps > 0:
        return _practice_bank_remains_line(banked_practice_reps)
    return "Finish the lessons to reach Competent"


def skill_wall_payload(
    progress: Any, manifest: dict[str, SkillSpec] | None = None
) -> list[dict[str, Any]]:
    """Derived Earned-Wall payload for the ``ipc.learn.progress_state`` envelope.

    Folds :meth:`SkillTree.compute` into a JSON-safe, manifest-ordered list — the
    paint-ready block the webview renders as the Earned Wall. The Competent/
    Mastered stage rule AND the ``what_remains`` advance line stay single-sourced
    HERE (Python), so the frontend never re-derives ``COMPETENT_THRESHOLD``/weights
    (no manifest-drift risk). IPC-only: this is NEVER persisted — it rides the
    snapshot envelope, never ``to_dict``.
    """
    tree = SkillTree(manifest) if manifest is not None else SkillTree()
    rows: list[dict[str, Any]] = []
    for skill_id, sp in tree.compute(progress).items():
        row = sp.as_payload()
        spec = tree._manifest.get(skill_id)
        if spec is not None:
            row["what_remains"] = _what_remains(
                sp,
                spec,
                banked_practice_reps=_practice_bank_count_for_spec(progress, spec),
            )
        else:
            row["what_remains"] = ""
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Phase 103 (v11.0 "Earned"), Plan 01 — the live-portion WRITER (MAST-01/04)
# ---------------------------------------------------------------------------
# Phase 102 deliberately left ``record_live_demo`` + the ``skills`` live-portion
# fields as the forward seam: 102 SHIPPED the storage (``_fresh_skills_block``)
# and the ``stage="mastered"`` DERIVATION (``compute`` above). Plan 103-01 only
# WRITES the slot. The Wave-2 recognizer (Plan 103-02) is the citation-gated
# caller; this mutator is reached only after that gate, but enforces the
# MAST-01 Competent floor itself so it can never over-credit on its own.


def _threshold_for(
    skill_id: str, manifest: dict[str, SkillSpec] | None = None
) -> int:
    """Mastered threshold (N grounded demos) for one skill — MAST-04.

    Reads :attr:`SkillSpec.mastered_threshold` off the manifest so a per-skill
    tune (``§EARNED-MASTERY-THRESHOLD-TUNE``) needs no code change. An unknown
    skill id falls back to the uniform default ``3`` (defensive — an unmapped id
    never reaches here because :func:`record_live_demo` gates on Competent
    first, which is False for an unknown id).
    """
    table = manifest if manifest is not None else SKILL_MANIFEST
    spec = table.get(skill_id)
    return spec.mastered_threshold if spec is not None else 3


def record_live_demo(progress: Any, skill_id: str, *, now: str) -> Any:
    """Credit ONE grounded live demonstration toward a skill's Mastered fill.

    A PURE transform over ``progress.skills[skill_id]``: mutates that single
    block in place and returns ``progress``. Calls no clock and does no I/O —
    ``now`` is INJECTED (a string) for determinism (102 precedent) and
    persistence is the caller's job (``save_progress``). Mutates ONLY the one
    skill's live-portion; touches no other field.

    Contract (MAST-01 / MAST-04):

      1. MAST-01 GATE — Competent is DERIVED, never stored, so we read it via
         ``SkillTree().compute(progress)[skill_id].competent``. If the skill is
         not yet Competent (or the id is unknown), this is a NO-OP: return
         ``progress`` unchanged with NO ``setdefault`` write. Locked skills
         ignore live events entirely — no buffered backfill (you cannot master
         what you have not learned).
      2. ``setdefault`` the live-portion block to its safe defaults (mirrors
         ``_fresh_skills_block`` — ``live_proof_count`` 0 / ``mastered`` False /
         ``first_mastered_at`` None) so a sparse/missing entry is filled in.
      3. Increment ``live_proof_count`` using the same ``int(... or 0)`` +
         ``try/except`` guard ``compute`` uses (skill_tree.py ~:294) — a
         hand-edited / garbage count degrades to 0 instead of raising the
         uncaught ``ValueError`` that would contradict the engine's never-raises
         contract (V5 input validation; the file is user-owned).
      4. If ALREADY mastered: increment the count only — NEVER re-stamp
         ``first_mastered_at`` (Pitfall 2: a 4th/5th demo must not lose the true
         first-mastery moment). ``mastered`` is monotonic.
      5. Otherwise increment, and ONLY on the not-mastered→mastered transition
         (``count >= threshold and not mastered``) set ``mastered=True`` +
         ``first_mastered_at=now`` — stamped exactly once, by construction.

    WHY ``first_mastered_at`` is guarded: it records the genuine first moment a
    skill was earned to Mastered; over-writing it on later demos would erase
    that. WHY the count guard mirrors ``compute``: both read the same
    user-editable ``skills`` block, so they must share the never-raises posture.
    """
    # (1) MAST-01 gate — read DERIVED Competent (not a stored field). An unknown
    # skill id yields no SkillProgress entry → treated as not-Competent → NO-OP.
    computed = SkillTree().compute(progress).get(skill_id)
    if computed is None or not computed.competent:
        return progress  # locked / unknown — ignore the event, write nothing

    # (2) Fill the live-portion block if sparse/missing (mirror the 102 shape).
    block = progress.skills.setdefault(
        skill_id,
        {"live_proof_count": 0, "mastered": False, "first_mastered_at": None},
    )

    # (3) Read the current count with the same never-raises guard as compute.
    try:
        count = int(block.get("live_proof_count", 0) or 0)
    except (TypeError, ValueError):
        count = 0

    already_mastered = bool(block.get("mastered", False))
    count += 1
    block["live_proof_count"] = count

    if already_mastered:
        # (4) Monotonic — count may keep climbing, ts NEVER re-stamped.
        return progress

    # (5) Stamp the first-mastery moment exactly once, on the transition only.
    if count >= _threshold_for(skill_id):
        block["mastered"] = True
        block["first_mastered_at"] = now
    return progress
