# SPDX-License-Identifier: Apache-2.0
"""Local-only TTS factory for the live co-host.

The product voice is local by contract: cloud TTS keys are intentionally ignored
here so a missing or failing local voice can never silently fall back to a
paid/provider voice. The default engine is ``MossLocalTTS``. Operators may opt in
to the Apple-GPU Chatterbox-Turbo voice with ``VIBEMIX_TTS_ENGINE=chatterbox``;
when that engine is selected but unavailable (no ``mlx-audio`` / no reference clip)
the chain falls back to MOSS so the voice is never muted.
"""

from __future__ import annotations

import os
from typing import Literal

from livekit.agents import tts as agents_tts


def _build_moss_chain(*, voice: str | None = None, moss: object | None = None) -> agents_tts.FallbackAdapter:
    """Build the default live TTS chain: local MOSS, one provider."""
    from vibemix.agent.local_tts import MossLocalTTS, build_local_tts_adapter

    if moss is not None and not isinstance(moss, MossLocalTTS):
        raise TypeError("moss must be a MossLocalTTS instance")
    return build_local_tts_adapter(voice=voice, moss=moss)


def _build_chatterbox_chain() -> agents_tts.FallbackAdapter:
    """Build the opt-in Chatterbox-Turbo MLX voice chain (Apple GPU, zero-shot clone)."""
    from vibemix.agent.chatterbox_tts import build_chatterbox_adapter

    return build_chatterbox_adapter()


def build_tts_chain(
    *,
    mode: Literal["direct", "proxy"] = "direct",
    voice: str | None = None,
    moss: object | None = None,
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

    if os.environ.get("VIBEMIX_TTS_ENGINE", "moss").strip().lower() == "chatterbox":
        from vibemix.agent.chatterbox_tts import chatterbox_available, chatterbox_unavailable_reason

        if chatterbox_available():
            return _build_chatterbox_chain()
        # Selected but unavailable -> never mute, fall back to the MOSS floor.
        import sys

        print(
            f"[tts] VIBEMIX_TTS_ENGINE=chatterbox unavailable "
            f"({chatterbox_unavailable_reason()}); falling back to MOSS",
            file=sys.stderr,
        )

    return _build_moss_chain(voice=voice, moss=moss)
