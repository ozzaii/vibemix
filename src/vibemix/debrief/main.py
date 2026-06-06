# SPDX-License-Identifier: Apache-2.0
"""Plan 29-02 — debrief sidecar orchestrator.

``python -m vibemix --debrief <session_dir>`` dispatches here via
:func:`vibemix.__main__._run_debrief_sidecar`. Lifecycle:

1. Canonicalize + path-traversal validate ``session_dir``.
2. Cache-hit fast path — if ``session_debrief.json`` + ``debrief_tldr.mp3``
   exist with matching ``tldr_sha256``, skip Gemini entirely.
3. First-time generation — load_session → derive_chapters →
   generate_drills → generate_tldr_mp3 → write_debrief.
4. Start the WS server on 127.0.0.1:8766 and ``serve_forever``.

All errors from Plan 29-01's exception types are caught and surfaced via
``ws_server.emit_error(reason, message)`` BEFORE the process exits.
Renderer (Plan 29-05) listens for ``ipc.debrief.error`` and maps reason
codes to user copy.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from vibemix.debrief.chapters import ChapterRegion, derive_chapters
from vibemix.debrief.drills import (
    Drill,
    Drills,
    DrillsGenerationError,
    generate_drills,
)
from vibemix.debrief.persistence import (
    TLDR_MP3_FILENAME,
    read_debrief,
    write_debrief,
)
from vibemix.debrief.session_loader import (
    EventsMissing,
    InvalidSessionDir,
    SessionTooShort,
    load_session,
)
from vibemix.debrief.stripper import strip_uncited_sentences
from vibemix.debrief.tldr import (
    DebriefGenerationError,
    generate_tldr_mp3,
)

__all__ = ["resolve_recordings_root", "run", "validate_session_dir_under_root"]

logger = logging.getLogger("vibemix.debrief")


# ---------------------------------------------------------------------------
# Path validation — defense-in-depth alongside Rust validate_under_root
# ---------------------------------------------------------------------------


def resolve_recordings_root() -> Path:
    """Return the OS-aware recordings root (mirrors recordings.rs)."""
    from vibemix.runtime.config_store import app_data_dir

    return app_data_dir() / "recordings"


def validate_session_dir_under_root(
    session_dir: Path | str,
    recordings_root: Path | None = None,
) -> Path:
    """Canonicalize ``session_dir`` and assert it lives under recordings_root.

    Raises :class:`InvalidSessionDir` on any failure. The Rust shell
    (Plan 29-04) already gates this — we do it again here as
    defense-in-depth so that running the sidecar directly from CLI is
    just as safe.

    The function accepts session_dir either as an absolute path or as a
    bare session-id (``20260515-112139``); in the second case it resolves
    against ``recordings_root``.
    """
    if recordings_root is None:
        recordings_root = resolve_recordings_root()
    recordings_root = recordings_root.resolve()

    candidate = Path(session_dir)
    if not candidate.is_absolute():
        candidate = recordings_root / candidate

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as e:
        raise InvalidSessionDir(session_dir) from e

    if not resolved.is_dir():
        raise InvalidSessionDir(session_dir)

    try:
        resolved.relative_to(recordings_root)
    except ValueError as e:
        raise InvalidSessionDir(session_dir) from e

    return resolved


# ---------------------------------------------------------------------------
# Coercion: ChapterRegion / Drill → IPC payloads
# ---------------------------------------------------------------------------


def _chapter_to_payload(c: ChapterRegion):
    from vibemix.ui_bus import ChapterRegionPayload

    return ChapterRegionPayload(
        id=c.id,
        start=c.start,
        end=c.end,
        label=c.label,
        kind=c.kind,
        citation_event_id=c.citation_event_id,
    )


def _drill_to_payload(d: Drill):
    from vibemix.debrief.learn_referral import learn_referral_for_drill
    from vibemix.ui_bus import DrillPayload, LearnReferralPayload

    referral = learn_referral_for_drill(
        {
            "situation": d.situation,
            "behavior": d.behavior,
            "impact": d.impact,
            "action_recommended": d.action_recommended,
            "citation": d.citation,
        }
    )

    return DrillPayload(
        situation=d.situation,
        behavior=d.behavior,
        impact=d.impact,
        action_recommended=d.action_recommended,
        citation=d.citation,
        learn_referral=(
            LearnReferralPayload(
                lesson_id=referral.lesson_id,
                course_id=referral.course_id,
                course_label=referral.course_label,
                skill_id=referral.skill_id,
                skill_label=referral.skill_label,
                title=referral.title,
                reason=referral.reason,
                cta=referral.cta,
            )
            if referral is not None
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Build cited critique from events + chapter labels
# ---------------------------------------------------------------------------


def _build_cited_critique(events: list[dict], chapters: list[ChapterRegion]) -> str:
    """Lossy condensation of events.jsonl into a citation-rich critique string.

    Picks up the ``ai_text`` event lines (the live cohost's replies — already
    cited per Phase 18 grammar) plus Learn lesson/action events. Result is the
    input the TLDR + drills prompts consume.
    """
    out: list[str] = []
    last_event_tag: str | None = None
    for e in events:
        kind = e.get("kind")
        if kind == "event":
            etype = e.get("type", "EVENT")
            t = e.get("t", 0.0)
            last_event_tag = f"[ev:{etype}@{t:.3f}]"
        elif kind == "ai_text":
            text = e.get("text", "").strip()
            if text and last_event_tag:
                # Ensure the line carries a citation — if Gemini's own
                # output didn't include one, prepend.
                from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE
                if not EVIDENCE_CITATION_RE.search(text):
                    text = f"{text} {last_event_tag}"
                out.append(text)
        elif kind == "learn_action_observed":
            text = _learn_action_critique_line(e)
            if text:
                out.append(text)
        elif kind == "learn_tutor_speak":
            text = _learn_tutor_critique_line(e)
            if text:
                out.append(text)
        elif kind in {
            "learn_beatmatch_practice_graded",
            "learn_cue_placement_practice_graded",
        }:
            text = _learn_grade_critique_line(e)
            if text:
                out.append(text)
        elif kind == "transition_judged":
            text = _transition_judged_critique_line(e)
            if text:
                out.append(text)
    return " ".join(out)


def _session_duration_s(events: list[dict]) -> float:
    ts = [float(e.get("t")) for e in events if isinstance(e.get("t"), (int, float))]
    if not ts:
        return 0.0
    return max(ts) - min(ts)


def _build_debrief_near_miss_payload(
    session_dir: Path,
    *,
    events: list[dict],
    evidence_snapshot: dict[str, dict[str, list[float]]],
    duration_s: float,
):
    input_wav = session_dir / "input.wav"
    if not input_wav.exists() or input_wav.stat().st_size == 0:
        return None
    try:
        from vibemix.debrief.friend_line import build_morning_friend_lines
        from vibemix.debrief.near_miss_detector import detect_near_miss
        from vibemix.ui_bus import DebriefNearMissPayload

        near_miss = detect_near_miss(session_dir)
        lines = build_morning_friend_lines(
            near_miss=near_miss,
            events=events,
            evidence_snapshot=evidence_snapshot,
        )
    except Exception as exc:  # pragma: no cover - defensive debrief add-on
        logger.warning("[debrief] near-miss payload skipped: %s", exc)
        return None

    chosen = lines.near_miss or lines.gap
    has_replay_window = near_miss is not None and lines.near_miss is not None
    receipt_text = chosen.receipt_text if chosen else ""
    if has_replay_window:
        receipt_text = _near_miss_receipt_text(near_miss, receipt_text, events)
    return DebriefNearMissPayload(
        input_wav_relative_path="input.wav",
        t_center=near_miss.t_center_s if has_replay_window else None,
        window=(
            (near_miss.window_start_s, near_miss.window_end_s)
            if has_replay_window
            else None
        ),
        receipt_text=receipt_text,
        friend_line_text=chosen.text if chosen else "",
        duration_s=max(duration_s, 0.0),
        waveform_peaks=_build_debrief_waveform_peaks(input_wav),
    )


def _build_debrief_waveform_peaks(
    input_wav: Path,
    *,
    buckets: int = 192,
) -> tuple[tuple[int, int, int], ...] | None:
    """Return bounded display peaks for the debrief replay rail.

    Failure means "no waveform proof", not "silent recording", so callers keep
    the near-miss payload and let the renderer fall back to its quiet placeholder.
    """

    try:
        from vibemix.audio.waveform_peaks import compute_three_band_peaks
        from vibemix.debrief.near_miss_detector import _read_wav_mono_float32

        decoded = _read_wav_mono_float32(input_wav)
        if decoded is None:
            return None
        samples, sample_rate = decoded
        raw_peaks = compute_three_band_peaks(
            samples,
            sample_rate=sample_rate,
            buckets=max(1, min(512, int(buckets))),
        )
    except Exception as exc:  # pragma: no cover - defensive debrief add-on
        logger.warning("[debrief] waveform peaks skipped: %s", exc)
        return None

    peaks: list[tuple[int, int, int]] = []
    for row in raw_peaks:
        if len(row) < 3:
            continue
        low, mid, high = (max(0, min(255, int(v))) for v in row[:3])
        peaks.append((low, mid, high))
    return tuple(peaks) if peaks else None


def _learn_action_critique_line(event: dict) -> str:
    observed = str(event.get("observed_control_id") or "").strip()
    if not observed:
        return ""
    lesson_id = str(event.get("lesson_id") or "unknown").strip()
    step_id = str(event.get("step_id") or "").strip()
    expected = str(event.get("expected_control_id") or "").strip()
    source = str(event.get("source") or "midi").strip()
    citation_source = "screen" if source == "click" else "midi"
    citation_time = _learn_event_time(event)
    citation = f"[{citation_source}:{observed}@{citation_time:.3f}]"
    matched = event.get("matched")
    if matched is True:
        action = f"matched {observed}"
    elif expected:
        action = f"moved {observed} while the lesson expected {expected}"
    else:
        action = f"moved {observed}"
    step = f" step {step_id}" if step_id else ""
    return f"Learn {lesson_id}{step}: learner {action} via {source} {citation}."


def _learn_tutor_critique_line(event: dict) -> str:
    citations = event.get("citations")
    citation_list = [str(c) for c in citations] if isinstance(citations, list) else []
    if not citation_list:
        return ""
    text = str(event.get("text") or "").strip()
    if not text:
        return ""
    lesson_id = str(event.get("lesson_id") or "unknown").strip()
    tts_marker = str(event.get("tts_marker") or "").strip()
    marker = f" {tts_marker}" if tts_marker else ""
    return f"Learn tutor {lesson_id}{marker}: {text} {' '.join(citation_list)}"


def _learn_grade_critique_line(event: dict) -> str:
    kind = str(event.get("kind") or "")
    if kind == "learn_beatmatch_practice_graded":
        label = "beatmatch practice"
        evidence_key = "BEATMATCH_GRADED"
    elif kind == "learn_cue_placement_practice_graded":
        label = "cue placement practice"
        evidence_key = "CUE_PLACEMENT_GRADED"
    else:
        return ""

    citation_time = _learn_event_time_or_none(event)
    if citation_time is None:
        return ""
    verdict = str(event.get("verdict") or "").strip()
    if not verdict:
        return ""

    lesson_id = str(event.get("lesson_id") or "unknown").strip()
    step_id = str(event.get("step_id") or "").strip()
    step = f" step {step_id}" if step_id else ""
    credited = event.get("credited")
    credited_list = [str(item) for item in credited] if isinstance(credited, list) else []
    credited_clause = f"; credited {', '.join(credited_list)}" if credited_list else ""
    citation = f"[ev:{evidence_key}@{citation_time:.3f}]"
    return (
        f"Learn {lesson_id}{step}: {label} graded {verdict}"
        f"{credited_clause} {citation}."
    )


def _transition_judged_critique_line(event: dict) -> str:
    if event.get("verdict_state") != "judged":
        return ""
    citation_id = str(event.get("citation_id") or "").strip()
    if not citation_id:
        return ""
    components = event.get("components")
    if not isinstance(components, dict):
        components = {}

    clauses: list[str] = []
    harmonic = _metric_value(components.get("harmonic"))
    if harmonic is not None:
        clauses.append("key clash" if harmonic <= 0.0 else "compatible keys")
    bass = _metric_value(components.get("bass_collision"))
    if bass is not None:
        clauses.append(
            "both basslines up, low-end mud"
            if bass <= 0.0
            else "clean low end, one bass ducked"
        )
    if not clauses:
        return ""

    line = f"[{citation_id}] Judge graded the transition: {'; '.join(clauses)}"
    score = _metric_value(event.get("score"))
    if score is not None:
        line += f" (blend score {score:.2f}/1)"
    return f"{line}."


def _metric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _learn_event_time(event: dict) -> float:
    value = _learn_event_time_or_none(event)
    return value if value is not None else 0.0


def _learn_event_time_or_none(event: dict) -> float | None:
    for key in ("evidence_time", "t"):
        try:
            return max(0.0, float(event.get(key)))
        except (TypeError, ValueError):
            continue
    return None


def _near_miss_receipt_text(near_miss: Any, fallback_receipt: str, events: list[dict]) -> str:
    parts = [fallback_receipt.rstrip(".")]
    clock = _wall_clock_label(events, near_miss.t_center_s)
    if clock:
        parts.append(f"wall clock {clock}")
    transition = _matching_transition_receipt(events, near_miss)
    if transition:
        parts.append(transition.rstrip("."))
    return "; ".join(part for part in parts if part) + "."


def _wall_clock_label(events: list[dict], t_s: float) -> str | None:
    for event in events:
        if str(event.get("kind") or "") != "session_start":
            continue
        iso = str(event.get("wall_clock_iso") or "").strip()
        if not iso:
            continue
        try:
            start = datetime.fromisoformat(iso)
        except ValueError:
            continue
        return f"{(start + timedelta(seconds=max(0.0, t_s))).strftime('%H:%M:%S')} last night"
    return None


def _matching_transition_receipt(events: list[dict], near_miss: Any) -> str:
    best: tuple[float, str] | None = None
    for event in events:
        if str(event.get("kind") or "") != "transition_judged":
            continue
        event_t = _event_time_or_none(event)
        if event_t is None:
            continue
        if not (
            near_miss.window_start_s <= event_t <= near_miss.window_end_s
            or abs(event_t - near_miss.event_t_s) <= 2.0
        ):
            continue
        line = _transition_judged_critique_line(event)
        if not line:
            continue
        distance = abs(event_t - near_miss.event_t_s)
        if best is None or distance < best[0]:
            best = (distance, line)
    return best[1] if best is not None else ""


def _event_time_or_none(event: dict) -> float | None:
    try:
        return max(0.0, float(event.get("t")))
    except (TypeError, ValueError):
        return None


def _chapter_summaries(chapters: list[ChapterRegion]) -> list[str]:
    return [f"{c.label} ({c.start:.0f}–{c.end:.0f}s) [{c.citation_event_id}]" for c in chapters]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run(
    session_dir: Path | str,
    *,
    client: Any = None,
    recordings_root: Path | None = None,
    serve: bool = True,
    port: int = 8766,
) -> dict[str, Any]:
    """Orchestrate the debrief generation + WS server.

    Args:
        session_dir: path to the recorded session.
        client: a Gemini client (real or mock). When ``None``, we
            construct ``google.genai.Client()`` lazily.
        recordings_root: override the recordings root (test ergonomics).
        serve: when True (production), block on ``serve_forever``.
            When False (test ergonomics), return the assembled state dict
            without starting the WS server.
        port: WS server port; defaults to ``DEBRIEF_PORT`` (8766).

    Returns:
        On serve=False, returns the state dict
        ``{chapters, drills, debrief, evidence_snapshot, voice_meta,
        tldr_mp3_path, cache_hit}``.

    Raises:
        InvalidSessionDir / EventsMissing / SessionTooShort /
        DebriefGenerationError / DrillsGenerationError — these are
        caught and surfaced over the WS bus when serve=True;
        propagated to the caller when serve=False (test harness).
    """
    try:
        validated_session_dir = validate_session_dir_under_root(
            session_dir, recordings_root
        )
    except InvalidSessionDir:
        if serve:
            _emit_error_and_exit(port, "invalid_session_dir", str(session_dir))
            return {}
        raise

    # Cache-hit fast path.
    cached = read_debrief(validated_session_dir)
    if cached is not None:
        logger.info(
            "[debrief] cache hit on %s — skipping Gemini",
            validated_session_dir,
        )
        try:
            events, evidence_snapshot, voice_meta = load_session(validated_session_dir)
        except (EventsMissing, SessionTooShort) as e:
            if serve:
                _emit_error_and_exit(port, e.reason, str(e))
                return {}
            raise
        duration_s = _session_duration_s(events)
        near_miss_payload = _build_debrief_near_miss_payload(
            validated_session_dir,
            events=events,
            evidence_snapshot=evidence_snapshot,
            duration_s=duration_s,
        )
        _write_back_profile_best_effort(events, evidence_snapshot)
        state = {
            "session_dir": validated_session_dir,
            "chapters": [],  # already in `cached`
            "drills": Drills(drills=[Drill(**d) for d in cached.get("drills", [])]) if cached.get("drills") else None,
            "debrief": cached,
            "evidence_snapshot": evidence_snapshot,
            "voice_meta": voice_meta,
            "duration_s": duration_s,
            "near_miss_payload": near_miss_payload,
            "tldr_mp3_path": validated_session_dir / TLDR_MP3_FILENAME,
            "cache_hit": True,
        }
        if not serve:
            return state
        asyncio.run(_serve_loop(state, port))
        return state

    # First-time generation.
    try:
        events, evidence_snapshot, voice_meta = load_session(validated_session_dir)
    except (EventsMissing, SessionTooShort) as e:
        if serve:
            _emit_error_and_exit(port, e.reason, str(e))
            return {}
        raise
    duration_s = _session_duration_s(events)
    near_miss_payload = _build_debrief_near_miss_payload(
        validated_session_dir,
        events=events,
        evidence_snapshot=evidence_snapshot,
        duration_s=duration_s,
    )

    chapters = derive_chapters(validated_session_dir / "events.jsonl")
    chapter_summaries = _chapter_summaries(chapters)
    cited_critique = _build_cited_critique(events, chapters)

    if client is None:
        try:
            from google import genai

            client = genai.Client()
        except Exception as e:
            if serve:
                _emit_error_and_exit(
                    port,
                    "tldr_generation_failed",
                    f"Gemini client init failed: {e}",
                )
                return {}
            raise

    # Drills
    try:
        drills = generate_drills(
            client, cited_critique, chapter_summaries, evidence_snapshot
        )
    except DrillsGenerationError as e:
        if serve:
            _emit_error_and_exit(port, e.reason, e.message)
            return {}
        raise

    # TLDR
    try:
        tldr_mp3 = generate_tldr_mp3(client, chapter_summaries, cited_critique)
    except DebriefGenerationError as e:
        if serve:
            _emit_error_and_exit(port, e.reason, e.message)
            return {}
        raise

    # Defense-in-depth: final stripper sweep on every text field
    # before persistence. Plan 29-07 hardens this further.
    cleaned_drills_list = []
    for d in drills.drills:
        cleaned_drills_list.append(
            Drill(
                situation=d.situation,
                behavior=strip_uncited_sentences(d.behavior)[0] or d.behavior,
                impact=strip_uncited_sentences(d.impact)[0] or d.impact,
                action_recommended=strip_uncited_sentences(d.action_recommended)[0]
                or d.action_recommended,
                citation=d.citation,
            )
        )
    drills = Drills(drills=cleaned_drills_list)

    # Persist
    debrief_dict = {
        "chapters": [
            {
                "id": c.id,
                "start": c.start,
                "end": c.end,
                "label": c.label,
                "kind": c.kind,
                "citation_event_id": c.citation_event_id,
            }
            for c in chapters
        ],
        "drills": [
            {
                "situation": d.situation,
                "behavior": d.behavior,
                "impact": d.impact,
                "action_recommended": d.action_recommended,
                "citation": d.citation,
            }
            for d in drills.drills
        ],
    }
    write_debrief(validated_session_dir, debrief_dict, tldr_mp3)

    _write_back_profile_best_effort(events, evidence_snapshot)

    state = {
        "session_dir": validated_session_dir,
        "chapters": chapters,
        "drills": drills,
        "debrief": debrief_dict,
        "evidence_snapshot": evidence_snapshot,
        "voice_meta": voice_meta,
        "duration_s": duration_s,
        "near_miss_payload": near_miss_payload,
        "tldr_mp3_path": validated_session_dir / TLDR_MP3_FILENAME,
        "cache_hit": False,
    }
    if not serve:
        return state
    asyncio.run(_serve_loop(state, port))
    return state


def _write_back_profile_best_effort(
    events: list[dict],
    evidence_snapshot: dict[str, Any],
) -> None:
    """Feed reviewed debrief sessions back into the long-term DJ profile."""
    from vibemix.debrief.profile_writeback import write_back_profile

    if write_back_profile(events, evidence_snapshot):
        logger.info("[debrief] profile updated from session evidence")


def _emit_error_and_exit(port: int, reason: str, message: str) -> None:
    """Best-effort: spawn a short-lived WS server emitting one error frame.

    The renderer connects within ~100ms of window load; this keeps the
    server up for 2 seconds so the error reaches the renderer before
    the process exits.
    """
    logger.info("[debrief] emit_error_and_exit: reason=%r", reason)
    try:
        from vibemix.debrief.ws_server import DebriefWsServer

        async def _one_shot():
            server = DebriefWsServer(port=port)
            server.emit_error(reason, message)
            await server.serve_for_seconds(2.0)

        asyncio.run(_one_shot())
    except Exception as e:
        logger.error("[debrief] failed to emit error: %s", e)


async def _serve_loop(state: dict, port: int) -> None:
    from vibemix.debrief.ws_server import DebriefWsServer

    server = DebriefWsServer(port=port, state=state)
    # Pre-fill the emit queue with the progressive frames.
    server.enqueue_initial_frames()
    await server.serve_forever()
