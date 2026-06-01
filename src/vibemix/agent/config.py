# SPDX-License-Identifier: Apache-2.0
"""Agent-layer constants for the live co-host.

I/O sample-rate / blocksize / gain constants live in ``vibemix.audio.constants``
(already shipped by Phase 2). Phase 4's __main__ imports the audio-side
constants from there; this module only holds the agent-layer string IDs
(LLM model names and device names) that ride with the LiveKit/Gemini surface.

Phase 11's calibration wizard will surface the device names as user-editable
Settings; v4 hard-codes them so we port the v4 defaults verbatim.

Plan 41-01 migration: the LLM model string is resolved through
:func:`vibemix.llm.model_router.resolve_model` so a future SKU bump is a
one-file edit in ``vibemix/llm/_router_config.py``. Live co-host speech never
uses cloud TTS IDs; ``agent.tts_chain`` resolves to local MOSS only.
"""

from __future__ import annotations

import os

from vibemix.llm.model_router import resolve, resolve_model

# ---- LLM model identifiers (router-derived per Plan 41-01) ----
LLM_MODEL: str = resolve_model("live_coach")

# OpenRouter-routed Gemini brain model id. The retired OpenRouter TTS id is not
# exported from the agent layer; live speech resolves through local MOSS only.
OPENROUTER_LLM_MODEL: str = resolve_model("live_coach_openrouter")

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
