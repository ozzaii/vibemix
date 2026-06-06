# SPDX-License-Identifier: Apache-2.0
"""Local-only TTS factory for the live co-host.

The product voice is local by contract: cloud TTS keys are intentionally ignored
here so a missing or failing local voice can never silently fall back to a
paid/provider voice. Chatterbox-Turbo is the only supported live engine. If it
cannot be built on this machine, callers start voiceless with a clear reason.
"""

from __future__ import annotations

from typing import Literal

from livekit.agents import tts as agents_tts


def build_tts_chain(
    *,
    mode: Literal["direct", "proxy"] = "direct",
    chatterbox: object | None = None,
) -> agents_tts.FallbackAdapter:
    """Build the live voice chain.

    ``mode`` is still accepted for the direct/proxy callers, but it no longer
    selects a provider. Chatterbox is the single source of live speech in every
    mode, and cloud/provider keys are not part of this API.
    """
    if mode not in {"direct", "proxy"}:
        raise ValueError(f"unknown mode: {mode}")

    from vibemix.agent.chatterbox_tts import (
        ChatterboxLocalTTS,
        ChatterboxUnavailable,
        build_chatterbox_adapter,
        engine_selected,
        system_fallback_available,
    )

    if not engine_selected():
        raise ChatterboxUnavailable("Chatterbox is the only supported local voice engine")
    if chatterbox is None and not system_fallback_available():
        from vibemix.agent.chatterbox_tts import chatterbox_available, chatterbox_unavailable_reason

        if not chatterbox_available():
            raise ChatterboxUnavailable(chatterbox_unavailable_reason())
    if chatterbox is not None and not isinstance(chatterbox, ChatterboxLocalTTS):
        raise TypeError("chatterbox must be a ChatterboxLocalTTS instance")
    return build_chatterbox_adapter(chatterbox=chatterbox)
