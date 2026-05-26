# SPDX-License-Identifier: Apache-2.0
"""YouTube ingestion — let the Viber agent "listen to" a YouTube track/mix.

Data flow:

    url (str)
      -> is_youtube_url / youtube_deep_link  (pure URL parse + normalize)
      -> build_youtube_part                  (lazy google.genai types.Part:
                                               FileData(file_uri) + VideoMetadata)
      -> ingest_youtube                       (Part + text prompt -> injected
                                               Gemini client.models.generate_content
                                               under a wall-clock timeout -> summary dict)

DEEP-LINK posture (legal-safe, the default): we NEVER download the audio/video.
Gemini ingests the YouTube URL natively via ``FileData(file_uri=...)`` — the
media stays on YouTube; only a reference URL crosses the wire. A low sampling
``fps`` (default 0.2) keeps an audio-ish summarization bounded on tokens.

GROUNDING CAVEAT — timestamps are HINTS only. Any ``MM:SS`` Gemini reports for a
track served from a remote URL drifts (model-side sampling has no frame-accurate
clock against the source). Treat every reported moment as an approximate hint,
never a precise cut point — resolve real cue/transition points locally (the
auto-cue engine / on-device DSP), never from the model's timestamps.

Tool contract: the public functions RETURN dicts (``{"available": bool, ...}``)
and never raise — a bad url, a missing client, a timeout, or an API error all
degrade to a recoverable ``{"available": False, "error": "..."}``. The one
exception is ``build_youtube_part`` (a low-level builder, documented inline),
which raises ``ValueError`` on a non-YouTube url.
"""

from __future__ import annotations

import concurrent.futures
import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from vibemix.llm import model_router

logger = logging.getLogger(__name__)

# Hard wall-clock for the one Gemini ingest call (mirrors agent.py _gemini_call).
INGEST_TIMEOUT_S = 90.0

# Default summarization prompt — coarse, audio-ish description with HINT-only
# timestamps (per the grounding caveat above).
_DEFAULT_PROMPT = (
    "Describe this track: genre, energy, mood, structure "
    "(intro/build/drop/breakdown/outro) and any notable moments. "
    "Give approximate timestamps as HINTS only."
)

# Matches the three YouTube URL shapes, with or without scheme, capturing the
# 11-char video id. youtu.be/<id>, youtube.com/watch?v=<id>,
# youtube.com/shorts/<id> (m. / www. host prefixes accepted).
_YOUTUBE_RE = re.compile(
    r"""^(?:https?://)?
        (?:
            (?:www\.|m\.)?youtube\.com/(?:watch\?(?:[^ ]*&)?v=|shorts/)
          | youtu\.be/
        )
        (?P<id>[A-Za-z0-9_-]{11})
    """,
    re.VERBOSE,
)


def is_youtube_url(url: str) -> bool:
    """True if ``url`` is a recognizable YouTube watch / shorts / youtu.be link."""
    if not isinstance(url, str) or not url.strip():
        return False
    return _YOUTUBE_RE.match(url.strip()) is not None


def _extract_video_id(url: str) -> str | None:
    """Pull the 11-char YouTube video id out of any accepted URL shape.

    Tries the fast regex first, then falls back to a tolerant query-string parse
    (handles extra params / orderings the regex anchors miss).
    """
    if not isinstance(url, str) or not url.strip():
        return None
    candidate = url.strip()
    m = _YOUTUBE_RE.match(candidate)
    if m:
        return m.group("id")
    # Tolerant fallback: parse the URL and inspect host/path/query.
    parsed = urlparse(candidate if "//" in candidate else "https://" + candidate)
    host = (parsed.netloc or "").lower()
    if host.endswith("youtu.be"):
        vid = parsed.path.lstrip("/").split("/")[0]
        return vid if _is_video_id(vid) else None
    if "youtube.com" in host:
        path = parsed.path or ""
        if path.startswith("/shorts/"):
            vid = path[len("/shorts/"):].split("/")[0]
            return vid if _is_video_id(vid) else None
        qs = parse_qs(parsed.query)
        v = (qs.get("v") or [None])[0]
        return v if _is_video_id(v) else None
    return None


def _is_video_id(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", value))


def youtube_deep_link(url: str, t_seconds: int | None = None) -> str:
    """Normalize ``url`` to a canonical ``https://youtu.be/<id>`` deep link.

    Appends ``?t=<n>`` when ``t_seconds`` is given (the YouTube start-time param).
    If the video id cannot be parsed, returns the input unchanged (best-effort —
    this is a display/normalization helper, not a gate).
    """
    vid = _extract_video_id(url)
    if vid is None:
        return url
    link = f"https://youtu.be/{vid}"
    if t_seconds is not None:
        try:
            n = int(t_seconds)
        except (TypeError, ValueError):
            n = None
        if n is not None and n > 0:
            link = f"{link}?t={n}"
    return link


def build_youtube_part(url: str, *, fps: float = 0.2) -> Any:
    """Build the ``types.Part`` that hands a YouTube URL to Gemini (no download).

    Returns a ``types.Part`` carrying ``FileData(file_uri=<url>)`` plus
    ``VideoMetadata(fps=...)`` — Gemini ingests the media directly from YouTube;
    nothing is downloaded locally. A low ``fps`` (default 0.2) bounds the token
    cost for audio-ish summarization.

    RAISES ``ValueError`` on a non-YouTube url. This is the ONE place in this
    module a raise is intentional: it is a low-level builder, not the grounded
    tool entrypoint — callers that want the never-raise contract use
    ``ingest_youtube``, which guards this.
    """
    if not is_youtube_url(url):
        raise ValueError(f"not a YouTube URL: {url!r}")
    # Lazy import — google.genai stays out of the import boundary of callers that
    # only need the pure URL helpers.
    from google.genai import types

    return types.Part(
        file_data=types.FileData(file_uri=url.strip()),
        video_metadata=types.VideoMetadata(fps=fps),
    )


def ingest_youtube(
    url: str,
    prompt: str | None = None,
    *,
    client: Any | None = None,
    model: str | None = None,
    timeout_s: float = INGEST_TIMEOUT_S,
) -> dict[str, Any]:
    """Grounded tool: summarize a YouTube track/mix via Gemini native video.

    Builds ``contents = [youtube_part, text_prompt]`` and runs ONE
    ``client.models.generate_content`` call under a hard wall-clock timeout
    (mirrors ``agent.py._gemini_call``). RETURNS a dict and never raises:

    * not a YouTube url -> ``{"available": False, "error": "not a YouTube URL"}``
    * ``client is None`` -> ``{"available": False, "error": "...needs a Gemini client"}``
    * timeout / API error -> ``{"available": False, "error": "..."}``
    * success -> ``{"available": True, "url": <deep-link>, "summary": <text>,
      "note": <timestamp-hint caveat>}``

    The summary's timestamps are HINTS only (see module docstring); the ``note``
    field carries that caveat back to the agent.
    """
    if not is_youtube_url(url):
        return {"available": False, "error": "not a YouTube URL"}
    if client is None:
        return {
            "available": False,
            "error": "ingest_youtube needs a Gemini client",
        }

    # Resolve the model through the router — never a hardcoded literal.
    if model is None:
        try:
            model = model_router.resolve("library_agent")[0]
        except Exception as e:  # noqa: BLE001 — degrade, never raise
            logger.warning("[youtube] model resolve failed: %s", e)
            return {"available": False, "error": f"model resolve failed: {type(e).__name__}"}

    try:
        from google.genai import types

        yt_part = build_youtube_part(url)
        text_part = types.Part.from_text(text=prompt or _DEFAULT_PROMPT)
        contents = [yt_part, text_part]
    except Exception as e:  # noqa: BLE001 — build must not escape as a raise
        logger.warning("[youtube] build_youtube_part failed: %s", e)
        return {"available": False, "error": f"could not build request: {type(e).__name__}"}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=None,
            )
            response = fut.result(timeout=timeout_s)
    except concurrent.futures.TimeoutError:
        return {"available": False, "error": f"ingest timed out after {timeout_s:g}s"}
    except Exception as e:  # noqa: BLE001 — any API error degrades, never raises
        logger.warning("[youtube] ingest_youtube failed: %s", e)
        return {"available": False, "error": f"ingest failed: {type(e).__name__}"}

    summary = getattr(response, "text", None)
    if not summary:
        return {"available": False, "error": "ingest returned no text"}

    return {
        "available": True,
        "url": youtube_deep_link(url),
        "summary": summary,
        "note": (
            "Gemini-reported timestamps are approximate hints; "
            "resolve precise cut points locally."
        ),
    }


__all__ = [
    "INGEST_TIMEOUT_S",
    "is_youtube_url",
    "youtube_deep_link",
    "build_youtube_part",
    "ingest_youtube",
]
