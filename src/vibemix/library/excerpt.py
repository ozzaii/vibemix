# SPDX-License-Identifier: Apache-2.0
"""excerpt — cue-anchored ≤80s mixable-window mapping (Phase 89 Plan 03).

The single consumer that turns a track's structural cues into mixable audio
windows for the cue-anchored embed path. It is deliberately PURE mapping +
geometry: no DSP, no ffmpeg, no audio decode, no genai. Those live downstream
(``ingest.py`` slices + embeds the windows this module computes).

Two functions:

    anchors_for_track(track) -> list[CueAnchor]
        DJ-FIRST: a track carrying ≥1 *structural* cue (a ``cue`` or ``loop``
        position mark — hot OR memory, or materialized ANLZ/auto structure)
        yields :class:`CueAnchor`s, one per usable cue, sorted by ``start_s``,
        capped at ``max_cues``. Each anchor's window ``end_s`` is clamped to
        ``min(start + 80s, next_cue, duration)``. Labels are BEST-EFFORT and
        never fabricated beyond the shared cue vocabulary. Positions are
        authoritative; a ``load`` / ``fadein`` / ``fadeout`` mark is NOT a
        structural anchor (it is dropped — T-89-08, "trust the audio").

        ANLZ SECOND: if the caller supplies an ANLZ index, a unique Rekordbox
        ANLZ match yields ``source="anlz"`` anchors from PSSI/PQTZ structure.

        AUTO FALLBACK: a track with NO usable DJ cue and NO usable ANLZ match
        delegates to :func:`vibemix.library.cue_engine.detect_cues_auto`
        (``source="auto"``, lazy-imported). That tries CUE-DETR ONNX first and
        falls back to the dep-free heuristic. When neither engine finds
        structure it returns ``[]`` HONESTLY — the ingest caller then
        whole-track falls back, so a track is never left anchor-less AND never
        gets a faked anchor (T-89-09).

    cut_windows(anchors, duration_s) -> list[(start_s, end_s)]
        Geometry: clamp each anchor span to ``[0, duration_s]``, keep only spans
        1.0..80s; degenerate/zero spans dropped.

Import posture: stdlib + ``cue_types`` (frozen dataclass) + ``rekordbox`` types
only at module top. ``cue_engine`` is imported *inside* the fallback branch, so
importing :mod:`excerpt` pulls NO heavy dep (no torch, no ffmpeg, no numpy needed
here).
"""

from __future__ import annotations

from pathlib import Path

from vibemix.library.cue_types import CueAnchor, CueLabel
from vibemix.library.rekordbox import CuePoint, TrackEntry

__all__ = [
    "CUE_WINDOW_SECONDS",
    "MAX_CUES_PER_TRACK",
    "anchors_for_track",
    "cut_windows",
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
    anlz_index: object | None = None,
    max_cues: int = MAX_CUES_PER_TRACK,
    window_s: float = CUE_WINDOW_SECONDS,
) -> list[CueAnchor]:
    """Map a track's structural DJ cues to anchors; fall back to detect_cues_auto.

    Args:
        track: a parsed :class:`TrackEntry` (its ``cues`` + ``duration_s`` +
            ``filepath`` drive the mapping).
        anlz_index: optional :class:`vibemix.library.anlz_ingest.AnlzIndex`.
            When supplied, ANLZ structure is tried after DJ cues and before the
            auto-cue engine.
        max_cues: cap on how many DJ anchors to emit (also the auto-cue cap).
        window_s: the mixable-window length cap (≤80s by contract).

    Returns:
        A list of :class:`CueAnchor`. ``source="dj"`` when the track carries
        usable structural cues; otherwise ``source="anlz"`` from Rekordbox
        offline structure when available; otherwise ``source="auto"`` from
        ``detect_cues_auto`` — or ``[]`` honestly when no path finds structure.
    """
    duration_s = float(track.duration_s) if track.duration_s else 0.0

    # DJ-FIRST: keep only structural cue/loop marks (load/fade dropped),
    # sorted by position, capped at max_cues.
    structural = [c for c in track.cues if c.type in _STRUCTURAL_CUE_TYPES]
    structural.sort(key=lambda c: float(c.start_s))
    structural = structural[: max(0, int(max_cues))]

    if structural:
        anchors: list[CueAnchor] = []
        for i, cue in enumerate(structural):
            start = max(0.0, float(cue.start_s))
            # Window end = min(start + window, next cue start, duration).
            end = start + float(window_s)
            if cue.end_s is not None and float(cue.end_s) > start:
                end = min(end, float(cue.end_s))
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
                    confidence=_confidence_for_cue(cue),
                    source=_source_for_cue(cue),
                )
            )
        if anchors:
            return anchors

    # ANLZ SECOND: no usable DJ cue -> caller-supplied Rekordbox offline
    # structure. Lazy import keeps excerpt.py top-level heavy-dep-free.
    if anlz_index is not None:
        try:
            from vibemix.library.anlz_ingest import anchors_from_anlz, match_track_to_anlz

            meta = match_track_to_anlz(track, anlz_index)
            if meta is not None:
                anchors = anchors_from_anlz(
                    track,
                    meta,
                    max_cues=max_cues,
                    window_s=window_s,
                )
                if anchors:
                    return anchors
        except Exception:
            # A stale/corrupt caller-supplied index must not block the existing
            # auto fallback. Parser/audit code reports quality separately.
            pass

    # AUTO FALLBACK: no usable DJ/ANLZ cue -> the offline structure engine. Lazy
    # import keeps excerpt.py's top level heavy-dep-free.
    from vibemix.library.cue_engine import detect_cues_auto

    return list(detect_cues_auto(Path(track.filepath), max_cues=max_cues))


def _label_for_cue(cue: CuePoint) -> CueLabel:
    """Best-effort label for a DJ cue (positions authoritative, labels hedged).

    Hot cue slot 0 is conventionally the load / mix-in point → ``"intro"``.
    Every other cue (later hot slots, memory cues, loops) is treated as a
    mixable landing → ``"drop"``. We deliberately do NOT fabricate
    ``"build"`` / ``"breakdown"`` semantics from a bare position mark — the
    source XML carries no such signal (T-89-08).
    """
    name = (cue.name or "").strip().lower()
    if "intro" in name or "mix in" in name or "mix-in" in name or "start" in name:
        return "intro"
    if "build" in name or "rise" in name:
        return "build"
    if "break" in name or "breakdown" in name:
        return "breakdown"
    if "outro" in name or "mix out" in name or "mix-out" in name or "end" in name:
        return "outro"
    if "drop" in name or "chorus" in name or "hook" in name:
        return "drop"
    if cue.number == 0:
        return "intro"
    return "drop"


def _source_for_cue(cue: CuePoint) -> str:
    source = (getattr(cue, "source", "") or "dj").strip().lower()
    return source or "dj"


def _confidence_for_cue(cue: CuePoint) -> float:
    raw = getattr(cue, "confidence", None)
    if raw is not None:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = _DJ_CONFIDENCE
        else:
            if 0.0 <= value <= 1.0:
                return value
    return _DJ_CONFIDENCE if _source_for_cue(cue) == "dj" else 0.65


def cut_windows(anchors: list[CueAnchor], duration_s: float) -> list[tuple[float, float]]:
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
