# SPDX-License-Identifier: Apache-2.0
"""Derived next-practice mission for the Learn booth.

The mission is an IPC-only projection. It turns the stored progress ledger plus
the derived skill wall into one plain next move for the frontstage, without
writing a second recommendation source into ``learn-progress.json``.
"""

from __future__ import annotations

from typing import Any

from vibemix.learn.coaching_aim import resolve_coaching_aim_skill
from vibemix.learn.curriculum import COURSE_REGISTRY, CURRICULUM
from vibemix.learn.skill_tree import SKILL_MANIFEST, skill_wall_payload

_INTRO_LESSON_IDS = {"L0.00-press-play", "L1.01"}
_LESSON_SKILL_LABELS: dict[str, str] = {
    lesson_id: skill_id
    for skill_id, spec in SKILL_MANIFEST.items()
    for lesson_id in spec.lesson_ids
}
_SKILL_LABELS: dict[str, str] = {
    "deck_control": "deck control",
    "beatmatching": "beatmatching",
    "eq_mixing": "EQ mixing",
    "harmonic_mixing": "harmonic mixing",
    "transitions": "transitions",
    "phrasing_performance": "phrasing",
}
_SKILL_PAYOFFS: dict[str, str] = {
    "deck_control": "Your hands learn where the booth lives before the music gets busy.",
    "beatmatching": "You hear drift tighten into lock instead of reading about it.",
    "eq_mixing": "You learn which part of the track each band actually changes.",
    "harmonic_mixing": "You hear when two melodies belong together and when they fight.",
    "transitions": "You build one clean handoff you can use in a real set.",
    "phrasing_performance": "You learn where the music gives you room to move.",
}
_COURSE_ESTIMATES: dict[str, int] = {
    "course_1_anatomy": 4,
    "course_2_transitions": 6,
    "course_3_play_mode": 10,
}
_SCREEN_WARMUP_REP_TARGET = 3


def next_practice_mission(
    progress: Any,
    *,
    active_lesson_id: str | None = None,
) -> dict[str, Any]:
    """Return the single next move the Learn booth should foreground.

    ``progress.to_dict()`` remains the persistence shape; callers add this to
    ``snapshot()`` only. The returned lesson always comes from ``CURRICULUM`` and
    respects the same course gates as the lesson chooser.
    """
    wall = skill_wall_payload(progress)
    lesson_id, mode = _recommended_lesson(
        progress,
        wall,
        active_lesson_id=active_lesson_id,
    )
    meta = CURRICULUM[lesson_id]
    skill_id = _mission_skill_id(lesson_id, wall)
    skill_label = _SKILL_LABELS.get(skill_id, "DJ skill")
    title = meta.title
    row = _lesson_row(progress, lesson_id)
    skill_row = _skill_row(wall, skill_id)
    feedback = _feedback_for(row)
    command = _command_for(mode, title, skill_label, wall, skill_id, row, feedback)
    payoff = _SKILL_PAYOFFS.get(
        skill_id,
        "You turn one abstract lesson into a move you can repeat.",
    )
    proof = _proof_for(progress, lesson_id, skill_label, skill_row, feedback)
    why = _why_for(mode, skill_label, wall, skill_id, feedback)
    focus = _focus_for(mode, row, skill_id, skill_row, feedback)
    focus_label = _focus_label_for(focus, row, skill_id, skill_row, feedback)
    challenge = _challenge_for(mode, row, skill_label, skill_row, feedback)
    practice_surface = _practice_surface_for(mode, focus, row, feedback)
    meter = _meter_for(mode, focus, row, skill_id, skill_label, skill_row, feedback)
    momentum = _momentum_for(mode, focus, row, skill_id, skill_row, feedback)
    chain = _practice_chain_for(
        progress,
        lesson_id=lesson_id,
        mode=mode,
        focus_label=focus_label,
    )
    return {
        "lesson_id": lesson_id,
        "course_id": meta.course_id,
        "course_label": COURSE_REGISTRY[meta.course_id].label,
        "skill_id": skill_id,
        "skill_label": skill_label,
        "title": title,
        "mode": mode,
        "command": command,
        "payoff": payoff,
        "proof": proof,
        "why": why,
        "estimated_minutes": _COURSE_ESTIMATES.get(meta.course_id, 5),
        "focus": focus,
        "focus_label": focus_label,
        "challenge": challenge,
        "practice_surface": practice_surface,
        "chain": chain,
        **meter,
        **momentum,
    }


def _recommended_lesson(
    progress: Any,
    wall: list[dict[str, Any]],
    *,
    active_lesson_id: str | None = None,
) -> tuple[str, str]:
    lessons = getattr(progress, "lessons", {}) or {}
    active_mastered = _active_mastered_lesson(progress, wall, active_lesson_id)
    if active_mastered is not None:
        return active_mastered, "mastered"
    active_proof = _active_proof_lesson(progress, wall, active_lesson_id)
    if active_proof is not None:
        return active_proof, "prove"
    recent_practice = _recent_practice_lesson(progress)
    if recent_practice is not None:
        return recent_practice, "finish"
    first_unlocked: str | None = None
    first_empty: str | None = None
    for lesson_id, meta in CURRICULUM.items():
        if lesson_id.startswith("L0."):
            continue
        row = lessons.get(lesson_id)
        status = _lesson_status(row)
        if not _course_unlocked(progress, meta.course_id) and status != "completed":
            continue
        if first_unlocked is None:
            first_unlocked = lesson_id
        if status == "in-progress":
            return lesson_id, "finish"
        if first_empty is None and status != "completed" and lesson_id not in _INTRO_LESSON_IDS:
            first_empty = lesson_id
    proof_lesson_id = _proof_lesson(progress, wall)
    if proof_lesson_id is not None:
        return proof_lesson_id, "prove"
    if first_empty is not None:
        return first_empty, "start"
    if first_unlocked is not None:
        return first_unlocked, "replay"
    return "L1.01", "start"


def _course_unlocked(progress: Any, course_id: str) -> bool:
    gate = COURSE_REGISTRY[course_id].unlock_gate
    if gate is None:
        return True
    return bool(getattr(progress, gate, False))


def _lesson_status(row: Any) -> str:
    if not isinstance(row, dict):
        return "empty"
    if row.get("completed") is True:
        return "completed"
    strikes = _safe_int(row.get("strikes_used"), default=0)
    if row.get("completed") is False or strikes > 0:
        return "in-progress"
    return "empty"


def _mission_skill_id(lesson_id: str, wall: list[dict[str, Any]]) -> str:
    mapped = _LESSON_SKILL_LABELS.get(lesson_id)
    if mapped:
        return mapped
    for row in wall:
        if row.get("stage") != "mastered":
            skill_id = row.get("skill_id")
            if isinstance(skill_id, str) and skill_id:
                return skill_id
    return next(iter(SKILL_MANIFEST))


def _proof_lesson(progress: Any, wall: list[dict[str, Any]]) -> str | None:
    started = _started_proof_lesson(progress, wall)
    if started is not None:
        return started
    aim_skill = resolve_coaching_aim_skill(progress)
    if aim_skill is not None:
        aimed = _proof_lesson_for_skill(progress, aim_skill)
        if aimed is not None:
            return aimed
    for row in wall:
        if row.get("stage") != "competent":
            continue
        skill_id = row.get("skill_id")
        if not isinstance(skill_id, str):
            continue
        lesson_id = _proof_lesson_for_skill(progress, skill_id)
        if lesson_id is not None:
            return lesson_id
    return None


def _started_proof_lesson(progress: Any, wall: list[dict[str, Any]]) -> str | None:
    for row in wall:
        if row.get("stage") != "competent":
            continue
        if _safe_int(row.get("live_proof_count"), default=0) <= 0:
            continue
        skill_id = row.get("skill_id")
        if not isinstance(skill_id, str):
            continue
        lesson_id = _proof_lesson_for_skill(progress, skill_id)
        if lesson_id is not None:
            return lesson_id
    return None


def _proof_lesson_for_skill(progress: Any, skill_id: str) -> str | None:
    spec = SKILL_MANIFEST.get(skill_id)
    if spec is None or not spec.live_creditable:
        return None
    if not bool(getattr(progress, spec.gate, False)):
        return None
    for lesson_id in spec.lesson_ids:
        meta = CURRICULUM.get(lesson_id)
        if meta is not None and _course_unlocked(progress, meta.course_id):
            return lesson_id
    return None


def _recent_practice_lesson(progress: Any) -> str | None:
    """Return the unfinished lesson behind the learner's latest banked gesture."""
    lessons = getattr(progress, "lessons", {}) or {}
    best_lesson_id: str | None = None
    best_seq = 0
    for lesson_id, row in lessons.items():
        if not isinstance(lesson_id, str) or not isinstance(row, dict):
            continue
        if _lesson_status(row) != "in-progress":
            continue
        if _practice_bank_count(row) <= 0:
            continue
        meta = CURRICULUM.get(lesson_id)
        if meta is None or not _course_unlocked(progress, meta.course_id):
            continue
        seq = _practice_sequence(row)
        if seq > best_seq:
            best_lesson_id = lesson_id
            best_seq = seq
    return best_lesson_id


def _active_mastered_lesson(
    progress: Any,
    wall: list[dict[str, Any]],
    active_lesson_id: str | None,
) -> str | None:
    if not active_lesson_id:
        return None
    meta = CURRICULUM.get(active_lesson_id)
    if meta is None or not _course_unlocked(progress, meta.course_id):
        return None
    skill_id = _LESSON_SKILL_LABELS.get(active_lesson_id)
    if skill_id is None:
        return None
    spec = SKILL_MANIFEST.get(skill_id)
    if spec is None or not spec.live_creditable:
        return None
    row = _skill_row(wall, skill_id)
    if row is None:
        return None
    if row.get("stage") == "mastered" or row.get("mastered") is True:
        return active_lesson_id
    return None


def _active_proof_lesson(
    progress: Any,
    wall: list[dict[str, Any]],
    active_lesson_id: str | None,
) -> str | None:
    if not active_lesson_id:
        return None
    meta = CURRICULUM.get(active_lesson_id)
    if meta is None or not _course_unlocked(progress, meta.course_id):
        return None
    skill_id = _LESSON_SKILL_LABELS.get(active_lesson_id)
    if skill_id is None:
        return None
    spec = SKILL_MANIFEST.get(skill_id)
    if spec is None or not spec.live_creditable:
        return None
    row = _skill_row(wall, skill_id)
    if row is None or row.get("stage") != "competent":
        return None
    return active_lesson_id


def _command_for(
    mode: str,
    title: str,
    skill_label: str,
    wall: list[dict[str, Any]],
    skill_id: str,
    row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    clean_title = title.strip() or "the next lesson"
    if feedback is not None and mode != "mastered":
        return f"Fix {feedback['label']} on {clean_title}; {feedback['message']}"
    if mode == "finish":
        if _strike_count(row) > 0:
            return f"Retry {clean_title}; no hints, one clean move is the checkpoint."
        if _screen_warmup_needs_hardware(row):
            return (
                f"Move {clean_title} onto the controller; screen reps warmed it up, "
                "one hardware touch is the checkpoint."
            )
        return f"Finish {clean_title}; use one clean move, then let Learn verify it."
    if mode == "prove":
        return f"Prove {skill_label}; earn the next cited proof on {clean_title}."
    if mode == "mastered":
        return f"Review {clean_title}; carry the mastered {skill_label} move into a real set."
    if mode == "replay":
        return f"Replay {clean_title}; make it feel automatic, not just completed."
    remaining = _what_remains(wall, skill_id)
    if remaining and remaining != "Finish the lessons to reach Competent":
        return f"Practice {clean_title}; {remaining[0].lower()}{remaining[1:]}."
    return f"Practice {clean_title}; build one useful {skill_label} rep."


def _proof_for(
    progress: Any,
    lesson_id: str,
    skill_label: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    if feedback is not None:
        return f"last measured miss: {feedback['label']}"
    if skill_row and skill_row.get("stage") == "competent":
        skill_id = str(skill_row.get("skill_id") or "")
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = spec.mastered_threshold if spec is not None else 3
        count = max(0, _safe_int(skill_row.get("live_proof_count"), default=0))
        remaining = max(0, threshold - count)
        if remaining > 0:
            unit = "proof" if count == 1 else "proofs"
            return f"{count} cited {unit} banked; {remaining} left"
    if skill_row and (skill_row.get("stage") == "mastered" or skill_row.get("mastered") is True):
        count = max(0, _safe_int(skill_row.get("live_proof_count"), default=0))
        unit = "proof" if count == 1 else "proofs"
        return f"{count} cited {unit} banked; Mastery earned"
    row = _lesson_row(progress, lesson_id)
    if isinstance(row, dict):
        if _screen_warmup_needs_hardware(row):
            return "screen warm-up is banked; controller rep is next"
        last_source = str(row.get("last_practice_source") or "")
        if last_source == "hardware":
            return "last pass used hardware; repeat it on the controller"
        if last_source == "screen":
            return "screen deck has worked; repeat it cleanly"
    return f"Learn waits for a real {skill_label} move"


def _why_for(
    mode: str,
    skill_label: str,
    wall: list[dict[str, Any]],
    skill_id: str,
    feedback: dict[str, str] | None,
) -> str:
    if feedback is not None and mode != "mastered":
        return "fix the measured miss before chasing the next proof"
    if mode == "mastered":
        return "Mastery earned from cited live proof"
    if mode == "replay":
        return f"keep {skill_label} warm after the course is cleared"
    remaining = _what_remains(wall, skill_id)
    if remaining:
        return remaining
    return f"move {skill_label} forward"


def _what_remains(wall: list[dict[str, Any]], skill_id: str) -> str:
    for row in wall:
        if row.get("skill_id") == skill_id:
            value = row.get("what_remains", "")
            return value if isinstance(value, str) else ""
    return ""


def _focus_for(
    mode: str,
    row: dict[str, Any] | None,
    skill_id: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    if mode == "mastered" or (
        skill_row is not None
        and (skill_row.get("stage") == "mastered" or skill_row.get("mastered") is True)
    ):
        return "mastery"
    if feedback is not None:
        return "recovery"
    if mode == "prove" or (skill_row is not None and skill_row.get("stage") == "competent"):
        return "proof"
    if mode == "finish" and _strike_count(row) > 0:
        return "retry"
    if mode == "replay":
        return "replay"
    if _screen_warmup_needs_hardware(row):
        return "hardware"
    if _source_total(row, "hardware") > 0:
        return "hardware"
    if skill_id == "beatmatching":
        return "lock"
    return "first_rep"


def _focus_label_for(
    focus: str,
    row: dict[str, Any] | None,
    skill_id: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    if focus == "mastery":
        return "mastered"
    if focus == "recovery" and feedback is not None:
        return feedback["label"]
    if focus == "retry":
        return f"retry {_strike_count(row)}/3"
    if focus == "proof":
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = spec.mastered_threshold if spec is not None else 3
        count = 0
        if skill_row is not None:
            count = max(0, _safe_int(skill_row.get("live_proof_count"), default=0))
        return f"proof {min(count, threshold)}/{threshold}"
    if focus == "replay":
        return "clean replay"
    if focus == "hardware":
        if _screen_warmup_needs_hardware(row):
            return "controller rep next"
        return _practice_bank_label(row)
    if _source_total(row, "screen") > 0:
        return _practice_bank_label(row)
    if focus == "lock":
        return "lock drill"
    return "first rep"


def _challenge_for(
    mode: str,
    row: dict[str, Any] | None,
    skill_label: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    if mode == "mastered" or (
        skill_row is not None
        and (skill_row.get("stage") == "mastered" or skill_row.get("mastered") is True)
    ):
        return "Carry it into a real set while it is fresh."
    if feedback is not None:
        return feedback["message"]
    if mode == "prove" or (skill_row is not None and skill_row.get("stage") == "competent"):
        return "Only cited live proof moves Mastery."
    if mode == "finish" and _strike_count(row) > 0:
        return "No hint this time; one clean move clears the loop."
    if mode == "finish" and _screen_warmup_needs_hardware(row):
        return "Screen warm-up is banked; repeat it once on the controller when connected."
    if mode == "finish" and _source_total(row, "hardware") > 0:
        return "Repeat the controller move inside the lesson."
    if mode == "finish" and _source_total(row, "screen") > 0:
        return "Repeat a banked move inside the lesson."
    if mode == "replay":
        return f"Make {skill_label} feel automatic before moving on."
    return "Touch the control before you read ahead."


def _practice_surface_for(
    mode: str,
    focus: str,
    row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> str:
    """Name the physical surface the frontstage should route the learner toward."""
    if focus == "recovery" and feedback is not None:
        return "controller" if feedback.get("kind") == "control" else "live_proof"
    if mode == "prove" or focus in {"proof", "mastery"}:
        return "live_proof"
    if _screen_warmup_needs_hardware(row) or _source_total(row, "hardware") > 0:
        return "controller"
    return "screen_deck"


def _meter_for(
    mode: str,
    focus: str,
    row: dict[str, Any] | None,
    skill_id: str,
    skill_label: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> dict[str, Any]:
    if focus == "mastery":
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = max(1, spec.mastered_threshold if spec is not None else 3)
        return {
            "meter_label": "mastery",
            "meter_value": threshold,
            "meter_max": threshold,
            "meter_state": "mastered",
            "meter_caption": "Mastery earned",
        }
    if focus == "recovery" and feedback is not None:
        return {
            "meter_label": "recovery target",
            "meter_value": 0,
            "meter_max": 1,
            "meter_state": "retry",
            "meter_caption": feedback.get("detail") or feedback["message"],
        }
    if focus == "proof":
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = max(1, spec.mastered_threshold if spec is not None else 3)
        count = 0
        if skill_row is not None:
            count = max(0, _safe_int(skill_row.get("live_proof_count"), default=0))
        shown_count = min(count, threshold)
        remaining = max(0, threshold - count)
        caption = "Mastery earned" if remaining == 0 else _plural_left(remaining, "proof", "Mastery")
        state = "mastered" if remaining == 0 else "proof"
        return {
            "meter_label": "proof bank",
            "meter_value": shown_count,
            "meter_max": threshold,
            "meter_state": state,
            "meter_caption": caption,
        }
    if focus == "retry":
        return {
            "meter_label": "retry loop",
            "meter_value": _strike_count(row),
            "meter_max": 3,
            "meter_state": "retry",
            "meter_caption": "one clean move clears it",
        }
    if mode == "replay":
        return {
            "meter_label": "replay lane",
            "meter_value": 1,
            "meter_max": 1,
            "meter_state": "replay",
            "meter_caption": f"keep {skill_label} warm",
        }
    if _screen_warmup_needs_hardware(row):
        return {
            "meter_label": "controller checkpoint",
            "meter_value": 0,
            "meter_max": 1,
            "meter_state": "armed",
            "meter_caption": "3 screen reps banked; controller rep next",
        }
    if _source_total(row, "hardware") > 0:
        count = _practice_bank_count(row)
        return {
            "meter_label": "practice bank",
            "meter_value": count,
            "meter_max": 3,
            "meter_state": "armed",
            "meter_caption": _practice_bank_caption(row),
        }
    if _source_total(row, "screen") > 0:
        count = _practice_bank_count(row)
        return {
            "meter_label": "practice bank",
            "meter_value": count,
            "meter_max": 3,
            "meter_state": "armed",
            "meter_caption": _practice_bank_caption(row),
        }
    return {
        "meter_label": "first rep",
        "meter_value": 0,
        "meter_max": 1,
        "meter_state": "armed",
        "meter_caption": "touch the control to begin",
    }


def _momentum_for(
    mode: str,
    focus: str,
    row: dict[str, Any] | None,
    skill_id: str,
    skill_row: dict[str, Any] | None,
    feedback: dict[str, str] | None,
) -> dict[str, Any]:
    """Return a short streak loop grounded in persisted practice receipts."""
    if focus == "mastery":
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = max(1, spec.mastered_threshold if spec is not None else 3)
        return {
            "momentum_label": f"proof streak {threshold}/{threshold}",
            "momentum_value": threshold,
            "momentum_max": threshold,
            "momentum_caption": "Mastery earned; carry it into a set",
        }
    if focus == "recovery" and feedback is not None:
        return {
            "momentum_label": "fix loop",
            "momentum_value": 0,
            "momentum_max": 1,
            "momentum_caption": "fix the miss before chasing proof",
        }
    if focus == "proof":
        spec = SKILL_MANIFEST.get(skill_id)
        threshold = max(1, spec.mastered_threshold if spec is not None else 3)
        count = 0
        if skill_row is not None:
            count = max(0, _safe_int(skill_row.get("live_proof_count"), default=0))
        shown_count = min(count, threshold)
        remaining = max(0, threshold - count)
        caption = (
            "Mastery earned; review it while fresh"
            if remaining == 0
            else _plural_left(remaining, "cited proof", "Mastery")
        )
        return {
            "momentum_label": f"proof streak {shown_count}/{threshold}",
            "momentum_value": shown_count,
            "momentum_max": threshold,
            "momentum_caption": caption,
        }
    if focus == "retry":
        return {
            "momentum_label": "clean rep 0/1",
            "momentum_value": 0,
            "momentum_max": 1,
            "momentum_caption": "one clean rep clears the retry loop",
        }
    if mode == "replay":
        return {
            "momentum_label": "replay streak 1/1",
            "momentum_value": 1,
            "momentum_max": 1,
            "momentum_caption": "keep it automatic while it is warm",
        }
    if _screen_warmup_needs_hardware(row):
        return {
            "momentum_label": "streak 3/3",
            "momentum_value": 3,
            "momentum_max": 3,
            "momentum_caption": "streak armed; controller checkpoint next",
        }
    count = _practice_bank_count(row)
    if count > 0:
        remaining = max(0, 3 - count)
        if remaining == 0:
            caption = "streak full; finish the lesson now"
        else:
            unit = "rep" if remaining == 1 else "reps"
            caption = f"{remaining} clean {unit} to fill the bank"
        return {
            "momentum_label": f"streak {count}/3",
            "momentum_value": count,
            "momentum_max": 3,
            "momentum_caption": caption,
        }
    return {
        "momentum_label": "streak 0/3",
        "momentum_value": 0,
        "momentum_max": 3,
        "momentum_caption": "one clean move starts the streak",
    }


def _practice_chain_for(
    progress: Any,
    *,
    lesson_id: str,
    mode: str,
    focus_label: str,
) -> list[dict[str, str]]:
    """Return the short run the booth should make feel finishable now."""
    chain: list[dict[str, str]] = []
    current_meta = CURRICULUM.get(lesson_id)
    if current_meta is None:
        return chain
    chain.append(
        _chain_step(
            lesson_id,
            state="now",
            mode=mode,
            label=focus_label,
        )
    )
    seen = {lesson_id}
    for candidate_id in _lesson_ids_after(lesson_id):
        if len(chain) >= 3:
            break
        meta = CURRICULUM[candidate_id]
        row = _lesson_row(progress, candidate_id)
        status = _lesson_status(row)
        if not _course_unlocked(progress, meta.course_id) and status != "completed":
            if len(chain) < 3:
                chain.append(
                    _chain_step(
                        candidate_id,
                        state="locked",
                        mode="start",
                        label=_locked_chain_label(meta.course_id),
                    )
                )
            break
        if candidate_id in seen or status == "completed":
            continue
        chain.append(
            _chain_step(
                candidate_id,
                state="next",
                mode="finish" if status == "in-progress" else "start",
                label=_chain_label_for(row, status),
            )
        )
        seen.add(candidate_id)
    return chain


def _lesson_ids_after(lesson_id: str) -> list[str]:
    lesson_ids = [
        lid for lid in CURRICULUM if not lid.startswith("L0.") and lid not in _INTRO_LESSON_IDS
    ]
    if lesson_id not in lesson_ids:
        return lesson_ids
    index = lesson_ids.index(lesson_id)
    return lesson_ids[index + 1 :] + lesson_ids[:index]


def _chain_step(
    lesson_id: str,
    *,
    state: str,
    mode: str,
    label: str,
) -> dict[str, str]:
    meta = CURRICULUM[lesson_id]
    return {
        "lesson_id": lesson_id,
        "course_id": meta.course_id,
        "course_label": COURSE_REGISTRY[meta.course_id].label,
        "title": meta.title,
        "state": state,
        "mode": mode,
        "label": label,
    }


def _locked_chain_label(course_id: str) -> str:
    course = COURSE_REGISTRY.get(course_id)
    if course is None:
        return "locked"
    return course.lock_reason or "locked"


def _chain_label_for(row: dict[str, Any] | None, status: str) -> str:
    if status == "empty":
        return "next rep"
    if _screen_warmup_needs_hardware(row):
        return "controller next"
    bank_count = _practice_bank_count(row)
    if bank_count > 0:
        return f"banked {bank_count}/3"
    return "finish"


def _plural_left(count: int, unit: str, target: str) -> str:
    label = unit if count == 1 else f"{unit}s"
    return f"{count} {label} left to {target}"


def _skill_row(wall: list[dict[str, Any]], skill_id: str) -> dict[str, Any] | None:
    for row in wall:
        if row.get("skill_id") == skill_id:
            return row
    return None


def _lesson_row(progress: Any, lesson_id: str) -> dict[str, Any] | None:
    row = (getattr(progress, "lessons", {}) or {}).get(lesson_id)
    return row if isinstance(row, dict) else None


def _feedback_for(row: dict[str, Any] | None) -> dict[str, str] | None:
    if row is None:
        return None
    raw = row.get("practice_feedback")
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip()
    label = str(raw.get("label") or "").strip()
    message = str(raw.get("message") or "").strip()
    if kind not in {"beatmatch", "cue_placement", "control"} or not label or not message:
        return None
    feedback = {
        "kind": kind,
        "label": label[:48],
        "message": message[:180],
    }
    detail = str(raw.get("detail") or "").strip()
    if detail:
        feedback["detail"] = detail[:120]
    return feedback


def _strike_count(row: dict[str, Any] | None) -> int:
    if row is None:
        return 0
    return max(0, min(3, _safe_int(row.get("strikes_used"), default=0)))


def _source_total(row: dict[str, Any] | None, source: str) -> int:
    if row is None:
        return 0
    counts = row.get("practice_sources")
    if not isinstance(counts, dict):
        return 0
    return max(0, _safe_int(counts.get(source), default=0))


def _practice_bank_count(row: dict[str, Any] | None) -> int:
    return max(
        0,
        min(3, _source_total(row, "hardware") + _source_total(row, "screen")),
    )


def _screen_warmup_needs_hardware(row: dict[str, Any] | None) -> bool:
    return (
        _source_total(row, "screen") >= _SCREEN_WARMUP_REP_TARGET
        and _source_total(row, "hardware") <= 0
    )


def _practice_sequence(row: dict[str, Any] | None) -> int:
    if row is None:
        return 0
    try:
        return max(0, int(row.get("last_practice_seq", 0)))
    except (TypeError, ValueError):
        return 0


def _practice_bank_label(row: dict[str, Any] | None) -> str:
    count = _practice_bank_count(row)
    return f"practice bank {count}/3"


def _practice_bank_caption(row: dict[str, Any] | None) -> str:
    hardware = _source_total(row, "hardware")
    screen = _source_total(row, "screen")
    count = _practice_bank_count(row)
    if hardware > 0 and screen > 0:
        return f"{count} reps banked: screen + hardware"
    unit = "rep" if count == 1 else "reps"
    if hardware > 0:
        return f"{count} controller {unit} banked"
    return f"{count} screen {unit} banked"


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
