# SPDX-License-Identifier: Apache-2.0
"""MOSS-only TTS factory for the live co-host.

The product voice has exactly one source: ``MossLocalTTS``. Direct and proxy
sessions both build the same local provider; cloud TTS keys are intentionally
ignored here so a missing or failing local voice cannot silently fall back to a
paid/provider voice.
"""

from __future__ import annotations

from typing import Literal

from livekit.agents import tts as agents_tts


def _build_moss_chain() -> agents_tts.FallbackAdapter:
    """Build the only supported live TTS chain: local MOSS, one provider."""
    from vibemix.agent.local_tts import build_local_tts_adapter

    return build_local_tts_adapter()


def build_tts_chain(
    *,
    mode: Literal["direct", "proxy"] = "direct",
) -> agents_tts.FallbackAdapter:
    """Build the live voice chain.

    ``mode`` is still accepted for the direct/proxy callers, but it no longer
    selects a provider. MOSS is the single source of TTS in every mode, and
    cloud/provider keys are not part of this API anymore. If the local model is
    unavailable, ``build_local_tts_adapter`` raises a clear
    ``LocalTTSUnavailable`` instead of routing speech to a cloud fallback.
    """
    if mode not in {"direct", "proxy"}:
        raise ValueError(f"unknown mode: {mode}")
    return _build_moss_chain()
