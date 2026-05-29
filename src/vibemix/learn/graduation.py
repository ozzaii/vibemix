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
    debrief_session_dir = _latest_debrief_session_dir(recordings_root_loader)
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
        return f"{progress}. {debrief}. {profile}. {practice}."
    return f"{progress}. {debrief}. {profile}."


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


def _latest_debrief_session_dir(
    recordings_root_loader: Callable[[], Path] | None,
) -> str | None:
    try:
        if recordings_root_loader is None:
            from vibemix.debrief import resolve_recordings_root

            recordings_root_loader = resolve_recordings_root
        recordings_root = Path(recordings_root_loader())
    except Exception:
        return None

    try:
        from vibemix.debrief import read_debrief
        from vibemix.runtime.recordings_index import RecordingsIndex

        for summary in RecordingsIndex(recordings_root).list():
            session_dir = summary.session_dir
            if read_debrief(recordings_root / session_dir) is not None:
                return session_dir
    except Exception:
        return None
    return None


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


__all__ = [
    "GraduationSummary",
    "build_graduation_summary",
    "build_graduation_tutor_line",
    "graduation_citations",
]
