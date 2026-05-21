# SPDX-License-Identifier: Apache-2.0
"""OpenRouter LLM path — OpenAI-compat streaming adapter for the live coach.

2026-05-21 (Kaan): the brain (gemini-3.5-flash) was 503ing on the direct
Gemini free tier. OpenRouter serves the same model with its own quota AND
accepts inline audio (verified: ``scripts/_probe_or_audio.py`` → Gemini
heard "Kick, lead, texture." through OpenRouter's ``input_audio`` parts).

This module converts the genai-format ``contents`` the agent already builds
(a leading text str + ``types.Part`` audio/image parts) into OpenAI-compat
``messages`` and streams the completion back as objects that quack like the
google.genai stream chunks (``.text`` + ``.usage_metadata``) — so
``DJCoHostAgent.llm_node`` consumes either source through the SAME loop with
no downstream change (speculative-head, citation lint, slop gate all intact).

The 3.5-flash reasoning trap (probe finding): with a tiny token budget the
model spent the whole budget on hidden reasoning and returned empty content.
Mitigated by (a) a generous ``max_tokens`` and (b) ``reasoning.effort=low``
so Gemini keeps thinking minimal and leaves budget for the actual reply.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def build_or_client(api_key: str) -> AsyncOpenAI:
    """OpenAI-compat client pointed at OpenRouter."""
    return AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


@dataclass
class _Chunk:
    """Minimal stand-in for a google.genai stream chunk: only the two fields
    ``llm_node`` reads. ``usage_metadata`` stays None (OR streams don't carry
    Gemini's cached-token telemetry; the cache-hit branch noops on None)."""

    text: str | None
    usage_metadata: None = None


def _parts_to_openai_content(contents: list[Any]) -> list[dict[str, Any]]:
    """Convert the agent's genai ``contents`` list to an OpenAI content array.

    ``contents[0]`` is the prompt text (str). ``contents[1:]`` are
    ``types.Part`` objects carrying inline audio (audio/wav) or image
    (image/jpeg) bytes in ``part.inline_data``. Audio → ``input_audio``
    (base64 wav); image → ``image_url`` (data URI).
    """
    out: list[dict[str, Any]] = []
    for item in contents:
        if isinstance(item, str):
            out.append({"type": "text", "text": item})
            continue
        blob = getattr(item, "inline_data", None)
        if blob is None:
            # Unknown part shape — stringify defensively rather than drop.
            out.append({"type": "text", "text": str(item)})
            continue
        data: bytes = blob.data
        mime: str = blob.mime_type or "application/octet-stream"
        b64 = base64.b64encode(data).decode()
        if mime.startswith("audio/"):
            fmt = "wav" if "wav" in mime else mime.split("/", 1)[1]
            out.append(
                {"type": "input_audio", "input_audio": {"data": b64, "format": fmt}}
            )
        elif mime.startswith("image/"):
            out.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            )
        else:
            out.append({"type": "text", "text": f"[unsupported part: {mime}]"})
    return out


async def stream_or(
    client: AsyncOpenAI,
    *,
    model: str,
    system_instruction: str,
    contents: list[Any],
    temperature: float = 1.0,
    max_tokens: int = 2048,
) -> AsyncIterator[_Chunk]:
    """Stream an OpenRouter chat completion, yielding genai-shaped chunks.

    ``max_tokens`` is generous and ``reasoning.effort='low'`` keeps Gemini's
    hidden thinking minimal so the visible reply isn't starved (probe trap).
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": _parts_to_openai_content(contents)},
    ]
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body={
            # Research-confirmed (2026-05-21): for Gemini 3.x, OpenRouter maps
            # reasoning.effort 1:1 to Google's thinkingLevel — "minimal" is the
            # lowest (Gemini can't fully disable thinking) and genuinely cuts
            # compute. exclude:true drops the reasoning text from the stream.
            # This is THE fix for the probe's empty-content bug: at default
            # "medium" thinking the model burned the whole budget internally.
            # Kaan: "thinking minimal". max_tokens (≥512) keeps the visible
            # reply from being starved.
            "reasoning": {"effort": "minimal", "exclude": True},
            # Pin first-party Google + sort by latency — avoids slow third-party
            # routes, biggest TTFT lever after thinking level.
            "provider": {"only": ["google-ai-studio"], "sort": "latency"},
        },
    )
    async for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta
        txt = getattr(delta, "content", None)
        if txt:
            yield _Chunk(text=txt)
