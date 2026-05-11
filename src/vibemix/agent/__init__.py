# SPDX-License-Identifier: Apache-2.0
"""vibemix.agent — LiveKit cascade agent layer.

Phase 4 of the roadmap. Hosts the DJCoHostAgent (multimodal llm_node override
calling google.genai.aio.models.generate_content_stream with the last
INVOKE_AUDIO_SECONDS of audio attached as a Part), the PlaybackQueueAudioOutput
TTS sink, the SYSTEM_INSTRUCTION persona (byte-identical port of v4:150-213),
the LLM factory, and the OpenRouter-primary TTS chain (with a load-bearing
module-load monkey-patch that puts the OpenRouter Gemini TTS model on
LiveKit's AudioChunkedStream path).

DJCoHostAgent + PlaybackQueueAudioOutput land in plan 04-02; this package's
__init__ exports them after that wave commits.
"""

from __future__ import annotations

from vibemix.agent.config import (
    INPUT_DEVICE,
    LLM_MODEL,
    MIC_DEVICE,
    OPENROUTER_TTS_MODEL,
    OUTPUT_DEVICE,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)
from vibemix.agent.llm_factory import build_llm
from vibemix.agent.persona import SYSTEM_INSTRUCTION
from vibemix.agent.tts_chain import build_tts_chain

__all__ = [
    "INPUT_DEVICE",
    "LLM_MODEL",
    "MIC_DEVICE",
    "OPENROUTER_TTS_MODEL",
    "OUTPUT_DEVICE",
    "SYSTEM_INSTRUCTION",
    "TTS_FALLBACK_MODEL",
    "TTS_MODEL",
    "VOICE",
    "build_llm",
    "build_tts_chain",
]
