# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for `(model_id, ServiceTier | None)` per router path.

This is the ONLY file in `src/vibemix/` allowed to carry Gemini model
literals. The CI grep gate (`scripts/release/check_no_hardcoded_model.sh`)
allowlists this path; every other call site in `src/vibemix/` MUST go
through `vibemix.llm.model_router.resolve(path)`.

Future SKU bumps land here as a one-line edit. The `_ROUTES` table is the
foundation Plans 41-02..06 consume — keep it stable.

Tier dispatch follows CONTEXT.md (LAT-07). The ``embedding`` route is retained
only for the legacy Gemini cache/migration helper in ``vibemix.library.embed``;
the product library embedder is local CLAP ONNX via ``embed_factory``.

- live_coach + live_coach_tts (+ fallback) → STANDARD (latency-critical)
- debrief / library auto-tag / embedding  → FLEX     (cost lane)
- live_coach_openrouter / *_tts_openrouter → None     (non-Gemini API surface)
"""

from __future__ import annotations

from typing import Literal

ServiceTierName = Literal["STANDARD", "FLEX"]

# (model_id, tier-or-None). The OpenRouter entry uses None as a sentinel —
# the OpenRouter API is consumed by the LiveKit OpenAI plugin, not by the
# Gemini SDK, so ServiceTier has no semantic meaning there.
_ROUTES: dict[str, tuple[str, ServiceTierName | None]] = {
    # Phase 80 / GROUND-02 — "live_coach" is the Phase-81 BENCH bench-swap
    # alias for the reaction model. Swap the winning model here (one-line edit,
    # no code change); it resolves at agent/config.py:25 via
    # resolve("live_coach") and flows to dj_cohost.py as model=LLM_MODEL.
    "live_coach": ("gemini-3.5-flash", "STANDARD"),
    "live_coach_openrouter": ("google/gemini-3.5-flash", None),
    "live_coach_tts": ("gemini-3.1-flash-tts-preview", "STANDARD"),
    "live_coach_tts_fallback": (
        "gemini-2.5-flash-preview-tts",
        "STANDARD",
    ),
    "live_coach_tts_openrouter": (
        "google/gemini-3.1-flash-tts-preview",
        None,
    ),
    "debrief": ("gemini-3.5-flash", "FLEX"),
    "debrief_tts": ("gemini-3-flash-tts-preview", "FLEX"),
    "library_auto_tag": ("gemini-3.5-flash", "FLEX"),
    # Legacy-only: migration/cache audit path for old Gemini embedding rows.
    # Normal library search/ingest/chat/build-set uses local CLAP ONNX/512.
    "embedding": ("gemini-embedding-2", "FLEX"),
}

# Plan 41-05 LAT-06 — GA-rename probe candidates for the embedding model.
# These literals live here (the only allowlisted file) so the GA-rename
# auto-bump can iterate them at runtime without tripping the grep gate.
# Order MUST be ``GA-renamed first, legacy second`` so we land on the
# canonical id as soon as the rename ships.
EMBEDDING_GA_CANDIDATES: tuple[str, ...] = (
    "gemini-embedding-002",
    "gemini-embedding-2",
)
