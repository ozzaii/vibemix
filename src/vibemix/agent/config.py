# SPDX-License-Identifier: Apache-2.0
"""Agent-layer constants — verbatim port of cohost_v4.py:97-104.

I/O sample-rate / blocksize / gain constants live in ``vibemix.audio.constants``
(already shipped by Phase 2). Phase 4's __main__ imports the audio-side
constants from there; this module only holds the agent-layer string IDs
(model names, voice, device names) that ride with the LiveKit/Gemini surface.

Phase 11's calibration wizard will surface the device names as user-editable
Settings; v4 hard-codes them so we port the v4 defaults verbatim.
"""

from __future__ import annotations

# ---- LLM + TTS model identifiers (v4:97-99) ----
LLM_MODEL: str = "gemini-3-flash-preview"
TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
TTS_FALLBACK_MODEL: str = "gemini-2.5-flash-preview-tts"

# OpenRouter-routed Gemini TTS model id (v4:1995). NOT in v4 as a constant but
# used inline at v4:1995 — promoted to a constant here so the monkey-patch
# (tts_chain.py) and the factory body reference the same source string.
OPENROUTER_TTS_MODEL: str = "google/gemini-3.1-flash-tts-preview"

# ---- Voice id (v4:104) ----
VOICE: str = "Achird"

# ---- Device names (v4:101-103) ----
INPUT_DEVICE: str = "BlackHole 2ch"
OUTPUT_DEVICE: str = "AI Capture"  # v4:102 — Multi-Output: External Headphones + BlackHole 16ch (OBS picks BH16ch). Phase 11 calibration wizard will surface this.
MIC_DEVICE: str = "MacBook Pro Microphone"
