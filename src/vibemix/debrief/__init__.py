# SPDX-License-Identifier: Apache-2.0
"""Phase 29 — post-session debrief generation package.

Pure-Python backend that converts a recorded session_dir into:

- a list of :class:`ChapterRegion` from events.jsonl
- a voiced TL;DR MP3 (60-90s, Achird voice via Gemini TTS)
- exactly 3 SBI/STAR-AR :class:`Drill` objects with cited evidence
- cited-critique-stripped text everywhere (DEBRIEF-07 hard gate)

Plans:

- 29-01 — this package (data + LLM transforms)
- 29-02 — sidecar wrapper (``python -m vibemix --debrief <dir>``) +
  ws_server on 127.0.0.1:8766
- 29-04 — Tauri Rust shell (window + sidecar lifecycle)
- 29-05 — vanilla-TS UI
- 29-06 — Settings → Recordings entry-point button
- 29-07 — defense-in-depth stripper integration
- 29-08 — cross-platform smoke + verdict
"""

from __future__ import annotations

from vibemix.debrief.chapters import ChapterRegion, derive_chapters
from vibemix.debrief.persistence import read_debrief, write_debrief
from vibemix.debrief.session_loader import (
    EventsMissing,
    SessionTooShort,
    load_session,
)
from vibemix.debrief.stripper import (
    UncitedSentencesFound,
    assert_all_cited,
    strip_uncited_sentences,
)

__all__ = [
    "ChapterRegion",
    "EventsMissing",
    "SessionTooShort",
    "UncitedSentencesFound",
    "assert_all_cited",
    "derive_chapters",
    "load_session",
    "read_debrief",
    "strip_uncited_sentences",
    "write_debrief",
]
