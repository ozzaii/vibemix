# SPDX-License-Identifier: Apache-2.0
"""Grounded Course 3 graduation lens.

L3.06 is the handoff from Learn into the existing debrief/profile surfaces. The
frontstage stays one calm prompt, but the runtime should not claim a profile or
debrief exists without checking the real seams first.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.progress import LearnProgress
from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE


@dataclass(frozen=True, slots=True)
class GraduationSummary:
    """Small truthful packet for the final beginner lesson."""

    completed_lessons: int
    total_lessons: int
    profile_consent: bool
    profile_available: bool
    profile_genre: str | None = None
    profile_tempo_bin: str | None = None
    profile_tags: tuple[str, ...] = ()
    debrief_available: bool = False
    debrief_session_dir: str | None = None
    debrief_recommended_lesson_id: str | None = None
    debrief_recommended_lesson_title: str | None = None
    debrief_recommendation_reason: str | None = None
    hardware_practice_actions: int = 0
    screen_practice_actions: int = 0
    last_practice_source: str | None = None


def build_graduation_summary(
    progress: LearnProgress,
    *,
    profile_loader: Callable[[], dict[str, Any] | None] | None = None,
    consent_loader: Callable[[], bool] | None = None,
    recordings_root_loader: Callable[[], Path] | None = None,
) -> GraduationSummary:
    """Read Learn progress plus existing profile/debrief storage seams."""
    completed = _completed_beginner_lessons(progress)
    total = _total_beginner_lessons()
    consent = _load_profile_consent(consent_loader)
    profile = _load_profile(profile_loader) if consent else None
    debrief_session_dir, debrief = _latest_debrief(recordings_root_loader)
    recommendation = _recommend_lesson_from_debrief(debrief)
    hardware_actions, screen_actions, last_practice_source = _practice_source_summary(
        progress
    )

    return GraduationSummary(
        completed_lessons=completed,
        total_lessons=total,
        profile_consent=consent,
        profile_available=profile is not None,
        profile_genre=_profile_str(profile, "preferred_genre"),
        profile_tempo_bin=_profile_str(profile, "tempo_preference_bin"),
        profile_tags=_profile_tags(profile),
        debrief_available=debrief_session_dir is not None,
        debrief_session_dir=debrief_session_dir,
        debrief_recommended_lesson_id=recommendation[0],
        debrief_recommended_lesson_title=recommendation[1],
        debrief_recommendation_reason=recommendation[2],
        hardware_practice_actions=hardware_actions,
        screen_practice_actions=screen_actions,
        last_practice_source=last_practice_source,
    )


def build_graduation_tutor_line(summary: GraduationSummary) -> str:
    """Return one concise, non-bluffing line for the tutor dock."""
    progress = f"saved: {summary.completed_lessons}/{summary.total_lessons} lessons"
    debrief = (
        f"latest debrief: {summary.debrief_session_dir}"
        if summary.debrief_available and summary.debrief_session_dir
        else "no debrief saved yet"
    )
    if summary.profile_available:
        genre = summary.profile_genre or "unknown"
        tempo = summary.profile_tempo_bin or "unknown bpm"
        profile = f"profile: {genre}, {tempo}"
    elif summary.profile_consent:
        profile = "profile still empty"
    else:
        profile = "profile consent off"
    practice = _practice_surface_phrase(summary)
    if practice:
        base = f"{progress}. {debrief}. {profile}. {practice}"
    else:
        base = f"{progress}. {debrief}. {profile}"
    recommended = _recommended_lesson_phrase(summary)
    if recommended:
        return f"{base}. {recommended}."
    return f"{base}."


def graduation_citations(
    summary: GraduationSummary,
    *,
    registry_available: bool,
) -> tuple[str, ...]:
    """Citation atoms for registry-backed graduation facts."""
    if not registry_available:
        return ()
    citations = ["[screen:learn-progress]"]
    if summary.debrief_available:
        citations.append("[screen:learn-debrief]")
    if summary.profile_available:
        citations.append("[screen:learn-profile]")
    return tuple(citations)


def _completed_beginner_lessons(progress: LearnProgress) -> int:
    total = 0
    for lesson_id, row in progress.lessons.items():
        if not lesson_id.startswith(("L1.", "L2.", "L3.")):
            continue
        if isinstance(row, dict) and row.get("completed") is True:
            total += 1
    return total


def _total_beginner_lessons() -> int:
    return sum(
        1
        for lesson_id in CURRICULUM
        if lesson_id.startswith(("L1.", "L2.", "L3."))
    )


def _practice_source_summary(progress: LearnProgress) -> tuple[int, int, str | None]:
    hardware = 0
    screen = 0
    last_source: str | None = None
    for lesson_id, row in progress.lessons.items():
        if not lesson_id.startswith(("L1.", "L2.", "L3.")):
            continue
        if not isinstance(row, dict):
            continue
        sources = row.get("practice_sources")
        if isinstance(sources, dict):
            hardware += _int_count(sources.get("hardware"))
            screen += _int_count(sources.get("screen"))
        raw_last = row.get("last_practice_source")
        if raw_last in {"hardware", "screen"}:
            last_source = str(raw_last)
    return hardware, screen, last_source


def _int_count(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _practice_surface_phrase(summary: GraduationSummary) -> str | None:
    hardware = max(0, int(summary.hardware_practice_actions))
    screen = max(0, int(summary.screen_practice_actions))
    if hardware <= 0 and screen <= 0:
        return None
    if hardware > screen:
        return "practice: mostly hardware deck"
    if screen > hardware:
        return "practice: mostly screen deck"
    return "practice: hardware + screen"


def _load_profile_consent(loader: Callable[[], bool] | None) -> bool:
    try:
        if loader is None:
            from vibemix.profile import load_consent

            loader = load_consent
        return bool(loader())
    except Exception:
        return False


def _load_profile(loader: Callable[[], dict[str, Any] | None] | None) -> dict[str, Any] | None:
    try:
        if loader is None:
            from vibemix.profile import load_profile

            loader = load_profile
        profile = loader()
    except Exception:
        return None
    return profile if isinstance(profile, dict) else None


def _latest_debrief(
    recordings_root_loader: Callable[[], Path] | None,
) -> tuple[str | None, dict[str, Any] | None]:
    try:
        if recordings_root_loader is None:
            from vibemix.debrief import resolve_recordings_root

            recordings_root_loader = resolve_recordings_root
        recordings_root = Path(recordings_root_loader())
    except Exception:
        return None, None

    try:
        from vibemix.debrief import read_debrief
        from vibemix.runtime.recordings_index import RecordingsIndex

        for summary in RecordingsIndex(recordings_root).list():
            session_dir = summary.session_dir
            debrief = read_debrief(recordings_root / session_dir)
            if debrief is not None:
                return session_dir, debrief
    except Exception:
        return None, None
    return None, None


def _profile_str(profile: dict[str, Any] | None, key: str) -> str | None:
    if not profile:
        return None
    value = profile.get(key)
    return value if isinstance(value, str) and value else None


def _profile_tags(profile: dict[str, Any] | None) -> tuple[str, ...]:
    if not profile:
        return ()
    tags = profile.get("mix_style_tags", ())
    if not isinstance(tags, list):
        return ()
    return tuple(str(tag) for tag in tags if isinstance(tag, str))


_DEBRIEF_LESSON_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("L2.01", "beatmatching drift", ("beatmatch", "off-bpm", "off bpm", "drift")),
    ("L2.02", "sync workflow", ("sync",)),
    ("L2.04", "EQ handoff", ("eq", "equalizer", "mid", "high", "low")),
    ("L2.05", "bassline handoff", ("bassline", "two bass", "stacking bass", "kick handoff")),
    ("L2.06", "filter fade", ("filter", "high-pass", "low-pass")),
    ("L2.07", "echo-out recovery", ("echo", "echo-out", "echo out")),
    ("L2.08", "drop swap timing", ("drop swap", "drop timing", "at the drop")),
    ("L2.09", "loop transition", ("loop", "beatjump")),
    ("L2.10", "hot-cue placement", ("hot cue", "hot-cue", "memory cue", "cue point")),
    ("L2.11", "harmonic mixing", ("camelot", "key clash", "harmonic", "off-key", "off key")),
    ("L2.12", "phrase matching", ("phrase", "off-phrase", "off phrase", "bar count")),
    ("L2.13", "train-wreck diagnosis", ("train wreck", "trainwreck")),
    ("L3.03", "energy reading", ("energy curve", "reading the room", "next-track", "next track")),
    ("L3.05", "recovery drill", ("recovery", "bail out", "bailout")),
)


def _recommend_lesson_from_debrief(
    debrief: dict[str, Any] | None,
) -> tuple[str | None, str | None, str | None]:
    """Map the latest cited debrief drill to one authored lesson.

    Debrief drills are model-authored, so this bridge is intentionally narrow:
    it only trusts fields that still carry a locked evidence citation and only
    maps concrete technique words to existing authored lessons.
    """
    if not isinstance(debrief, dict):
        return None, None, None
    drills = debrief.get("drills")
    if not isinstance(drills, list):
        return None, None, None
    for raw in drills:
        if not isinstance(raw, dict):
            continue
        text = _cited_drill_text(raw)
        if not text:
            continue
        lowered = text.lower()
        for lesson_id, reason, tokens in _DEBRIEF_LESSON_RULES:
            if any(token in lowered for token in tokens):
                meta = CURRICULUM.get(lesson_id)
                if meta is None:
                    continue
                return lesson_id, meta.title, reason
    return None, None, None


def _cited_drill_text(drill: dict[str, Any]) -> str:
    fields = (
        drill.get("action_recommended"),
        drill.get("behavior"),
        drill.get("impact"),
        drill.get("citation"),
    )
    cited_fields = [
        str(value)
        for value in fields
        if isinstance(value, str) and EVIDENCE_CITATION_RE.search(value)
    ]
    return " ".join(cited_fields)


def _recommended_lesson_phrase(summary: GraduationSummary) -> str | None:
    lesson_id = summary.debrief_recommended_lesson_id
    title = summary.debrief_recommended_lesson_title
    if not lesson_id or not title:
        return None
    return f"next lesson from debrief: {lesson_id} {title}"


__all__ = [
    "GraduationSummary",
    "build_graduation_summary",
    "build_graduation_tutor_line",
    "graduation_citations",
]
