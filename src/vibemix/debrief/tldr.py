# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-04 — Achird TTS narration → MP3 (60–90 seconds).

Two-stage pipeline:

1. :func:`generate_tldr_text` — single Gemini 3 Flash call to compose
   60–90 second (150–220 word) narration. Output is then run through the
   :mod:`stripper` so every sentence carries a citation.
2. :func:`synthesize_achird_mp3` — Gemini TTS call (Achird voice) →
   raw PCM 24kHz s16le → PyAV libmp3lame encode → MP3 bytes.

Both stages are guarded by typed exceptions so the orchestrator (Plan
29-02) can surface ``DebriefError(reason="tldr_generation_failed")``
without crashing the sidecar.

Wave 0 A1 verdict: model id is ``gemini-3-pro-preview`` (not bare).
Wave 0 A3 verdict: PyAV libmp3lame is in-process available; no system
ffmpeg fallback required.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Protocol

from vibemix.debrief.stripper import strip_uncited_sentences

__all__ = [
    "ACHIRD_VOICE_NAME",
    "DEBRIEF_TLDR_MODEL",
    "DEBRIEF_TTS_MODEL",
    "MAX_TLDR_WORDS",
    "MIN_TLDR_WORDS",
    "DebriefGenerationError",
    "GeminiClientProtocol",
    "generate_tldr_text",
    "generate_tldr_mp3",
    "synthesize_achird_mp3",
]

logger = logging.getLogger(__name__)

# Wave 0 A1: full preview id is required. Bare 'gemini-3-pro' → 404.
DEBRIEF_TLDR_MODEL = "gemini-3-pro-preview"
DEBRIEF_TTS_MODEL = "gemini-3-flash-tts-preview"
ACHIRD_VOICE_NAME = "Achird"

# 150 wpm × (60-90s) bounds → 150-225 words target.
MIN_TLDR_WORDS = 150
MAX_TLDR_WORDS = 220


class DebriefGenerationError(Exception):
    """Raised when TLDR or drills generation fails after retries.

    Used by main.py (Plan 29-02) to surface
    ``DebriefError(reason="tldr_generation_failed")`` or
    ``DebriefError(reason="drills_generation_failed")`` over the WS bus.
    """

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


class GeminiClientProtocol(Protocol):
    """Minimal protocol that ``generate_tldr_*`` requires.

    Matches ``google.genai.Client`` at the call sites we use. The tests
    pass a Mock object satisfying this protocol so they stay offline.
    """

    models: Any


def _build_tldr_prompt(
    chapter_summaries: list[str], cited_critique: str
) -> str:
    """Build the narration prompt with explicit citation grammar reminder."""
    chapter_block = "\n".join(f"- {s}" for s in chapter_summaries)
    return (
        "You are the post-session debrief narrator for vibemix, an AI DJ "
        "co-host. Write a 150-220 word narration (about 60-90 seconds "
        "spoken at the Achird voice's natural ~150 WPM) summarizing the "
        "DJ's set.\n\n"
        "HARD RULE: every sentence MUST contain at least one citation in "
        "the form `[ev:<id>@<t>]`, `[track:<id>]`, `[mix:<id>]`, "
        "`[aud:<id>]`, `[midi:<id>]`, `[screen:<id>]`, or `[tend:<id>]`. "
        "Sentences without a citation will be stripped before the user "
        "hears them — wasted tokens.\n\n"
        "Voice: warm, grounded, no hype, no AI slop. Talk like a friend "
        "playing back a recording — observational, not theatrical.\n\n"
        f"Chapter summaries:\n{chapter_block}\n\n"
        f"Cited critique points (use these verbatim or paraphrase but "
        f"keep the citation tags intact):\n{cited_critique}\n\n"
        "Output: just the narration text. No headers, no bullet lists, "
        "no quotation marks. Plain prose."
    )


def generate_tldr_text(
    client: GeminiClientProtocol,
    chapter_summaries: list[str],
    cited_critique: str,
    *,
    model: str = DEBRIEF_TLDR_MODEL,
) -> str:
    """Generate the TL;DR narration text.

    Runs the Gemini output through :func:`strip_uncited_sentences` to
    enforce DEBRIEF-07 even at this layer. Raises
    :class:`DebriefGenerationError(reason="tldr_generation_failed")`
    when the stripper drops everything.
    """
    prompt = _build_tldr_prompt(chapter_summaries, cited_critique)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as e:  # noqa: BLE001 — surface as typed error
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=f"Gemini call failed: {type(e).__name__}: {e}",
        ) from e

    raw_text = _extract_text(response)
    if not raw_text:
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message="Empty response from Gemini",
        )

    narration, stripped = strip_uncited_sentences(raw_text)
    if not narration.strip():
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=(
                f"All {stripped} sentences uncited; nothing left after "
                f"stripper. Gemini output: {raw_text[:200]!r}"
            ),
        )

    # Truncate at sentence boundary if it overshoots 220 words.
    return _truncate_to_word_budget(narration, MAX_TLDR_WORDS)


def synthesize_achird_mp3(
    client: GeminiClientProtocol,
    text: str,
    *,
    model: str = DEBRIEF_TTS_MODEL,
    voice_name: str = ACHIRD_VOICE_NAME,
) -> bytes:
    """Synthesize ``text`` via Gemini TTS → PCM 24kHz s16le → MP3 bytes.

    Returns the encoded MP3 bytes ready for :func:`persistence.write_debrief`.
    Raises :class:`DebriefGenerationError(reason="tldr_generation_failed")`
    on any failure.
    """
    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config={
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {"voice_name": voice_name}
                    }
                }
            },
        )
    except Exception as e:  # noqa: BLE001
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=f"TTS call failed: {type(e).__name__}: {e}",
        ) from e

    pcm = _extract_audio_pcm(response)
    if not pcm:
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message="TTS returned empty PCM",
        )
    return _encode_pcm_to_mp3(pcm, sample_rate=24000)


def generate_tldr_mp3(
    client: GeminiClientProtocol,
    chapter_summaries: list[str],
    cited_critique: str,
) -> bytes:
    """Compose narration text + synthesize MP3 in one call."""
    text = generate_tldr_text(client, chapter_summaries, cited_critique)
    return synthesize_achird_mp3(client, text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text(response: Any) -> str:
    """Pull narration text out of a Gemini response object.

    Handles both the ``.text`` shortcut and the explicit
    ``.candidates[0].content.parts[0].text`` shape.
    """
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text
    try:
        return response.candidates[0].content.parts[0].text  # type: ignore[no-any-return]
    except (AttributeError, IndexError, TypeError):
        return ""


def _extract_audio_pcm(response: Any) -> bytes:
    """Pull raw PCM bytes out of a Gemini TTS response."""
    # The TTS response shape: ``response.candidates[0].content.parts[0].inline_data.data``.
    # Tests pass a SimpleNamespace mock; production hits the real Gemini SDK.
    try:
        part = response.candidates[0].content.parts[0]
    except (AttributeError, IndexError, TypeError):
        return b""
    inline = getattr(part, "inline_data", None)
    if inline is not None:
        data = getattr(inline, "data", b"")
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    # Some SDK shapes expose ``audio`` directly.
    audio = getattr(part, "audio", None)
    if isinstance(audio, (bytes, bytearray)):
        return bytes(audio)
    return b""


def _encode_pcm_to_mp3(pcm: bytes, sample_rate: int = 24000) -> bytes:
    """Encode raw PCM s16le mono → MP3 using PyAV libmp3lame.

    Wave 0 A3 verified libmp3lame is in-process. If PyAV import fails
    (e.g. test environment without av installed), raises the underlying
    ImportError so the caller can fall back.
    """
    import av  # local import — keep startup light; tests can stub

    buf = io.BytesIO()
    container = av.open(buf, mode="w", format="mp3")
    try:
        stream = container.add_stream("mp3", rate=sample_rate)
        stream.bit_rate = 96_000
        stream.layout = "mono"

        # Decode raw PCM into an AudioFrame.
        import numpy as np

        samples = np.frombuffer(pcm, dtype=np.int16)
        # PyAV expects 2D for planar; 1D works for packed s16.
        frame = av.AudioFrame.from_ndarray(
            samples.reshape(1, -1),
            format="s16",
            layout="mono",
        )
        frame.sample_rate = sample_rate
        for packet in stream.encode(frame):
            container.mux(packet)
        # Flush.
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    return buf.getvalue()


def _truncate_to_word_budget(text: str, max_words: int) -> str:
    """Truncate ``text`` at sentence boundary if it exceeds ``max_words``.

    Keeps full sentences only — never cuts mid-clause. Returns the
    longest prefix whose word count ≤ max_words.
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    # Find a sentence-ending boundary within the first max_words tokens.
    import re

    truncated = " ".join(words[:max_words])
    # Walk back to the last sentence terminator.
    last_term = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )
    if last_term > 0:
        return truncated[: last_term + 1]
    return truncated
