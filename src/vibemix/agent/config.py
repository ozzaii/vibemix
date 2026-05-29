# SPDX-License-Identifier: Apache-2.0
"""Agent-layer constants — verbatim port of cohost_v4.py:97-104.

I/O sample-rate / blocksize / gain constants live in ``vibemix.audio.constants``
(already shipped by Phase 2). Phase 4's __main__ imports the audio-side
constants from there; this module only holds the agent-layer string IDs
(model names, voice, device names) that ride with the LiveKit/Gemini surface.

Phase 11's calibration wizard will surface the device names as user-editable
Settings; v4 hard-codes them so we port the v4 defaults verbatim.

Plan 41-01 migration: the four LLM/TTS model strings are now resolved
through :func:`vibemix.llm.model_router.resolve` so a future SKU bump is
a one-file edit in ``vibemix/llm/_router_config.py``. The constant
*names* are preserved (``LLM_MODEL``, ``TTS_MODEL``, …) for backward
compatibility — every existing import (``__main__.py``, ``agent/cache.py``,
``debrief/*``, multiple tests) keeps working unchanged.
"""

from __future__ import annotations

import os

from vibemix.llm.model_router import resolve, resolve_model

# ---- LLM + TTS model identifiers (v4:97-99, router-derived per Plan 41-01) ----
LLM_MODEL: str = resolve_model("live_coach")
TTS_MODEL: str = resolve_model("live_coach_tts")
TTS_FALLBACK_MODEL: str = resolve_model("live_coach_tts_fallback")

# OpenRouter-routed Gemini model ids. The TTS id was used inline at v4:1995;
# both now ride the router so OpenRouter surfaces do not reintroduce literals
# outside ``llm/_router_config.py``.
OPENROUTER_LLM_MODEL: str = resolve_model("live_coach_openrouter")
OPENROUTER_TTS_MODEL: str = resolve_model("live_coach_tts_openrouter")

# ---- ServiceTier dispatch (Plan 41-01, LAT-07) ----
# Exposed alongside LLM_MODEL so callers that need the tier (e.g. the
# coach loop wiring up ``GenerateContentConfig(service_tier=...)``) don't
# need to round-trip back through ``resolve()``. Other call sites that
# want both values for a different path should import ``resolve`` directly.
# ---- Voice id (v4:104) ----
VOICE: str = "Achird"

# ---- Device names (v4:101-103) ----
# Factory defaults stay pinned for ordinary installs. The env overrides are
# intentionally import-time only so live proof runs can select a rig-specific
# CoreAudio device before ``python -m vibemix`` boots.


def _device_name(env_name: str, default: str) -> str:
    override = os.environ.get(env_name, "").strip()
    return override or default


INPUT_DEVICE: str = _device_name("VIBEMIX_INPUT_DEVICE", "BlackHole 2ch")
OUTPUT_DEVICE: str = _device_name("VIBEMIX_OUTPUT_DEVICE", "MacBook Pro Speakers")
MIC_DEVICE: str = _device_name("VIBEMIX_MIC_DEVICE", "MacBook Pro Microphone")


def __getattr__(name: str):
    if name == "LIVE_COACH_SERVICE_TIER":
        return resolve("live_coach")[1]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
