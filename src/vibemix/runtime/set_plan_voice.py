# SPDX-License-Identifier: Apache-2.0
"""Grounded voice receipt for saved-set progress.

This module does not speak. It converts ``MusicState.set_progress`` into a
bounded prompt receipt that Sven may use if the live moment supports it. The
receipt is intentionally conservative: it can mention the matched saved-pool
slot and the next planned track, but it cannot claim energy-curve progress
because the current saved playlist artifact does not persist that data.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibemix.state.evidence_registry import EvidenceRegistry

_CITATION_BODY_RE = re.compile(r"^[^\s,\]]+$")
_VOICE_EVENT_TYPES = frozenset({"TRACK_CHANGE", "TRANSITION_OPPORTUNITY"})
_TEXT_ESCAPE = str.maketrans({"[": "(", "]": ")", "\n": " ", "\r": " ", "|": "/"})


def build_set_progress_voice_line(
    set_progress: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
) -> str | None:
    """Return a citable receipt for saved-pool progress, or abstain.

    ``set_progress`` is derived state written by ``state_refresh_loop``. We cite
    the next planned track and the derived saved-pool match, and we tell the LLM
    to keep the plan optional. Off-script is already represented by
    ``set_progress is None``.
    """

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if set_progress is None or evidence_registry is None:
        return None

    next_track_id = _clean_citation_body(set_progress.get("next_track_id"))
    current_track_id = _clean_citation_body(set_progress.get("current_track_id"))
    if next_track_id is None or current_track_id is None:
        return None

    current_index = _non_negative_int(set_progress.get("current_index"))
    total = _positive_int(set_progress.get("total"))
    if current_index is None or total is None or current_index + 1 >= total:
        return None

    mix_key = f"set_progress={current_track_id}->{next_track_id}"
    evidence_registry.write("track", next_track_id, 0.0)
    evidence_registry.write("mix", mix_key, 0.0)

    pool_name = _clean_text(set_progress.get("pool_name"), fallback="saved pool", cap=58)
    next_title = _clean_text(set_progress.get("next_title"), fallback=next_track_id, cap=72)
    next_artist = _clean_text(set_progress.get("next_artist"), fallback="", cap=48)
    artist_clause = f" by {next_artist}" if next_artist else ""
    slot = current_index + 1

    return (
        "Saved-set receipt: the current deck matches slot "
        f"{slot}/{total} in {pool_name}; the next track in that saved pool is "
        f"{next_title}{artist_clause}. If you mention it, keep it optional and "
        f"copy these citations exactly: [track:{next_track_id}] [mix:{mix_key}]. "
        "Do not say the track is loaded or playing. Do not say ahead/behind the "
        "energy curve; the saved-pool artifact does not carry a citable curve yet. "
        "If the DJ sounds off-script or the moment is not useful, stay silent."
    )


def _clean_citation_body(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or _CITATION_BODY_RE.fullmatch(value) is None:
        return None
    return value


def _clean_text(value: object, *, fallback: str, cap: int) -> str:
    if not isinstance(value, str):
        return fallback
    text = " ".join(value.translate(_TEXT_ESCAPE).split())
    if not text:
        return fallback
    if len(text) <= cap:
        return text
    return text[: cap - 1].rstrip() + "..."


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


__all__ = ["build_set_progress_voice_line"]
