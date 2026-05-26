# SPDX-License-Identifier: Apache-2.0
"""quote_moment — point at a specific moment in a library track, grounded.

This is the Viber/Codex agent's "quote-a-moment" surface: the agent says
*"this is the breakdown I'm talking about"* and backs it with a **resolvable,
grounded** reference — a track + a [start, end] window + a human caption.
It mirrors Bravoh's quoting engine, but every quote is anchored to a real
library track under Cardinal Invariant #2 (citation grounding) and Invariant
#3 ("trust the audio" — bounds come from the track's real duration, never the
model's imagination).

Data flow::

    agent picks track_id + start_s/end_s (or a CueAnchor from cue_detect)
        -> resolve_quote / quote_from_cue
            gate #1: if a per-run ``seen`` set is supplied, track_id MUST be
                     in it (returned by a prior search this run) — else the
                     quote is ungrounded and rejected.
            gate #2: library.lookup_by_id(track_id) MUST resolve — else the
                     quote points at a track the library does not contain.
            bounds: 0 <= start_s < end_s; end_s clamped to the track duration
                    (with a small slack) when it overruns, and the clamp is
                    noted honestly rather than silently widening the window.
        -> Quote.to_dict() with ``available: True`` + a human caption
           (e.g. "[breakdown @ 3:12-3:48] Artist - Title").

DEFAULT POSTURE = metadata only. No audio is decoded and no clip is cut. A
caller that genuinely wants a rendered clip injects a ``clip_writer`` callable
into ``resolve_quote``; only then (and only if the track has a filepath) is a
``clip_path`` produced. No audio/ffmpeg library is ever imported at module
top — the seam stays inert until a caller opts in.

Like the rest of the grounded tool core (``toolset.py``), every function here
RETURNS a dict (an ``{"available": False, "error": ...}`` shape on any failure)
and NEVER raises — a bad arg degrades to a recoverable message instead of
wedging the agent's loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from vibemix.library.cue_types import CueAnchor

__all__ = ["Quote", "quote_from_cue", "resolve_quote"]

# Slack (seconds) by which an end_s may overrun the track's reported duration
# before we clamp. Rekordbox TotalTime is integer-seconds and DSP cue ends can
# round just past the tail; a sub-second overrun is benign, so we absorb it
# rather than clamp-and-note for noise.
_DURATION_SLACK_S: float = 1.0


@dataclass(frozen=True, slots=True)
class Quote:
    """A grounded, resolvable pointer to a moment inside one library track.

    A Quote is metadata: the track it lives in, the ``[start_s, end_s]`` window
    it spans, an optional structural ``label`` (intro/build/breakdown/drop/
    outro), and a human ``caption`` the agent can speak verbatim. ``available``
    is ``True`` only for a fully grounded + bounds-valid quote.
    """

    track_id: str
    title: str
    artist: str
    start_s: float
    end_s: float
    label: str | None
    caption: str
    available: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mmss(seconds: float) -> str:
    """Format a non-negative second count as ``M:SS`` (e.g. 192.0 -> "3:12").

    Clamps negatives to 0 (a caption never shows a nonsensical negative time)
    and floors fractional seconds. Minutes are unbounded (a 70-minute set
    reads "70:00", not "1:10:00") — quotes point inside single tracks, so the
    minute field never needs an hour rollover.
    """
    if seconds < 0 or seconds != seconds:  # negative or NaN -> 0
        seconds = 0.0
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _synthesize_caption(
    *, label: str | None, artist: str, title: str, start_s: float, end_s: float
) -> str:
    """Build a speakable caption: ``[label @ M:SS-M:SS] Artist - Title``.

    The label segment is dropped when no label is known (``[@ 3:12-3:48]``),
    and the trailing attribution degrades gracefully when artist/title are
    blank so the caption never reads "  - " on a bare track.
    """
    window = f"{_mmss(start_s)}-{_mmss(end_s)}"
    head = f"[{label} @ {window}]" if label else f"[@ {window}]"
    artist = (artist or "").strip()
    title = (title or "").strip()
    if artist and title:
        attribution = f"{artist} - {title}"
    else:
        attribution = artist or title  # whichever is present, possibly ""
    return f"{head} {attribution}".rstrip()


def resolve_quote(
    library: Any,
    track_id: str,
    start_s: float,
    end_s: float,
    *,
    label: str | None = None,
    caption: str | None = None,
    seen: set[str] | None = None,
    clip_writer: Callable[[str, float, float], str] | None = None,
) -> dict[str, Any]:
    """Resolve a grounded quote pointing at ``[start_s, end_s]`` in a track.

    Grounding (Invariant #2):

    * **Gate #1** — if ``seen`` is supplied and ``track_id`` is not in it, the
      quote is ungrounded (the agent never surfaced this id this run) and is
      rejected. ``seen=None`` means "no per-run grounding context" (e.g. a
      direct CLI call) and skips this gate.
    * **Gate #2** — ``library.lookup_by_id(track_id)`` must resolve to a real
      entry, else the quote points at an unknown track.

    Bounds (Invariant #3 — trust the track, not the model): ``start_s`` must be
    ``>= 0`` and strictly less than ``end_s``. When the track reports a
    ``duration_s`` and ``end_s`` overruns it by more than ``_DURATION_SLACK_S``,
    ``end_s`` is clamped to the duration and the clamp is noted in the result
    (``"clamped": True`` + ``"note"``) rather than silently widening the window.

    Clip seam (inert by default): if ``clip_writer`` is provided AND the
    resolved entry has a ``filepath``, the writer is called as
    ``clip_writer(filepath, start_s, end_s)`` and its return value is attached
    as ``"clip_path"``. No audio library is imported here; rendering is entirely
    the injected writer's concern. A writer failure degrades to no clip_path
    (the quote still resolves) rather than raising.

    Always RETURNS a dict; never raises.
    """
    # Gate #1: per-run grounding. An id the agent never surfaced this run is
    # a hallucination — reject before touching the library.
    if seen is not None and track_id not in seen:
        return {
            "available": False,
            "error": (
                "track_id was not returned by a prior search this run "
                "(ungrounded)"
            ),
        }

    # Gate #2: the track must exist in the live library.
    try:
        entry = library.lookup_by_id(track_id)
    except Exception as e:  # noqa: BLE001 — resolver must not raise
        return {
            "available": False,
            "error": f"library lookup failed: {type(e).__name__}",
        }
    if entry is None:
        return {"available": False, "error": "unknown track_id"}

    # Bounds validation — coerce defensively (the model may hand us str/None).
    try:
        start_s = float(start_s)
        end_s = float(end_s)
    except (TypeError, ValueError):
        return {"available": False, "error": "start_s/end_s must be numbers"}
    if start_s != start_s or end_s != end_s:  # NaN guard
        return {"available": False, "error": "start_s/end_s must be finite"}
    if start_s < 0:
        return {"available": False, "error": "start_s must be >= 0"}
    if not (start_s < end_s):
        return {"available": False, "error": "start_s must be < end_s"}

    note: str | None = None
    clamped = False
    duration_s = float(getattr(entry, "duration_s", 0.0) or 0.0)
    if duration_s > 0 and end_s > duration_s + _DURATION_SLACK_S:
        # end overruns the real track tail by more than the slack — clamp to
        # the duration and note it (never silently widen past the audio).
        if duration_s <= start_s:
            return {
                "available": False,
                "error": (
                    f"start_s ({_mmss(start_s)}) is at or past the track "
                    f"duration ({_mmss(duration_s)})"
                ),
            }
        note = (
            f"end_s clamped from {_mmss(end_s)} to track duration "
            f"{_mmss(duration_s)}"
        )
        end_s = duration_s
        clamped = True

    title = str(getattr(entry, "title", "") or "")
    artist = str(getattr(entry, "artist", "") or "")

    text = caption if (isinstance(caption, str) and caption.strip()) else None
    if text is None:
        text = _synthesize_caption(
            label=label, artist=artist, title=title, start_s=start_s, end_s=end_s
        )

    quote = Quote(
        track_id=track_id,
        title=title,
        artist=artist,
        start_s=start_s,
        end_s=end_s,
        label=label,
        caption=text,
        available=True,
    )
    out = quote.to_dict()
    if clamped:
        out["clamped"] = True
        out["note"] = note

    # Clip seam — inert unless a writer is injected AND the track has a file.
    if clip_writer is not None:
        filepath = getattr(entry, "filepath", None)
        if filepath:
            try:
                clip_path = clip_writer(str(filepath), start_s, end_s)
            except Exception as e:  # noqa: BLE001 — writer failure is non-fatal
                out["clip_error"] = f"clip_writer failed: {type(e).__name__}"
            else:
                if clip_path:
                    out["clip_path"] = str(clip_path)

    return out


def quote_from_cue(
    library: Any,
    track_id: str,
    cue: CueAnchor,
    *,
    seen: set[str] | None = None,
    clip_writer: Callable[[str, float, float], str] | None = None,
) -> dict[str, Any]:
    """Build a grounded quote from a :class:`CueAnchor`.

    Convenience over :func:`resolve_quote`: lifts ``label`` / ``start_s`` /
    ``end_s`` straight off the cue (the structural moment the auto-cue or DJ
    library already located) and runs the same grounding + bounds gates. The
    ``CueAnchor`` import is local so this module carries no hard dependency on
    the cue-detect subtree at import time.

    Always RETURNS a dict; never raises.
    """
    return resolve_quote(
        library,
        track_id,
        getattr(cue, "start_s", 0.0),
        getattr(cue, "end_s", 0.0),
        label=getattr(cue, "label", None),
        seen=seen,
        clip_writer=clip_writer,
    )
