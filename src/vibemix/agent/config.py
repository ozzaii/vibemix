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

from vibemix.llm.model_router import resolve

# ---- LLM + TTS model identifiers (v4:97-99, router-derived per Plan 41-01) ----
LLM_MODEL: str = resolve("live_coach")[0]
TTS_MODEL: str = resolve("live_coach_tts")[0]
TTS_FALLBACK_MODEL: str = resolve("live_coach_tts_fallback")[0]

# OpenRouter-routed Gemini TTS model id (v4:1995). NOT in v4 as a constant but
# used inline at v4:1995 — promoted to a constant here so the monkey-patch
# (tts_chain.py) and the factory body reference the same source string.
OPENROUTER_TTS_MODEL: str = resolve("live_coach_tts_openrouter")[0]

# ---- ServiceTier dispatch (Plan 41-01, LAT-07) ----
# Exposed alongside LLM_MODEL so callers that need the tier (e.g. the
# coach loop wiring up ``GenerateContentConfig(service_tier=...)``) don't
# need to round-trip back through ``resolve()``. Other call sites that
# want both values for a different path should import ``resolve`` directly.
LIVE_COACH_SERVICE_TIER = resolve("live_coach")[1]

# ---- Voice id (v4:104) ----
VOICE: str = "Achird"

# ---- Device names (v4:101-103) ----
INPUT_DEVICE: str = "BlackHole 2ch"
OUTPUT_DEVICE: str = "MacBook Pro Speakers"  # 2026-05-18 — Kaan's pick for tonight (was "AI Capture" aggregate, switched to laptop speakers).
MIC_DEVICE: str = "MacBook Pro Microphone"
