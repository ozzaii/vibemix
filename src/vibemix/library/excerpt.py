# SPDX-License-Identifier: Apache-2.0
"""excerpt — cue-anchored ≤80s mixable-window mapping (Phase 89 Plan 03).

The single consumer that turns a track's structural cues into mixable audio
windows for the cue-anchored embed path. It is deliberately PURE mapping +
geometry: no DSP, no ffmpeg, no audio decode, no genai. Those live downstream
(``ingest.py`` slices + embeds the windows this module computes).

Two functions:

    anchors_for_track(track) -> list[CueAnchor]
        DJ-FIRST: a track carrying ≥1 *structural* DJ cue (a ``cue`` or ``loop``
        position mark — hot OR memory) yields ``source="dj"`` :class:`CueAnchor`s,
        one per usable cue, sorted by ``start_s``, capped at ``max_cues``. Each
        anchor's window ``end_s`` is clamped to ``min(start + 80s, next_cue,
        duration)``. Labels are BEST-EFFORT and NEVER fabricated: hot cue number
        0 → ``"intro"``, every other cue → ``"drop"``. Positions are
        authoritative; a ``load`` / ``fadein`` / ``fadeout`` mark is NOT a
        structural anchor (it is dropped — T-89-08, "trust the audio").

        AUTO FALLBACK: a track with NO usable DJ cue delegates to
        :func:`vibemix.library.cue_detect.detect_cues` (``source="auto"``,
        lazy-imported). When that engine also finds no structure it returns
        ``[]`` HONESTLY — the ingest caller then whole-track falls back, so a
        track is never left anchor-less AND never gets a faked anchor (T-89-09).

    cut_windows(anchors, duration_s) -> list[(start_s, end_s)]
        Geometry: clamp each anchor span to ``[0, duration_s]``, keep only spans
        1.0..80s; degenerate/zero spans dropped.

Import posture: stdlib + ``cue_types`` (frozen dataclass) + ``rekordbox`` types
only at module top. ``cue_detect`` (which lazy-imports its DSP) is imported
*inside* the fallback branch — so importing :mod:`excerpt` pulls NO heavy dep
(no torch, no ffmpeg, no numpy needed here).
"""

from __future__ import annotations

from pathlib import Path

from vibemix.library.cue_types import CueAnchor, CueLabel
from vibemix.library.rekordbox import CuePoint, TrackEntry

__all__ = [
    "anchors_for_track",
    "cut_windows",
    "CUE_WINDOW_SECONDS",
    "MAX_CUES_PER_TRACK",
]

# Mirror embed.py's cue-anchored constants locally so excerpt.py stays
# import-light (embed.py drags in the Gemini/genai surface; we keep excerpt
# genai-free and torch-free). Keep these in lock-step with embed.CUE_WINDOW_*.
CUE_WINDOW_SECONDS: float = 80.0
MAX_CUES_PER_TRACK: int = 4

# The cue *types* that mark a mixable structural point. A load / fadein /
# fadeout mark records playback geometry, NOT song structure — those are
# dropped so we never force a structural label onto them (T-89-08).
_STRUCTURAL_CUE_TYPES = frozenset({"cue", "loop"})

# DJ-placed cues are human judgement — high (but not absolute) trust.
_DJ_CONFIDENCE: float = 0.9


def anchors_for_track(
    track: TrackEntry,
    *,
    max_cues: int = MAX_CUES_PER_TRACK,
    window_s: float = CUE_WINDOW_SECONDS,
) -> list[CueAnchor]:
    """Map a track's structural DJ cues to anchors; fall back to detect_cues.

    Args:
        track: a parsed :class:`TrackEntry` (its ``cues`` + ``duration_s`` +
            ``filepath`` drive the mapping).
        max_cues: cap on how many DJ anchors to emit (also the detect_cues cap).
        window_s: the mixable-window length cap (≤80s by contract).

    Returns:
        A list of :class:`CueAnchor`. ``source="dj"`` when the track carries
        usable structural cues; otherwise ``source="auto"`` from
        ``detect_cues`` — or ``[]`` honestly when neither path finds structure.
    """
    duration_s = float(track.duration_s) if track.duration_s else 0.0

    # DJ-FIRST: keep only structural cue/loop marks (load/fade dropped),
    # sorted by position, capped at max_cues.
    structural = [
        c
        for c in track.cues
        if c.type in _STRUCTURAL_CUE_TYPES
    ]
    structural.sort(key=lambda c: float(c.start_s))
    structural = structural[: max(0, int(max_cues))]

    if structural:
        anchors: list[CueAnchor] = []
        for i, cue in enumerate(structural):
            start = max(0.0, float(cue.start_s))
            # Window end = min(start + window, next cue start, duration).
            end = start + float(window_s)
            if i + 1 < len(structural):
                end = min(end, float(structural[i + 1].start_s))
            if duration_s > 0.0:
                end = min(end, duration_s)
            # A cue that does not leave a positive window (e.g. coincident with
            # the next cue, or past EOT) is dropped — never a zero/negative span.
            if end <= start:
                continue
            anchors.append(
                CueAnchor(
                    label=_label_for_cue(cue),
                    start_s=start,
                    end_s=end,
                    confidence=_DJ_CONFIDENCE,
                    source="dj",
                )
            )
        if anchors:
            return anchors

    # AUTO FALLBACK: no usable DJ cue → the offline structure engine. Lazy
    # import keeps excerpt.py's top level heavy-dep-free (cue_detect drags in
    # its DSP only when actually called).
    from vibemix.library.cue_detect import detect_cues

    return list(detect_cues(Path(track.filepath), max_cues=max_cues))


def _label_for_cue(cue: CuePoint) -> CueLabel:
    """Best-effort label for a DJ cue (positions authoritative, labels hedged).

    Hot cue slot 0 is conventionally the load / mix-in point → ``"intro"``.
    Every other cue (later hot slots, memory cues, loops) is treated as a
    mixable landing → ``"drop"``. We deliberately do NOT fabricate
    ``"build"`` / ``"breakdown"`` semantics from a bare position mark — the
    source XML carries no such signal (T-89-08).
    """
    if cue.number == 0:
        return "intro"
    return "drop"


def cut_windows(
    anchors: list[CueAnchor], duration_s: float
) -> list[tuple[float, float]]:
    """Turn anchors into clamped ``(start_s, end_s)`` audio windows.

    Each window is clamped to ``[0, duration_s]`` and kept only when its span is
    in ``[1.0, 80s]``; degenerate / zero / inverted spans are dropped. Returned
    in input order (anchors are already sorted by the producer).
    """
    dur = float(duration_s) if duration_s and duration_s > 0.0 else 0.0
    out: list[tuple[float, float]] = []
    for a in anchors:
        start = max(0.0, float(a.start_s))
        end = float(a.end_s)
        if dur > 0.0:
            end = min(end, dur)
        span = end - start
        if span < 1.0:
            continue
        if span > CUE_WINDOW_SECONDS:
            end = start + CUE_WINDOW_SECONDS
        out.append((start, end))
    return out
