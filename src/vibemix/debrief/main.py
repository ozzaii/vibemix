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
    from vibemix.ui_bus import DrillPayload

    return DrillPayload(
        situation=d.situation,
        behavior=d.behavior,
        impact=d.impact,
        action_recommended=d.action_recommended,
        citation=d.citation,
    )


# ---------------------------------------------------------------------------
# Build cited critique from events + chapter labels
# ---------------------------------------------------------------------------


def _build_cited_critique(events: list[dict], chapters: list[ChapterRegion]) -> str:
    """Lossy condensation of events.jsonl into a citation-rich critique string.

    Picks up the ``ai_text`` event lines (the live cohost's replies — already
    cited per Phase 18 grammar) and joins them with their preceding event-id
    citations. Result is the input the TLDR + drills prompts consume.
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
    return " ".join(out)


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
        state = {
            "session_dir": validated_session_dir,
            "chapters": [],  # already in `cached`
            "drills": Drills(drills=[Drill(**d) for d in cached.get("drills", [])]) if cached.get("drills") else None,
            "debrief": cached,
            "evidence_snapshot": evidence_snapshot,
            "voice_meta": voice_meta,
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

    chapters = derive_chapters(validated_session_dir / "events.jsonl")
    chapter_summaries = _chapter_summaries(chapters)
    cited_critique = _build_cited_critique(events, chapters)

    if client is None:
        try:
            from google import genai

            client = genai.Client()
        except Exception as e:  # noqa: BLE001
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

    state = {
        "session_dir": validated_session_dir,
        "chapters": chapters,
        "drills": drills,
        "debrief": debrief_dict,
        "evidence_snapshot": evidence_snapshot,
        "voice_meta": voice_meta,
        "tldr_mp3_path": validated_session_dir / TLDR_MP3_FILENAME,
        "cache_hit": False,
    }
    if not serve:
        return state
    asyncio.run(_serve_loop(state, port))
    return state


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
    except Exception as e:  # noqa: BLE001 — emit_error path can't crash
        logger.error("[debrief] failed to emit error: %s", e)


async def _serve_loop(state: dict, port: int) -> None:
    from vibemix.debrief.ws_server import DebriefWsServer

    server = DebriefWsServer(port=port, state=state)
    # Pre-fill the emit queue with the progressive frames.
    server.enqueue_initial_frames()
    await server.serve_forever()
