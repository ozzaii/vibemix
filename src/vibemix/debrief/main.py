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
import os
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
            "learn_control_practice_graded",
            "learn_cue_placement_practice_graded",
            "learn_harmonic_practice_graded",
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
    ear_test_clip_relative_path = (
        _near_miss_ear_test_clip_relative_path(session_dir, near_miss)
        if has_replay_window
        else None
    )
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
        ear_test_clip_relative_path=ear_test_clip_relative_path,
        friend_line_audio_relative_path=_friend_line_audio_relative_path(
            session_dir,
            chosen,
        ),
        waveform_peaks=_build_debrief_waveform_peaks(input_wav),
    )


def _near_miss_ear_test_clip_relative_path(session_dir: Path, near_miss: Any) -> str | None:
    """Write the focused near-miss replay clip for the debrief renderer."""

    import wave

    from vibemix.debrief.ear_test import write_near_miss_clip

    try:
        clip_path = write_near_miss_clip(session_dir, near_miss)
    except (EOFError, OSError, ValueError, wave.Error) as exc:
        logger.warning("[debrief] near-miss ear-test clip skipped: %s", exc)
        return None
    try:
        return clip_path.relative_to(session_dir).as_posix()
    except ValueError:
        return clip_path.name


def _friend_line_audio_relative_path(
    session_dir: Path,
    line: Any | None,
    *,
    synthesizer=None,
) -> str | None:
    """Best-effort local-voice render for the already-grounded friend line."""

    text = str(getattr(line, "text", "") or "").strip()
    if not text:
        return None

    from vibemix.debrief.persistence import FRIEND_LINE_MP3_FILENAME, write_friend_line_audio

    path = Path(session_dir) / FRIEND_LINE_MP3_FILENAME
    try:
        if path.exists() and path.stat().st_size > 0:
            return FRIEND_LINE_MP3_FILENAME
    except OSError:
        return None

    try:
        if synthesizer is None:
            from vibemix.debrief.tldr import synthesize_chatterbox_mp3 as synthesizer

        mp3 = synthesizer(text)
        if not mp3:
            return None
        write_friend_line_audio(session_dir, bytes(mp3))
    except Exception as exc:  # pragma: no cover - local voice is optional here
        logger.warning("[debrief] friend-line audio skipped: %s", exc)
        return None
    return FRIEND_LINE_MP3_FILENAME


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
        verdict = str(event.get("verdict") or "").strip()
    elif kind == "learn_control_practice_graded":
        label = "control practice"
        evidence_key = "CONTROL_PRACTICE_GRADED"
        verdict = _learn_control_grade_detail(event)
    elif kind == "learn_cue_placement_practice_graded":
        label = "cue placement practice"
        evidence_key = "CUE_PLACEMENT_GRADED"
        verdict = str(event.get("verdict") or "").strip()
    elif kind == "learn_harmonic_practice_graded":
        label = "harmonic practice"
        evidence_key = "HARMONIC_PRACTICE_GRADED"
        verdict = _learn_harmonic_grade_detail(event)
    else:
        return ""

    citation_time = _learn_event_time_or_none(event)
    if citation_time is None:
        return ""
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


def _learn_control_grade_detail(event: dict) -> str:
    control = str(event.get("control") or "").strip()
    deck = str(event.get("deck") or "").strip()
    skill_id = str(event.get("skill_id") or "").strip()
    control_id = f"{control}:{deck}" if control and deck else control
    if control_id and skill_id:
        return f"{control_id} for {skill_id}"
    return control_id or skill_id


def _learn_harmonic_grade_detail(event: dict) -> str:
    relation = str(event.get("relation") or "").strip()
    source = str(event.get("source_track_id") or "").strip()
    target = str(event.get("target_track_id") or "").strip()
    if relation:
        return relation
    if source and target:
        return f"{source} into {target}"
    return "compatible pair"


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


def _build_debrief_client() -> Any | None:
    """Resolve a genai client the way the live brain does (direct-first).

    The debrief sidecar is its own process: ``open -a`` strips env and the
    Tauri shell only relays keys it has itself (sidecar.rs
    FORWARDED_ENV_KEYS), so a packaged proxy-mode user reaches here with no
    GEMINI_API_KEY anywhere. Mirror ``__main__``'s mode dispatch:

      1. GEMINI_API_KEY set (BYO dev relay) → direct client with the live
         path's 120s request bound (same precedent as
         ``__main__._library_genai_client``).
      2. mode != direct → self-provision proxy auth exactly like the live
         session: install-uuid + cached/refreshed JWT against the proxy
         (no env needed — keyring/file-backed, bounded keyring calls).
      3. ``None`` when neither resolves → caller degrades to the local
         frames (chapters / near-miss / waveform) instead of crashing.
    """
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if api_key:
        from google import genai
        from google.genai import types

        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120_000),  # ms — match live
        )

    mode = (os.environ.get("VIBEMIX_LLM_MODE") or "").strip().lower()
    if not mode:
        try:
            from vibemix.runtime.config_store import load_config

            mode = (load_config().llm_mode or "proxy").strip().lower()
        except Exception:
            mode = "proxy"
    if mode == "direct":
        # Explicit direct mode without a key: nothing to build.
        return None

    proxy_base_url = os.environ.get(
        "VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world"
    )
    try:
        jwt = (os.environ.get("VIBEMIX_PROXY_JWT") or "").strip()
        if not jwt:
            from vibemix import __version__
            from vibemix.agent.install_uuid import get_or_create_install_uuid
            from vibemix.agent.jwt_cache import get_or_refresh_jwt

            install_id = get_or_create_install_uuid()
            client_version = os.environ.get("VIBEMIX_CLIENT_VERSION", __version__)
            jwt = asyncio.run(
                get_or_refresh_jwt(install_id, proxy_base_url, client_version)
            )
        from vibemix.agent.proxy_client import build_proxy_genai_client

        return build_proxy_genai_client(jwt, proxy_base_url)
    except Exception as e:
        logger.warning("[debrief] proxy client unavailable: %s", e)
        return None


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

    serve=True (production): bind 127.0.0.1:port FIRST, then generate,
    emitting each frame as its stage completes. The renderer connects
    during sidecar boot and watches the debrief fill in progressively;
    errors are emitted on the already-bound socket and served until the
    window closes (no one-shot race, no silent dead-end).

    serve=False (test harness): synchronous generation; returns the
    state dict; raises the Plan 29-01 typed exceptions.
    """
    if not serve:
        return _generate(
            session_dir, client=client, recordings_root=recordings_root
        )
    return asyncio.run(
        _serve_and_generate(
            session_dir,
            client=client,
            recordings_root=recordings_root,
            port=port,
        )
    )


def _generate(
    session_dir: Path | str,
    *,
    client: Any = None,
    recordings_root: Path | None = None,
    progress: Any = None,
) -> dict[str, Any]:
    """Build the debrief state, calling ``progress(stage, state)`` after
    each completed stage (loaded / near_miss / chapters / drills / tldr).
    Raises the typed exceptions; the served path maps them onto the bus.
    """

    def _stage(name: str, st: dict[str, Any]) -> None:
        if progress is not None:
            progress(name, st)

    validated_session_dir = validate_session_dir_under_root(
        session_dir, recordings_root
    )

    cached = read_debrief(validated_session_dir)
    events, evidence_snapshot, voice_meta = load_session(validated_session_dir)
    duration_s = _session_duration_s(events)
    state: dict[str, Any] = {
        "session_dir": validated_session_dir,
        "chapters": [],
        "drills": None,
        "debrief": cached,
        "evidence_snapshot": evidence_snapshot,
        "voice_meta": voice_meta,
        "duration_s": duration_s,
        "near_miss_payload": None,
        "tldr_mp3_path": validated_session_dir / TLDR_MP3_FILENAME,
        "cache_hit": cached is not None,
    }
    _stage("loaded", state)

    near_miss_payload = _build_debrief_near_miss_payload(
        validated_session_dir,
        events=events,
        evidence_snapshot=evidence_snapshot,
        duration_s=duration_s,
    )
    state["near_miss_payload"] = near_miss_payload
    _stage("near_miss", state)

    if cached is not None:
        logger.info(
            "[debrief] cache hit on %s — skipping Gemini",
            validated_session_dir,
        )
        state["drills"] = (
            Drills(drills=[Drill(**d) for d in cached.get("drills", [])])
            if cached.get("drills")
            else None
        )
        _write_back_profile_best_effort(events, evidence_snapshot)
        _stage("chapters", state)  # rebuilt from `cached` by the emitter
        _stage("drills", state)
        _stage("tldr", state)
        return state

    chapters = derive_chapters(validated_session_dir / "events.jsonl")
    chapter_summaries = _chapter_summaries(chapters)
    cited_critique = _build_cited_critique(events, chapters)
    state["chapters"] = chapters
    _stage("chapters", state)

    if client is None:
        client = _build_debrief_client()
    if client is None:
        # Local frames already emitted via the stages above — the served
        # runner maps this typed raise onto an honest llm_unavailable
        # frame ON TOP of them. Cache untouched, so a later open retries.
        _write_back_profile_best_effort(events, evidence_snapshot)
        raise DebriefGenerationError(
            reason="llm_unavailable",
            message="no GEMINI_API_KEY and no proxy auth available",
        )

    drills = generate_drills(
        client, cited_critique, chapter_summaries, evidence_snapshot
    )

    # Defense-in-depth: final stripper sweep BEFORE the drills frame is
    # emitted or persisted. Plan 29-07 hardens this further.
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
    state["drills"] = drills
    _stage("drills", state)

    tldr_mp3 = generate_tldr_mp3(client, chapter_summaries, cited_critique)

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
    # write_debrief persists a COPY enriched with tldr_sha256/tldr_path —
    # re-read so emit_tldr_audio sees the sha (the cache-hit path proves
    # read_debrief returns it).
    state["debrief"] = read_debrief(validated_session_dir) or debrief_dict
    _write_back_profile_best_effort(events, evidence_snapshot)
    _stage("tldr", state)
    return state


def _write_back_profile_best_effort(
    events: list[dict],
    evidence_snapshot: dict[str, Any],
) -> None:
    """Feed reviewed debrief sessions back into the long-term DJ profile."""
    from vibemix.debrief.profile_writeback import write_back_profile

    if write_back_profile(events, evidence_snapshot):
        logger.info("[debrief] profile updated from session evidence")


async def _serve_and_generate(
    session_dir: Path | str,
    *,
    client: Any = None,
    recordings_root: Path | None = None,
    port: int = 8766,
) -> dict[str, Any]:
    """Bind 127.0.0.1:port FIRST, then generate, emitting frames per stage.

    Every failure becomes an ipc.debrief.error frame on the already-bound
    socket, and the server keeps serving (frames + tooltip RPC) until the
    window closes and the Rust shell reaps this process — a retrying
    renderer can never miss the verdict.
    """
    from vibemix.debrief.ws_server import DebriefWsServer

    server = DebriefWsServer(port=port)
    bound = asyncio.Event()
    serve_task = asyncio.create_task(server.serve_forever(bound=bound))
    await bound.wait()

    loop = asyncio.get_running_loop()

    def _on_stage(stage: str, state: dict[str, Any]) -> None:
        # Runs on the executor thread — hop to the loop before touching
        # the server (its connections/history live on the loop).
        loop.call_soon_threadsafe(_emit_stage_frames, server, stage, state)

    state: dict[str, Any] = {}
    try:
        state = await loop.run_in_executor(
            None,
            lambda: _generate(
                session_dir,
                client=client,
                recordings_root=recordings_root,
                progress=_on_stage,
            ),
        )
        server.state = state
    except InvalidSessionDir:
        server.emit_error("invalid_session_dir", str(session_dir))
    except (EventsMissing, SessionTooShort) as e:
        server.emit_error(e.reason, str(e))
    except (DebriefGenerationError, DrillsGenerationError) as e:
        server.emit_error(e.reason, e.message)
    except Exception as e:  # never a silent dead-end
        logger.exception("[debrief] generation failed")
        server.emit_error("sidecar_crashed", f"{type(e).__name__}: {e}")

    await serve_task
    return state


def _emit_stage_frames(server: Any, stage: str, state: dict[str, Any]) -> None:
    """Map a generation stage onto its progressive ws frames."""
    server.state = state
    if stage == "loaded":
        server.emit_session_loaded()
    elif stage == "near_miss":
        server.emit_near_miss()
    elif stage == "chapters":
        server.emit_chapter_list()
    elif stage == "drills":
        server.emit_drills()
    elif stage == "tldr":
        server.emit_tldr_audio()
