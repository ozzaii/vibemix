# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for `(model_id, ServiceTier | None)` per router path.

This is the ONLY file in `src/vibemix/` allowed to carry Gemini model
literals. The CI grep gate (`scripts/release/check_no_hardcoded_model.sh`)
allowlists this path; every other call site in `src/vibemix/` MUST go
through `vibemix.llm.model_router.resolve(path)`.

Future SKU bumps land here as a one-line edit. The `_ROUTES` table is the
foundation Plans 41-02..06 consume — keep it stable.

Tier dispatch follows CONTEXT.md (LAT-07):

- live_coach + live_coach_tts (+ fallback) → STANDARD (latency-critical)
- debrief / library / embedding           → FLEX     (cost lane)
- live_coach_tts_openrouter               → None     (non-Gemini API surface)
"""

from __future__ import annotations

from google.genai.types import ServiceTier

# (model_id, tier-or-None). The OpenRouter entry uses None as a sentinel —
# the OpenRouter API is consumed by the LiveKit OpenAI plugin, not by the
# Gemini SDK, so ServiceTier has no semantic meaning there.
_ROUTES: dict[str, tuple[str, ServiceTier | None]] = {
    "live_coach": ("gemini-3-flash-preview", ServiceTier.STANDARD),
    "live_coach_tts": ("gemini-3.1-flash-tts-preview", ServiceTier.STANDARD),
    "live_coach_tts_fallback": (
        "gemini-2.5-flash-preview-tts",
        ServiceTier.STANDARD,
    ),
    "live_coach_tts_openrouter": (
        "google/gemini-3.1-flash-tts-preview",
        None,
    ),
    "debrief": ("gemini-3-pro-preview", ServiceTier.FLEX),
    "debrief_tts": ("gemini-3-flash-tts-preview", ServiceTier.FLEX),
    "library_auto_tag": ("gemini-3-flash-preview", ServiceTier.FLEX),
    "embedding": ("gemini-embedding-2", ServiceTier.FLEX),
}
