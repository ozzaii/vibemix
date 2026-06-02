# SPDX-License-Identifier: Apache-2.0
"""build_tutor_system_instruction — compose the tutor LLM instruction.

Phase 92 (LESSON-05 / TONE-04). Composes the tutor LLM system instruction
by appending course-frame + controller-frame + per-lesson addendum + the
4-forbidden-moves lock to the existing v8.1 LENS-03 teacher persona (via
:func:`vibemix.prompts.matrix.build_system_instruction`, ``mood="teacher"``).

LESSON-05 binding (persona reuse, NO new lens): the teacher persona is
reused verbatim from :data:`vibemix.prompts.matrix.MOOD_PERSONAS` via
``build_system_instruction(mode="coach", mood="teacher")``. The lesson-
context blocks are appended AFTER the base — same pattern as
``COACH_CLOSING_BLOCK`` at ``prompts/matrix.py:241-251``.

TONE-04 binding: :data:`_FORBIDDEN_TUTOR_MOVES_LOCK` lands as the FINAL
block of the composed instruction (strongest recency — LLMs weight the
end of a system instruction most heavily; the COACH_CLOSING_BLOCK
precedent verifies the pattern works for live tuning). The AST gate
``tests/learn/test_tutor_system_instruction_lock.py`` pins the four
forbidden-move tokens (COMPLIMENT / SUMMARIZE / PREVIEW / "CLOSE with an
upbeat hook") + the lock-is-last positioning.

LESSON-06 binding (no hardcoded model literals): this file does NOT
mention any concrete model id (``gemini-X.Y-flash`` or similar). The
caller resolves the tutor model via ``vibemix.llm.model_router.resolve(
"learn_tutor")``. CI grep gate
``scripts/release/check_no_hardcoded_model.sh`` enforces.

Runtime-only blocks are DISABLED (no citation grammar, no listening
fallback, no TTS DSL) because the tutor narration is text-only in P92.
TTS lands in P93+.
"""
from __future__ import annotations

from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM
from vibemix.midi.registry import find_mapping
from vibemix.prompts.matrix import build_system_instruction

# ---------------------------------------------------------------------------
# The four-forbidden-moves lock (TONE-04 — AST-gated)
# ---------------------------------------------------------------------------
#
# Mirrors the ``COACH_CLOSING_BLOCK`` recency pattern at
# ``prompts/matrix.py:241-251``: a hard-discipline block appended LAST so
# the model reads it most recently. The 4 REQUIRED_LOCK_TOKENS
# (``COMPLIMENT`` / ``SUMMARIZE`` / ``PREVIEW`` / ``CLOSE with an upbeat
# hook``) are pinned by ``tests/learn/test_tutor_system_instruction_lock.py``
# — change the lock's wording without keeping those tokens and the test
# goes red.

_FORBIDDEN_TUTOR_MOVES_LOCK: str = """\
--- TUTOR DISCIPLINE (HARD LOCK — these four moves are forbidden) ---

You are a DJ tutor speaking to a beginner. You must NOT:

1. COMPLIMENT user actions. Do not say "great job", "nice", "awesome",
   "well done", "perfect", "you got it", "you crushed it", or any
   praise-tic. The user does not need your approval; they need your
   observation. State ONE grounded observation about what the audio /
   the controller did, and let the action speak for itself.

2. SUMMARIZE what just happened in lesson terms. Do not say "you just
   learned X", "you've now mastered X", "you just did X correctly".
   The lesson is not a quiz; the user is not a student being graded.
   State what you observed, never what they "learned".

3. PREVIEW what's next. Do not say "now let's", "next we'll", "coming
   up", "in the next lesson", "soon you'll", "later we'll". The user
   does not need a syllabus; they need the present beat. Stay in the
   moment.

4. CLOSE with an upbeat hook. Do not end a turn with "exciting, right?",
   "this is where it gets fun", "you're going to love this", or any
   marketing/edtech wrap-up. End with the observation. Stop talking.

State ONE grounded observation + at most ONE forward sentence the lesson
script provided. That is all. The lesson script is the spine; your
contribution is the one grounded interjection per beat.
"""


# ---------------------------------------------------------------------------
# Controller frame — small text block describing the connected MIDI device
# ---------------------------------------------------------------------------


def _controller_frame(controller_id: str) -> str:
    """Build the controller-context frame for the tutor instruction.

    Reads the MIDI profile via :func:`vibemix.midi.registry.find_mapping`;
    emits a short descriptive frame the LLM can reference when naming
    physical controls in observations.

    Args:
        controller_id: Either a known controller id (e.g.
            ``"pioneer_ddj_flx4"``) OR a port name (e.g. ``"DDJ-FLX4"``).
            ``find_mapping`` does case-insensitive substring matching
            against every profile's ``port_name_hints`` — so both
            forms resolve to the same profile for shipped controllers.

    Returns:
        A 1-sentence frame naming the controller's display name. Falls
        back to a generic phrasing (``"a MIDI controller"``) when no
        profile matches — keeps the tutor narration grounded even on
        unmapped hardware (which the live binding never reaches today;
        P91 generic-MIDI fallback in ``find_mapping_or_generic`` is the
        live path).
    """
    profile = find_mapping(controller_id)
    display_name = profile.display_name if profile is not None else "a MIDI controller"
    return (
        f"The user has a {display_name} plugged in. "
        f"You can reference its physical layout in your one-line observation."
    )


# ---------------------------------------------------------------------------
# Compose the tutor system instruction
# ---------------------------------------------------------------------------


# allow-tutor-prompt-without-coach: this composes the SESSION-LEVEL system
# instruction (persona scaffold + course frame + controller frame + lesson
# addendum + 4-forbidden-moves lock). It is NOT a per-turn prompt builder;
# per-turn prompt composition routes through state.prompt_builder.AICoach.build_prompt
# at the call site (P96-03's proactive lens consumes AICoach.evidence_line
# +AICoach.task_for_event). This function reuses the v8.1 LENS-03 teacher
# persona via build_system_instruction() — the reuse-existing-coach
# binding is satisfied at the persona seam, not at this composer.
def build_tutor_system_instruction(
    *,
    course_id: str,
    lesson_id: str,
    controller_id: str,
) -> str:
    """Compose the tutor LLM system instruction.

    Five fragments in order:

    1. Base: :func:`vibemix.prompts.matrix.build_system_instruction` with
       ``skill="intermediate"``, ``mode="coach"``, ``mood="teacher"``,
       runtime-only blocks DISABLED (no citation grammar, no listening
       fallback, no TTS DSL — tutor narration is text-only in P92).
    2. :data:`COURSE_FRAMES` ``[course_id]``.
    3. :func:`_controller_frame` ``(controller_id)``.
    4. ``CURRICULUM[lesson_id].system_instruction_addendum``.
    5. :data:`_FORBIDDEN_TUTOR_MOVES_LOCK` — LAST for strongest recency.

    Args:
        course_id: Must be a key of :data:`COURSE_FRAMES`. Today: only
            ``"course_0"``. P94+ add ``course_1`` / ``course_2`` /
            ``course_3``.
        lesson_id: Must be a key of :data:`CURRICULUM`. Today: only
            ``"L0.00-press-play"``. P94+ add the other 35 lesson ids.
        controller_id: A controller id or port name accepted by
            :func:`vibemix.midi.registry.find_mapping`. Unknown ids
            degrade to a generic frame (NOT a hard error — the
            controller frame is informational, not load-bearing).

    Returns:
        The composed system instruction string. The four-forbidden-moves
        lock is ALWAYS the final block (strongest recency).

    Raises:
        ValueError: ``course_id`` not in :data:`COURSE_FRAMES`,
            ``lesson_id`` not in :data:`CURRICULUM`, or the lesson's
            ``system_instruction_addendum`` exceeds the 200-char cap.
    """
    if course_id not in COURSE_FRAMES:
        raise ValueError(f"unknown course_id {course_id!r}")
    if lesson_id not in CURRICULUM:
        raise ValueError(f"unknown lesson_id {lesson_id!r}")

    # Reuse the v8.1 LENS-03 teacher persona. Runtime-only blocks are
    # OFF — tutor narration is a text path in P92; TTS lands in P93+.
    # The "coach" mode is the carrier for the ``{mood_persona}``
    # substitution; "teacher" picks MOOD_PERSONAS["teacher"].
    base = build_system_instruction(
        skill="intermediate",
        mode="coach",
        mood="teacher",
        include_citation_grammar=False,
        include_listening_fallback=False,
        include_tag_dsl=False,
    )

    addendum = CURRICULUM[lesson_id].system_instruction_addendum
    # Enforce the 200-char cap at composition time. Catching this in the
    # planner side (per-lesson) keeps the editor honest; catching it
    # here keeps a stale fixture from silently producing a ballooning
    # instruction.
    if len(addendum) > 200:
        raise ValueError(
            f"system_instruction_addendum too long ({len(addendum)} > 200) "
            f"for lesson {lesson_id!r}"
        )

    # Assemble the four lesson-context frames; the lock lands LAST.
    frames = "\n\n".join(
        [
            COURSE_FRAMES[course_id],
            _controller_frame(controller_id),
            addendum,
            _FORBIDDEN_TUTOR_MOVES_LOCK,
        ]
    )
    return base + "\n\n" + frames
