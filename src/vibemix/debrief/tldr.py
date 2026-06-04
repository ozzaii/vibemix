# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-04 — cited TLDR narration → Chatterbox MP3 (60–90 seconds).

Two-stage pipeline:

1. :func:`generate_tldr_text` — single Gemini debrief-route call to compose
   60–90 second (150–220 word) narration. Output is then run through the
   :mod:`stripper` so every sentence carries a citation.
2. :func:`synthesize_chatterbox_mp3` — local Chatterbox TTS line synthesis →
   raw PCM s16le → PyAV libmp3lame encode → MP3 bytes.

Both stages are guarded by typed exceptions so the orchestrator (Plan
29-02) can surface ``DebriefError(reason="tldr_generation_failed")``
without crashing the sidecar.

The text model id is resolved via :func:`vibemix.llm.model_router.resolve`
under the ``"debrief"`` path so SKU changes stay in one router file. TTS is
not routed through Gemini: Chatterbox is the single product voice source.
Wave 0 A3 verdict: PyAV libmp3lame is in-process available; no system
ffmpeg fallback required.
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Any, Protocol

import numpy as np

from vibemix.agent.chatterbox_tts import ChatterboxUnavailable, configured_model
from vibemix.agent.line_voice import build_default_line_adapter, synthesize_line
from vibemix.debrief.stripper import strip_uncited_sentences
from vibemix.llm.model_router import resolve
from vibemix.runtime.ai_observability import append_global_ai_message

__all__ = [
    "DEBRIEF_TLDR_MODEL",
    "DEBRIEF_TTS_PROVIDER",
    "MAX_TLDR_WORDS",
    "MIN_TLDR_WORDS",
    "DebriefGenerationError",
    "GeminiClientProtocol",
    "generate_tldr_mp3",
    "generate_tldr_text",
    "synthesize_chatterbox_mp3",
]

logger = logging.getLogger(__name__)

# Plan 41-01 routes both through vibemix.llm.model_router so a future SKU bump
# is a one-file edit.
DEBRIEF_TLDR_MODEL = resolve("debrief")[0]
DEBRIEF_TTS_PROVIDER = "chatterbox-local"

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
        "spoken at the local co-host voice's natural ~150 WPM) summarizing the "
        "DJ's set.\n\n"
        "HARD RULE: every sentence MUST contain at least one citation in "
        "the form `[ev:<id>@<t>]`, `[track:<id>]`, `[mix:<id>]`, "
        "`[aud:<id>]`, `[midi:<id>]`, `[screen:<id>]`, or `[key:<id>]`. "
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


def _record_tldr_ai_message(
    *,
    surface: str,
    text: str,
    model: str,
    stop_reason: str,
    prompt: str,
    response: str,
    extra: dict[str, Any] | None = None,
    engine: str = "gemini",
    provider: str = "gemini",
) -> None:
    try:
        append_global_ai_message(
            engine=engine,
            surface=surface,
            direction="assistant",
            text=text,
            provider=provider,
            model=model,
            stop_reason=stop_reason,
            prompt_chars=len(prompt),
            response_chars=len(response),
            extra=extra,
            prompt=prompt,
            response=response,
        )
    except Exception:  # pragma: no cover - observability must not break debrief
        pass


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
    except Exception as e:
        _record_tldr_ai_message(
            surface="debrief_tldr",
            text="",
            model=model,
            stop_reason=f"error:{type(e).__name__}",
            prompt=prompt,
            response=f"<error {type(e).__name__}: {e}>",
            extra={"error": f"{type(e).__name__}: {e}"},
        )
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=f"Gemini call failed: {type(e).__name__}: {e}",
        ) from e

    raw_text = _extract_text(response)
    if not raw_text:
        _record_tldr_ai_message(
            surface="debrief_tldr",
            text="",
            model=model,
            stop_reason="empty_response",
            prompt=prompt,
            response="",
        )
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message="Empty response from Gemini",
        )

    narration, stripped = strip_uncited_sentences(raw_text)
    if not narration.strip():
        _record_tldr_ai_message(
            surface="debrief_tldr",
            text="",
            model=model,
            stop_reason="all_stripped",
            prompt=prompt,
            response=raw_text,
            extra={"stripped_sentences": stripped},
        )
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=(
                f"All {stripped} sentences uncited; nothing left after "
                f"stripper. Gemini output: {raw_text[:200]!r}"
            ),
        )

    # Truncate at sentence boundary if it overshoots 220 words.
    out = _truncate_to_word_budget(narration, MAX_TLDR_WORDS)
    _record_tldr_ai_message(
        surface="debrief_tldr",
        text=out,
        model=model,
        stop_reason="stripped" if stripped else "model_done",
        prompt=prompt,
        response=raw_text,
        extra={"stripped_sentences": stripped, "output_words": len(out.split())},
    )
    return out


def synthesize_chatterbox_mp3(
    text: str,
    *,
    adapter_factory=None,
    line_synthesizer=None,
) -> bytes:
    """Synthesize ``text`` via local Chatterbox TTS → MP3 bytes.

    Returns the encoded MP3 bytes ready for :func:`persistence.write_debrief`.
    Raises :class:`DebriefGenerationError(reason="tldr_generation_failed")`
    on any failure.
    """
    if adapter_factory is None:
        adapter_factory = build_default_line_adapter
    if line_synthesizer is None:
        line_synthesizer = synthesize_line
    tts_model = configured_model()
    try:
        audio, sample_rate = asyncio.run(
            _synthesize_chatterbox_line(
                text,
                adapter_factory=adapter_factory,
                line_synthesizer=line_synthesizer,
            )
        )
    except Exception as e:
        _record_tldr_ai_message(
            surface="debrief_tts",
            text=text,
            model=tts_model,
            stop_reason=f"error:{type(e).__name__}",
            prompt=text,
            response=f"<error {type(e).__name__}: {e}>",
            extra={"provider": DEBRIEF_TTS_PROVIDER, "error": f"{type(e).__name__}: {e}"},
            engine="chatterbox_tts",
            provider=DEBRIEF_TTS_PROVIDER,
        )
        reason = (
            "Chatterbox TTS unavailable"
            if isinstance(e, ChatterboxUnavailable)
            else f"Chatterbox TTS failed: {type(e).__name__}: {e}"
        )
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message=reason,
        ) from e

    pcm = _float32_audio_to_pcm16_mono(audio)
    if not pcm:
        _record_tldr_ai_message(
            surface="debrief_tts",
            text=text,
            model=tts_model,
            stop_reason="empty_audio",
            prompt=text,
            response="<pcm bytes=0>",
            extra={"provider": DEBRIEF_TTS_PROVIDER, "pcm_bytes": 0},
            engine="chatterbox_tts",
            provider=DEBRIEF_TTS_PROVIDER,
        )
        raise DebriefGenerationError(
            reason="tldr_generation_failed",
            message="Chatterbox TTS returned empty PCM",
        )
    _record_tldr_ai_message(
        surface="debrief_tts",
        text=text,
        model=tts_model,
        stop_reason="model_done",
        prompt=text,
        response=f"<pcm bytes={len(pcm)}>",
        extra={
            "provider": DEBRIEF_TTS_PROVIDER,
            "pcm_bytes": len(pcm),
            "sample_rate": int(sample_rate),
        },
        engine="chatterbox_tts",
        provider=DEBRIEF_TTS_PROVIDER,
    )
    return _encode_pcm_to_mp3(pcm, sample_rate=int(sample_rate))


def generate_tldr_mp3(
    client: GeminiClientProtocol,
    chapter_summaries: list[str],
    cited_critique: str,
) -> bytes:
    """Compose narration text + synthesize MP3 in one call."""
    text = generate_tldr_text(client, chapter_summaries, cited_critique)
    return synthesize_chatterbox_mp3(text)


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


async def _synthesize_chatterbox_line(
    text: str,
    *,
    adapter_factory,
    line_synthesizer,
) -> tuple[np.ndarray, int]:
    adapter = adapter_factory()
    try:
        return await line_synthesizer(adapter, text)
    finally:
        closer = getattr(adapter, "aclose", None)
        if closer is not None:
            result = closer()
            if hasattr(result, "__await__"):
                await result


def _float32_audio_to_pcm16_mono(audio: np.ndarray) -> bytes:
    """Convert ``(N,)``/``(N, channels)`` float32 audio to mono int16 LE PCM."""
    arr = np.asarray(audio, dtype=np.float32)
    if arr.size == 0:
        return b""
    if arr.ndim == 2:
        if arr.shape[1] == 0:
            return b""
        mono = arr.mean(axis=1)
    else:
        mono = arr.reshape(-1)
    pcm = np.round(np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
    return pcm.tobytes()


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
